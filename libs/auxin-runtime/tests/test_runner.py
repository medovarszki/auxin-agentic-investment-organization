import asyncio
from datetime import timedelta

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage
from pydantic import BaseModel

from auxin_runtime.runner import run_task
from auxin_schemas.task import TaskState


class Out(BaseModel):
    answer: str


def result(**overrides) -> ResultMessage:
    data = dict(
        subtype="success", duration_ms=10, duration_api_ms=8, is_error=False, num_turns=3,
        session_id="s", total_cost_usd=0.42, usage={"input_tokens": 100}, structured_output={"answer": "ok"},
    )
    return ResultMessage(**(data | overrides))


def fake_query(*messages, delay: float = 0):
    async def query_fn(prompt, options):
        if delay:
            await asyncio.sleep(delay)
        for m in messages:
            yield m
    return query_fn


def run(query_fn, timeout=timedelta(minutes=10)):
    return asyncio.run(run_task("ms", "scan", ClaudeAgentOptions(), Out, timeout=timeout, query_fn=query_fn))


def test_completed_with_cost_and_validated_output():
    record = run(fake_query(result()))
    assert record.state is TaskState.COMPLETED
    assert record.output == {"answer": "ok"}
    assert record.cost_usd == 0.42 and record.num_turns == 3


def test_invalid_output_fails():
    record = run(fake_query(result(structured_output={"wrong": 1})))
    assert record.state is TaskState.FAILED
    assert "answer" in record.error


def test_sdk_error_fails():
    record = run(fake_query(result(is_error=True, subtype="error_max_budget_usd", structured_output=None)))
    assert record.state is TaskState.FAILED
    assert "error_max_budget_usd" in record.error


def test_timeout_fails_without_retry():
    record = run(fake_query(result(), delay=1), timeout=timedelta(milliseconds=50))
    assert record.state is TaskState.FAILED
    assert record.error.startswith("timeout")


def test_no_result_message_fails():
    record = run(fake_query())
    assert record.state is TaskState.FAILED
