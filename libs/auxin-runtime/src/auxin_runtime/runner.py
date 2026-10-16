"""Runs one task: SUBMITTED -> WORKING -> COMPLETED | FAILED, with a hard timeout and no retry."""
import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from claude_agent_sdk import (
    AssistantMessage, ClaudeAgentOptions, ClaudeSDKError, ResultMessage, ToolResultBlock, ToolUseBlock, UserMessage,
    query,
)
from opentelemetry.trace import Span, Status, StatusCode
from pydantic import BaseModel, ValidationError

from auxin_a2a.tracing import span, tracer
from auxin_schemas.task import TASK_TIMEOUT, TaskState, transition

log = logging.getLogger("auxin.runtime")

QueryFn = Callable[..., AsyncIterator[Any]]


class TaskRecord(BaseModel):
    task_id: str
    agent: str
    state: TaskState
    started_at: datetime
    finished_at: datetime | None = None
    cost_usd: float | None = None
    num_turns: int | None = None
    usage: dict | None = None
    output: dict | None = None
    error: str | None = None


def _event(record: TaskRecord, event: str) -> None:
    log.info(json.dumps({"event": event, **record.model_dump(mode="json", exclude={"output"})}))


def _tool_spans(message, open_spans: dict[str, Span]) -> None:
    """One execute_tool span per tool call, from its tool_use to its tool_result (children of invoke_agent)."""
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, ToolUseBlock):
                open_spans[block.id] = tracer.start_span(f"execute_tool {block.name}", attributes={
                    "gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": block.name,
                    "gen_ai.tool.call.id": block.id,
                    "gen_ai.tool.call.arguments": json.dumps(block.input, ensure_ascii=False)[:1000]})
    elif isinstance(message, UserMessage) and isinstance(message.content, list):
        for block in message.content:
            if isinstance(block, ToolResultBlock) and (tool_span := open_spans.pop(block.tool_use_id, None)):
                if block.is_error:
                    tool_span.set_status(Status(StatusCode.ERROR))
                tool_span.end()


async def _result(prompt: str, options: ClaudeAgentOptions, query_fn: QueryFn) -> ResultMessage:
    result, open_spans = None, {}
    try:
        async for message in query_fn(prompt=prompt, options=options):
            _tool_spans(message, open_spans)
            if isinstance(message, ResultMessage):
                result = message
    finally:
        for tool_span in open_spans.values():  # no result: timeout, or the session ended mid-call
            tool_span.end()
    if result is None:
        raise RuntimeError("session ended without a result message")
    return result


def _usage_attributes(record: "TaskRecord") -> dict:
    usage = record.usage or {}
    return {k: v for k, v in {
        "gen_ai.usage.input_tokens": usage.get("input_tokens"),
        "gen_ai.usage.output_tokens": usage.get("output_tokens"),
        "gen_ai.usage.cache_read.input_tokens": usage.get("cache_read_input_tokens"),
        "gen_ai.usage.cache_creation.input_tokens": usage.get("cache_creation_input_tokens"),
        "auxin.num_turns": record.num_turns,
        "auxin.cost_usd": record.cost_usd,  # nominal on a subscription
        "auxin.task.state": record.state.name,
    }.items() if v is not None}


async def run_task(
    agent: str,
    prompt: str,
    options: ClaudeAgentOptions,
    output_model: type[BaseModel],
    timeout: timedelta = TASK_TIMEOUT,
    query_fn: QueryFn = query,
    task_id: str | None = None,
) -> TaskRecord:
    record = TaskRecord(
        task_id=task_id or str(uuid.uuid4()),
        agent=agent,
        state=TaskState.SUBMITTED,
        started_at=datetime.now(timezone.utc),
    )
    with span(f"invoke_agent {agent}", attributes={
        "gen_ai.operation.name": "invoke_agent", "gen_ai.provider.name": "anthropic", "gen_ai.agent.name": agent,
        "gen_ai.request.model": options.model, "a2a.task_id": record.task_id,
    }) as agent_span:
        _event(record, "task_submitted")
        record.state = transition(record.state, TaskState.WORKING)
        _event(record, "task_working")
        try:
            result = await asyncio.wait_for(
                _result(prompt, options, query_fn), timeout=timeout.total_seconds()
            )
            record.cost_usd = result.total_cost_usd
            record.num_turns = result.num_turns
            record.usage = result.usage
            if result.is_error:
                raise RuntimeError(f"{result.subtype}: {result.errors or result.result}")
            record.output = output_model.model_validate(result.structured_output).model_dump(mode="json")
            record.state = transition(record.state, TaskState.COMPLETED)
        except TimeoutError:
            record.error = f"timeout after {timeout}"
            record.state = transition(record.state, TaskState.FAILED)
        except (ValidationError, RuntimeError, ClaudeSDKError) as exc:
            record.error = str(exc)
            record.state = transition(record.state, TaskState.FAILED)
        agent_span.set_attributes(_usage_attributes(record))
        if record.error:
            agent_span.set_status(Status(StatusCode.ERROR, record.error[:200]))
    record.finished_at = datetime.now(timezone.utc)
    _event(record, "task_finished")
    return record
