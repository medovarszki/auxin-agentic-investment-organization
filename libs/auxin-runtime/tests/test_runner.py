import asyncio
from datetime import timedelta

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKError, ResultMessage
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


def test_sdk_exception_fails():
    async def query_fn(prompt, options):
        raise ClaudeSDKError("API Error: 400")
        yield

    record = run(query_fn)
    assert record.state is TaskState.FAILED
    assert "API Error: 400" in record.error


def test_timeout_fails_without_retry():
    record = run(fake_query(result(), delay=1), timeout=timedelta(milliseconds=50))
    assert record.state is TaskState.FAILED
    assert record.error.startswith("timeout")


def test_no_result_message_fails():
    record = run(fake_query())
    assert record.state is TaskState.FAILED


def test_activity_steps_are_recorded_in_order(monkeypatch):
    from claude_agent_sdk import AssistantMessage, TextBlock, ToolResultBlock, ToolUseBlock, UserMessage

    from auxin_runtime import runner

    written = []

    async def fake_record(steps):
        written.extend(steps)

    monkeypatch.setattr(runner, "record_activity", fake_record)
    messages = [
        AssistantMessage(content=[TextBlock(text="Checking prices."),
                                  ToolUseBlock(id="t1", name="WebSearch", input={"query": "MSFT Azure"})], model="m"),
        UserMessage(content=[ToolResultBlock(tool_use_id="t1", content="Azure +48%", is_error=False)]),
        result(),
    ]
    record = asyncio.run(run_task("research", "scan", ClaudeAgentOptions(model="opus"), Out, task_id="task-1",
                                  trace_id="a" * 32, query_fn=fake_query(*messages)))
    assert record.state is TaskState.COMPLETED
    steps = [(s.seq, s.kind.value, s.name, s.text) for s in sorted(written, key=lambda s: s.seq)]
    assert steps == [
        (0, "task_started", "opus", ""),
        (1, "text", None, "Checking prices."),
        (2, "tool_use", "WebSearch", "MSFT Azure"),
        (3, "tool_result", "WebSearch", "Azure +48%"),
        (4, "task_finished", "COMPLETED", '{"num_turns": 3, "tokens": {"input": 100, "output": 0, "cache_read": 0, '
                                          '"cache_creation": 0, "total": 100}, "error": null}'),
    ]
    assert {(s.task_id, s.trace_id, s.agent) for s in written} == {("task-1", "a" * 32, "research")}
