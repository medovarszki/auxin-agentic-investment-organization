import asyncio

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, ToolResultBlock, ToolUseBlock, UserMessage
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import BaseModel

from auxin_a2a import tracing
from auxin_runtime.runner import run_task

exporter = InMemorySpanExporter()
provider = TracerProvider(id_generator=tracing._FlowIdGenerator())
provider.add_span_processor(SimpleSpanProcessor(exporter))
trace.set_tracer_provider(provider)

TRACE_ID = "0af7651916cd43dd8448eb211c80319c"


class Out(BaseModel):
    answer: str


def test_root_span_takes_the_flow_trace_id_and_propagates_as_traceparent():
    exporter.clear()
    with tracing.span("a2a send", trace_id=TRACE_ID):
        carrier = tracing.traceparent()
    with tracing.span("a2a task", trace_id="f" * 32, parent=carrier[tracing.TRACEPARENT]):
        pass
    send, task = exporter.get_finished_spans()
    assert format(send.context.trace_id, "032x") == TRACE_ID
    assert task.context.trace_id == send.context.trace_id  # the parent wins over the trace_id argument
    assert task.parent.span_id == send.context.span_id


def test_invoke_agent_with_tool_spans_and_usage():
    exporter.clear()

    async def query_fn(prompt, options):
        yield AssistantMessage(content=[ToolUseBlock(id="t1", name="WebSearch", input={"query": "TSM"})], model="m")
        yield UserMessage(content=[ToolResultBlock(tool_use_id="t1", content="ok")])
        yield ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=2,
                            session_id="s", total_cost_usd=0.1, usage={"input_tokens": 10, "output_tokens": 5},
                            structured_output={"answer": "ok"})

    async def run():
        with tracing.span("a2a task", trace_id=TRACE_ID):
            return await run_task("research", "p", ClaudeAgentOptions(model="opus"), Out, query_fn=query_fn)

    asyncio.run(run())
    tool, agent, task = exporter.get_finished_spans()
    assert tool.name == "execute_tool WebSearch" and tool.parent.span_id == agent.context.span_id
    assert agent.name == "invoke_agent research" and agent.parent.span_id == task.context.span_id
    assert agent.attributes["gen_ai.usage.input_tokens"] == 10
    assert agent.attributes["gen_ai.request.model"] == "opus"
    assert agent.attributes["auxin.task.state"] == "COMPLETED"
