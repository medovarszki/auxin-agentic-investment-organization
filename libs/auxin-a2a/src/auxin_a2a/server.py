"""A thin A2A server per agent: Agent Card, JSON-RPC + SSE, tasks in the shared Postgres store.

The agent's logic is a `Handler`: it gets the validated metadata and the JSON payload of the
incoming message and returns the JSON result, which becomes the task's artifact.
"""
import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import uvicorn
from a2a.helpers import get_data_parts, new_data_part, new_task_from_user_message, new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentExtension, AgentInterface, AgentSkill
from google.protobuf.json_format import MessageToDict
from opentelemetry.trace import SpanKind, Status, StatusCode
from pydantic import ValidationError
from starlette.applications import Starlette

from auxin_a2a import tracing
from auxin_a2a.store import open_task_store
from auxin_schemas.metadata import EXTENSION_URI, MessageMetadata
from auxin_schemas.task import task_timeout

log = logging.getLogger("auxin.a2a")

PORT = 8000  # inside the container; AUXIN_A2A_PORT overrides it for local runs


@dataclass(frozen=True)
class Incoming:
    meta: MessageMetadata
    payload: dict
    task_id: str  # the A2A task this message started on the receiving agent


Handler = Callable[[Incoming], Awaitable[dict]]


class Rejected(Exception):
    """Content rejection (weak idea, broken rule, no price): the task ends REJECTED, not FAILED."""


def _event(event: str, **fields) -> None:
    log.info(json.dumps({"event": event, **fields}, default=str))


def agent_card(name: str, description: str, accepts: list[str], url: str) -> AgentCard:
    return AgentCard(
        name=name,
        description=description,
        version="0.1.0",
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        capabilities=AgentCapabilities(
            streaming=True,
            extensions=[
                AgentExtension(
                    uri=EXTENSION_URI,
                    required=True,
                    description="Auxin message metadata (sender, recipient, type, trace_id, …)",
                )
            ],
        ),
        supported_interfaces=[
            AgentInterface(protocol_binding="JSONRPC", url=url, protocol_version="1.0")
        ],
        skills=[
            AgentSkill(id=t, name=t, description=f"accepts `{t}` messages", tags=[t]) for t in accepts
        ],
    )


class AuxinExecutor(AgentExecutor):
    """Validates the metadata, runs the handler with its message type's timeout, records the result."""

    def __init__(self, agent: str, accepts: list[str], handler: Handler):
        self.agent = agent
        self.accepts = set(accepts)
        self.handler = handler

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        message = context.message
        meta, error = None, None
        raw_metadata = MessageToDict(message.metadata)
        try:
            meta = MessageMetadata.from_a2a_metadata(raw_metadata)
        except (ValueError, ValidationError) as exc:
            error = f"invalid Auxin metadata: {exc}"

        task = context.current_task
        if task is None:
            task = new_task_from_user_message(message)
            # Flat copy of the routing fields, so the shared table is easy to query.
            task.metadata.update({"agent": self.agent})
            if meta:
                task.metadata.update(meta.model_dump(
                    mode="json", include={"sender", "type", "subject", "correlation_id", "trace_id"}
                ))
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        if meta and (meta.recipient != self.agent or meta.type not in self.accepts):
            error = f"{self.agent} does not accept {meta.type}"
        if error:
            _event("task_rejected", agent=self.agent, task_id=task.id, error=error)
            await updater.reject(new_text_message(error))
            return

        log_fields = {
            "agent": self.agent,
            "task_id": task.id,
            "sender": meta.sender,
            "type": meta.type,
            "correlation_id": meta.correlation_id,
            "trace_id": meta.trace_id,
        }
        attributes = {"auxin.agent": self.agent, "auxin.sender": meta.sender, "auxin.message.type": meta.type.value,
                      "auxin.subject": meta.subject, "auxin.correlation_id": meta.correlation_id, "a2a.task_id": task.id}
        with tracing.span(f"a2a task {meta.type.value}", trace_id=meta.trace_id,
                          parent=raw_metadata.get(tracing.TRACEPARENT), kind=SpanKind.SERVER,
                          attributes=attributes) as span:
            state = await self._run(meta, message, task.id, updater, log_fields)
            span.set_attribute("auxin.task.state", state)
            if state == "FAILED":
                span.set_status(Status(StatusCode.ERROR))

    async def _run(self, meta: MessageMetadata, message, task_id: str, updater: TaskUpdater, log_fields: dict) -> str:
        """Runs the handler; returns the final state (COMPLETED, REJECTED, FAILED)."""
        _event("task_working", **log_fields)
        await updater.start_work()
        payloads = get_data_parts(message.parts)
        incoming = Incoming(meta=meta, payload=payloads[0] if payloads else {}, task_id=task_id)
        timeout = task_timeout(meta.type)
        try:
            result = await asyncio.wait_for(self.handler(incoming), timeout.total_seconds())
        except Rejected as exc:
            _event("task_rejected", **log_fields, error=str(exc))
            await updater.reject(new_text_message(str(exc)))
            return "REJECTED"
        except TimeoutError:
            _event("task_failed", **log_fields, error=f"timeout after {timeout}")
            await updater.failed(new_text_message(f"timeout after {timeout}"))
            return "FAILED"
        except Exception as exc:  # noqa: BLE001 - any handler error ends the task FAILED, no retry
            log.exception("handler failed")
            _event("task_failed", **log_fields, error=str(exc))
            await updater.failed(new_text_message(f"{type(exc).__name__}: {exc}"))
            return "FAILED"
        await updater.add_artifact([new_data_part(result, media_type="application/json")], name="result")
        await updater.complete()
        _event("task_completed", **log_fields)
        return "COMPLETED"

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancel is not supported")


async def _serve(agent: str, description: str, accepts: list[str], handler: Handler, url: str) -> None:
    card = agent_card(agent, description, accepts, url)
    store = await open_task_store(agent)
    request_handler = DefaultRequestHandler(
        agent_executor=AuxinExecutor(agent, accepts, handler),
        task_store=store,
        agent_card=card,
    )
    app = Starlette(routes=[*create_agent_card_routes(card), *create_jsonrpc_routes(request_handler, "/")])
    _event("server_started", agent=agent, url=url, accepts=accepts)
    port = int(os.environ.get("AUXIN_A2A_PORT", PORT))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")  # noqa: S104
    await uvicorn.Server(config).serve()


def serve(agent: str, description: str, accepts: list[str], handler: Handler, url: str | None = None) -> None:
    tracing.setup(agent)
    url = url or os.environ.get("AUXIN_A2A_PUBLIC_URL", f"http://{agent}:{PORT}/")
    asyncio.run(_serve(agent, description, accepts, handler, url))
