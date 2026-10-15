"""Runs one task: SUBMITTED -> WORKING -> COMPLETED | FAILED, with a hard timeout and no retry."""
import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKError, ResultMessage, query
from pydantic import BaseModel, ValidationError

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


async def _result(prompt: str, options: ClaudeAgentOptions, query_fn: QueryFn) -> ResultMessage:
    result = None
    async for message in query_fn(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result = message
    if result is None:
        raise RuntimeError("session ended without a result message")
    return result


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
    record.finished_at = datetime.now(timezone.utc)
    _event(record, "task_finished")
    return record
