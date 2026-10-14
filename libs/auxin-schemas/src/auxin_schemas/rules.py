"""Deterministic entry checks from org/rules/portfolio-rules.yaml (the parts a single proposal can decide)."""
from auxin_schemas.domain import Proposal


def check_entry(proposal: Proposal, rules: dict) -> list[str]:
    """Returns the rule violations; an empty list means the proposal passes the entry checks."""
    violations = []
    min_upside = rules["entry"]["min_upside_pct"]
    if proposal.upside_pct < min_upside:
        violations.append(f"upside {proposal.upside_pct:.1f}% < {min_upside}%")
    if proposal.instrument.asset_class not in rules["universe"]["asset_classes"]:
        violations.append(f"asset class {proposal.instrument.asset_class} not allowed")
    return violations
