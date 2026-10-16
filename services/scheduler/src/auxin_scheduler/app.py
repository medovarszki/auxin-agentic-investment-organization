"""auxin-scheduler: timed A2A triggers on workdays (Europe/Budapest), deterministic, no LLM.

  serve            run the scheduler (the container's normal mode)
  run-job <job>    run one job now and print its result (scan | review | evaluate)

09:00 scan -> Market & Sentiment, 15:30 review -> Portfolio Manager, 21:00 evaluate: closed positions ->
decision_outcome (decision log) -> Research -> lesson. Monday to Friday, no exchange holiday calendar (6.5, 3.a);
one instance per job, a missed run is not made up.
"""
import argparse
import asyncio
import json
import logging
import sys
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from auxin_a2a.client import new_trace_id, send, task_summary
from auxin_schemas.knowledge import DecisionKind, DecisionRecord
from auxin_schemas.metadata import MessageType

from auxin_runtime.knowledge import record_decision
from auxin_scheduler.evaluator import new_outcomes, outcome_id

log = logging.getLogger("auxin.scheduler")

NAME = "scheduler"
TIMEZONE = "Europe/Budapest"
MISFIRE_GRACE_S = 300


async def _send(recipient: str, type: MessageType, subject: str, payload: dict, flow_id: str, trace_id: str) -> dict:
    return task_summary(await send(sender=NAME, recipient=recipient, type=type, subject=subject, payload=payload,
                                   task_id=flow_id, correlation_id=flow_id, trace_id=trace_id))


async def scan() -> dict:
    flow_id = str(uuid.uuid4())
    return await _send("market-sentiment", MessageType.SCAN_TRIGGER, "scan_trigger (scheduled)", {},
                       flow_id, new_trace_id())


async def review() -> dict:
    flow_id = str(uuid.uuid4())
    return await _send("portfolio-manager", MessageType.REVIEW_TRIGGER, "review_trigger (scheduled)", {},
                       flow_id, new_trace_id())


async def evaluate() -> dict:
    """Each new closed position: decision_outcome into the log, then to Research for a lesson, one after the other."""
    flow_id, trace_id = str(uuid.uuid4()), new_trace_id()
    results = []
    for outcome in await new_outcomes():
        await record_decision(DecisionRecord(
            id=outcome_id(outcome), kind=DecisionKind.DECISION_OUTCOME, agent=NAME,
            summary=f"{outcome.symbol} closed: {outcome.return_pct:+.2f}% ({outcome.realized_pnl:+.2f}) "
                    f"in {outcome.holding_days} days",
            conid=outcome.conid, symbol=outcome.symbol, decision_id=outcome.decision_id,
            payload=outcome.model_dump(mode="json"), correlation_id=flow_id, trace_id=trace_id, task_id=flow_id))
        task = await _send("research", MessageType.DECISION_OUTCOME,
                           f"Outcome: {outcome.symbol} {outcome.return_pct:+.2f}%", outcome.model_dump(mode="json"),
                           flow_id, trace_id)
        results.append({"symbol": outcome.symbol, "return_pct": outcome.return_pct, "research": task})
    return {"closed_positions": results}


JOBS = {
    "scan": (scan, {"hour": 9, "minute": 0}),
    "review": (review, {"hour": 15, "minute": 30}),
    "evaluate": (evaluate, {"hour": 21, "minute": 0}),
}


async def _logged(name: str) -> None:
    log.info(json.dumps({"event": "job_started", "job": name}))
    try:
        result = await JOBS[name][0]()
        log.info(json.dumps({"event": "job_finished", "job": name, "result": result}, default=str))
    except Exception as exc:  # a failed job is logged; the next run is the next scheduled time, no retry
        log.exception("job failed")
        log.info(json.dumps({"event": "job_failed", "job": name, "error": f"{type(exc).__name__}: {exc}"}))


async def _serve() -> None:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    for name, (_, at) in JOBS.items():
        scheduler.add_job(_logged, CronTrigger(day_of_week="mon-fri", timezone=TIMEZONE, **at), args=[name],
                          id=name, max_instances=1, coalesce=True, misfire_grace_time=MISFIRE_GRACE_S)
    scheduler.start()
    for job in scheduler.get_jobs():
        log.info(json.dumps({"event": "job_scheduled", "job": job.id, "next_run": job.next_run_time}, default=str))
    await asyncio.Event().wait()


def main() -> int:
    parser = argparse.ArgumentParser(prog="auxin-scheduler")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve", help="run the scheduler")
    run = sub.add_parser("run-job", help="run one job now")
    run.add_argument("job", choices=sorted(JOBS))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    if args.command == "serve":
        asyncio.run(_serve())
        return 0
    result = asyncio.run(JOBS[args.job][0]())
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0
