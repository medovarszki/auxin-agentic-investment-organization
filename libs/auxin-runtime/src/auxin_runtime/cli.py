"""auxin-agent:
  serve                    run this agent's A2A server (the container's normal mode)
  trigger --to <agent>     send one trigger message and print the final task as JSON
  run --trigger <name>     one-shot local run without A2A (phase 4)
"""
import argparse
import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path

from auxin_a2a import tracing
from auxin_a2a.client import new_trace_id, send, task_summary
from auxin_a2a.server import serve
from auxin_schemas.domain import MarketScanResult
from auxin_schemas.metadata import MessageType
from auxin_schemas.task import TaskState

from auxin_runtime.descriptor import build_options, load_descriptor, require_subscription_auth
from auxin_runtime.handlers import HANDLERS
from auxin_runtime.runner import run_task

# Output schema of each agent's one-shot run.
OUTPUTS = {"research": MarketScanResult}


def _run(agent_dir: Path, trigger: str) -> int:
    require_subscription_auth()
    desc = load_descriptor(agent_dir / "agent.yaml")
    output_model = OUTPUTS[desc.name]
    options = build_options(desc, agent_dir, output_model.model_json_schema())
    prompt = (agent_dir / "prompts" / f"{trigger}.md").read_text()
    record = asyncio.run(run_task(desc.name, prompt, options, output_model))
    print(record.model_dump_json(indent=2))
    return 0 if record.state is TaskState.COMPLETED else 1


def _serve(agent_dir: Path) -> int:
    desc = load_descriptor(agent_dir / "agent.yaml")
    handler = HANDLERS[desc.name](desc, agent_dir)
    serve(desc.name, desc.role, desc.messages.consumes, handler)
    return 0


def _trigger(recipient: str, message_type: str, payload: dict) -> int:
    tracing.setup("operator")
    flow_id = str(uuid.uuid4())
    task = asyncio.run(
        send(
            sender="operator",
            recipient=recipient,
            type=MessageType(message_type),
            subject=f"{message_type} (manual)",
            payload=payload,
            task_id=flow_id,
            correlation_id=flow_id,
            trace_id=new_trace_id(),
        )
    )
    summary = task_summary(task)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["state"] == "TASK_STATE_COMPLETED" else 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="auxin-agent")
    parser.add_argument("--agent-dir", type=Path, default=Path("/agent"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve", help="run the A2A server")
    trig = sub.add_parser("trigger", help="send one trigger message to an agent")
    trig.add_argument("--to", required=True, help="recipient agent, e.g. research")
    trig.add_argument("--type", default=MessageType.SCAN_TRIGGER.value)
    trig.add_argument("--payload", default="{}", help="JSON payload")
    run = sub.add_parser("run", help="run one task locally and exit")
    run.add_argument("--trigger", required=True, help="prompt file: <agent-dir>/prompts/<trigger>.md")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    if args.command == "serve":
        return _serve(args.agent_dir)
    if args.command == "trigger":
        return _trigger(args.to, args.type, json.loads(args.payload))
    return _run(args.agent_dir, args.trigger)


if __name__ == "__main__":
    sys.exit(main())
