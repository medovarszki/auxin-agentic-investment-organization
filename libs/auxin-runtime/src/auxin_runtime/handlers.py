"""What each agent does with an incoming A2A message. Result dict = the task's artifact."""
import logging
from pathlib import Path

from auxin_a2a.client import send, task_summary
from auxin_a2a.server import Handler, Incoming
from auxin_schemas.domain import Idea, MarketScanResult
from auxin_schemas.metadata import MessageType
from auxin_schemas.task import TaskState

from auxin_runtime.descriptor import AgentDescriptor, build_options
from auxin_runtime.runner import run_task

log = logging.getLogger("auxin.runtime")


def market_sentiment(desc: AgentDescriptor, agent_dir: Path) -> Handler:
    """scan_trigger: run the scan, then hand every idea to Research as its own task."""
    options = build_options(desc, agent_dir, MarketScanResult.model_json_schema())

    async def handle(msg: Incoming) -> dict:
        trigger = msg.payload.get("trigger", "scan")
        prompt = (agent_dir / "prompts" / f"{trigger}.md").read_text()
        record = await run_task(desc.name, prompt, options, MarketScanResult, task_id=msg.task_id)
        if record.state is not TaskState.COMPLETED:
            raise RuntimeError(record.error)
        scan = MarketScanResult.model_validate(record.output)

        handoffs = []
        for idea in scan.ideas:
            task = await send(
                sender=desc.name,
                recipient="research",
                type=MessageType.IDEA,
                subject=f"Idea: {idea.instrument.symbol}",
                payload=idea.model_dump(mode="json"),
                task_id=msg.task_id,
                correlation_id=msg.meta.correlation_id,
                trace_id=msg.meta.trace_id,
                reference_task_ids=[msg.task_id],
            )
            summary = task_summary(task)
            handoffs.append({"symbol": idea.instrument.symbol, **summary})
        return {
            "scan": record.output,
            "cost_usd": record.cost_usd,
            "num_turns": record.num_turns,
            "handoffs": handoffs,
        }

    return handle


def research_stub(desc: AgentDescriptor, agent_dir: Path) -> Handler:
    """Phase 5 stand-in: accepts and records the idea; the real Research logic comes in phase 6."""

    async def handle(msg: Incoming) -> dict:
        idea = Idea.model_validate(msg.payload)
        log.info("idea received: %s (%s)", idea.instrument.symbol, idea.thesis[:80])
        return {"idea_id": str(idea.idea_id), "symbol": idea.instrument.symbol, "status": "received"}

    return handle


HANDLERS = {
    "market-sentiment": market_sentiment,
    "research": research_stub,
}
