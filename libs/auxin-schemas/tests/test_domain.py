from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
import yaml
from pydantic import ValidationError

from auxin_schemas.domain import Instrument, Order, Proposal, ReviewResult, Source, is_paper_account
from auxin_schemas.rules import check_entry

RULES = yaml.safe_load(
    (Path(__file__).resolve().parents[3] / "org/rules/portfolio-rules.yaml").read_text()
)
ASML = Instrument(conid=117902840, symbol="ASML", exchange="AEB", currency="EUR", asset_class="stock")
SOURCES = [
    Source(title=f"Source {i}", url=f"https://example.com/{i}", published_at=date(2026, 10, i + 1))
    for i in range(3)
]


def proposal(**overrides) -> Proposal:
    data = dict(
        idea_id=uuid4(),
        instrument=ASML,
        market_price=100.0,
        target_price=120.0,
        horizon_weeks=26,
        thesis="EUV demand outlasts the cycle",
        risks=["export controls", "cyclical demand", "valuation"],
        sources=SOURCES,
        conviction=4,
        invalidation="Order intake falls two quarters in a row",
    )
    return Proposal(**(data | overrides))


def test_instrument_must_be_unambiguous():
    with pytest.raises(ValidationError):
        Instrument(conid=0, symbol="ASML", exchange="AEB", currency="EUR", asset_class="stock")
    with pytest.raises(ValidationError):
        Instrument(conid=1, symbol="ASML", exchange="AEB", currency="eur", asset_class="stock")
    with pytest.raises(ValidationError):
        Instrument(conid=1, symbol="ASML", exchange="AEB", currency="EUR", asset_class="bond")


def test_upside_and_entry_rules_pass():
    p = proposal()
    assert p.upside_pct == pytest.approx(20.0)
    assert check_entry(p, RULES) == []


def test_upside_below_15_pct_is_a_violation():
    violations = check_entry(proposal(target_price=110.0), RULES)
    assert violations == ["upside 10.0% < 15.0%"]


def test_proposal_needs_three_risks_and_three_sources():
    with pytest.raises(ValidationError):
        proposal(risks=["one", "two"])
    with pytest.raises(ValidationError):
        proposal(sources=SOURCES[:2])


def test_order_is_market_and_uses_decision_id_as_client_order_id():
    decision = uuid4()
    order = Order(decision_id=decision, instrument=ASML, side="BUY", quantity=10)
    assert order.order_type == "MKT"
    assert order.client_order_id == str(decision)
    with pytest.raises(ValidationError):
        Order(decision_id=decision, instrument=ASML, side="SHORT", quantity=10)


def test_reduce_requires_target_weight():
    with pytest.raises(ValidationError, match="REDUCE requires"):
        ReviewResult(conid=1, recommendation="REDUCE", rationale="weaker outlook")
    assert ReviewResult(conid=1, recommendation="REDUCE", target_weight_pct=5, rationale="x")


def test_paper_account_check():
    assert is_paper_account("DU1234567")
    assert not is_paper_account("U1234567")


def test_market_scan_result_accepts_unresolved_instrument():
    from auxin_schemas.domain import Idea, InstrumentRef, MarketScanResult, MarketView

    result = MarketScanResult(
        market_view=MarketView(
            summary="Risk appetite returns as rates ease",
            sentiment="risk_on",
            dominant_narratives=["rate cuts", "AI capex"],
            sources=SOURCES[:1],
        ),
        ideas=[
            Idea(
                instrument=InstrumentRef(symbol="ASML", name="ASML Holding", asset_class="stock"),
                thesis="Lithography demand recovers",
                rationale="Order intake up",
                sources=SOURCES[:1],
            )
        ],
    )
    assert result.ideas[0].instrument.conid is None
    assert MarketScanResult.model_json_schema()["required"] == ["market_view", "ideas"]
