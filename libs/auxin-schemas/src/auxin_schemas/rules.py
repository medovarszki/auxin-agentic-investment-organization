"""Deterministic entry checks from org/rules/portfolio-rules.yaml (the parts a single proposal can decide)."""
from auxin_schemas.domain import Holding, Idea, Proposal, ReviewResult


def check_entry(proposal: Proposal, rules: dict) -> list[str]:
    """Returns the rule violations; an empty list means the proposal passes the entry checks."""
    violations = []
    min_upside = rules["entry"]["min_upside_pct"]
    if proposal.upside_pct < min_upside:
        violations.append(f"upside {proposal.upside_pct:.1f}% < {min_upside}%")
    if proposal.instrument.asset_class not in rules["universe"]["asset_classes"]:
        violations.append(f"asset class {proposal.instrument.asset_class} not allowed")
    return violations


class GateReject(Exception):
    """The deterministic PM gate rejected the order; `rule` names the broken rule."""

    def __init__(self, rule: str, reason: str):
        super().__init__(f"{rule}: {reason}")
        self.rule = rule
        self.reason = reason


def precheck_idea(idea: Idea, rules: dict, *, base_currency: str, held_conids: set[int]) -> None:
    """The PM's cheap pre-gate on a Research idea, before any LLM call: raises GateReject for an idea that cannot be
    bought anyway (asset class, base currency in the MVP, already held). An unresolved field is left to the PM."""
    inst = idea.instrument
    if inst.asset_class not in rules["universe"]["asset_classes"]:
        raise GateReject("asset_class", f"asset class {inst.asset_class} not allowed")
    if inst.currency and inst.currency != base_currency:
        raise GateReject("currency", f"{inst.currency} != base currency {base_currency} (no FX conversion in the MVP)")
    if inst.conid and inst.conid in held_conids:
        raise GateReject("already_held", f"{inst.symbol} is already in the portfolio")


# Conviction 1-5 -> target position size in % of NAV (decision 6.a).
CONVICTION_WEIGHT_PCT = {1: 2.0, 2: 4.0, 3: 6.0, 4: 8.0, 5: 10.0}


def size_buy(
    proposal: Proposal,
    rules: dict,
    *,
    nav: float,
    cash: float,
    base_currency: str,
    price: float,
    industry: str | None,
    holdings: list[dict],
    risk_bucket: int | None = None,
) -> tuple[int, dict]:
    """Quantity of a new BUY under the portfolio rules, and how it was computed.

    holdings: open positions as {conid, market_value, industry, asset_class, risk_bucket}; values in the base
    currency. risk_bucket: the PM's class for the new instrument (1-4); holdings without one are not counted.
    Raises GateReject when no order is allowed. MVP: only instruments in the account's base currency (no FX).
    """
    inst = proposal.instrument
    if inst.currency != base_currency:
        raise GateReject("currency", f"{inst.currency} != base currency {base_currency} (no FX conversion in the MVP)")
    if any(h["conid"] == inst.conid for h in holdings):
        raise GateReject("already_held", f"{inst.symbol} is already in the portfolio")
    upside = (proposal.target_price - price) / price * 100
    min_upside = rules["entry"]["min_upside_pct"]
    if upside < min_upside:
        raise GateReject("min_upside_pct", f"upside {upside:.1f}% at {price} < {min_upside}%")

    weight_pct = min(CONVICTION_WEIGHT_PCT[proposal.conviction], rules["position"]["max_new_position_weight_pct"])
    amount = nav * weight_pct / 100
    limits = {"conviction": amount, "cash": cash}
    sector_used = None
    # Sector limit: stocks only; every ETF is in the diversified bucket (decision 1.b).
    if inst.asset_class == "stock" and industry:
        sector_used = sum(h["market_value"] for h in holdings
                          if h.get("asset_class") == "stock" and h.get("industry") == industry)
        limits["sector"] = nav * rules["sector"]["max_sector_weight_pct"] / 100 - sector_used
    bucket_used = None
    # Risk bucket limit: stocks and ETFs alike, by the PM's classification.
    if risk_bucket is not None:
        bucket_used = sum(h["market_value"] for h in holdings if h.get("risk_bucket") == risk_bucket)
        limits["risk_bucket"] = nav * rules["risk_bucket"]["buckets"][risk_bucket]["max_weight_pct"] / 100 - bucket_used
    amount = min(limits.values())
    quantity = int(amount // price)
    details = {
        "price": price, "upside_pct": round(upside, 2), "conviction": proposal.conviction,
        "target_weight_pct": weight_pct, "nav": nav, "cash": cash, "industry": industry,
        "sector_value_before": sector_used, "risk_bucket": risk_bucket, "risk_bucket_value_before": bucket_used,
        "unclassified_holdings": [h["conid"] for h in holdings if h.get("risk_bucket") is None],
        "limits": {k: round(v, 2) for k, v in limits.items()},
        "binding_limit": min(limits, key=limits.get), "quantity": quantity,
        "order_value": round(quantity * price, 2),
    }
    if quantity < 1:
        raise GateReject(details["binding_limit"], f"no room for one share: {details['limits']}")
    return quantity, details


def size_sell(review: ReviewResult, holding: Holding, *, nav: float, price: float) -> tuple[int, dict]:
    """Quantity to sell after a review (decision 6.4, 4.a); 0 = no order.

    CLOSE: the whole position. REDUCE: floor((current weight - target weight) * NAV / price), at least 1 share,
    never more than held; a target weight not below the current one counts as HOLD.
    """
    held = int(holding.quantity)
    weight = holding.market_value / nav * 100
    details = {"recommendation": review.recommendation, "held": held, "price": price, "nav": nav,
               "weight_pct": round(weight, 2), "target_weight_pct": review.target_weight_pct}
    if review.recommendation == "CLOSE":
        quantity = held
    elif review.recommendation == "REDUCE" and review.target_weight_pct < weight:
        quantity = min(held, max(1, int((weight - review.target_weight_pct) / 100 * nav // price)))
    else:
        quantity = 0
        if review.recommendation == "REDUCE":
            details["note"] = "target weight not below the current weight: HOLD"
    details |= {"quantity": quantity, "order_value": round(quantity * price, 2)}
    return quantity, details
