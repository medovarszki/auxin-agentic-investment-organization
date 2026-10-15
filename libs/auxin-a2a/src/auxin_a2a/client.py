"""Send one message to another agent and follow its task over SSE until a final state."""
import json
import logging
import os
import uuid

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.helpers import new_data_part
from a2a.types import GetTaskRequest, Message, Role, SendMessageRequest, Task, TaskState
from google.protobuf.json_format import MessageToDict

from auxin_a2a.server import PORT
from auxin_schemas.metadata import EXTENSION_URI, MessageMetadata, MessageType
from auxin_schemas.task import TASK_TIMEOUT

log = logging.getLogger("auxin.a2a")

FINAL_STATES = {
    TaskState.TASK_STATE_COMPLETED,
    TaskState.TASK_STATE_FAILED,
    TaskState.TASK_STATE_REJECTED,
    TaskState.TASK_STATE_CANCELED,
}


def agent_url(agent: str) -> str:
    """AUXIN_A2A_<NAME>_URL, else the compose service name."""
    return os.environ.get(f"AUXIN_A2A_{agent.upper().replace('-', '_')}_URL", f"http://{agent}:{PORT}/")


def new_trace_id() -> str:
    return uuid.uuid4().hex


async def send(
    *,
    sender: str,
    recipient: str,
    type: MessageType,  # noqa: A002 - the metadata field's name
    subject: str,
    payload: dict,
    task_id: str,
    correlation_id: str,
    trace_id: str,
    reference_task_ids: list[str] | None = None,
) -> Task:
    """Returns the recipient's task in its final state (COMPLETED, REJECTED, FAILED or CANCELED).

    `task_id` is the sender's own task this message belongs to; the recipient opens a new one.
    """
    meta = MessageMetadata(
        sender=sender,
        recipient=recipient,
        subject=subject,
        type=type,
        task_id=task_id,
        correlation_id=correlation_id,
        trace_id=trace_id,
    )
    message = Message(
        message_id=str(meta.message_id),
        role=Role.ROLE_USER,
        parts=[new_data_part(payload, media_type="application/json")],
        metadata=meta.to_a2a_metadata(),
        extensions=[EXTENSION_URI],
        reference_task_ids=reference_task_ids or [],
    )
    # Internal traffic never goes through the egress proxy (trust_env=False ignores HTTPS_PROXY).
    timeout = httpx.Timeout(30.0, read=TASK_TIMEOUT.total_seconds() + 60)
    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as http:
        card = await A2ACardResolver(http, agent_url(recipient)).get_agent_card()
        client = ClientFactory(ClientConfig(streaming=True, httpx_client=http)).create(card)
        task_id_seen = None
        async for event in client.send_message(SendMessageRequest(message=message)):
            if event.HasField("task"):
                task_id_seen, state = event.task.id, event.task.status.state
            elif event.HasField("status_update"):
                task_id_seen, state = event.status_update.task_id, event.status_update.status.state
            else:
                continue
            log.info(json.dumps({
                "event": "a2a_status",
                "from": sender,
                "to": recipient,
                "type": type,
                "task_id": task_id_seen,
                "state": TaskState.Name(state),
            }))
        if task_id_seen is None:
            raise RuntimeError(f"{recipient} returned no task")
        # The final task, with its artifacts, as the recipient stored it.
        task = await client.get_task(GetTaskRequest(id=task_id_seen))
        await client.close()
    if task.status.state not in FINAL_STATES:
        raise RuntimeError(f"{recipient} task {task.id} ended in {TaskState.Name(task.status.state)}")
    return task


def task_summary(task: Task) -> dict:
    """The task as plain JSON: id, state, status message, artifact data."""
    data = MessageToDict(task, preserving_proto_field_name=True)
    return {
        "task_id": data.get("id"),
        "state": data.get("status", {}).get("state"),
        "status_message": [p.get("text") for p in data.get("status", {}).get("message", {}).get("parts", [])],
        "artifacts": [p.get("data") for a in data.get("artifacts", []) for p in a.get("parts", [])],
    }
