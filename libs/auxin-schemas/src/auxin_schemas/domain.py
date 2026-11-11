"""Domain objects passed between agents as A2A artifacts."""
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Instrument(_Model):
    """Unambiguous instrument: IBKR conid + symbol + exchange + currency (+ ISIN if known)."""

    conid: int = Field(gt=0)
    symbol: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    asset_class: Literal["stock", "etf"]
    isin: str | None = Field(default=None, pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
    industry: str | None = None


class InstrumentRef(_Model):
    """Instrument as an idea names it, before it is resolved to an IBKR conid."""

    symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)
    asset_class: Literal["stock", "etf"]
    exchange: str | None = None
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    conid: int | None = Field(default=None, gt=0)


class Source(_Model):
    title: str = Field(min_length=1)
    url: HttpUrl
    published_at: date


class Revisit(_Model):
    """Re-proposing an instrument whose idea was rejected recently (in its cooldown, 2026-11-11): what changed since
    the rejection, with sources published after it. Without it, or without enough new sources, the runtime drops the
    idea before it reaches the Portfolio Manager (rules.check_revisit)."""

    rejected_idea_id: UUID  # the latest rejected idea of the instrument, as the scan prompt lists it
    what_changed: str = Field(min_length=1)  # how the change answers the rejection reason / reconsider_if
    sources: list[Source] = Field(min_length=1)  # dated after the rejection


class Idea(_Model):
    idea_id: UUID = Field(default_factory=uuid4)
    instrument: InstrumentRef
    thesis: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    sources: list[Source] = Field(min_length=1)
    revisit: Revisit | None = None
    created_at: datetime = Field(default_factory=_now)


class ManualIdea(Idea):
    """An idea entered by hand on the dashboard (2026-10-31). It goes to the Portfolio Manager exactly like a Research
    idea and gets the same challenge; only the evidence requirements differ: sources and the background are optional
    (the PM does its own research), and `origin` tells the two apart in the decision log."""

    origin: Literal["manual"] = "manual"
    rationale: str = ""
    sources: list[Source] = Field(default_factory=list)


def parse_idea(payload: dict) -> Idea:
    """The `idea` message body: a Research idea, or a manual one (`origin: manual`)."""
    return ManualIdea.model_validate(payload) if payload.get("origin") == "manual" else Idea.model_validate(payload)


class MarketView(_Model):
    summary: str = Field(min_length=1)
    sentiment: Literal["risk_on", "neutral", "risk_off"]
    dominant_narratives: list[str] = Field(min_length=1)
    key_indicators: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(min_length=1)


class MarketScanResult(_Model):
    """Output of one Market & Sentiment scan (the Research agent's scan function)."""

    market_view: MarketView
    ideas: list[Idea] = Field(max_length=3)  # decision 5.a


class ProposalBody(_Model):
    """What Research fills in (its structured output); the runtime adds the ids."""

    instrument: Instrument
    market_price: float = Field(gt=0)
    target_price: float = Field(gt=0)
    horizon_weeks: int = Field(ge=2, le=60)
    thesis: str = Field(min_length=1)
    risks: list[str] = Field(min_length=3)
    sources: list[Source] = Field(min_length=3)
    conviction: int = Field(ge=1, le=5)
    invalidation: str = Field(min_length=1)

    @property
    def upside_pct(self) -> float:
        return (self.target_price - self.market_price) / self.market_price * 100


class Proposal(ProposalBody):
    proposal_id: UUID = Field(default_factory=uuid4)
    idea_id: UUID
    action: Literal["BUY"] = "BUY"
    created_at: datetime = Field(default_factory=_now)


class IdeaReject(_Model):
    idea_id: UUID
    reason: str = Field(min_length=1)


