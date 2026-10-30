"""Knowledge base records: what the runtime and the services write through the knowledge REST API.

The LLM agents never write these; they read them through the knowledge MCP tools.
"""
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DecisionKind(StrEnum):
    IDEA = "idea"
    IDEA_REJECT = "idea_reject"
    PROPOSAL = "proposal"
    PROPOSAL_REJECT = "proposal_reject"
    ORDER = "order"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_REJECT = "order_reject"
    FILL = "fill"
    REVIEW = "review"
    DECISION_OUTCOME = "decision_outcome"


REJECTION_KINDS = (DecisionKind.IDEA_REJECT, DecisionKind.PROPOSAL_REJECT)


class DecisionRecord(_Model):
    """One entry of the decision log. `id` is the domain object's id (idea_id, proposal_id, order_id…),
    so writing the same record twice is a no-op."""

    id: UUID = Field(default_factory=uuid4)
    kind: DecisionKind
    agent: str = Field(min_length=1)  # who made the decision
    summary: str = Field(min_length=1)  # thesis or reason, in one or two sentences; full-text indexed
    conid: int | None = Field(default=None, gt=0)
    symbol: str | None = None
    idea_id: UUID | None = None  # the idea the chain started from
    decision_id: UUID | None = None  # the PM decision behind an order, fill or order reject
    payload: dict[str, Any] = Field(default_factory=dict)  # the full message (idea, proposal, order…)
    snapshot: dict[str, Any] | None = None  # account and positions at decision time (NAV, cash, …)
    correlation_id: str | None = None
    trace_id: str | None = None
    task_id: str | None = None


class CompanyNote(_Model):
    id: UUID = Field(default_factory=uuid4)
    conid: int = Field(gt=0)
    symbol: str = Field(min_length=1)
    agent: str = Field(min_length=1)
    note: str = Field(min_length=1)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    task_id: str | None = None


class Lesson(_Model):
    id: UUID = Field(default_factory=uuid4)
    agent: str = Field(min_length=1)
    lesson: str = Field(min_length=1)
    decision_id: UUID | None = None
    conid: int | None = Field(default=None, gt=0)
    symbol: str | None = None
    return_pct: float | None = None
    task_id: str | None = None


class ActivityKind(StrEnum):
    TASK_STARTED = "task_started"
    TEXT = "text"
    THINKING = "thinking"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    TASK_FINISHED = "task_finished"


class Activity(_Model):
    """One step of an LLM task as it happens (tool call, its result, the model's text), for live following.
    Not part of the decision log: an operational trace, written best-effort by the runtime."""

    id: UUID = Field(default_factory=uuid4)
    agent: str = Field(min_length=1)
    task_id: str | None = None
    trace_id: str | None = None
    seq: int = Field(ge=0)  # order within the task
    kind: ActivityKind
    name: str | None = None  # the tool's name for tool_use / tool_result
    text: str = ""  # truncated
    is_error: bool = False


class Written(_Model):
    id: UUID
    created: bool  # False: the record already existed (idempotent write)
