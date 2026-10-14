"""`auxin-agent run --trigger <name>`: one task, result as JSON on stdout, exit 1 unless COMPLETED."""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

from auxin_runtime.descriptor import build_options, load_descriptor
from auxin_runtime.runner import run_task
from auxin_schemas.domain import MarketScanResult
from auxin_schemas.task import TaskState

# Output schema of each agent's task, until the A2A layer (phase 5) carries typed artifacts.
OUTPUTS = {"market-sentiment": MarketScanResult}


def main() -> int:
    parser = argparse.ArgumentParser(prog="auxin-agent")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run one task and exit")
    run.add_argument("--agent-dir", type=Path, default=Path("/agent"))
    run.add_argument("--trigger", required=True, help="prompt file: <agent-dir>/prompts/<trigger>.md")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    desc = load_descriptor(args.agent_dir / "agent.yaml")
    output_model = OUTPUTS[desc.name]
    options = build_options(desc, args.agent_dir, output_model.model_json_schema())
    prompt = (args.agent_dir / "prompts" / f"{args.trigger}.md").read_text()
    record = asyncio.run(run_task(desc.name, prompt, options, output_model))
    print(record.model_dump_json(indent=2))
    return 0 if record.state is TaskState.COMPLETED else 1


if __name__ == "__main__":
    sys.exit(main())
