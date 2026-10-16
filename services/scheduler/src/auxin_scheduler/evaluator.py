"""Decision evaluator (deterministic): closed positions from the fills in the decision log -> DecisionOutcome.

A position is closed when its SELL fills add up to the bought quantity (decision 6.5, 2.a); a partial REDUCE is
evaluated only with the final close. No benchmark. Return = (proceeds - cost - commissions) / cost.
"""
import uuid
from datetime import datetime

from auxin_schemas.domain import DecisionOutcome
from auxin_schemas.knowledge import DecisionKind

from auxin_runtime.knowledge import get_decisions

LOOKBACK_DAYS = 400
EPSILON = 1e-9


def outcome_id(outcome: DecisionOutcome) -> uuid.UUID:
    return uuid.uuid5(outcome.decision_id, DecisionKind.DECISION_OUTCOME.value)


def closed_positions(fills: list[dict]) -> list[DecisionOutcome]:
    """fills: decision-log rows of kind fill (with payload), any order. One outcome per open -> flat cycle."""
    outcomes: list[DecisionOutcome] = []
    by_conid: dict[int, list[dict]] = {}
    for row in sorted(fills, key=lambda r: r["payload"]["filled_at"]):
        by_conid.setdefault(row["conid"], []).append(row)
    for conid, rows in by_conid.items():
        held = cost = proceeds = commission = bought = 0.0
        opened_at = None
        for row in rows:
            fill = row["payload"]
            side = fill.get("ibkr", {}).get("action")
            qty, value = float(fill["filled_quantity"]), float(fill["filled_quantity"]) * float(fill["avg_price"])
            commission += float(fill.get("commission") or 0)
            if side == "BUY":
                opened_at = opened_at or fill["filled_at"]
                held, cost, bought = held + qty, cost + value, bought + qty
            elif side == "SELL":
                held, proceeds = held - qty, proceeds + value
            if side == "SELL" and held <= EPSILON and cost > 0:
                pnl = proceeds - cost - commission
                opened, closed = datetime.fromisoformat(opened_at), datetime.fromisoformat(fill["filled_at"])
                outcomes.append(DecisionOutcome(
                    decision_id=row["decision_id"], conid=conid, symbol=row["symbol"], quantity=bought,
                    cost=round(cost, 2), proceeds=round(proceeds, 2), commission=round(commission, 4),
                    realized_pnl=round(pnl, 2), return_pct=round(pnl / cost * 100, 2),
                    opened_at=opened, closed_at=closed, holding_days=(closed - opened).days))
                held = cost = proceeds = commission = bought = 0.0
                opened_at = None
    return outcomes


async def new_outcomes() -> list[DecisionOutcome]:
    """Closed positions that have no decision_outcome in the log yet."""
    rows = await get_decisions(kind=[DecisionKind.FILL.value, DecisionKind.DECISION_OUTCOME.value],
                               days=LOOKBACK_DAYS, limit=500)  # the REST maximum; enough for the MVP
    done = {r["id"] for r in rows if r["kind"] == DecisionKind.DECISION_OUTCOME.value}
    fills = [r for r in rows if r["kind"] == DecisionKind.FILL.value]
    return [o for o in closed_positions(fills) if str(outcome_id(o)) not in done]