class PMDecision(_Model):
    """The Portfolio Manager's judgement on a Research idea (2026-10-26: the PM challenges the ideas): REJECT, or BUY
    with the proposal it built (target price, horizon, risks, sources, conviction). Sizing and rule checks are the
    runtime's."""

    decision: Literal["BUY", "REJECT"]
    rationale: str = Field(min_length=1)  # the rejection reason, or the case for the BUY
    # Company risk class (skill risk-bucket, portfolio-rules.yaml risk_bucket): 1 = stable ... 4 = speculative
    risk_bucket: Literal[1, 2, 3, 4]
    proposal: ProposalBody | None = None
    # REJECT only (2026-11-11): `thesis` = a judgement on the case, the valuation or the portfolio fit (starts the
    # instrument's cooldown); `data` = only missing / unreliable data, e.g. no live IBKR price (no cooldown).
    reject_basis: Literal["thesis", "data"] | None = None
    reconsider_if: str | None = None  # REJECT: what would change the decision; Research must answer it to re-propose

    @model_validator(mode="after")
    def _buy_needs_proposal(self) -> "PMDecision":
        if self.decision == "BUY" and self.proposal is None:
            raise ValueError("decision 'BUY' requires a proposal")
        return self


class ProposalReject(_Model):
    proposal_id: UUID
    reason: str = Field(min_length=1)
    rule: str | None = None  # the broken portfolio rule, when the deterministic gate rejected it


class Order(_Model):
    order_id: UUID = Field(default_factory=uuid4)
    decision_id: UUID  # idempotency key -> ibkrfacade client_order_id
    instrument: Instrument
    side: Literal["BUY", "SELL"]
    quantity: float = Field(gt=0)
    order_type: Literal["MKT"] = "MKT"
    created_at: datetime = Field(default_factory=_now)

    @property
    def client_order_id(self) -> str:
        return str(self.decision_id)


class Fill(_Model):
    order_id: UUID
    ibkr_order_id: int
    filled_quantity: float = Field(gt=0)
    avg_price: float = Field(gt=0)
    commission: float = Field(ge=0)
    filled_at: datetime


class OrderRejectReason(StrEnum):
    NO_PRICE = "NO_PRICE"
    MISMATCH = "MISMATCH"
    NOT_PAPER_ACCOUNT = "NOT_PAPER_ACCOUNT"
    BROKER_ERROR = "BROKER_ERROR"
    CANCELLED = "CANCELLED"  # the DAY order expired or was cancelled unfilled


class OrderReject(_Model):
    order_id: UUID
    reason: OrderRejectReason
    detail: str = ""


class Holding(_Model):
    """An open position as the daily review sees it (values in the base currency)."""

    instrument: Instrument
    quantity: float = Field(gt=0)
    avg_cost: float = Field(ge=0)
    market_price: float = Field(gt=0)
    market_value: float
    weight_pct: float  # market_value / NAV * 100
    unrealized_pnl: float | None = None


class ReviewRequest(_Model):
    """PM -> Research: re-evaluate one open position; `entry` is the decision-log story of the buy, if any."""

    holding: Holding
    entry: dict | None = None  # the BUY proposal (thesis, target, horizon, risks, invalidation) and its order


class ReviewResult(_Model):
    conid: int = Field(gt=0)
    recommendation: Literal["HOLD", "REDUCE", "CLOSE"]
    target_weight_pct: float | None = Field(default=None, ge=0, le=100)
    rationale: str = Field(min_length=1)
    sources: list[Source] = Field(default_factory=list)

    @model_validator(mode="after")
    def _reduce_needs_target(self) -> "ReviewResult":
        if self.recommendation == "REDUCE" and self.target_weight_pct is None:
            raise ValueError("REDUCE requires target_weight_pct")
        return self


class DecisionOutcome(_Model):
    """A closed position (sells added up to the bought quantity), computed from the fills in the decision log.
    No benchmark (decision 2026-10-15); return_pct = realized_pnl / cost * 100, commissions included."""

    decision_id: UUID  # the PM decision of the closing SELL
    conid: int = Field(gt=0)
    symbol: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    cost: float = Field(gt=0)
    proceeds: float = Field(ge=0)
    commission: float = Field(ge=0)
    realized_pnl: float
    return_pct: float
    opened_at: datetime
    closed_at: datetime
    holding_days: int = Field(ge=0)
    evaluated_at: datetime = Field(default_factory=_now)


class LessonDraft(_Model):
    """Research's structured output for a decision_outcome; the runtime writes it to the lessons table."""

    lesson: str = Field(min_length=1)


def is_paper_account(account_id: str) -> bool:
    """IBKR paper trading account IDs start with 'DU'."""
    return account_id.startswith("DU")
