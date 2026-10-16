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


class Idea(_Model):
    idea_id: UUID = Field(default_factory=uuid4)
    instrument: InstrumentRef
    thesis: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    sources: list[Source] = Field(min_length=1)
    created_at: datetime = Field(default_factory=_now)


class MarketView(_Model):
    summary: str = Field(min_length=1)
    sentiment: Literal["risk_on", "neutral", "risk_off"]
    dominant_narratives: list[str] = Field(min_length=1)
    key_indicators: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(min_length=1)


class MarketScanResult(_Model):
    """Output of one Market & Sentiment scan."""

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


class ResearchOutput(_Model):
    """Research's verdict on an idea: a proposal, or a rejection with the reason."""

    verdict: Literal["propose", "reject"]
    reason: str = Field(min_length=1)  # the rejection reason, or the one-paragraph case for the proposal
    proposal: ProposalBody | None = None

    @model_validator(mode="after")
    def _propose_needs_proposal(self) -> "ResearchOutput":
        if self.verdict == "propose" and self.proposal is None:
            raise ValueError("verdict 'propose' requires a proposal")
        return self


class IdeaReject(_Model):
    idea_id: UUID
    reason: str = Field(min_length=1)


class PMDecision(_Model):
    """The Portfolio Manager's investment judgement on a proposal; sizing and rule checks are the runtime's."""

    decision: Literal["BUY", "REJECT"]
    rationale: str = Field(min_length=1)


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
    decision_id: UUID
    evaluated_at: datetime
    realized_pnl: float
    unrealized_pnl: float
    return_pct: float
    benchmark_return_pct: float
    target_reached: bool
    horizon_elapsed: bool


def is_paper_account(account_id: str) -> bool:
    """IBKR paper trading account IDs start with 'DU'."""
    return account_id.startswith("DU")
