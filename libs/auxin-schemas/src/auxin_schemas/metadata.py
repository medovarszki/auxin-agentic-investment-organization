"""Mandatory metadata carried in every A2A Message under an Auxin extension."""
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

EXTENSION_URI = "https://auxin.local/a2a/ext/message-metadata/v1"
SCHEMA_VERSION = "1"


class MessageType(StrEnum):
    SCAN_TRIGGER = "scan_trigger"
    REVIEW_TRIGGER = "review_trigger"
    MARKET_VIEW = "market_view"
    IDEA = "idea"
    IDEA_REJECT = "idea_reject"
    PROPOSAL = "proposal"
    PROPOSAL_REJECT = "proposal_reject"
    VERIFY_REQUEST = "verify_request"
    VERIFY_RESULT = "verify_result"
    ORDER = "order"
    ORDER_REJECT = "order_reject"
    FILL = "fill"
    REVIEW_REQUEST = "review_request"
    REVIEW_RESULT = "review_result"
    DECISION_OUTCOME = "decision_outcome"
    LESSON = "lesson"


class Priority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    message_id: UUID = Field(default_factory=uuid4)
    sender: str = Field(min_length=1)
    recipient: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    type: MessageType
    priority: Priority = Priority.NORMAL
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    task_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    trace_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    reply_to: UUID | None = None
    schema_version: str = SCHEMA_VERSION
    ttl_seconds: int | None = Field(default=None, gt=0)

    @field_validator("timestamp")
    @classmethod
    def _must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError("timestamp must be timezone-aware UTC")
        return value

    def to_a2a_metadata(self) -> dict:
        """The value to put into an A2A Message's `metadata` field."""
        return {EXTENSION_URI: self.model_dump(mode="json")}

    @classmethod
    def from_a2a_metadata(cls, metadata: dict | None) -> "MessageMetadata":
        if not metadata or EXTENSION_URI not in metadata:
            raise ValueError(f"missing Auxin metadata extension {EXTENSION_URI}")
        return cls.model_validate(metadata[EXTENSION_URI])
