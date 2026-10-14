"""Validates org/org.yaml and agents/*/agent.yaml.

Checks: every agent.yaml matches org/schema/agent.schema.json; the agents in
org.yaml and under agents/ are the same set; every consumed message type has a
producer (an agent, or a known external source).
"""
import json
import sys
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
# Message types produced outside the agents (services).
EXTERNAL_PRODUCERS = {
    "scan_trigger": "scheduler",
    "review_trigger": "scheduler",
    "decision_outcome": "decision-evaluator",
}


def main() -> int:
    errors: list[str] = []
    schema = json.loads((ROOT / "org/schema/agent.schema.json").read_text())
    org = yaml.safe_load((ROOT / "org/org.yaml").read_text())

    descriptors = {}
    for path in sorted(ROOT.glob("agents/*/agent.yaml")):
        data = yaml.safe_load(path.read_text())
        for err in jsonschema.Draft202012Validator(schema).iter_errors(data):
            errors.append(f"{path.relative_to(ROOT)}: {err.message}")
        if data.get("name") != path.parent.name:
            errors.append(f"{path.relative_to(ROOT)}: name != directory name")
        descriptors[path.parent.name] = data

    in_org = {
        Path(p["agent"]).name
        for unit in org["units"]
        for p in unit["positions"]
    }
    if in_org != set(descriptors):
        errors.append(f"org.yaml agents {sorted(in_org)} != agents/ {sorted(descriptors)}")

    produced = set(EXTERNAL_PRODUCERS)
    for d in descriptors.values():
        produced |= set(d["messages"]["produces"])
    for name, d in descriptors.items():
        for msg in d["messages"]["consumes"]:
            if msg not in produced:
                errors.append(f"{name}: consumes '{msg}' but nothing produces it")

    for e in errors:
        print(f"ERROR {e}")
    print(f"{len(descriptors)} agents checked, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
