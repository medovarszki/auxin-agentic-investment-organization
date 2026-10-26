from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from auxin_schemas.metadata import EXTENSION_URI, MessageMetadata, MessageType, Priority

BASE = dict(
    sender="research",
    recipient="research",
    subject="Idea: ASML",
    type=MessageType.IDEA,
    task_id="t-1",
    correlation_id="c-1",
    trace_id="0af7651916cd43dd8448eb211c80319c",
)


def test_defaults_and_roundtrip_through_a2a_metadata():
    meta = MessageMetadata(**BASE)
    assert meta.priority is Priority.NORMAL
    assert meta.schema_version == "1"
    restored = MessageMetadata.from_a2a_metadata(meta.to_a2a_metadata())
    assert restored == meta


def test_missing_extension_is_rejected():
    with pytest.raises(ValueError, match="missing Auxin metadata"):
        MessageMetadata.from_a2a_metadata({"other": {}})


@pytest.mark.parametrize("field", ["sender", "recipient", "subject", "type", "task_id", "trace_id"])
def test_required_fields(field):
    data = {k: v for k, v in BASE.items() if k != field}
    with pytest.raises(ValidationError):
        MessageMetadata(**data)


def test_timestamp_must_be_utc():
    with pytest.raises(ValidationError, match="UTC"):
        MessageMetadata(**BASE, timestamp=datetime(2026, 10, 14, 12, 0))
    with pytest.raises(ValidationError, match="UTC"):
        MessageMetadata(**BASE, timestamp=datetime(2026, 10, 14, 12, 0, tzinfo=timezone(timedelta(hours=2))))


def test_bad_trace_id_and_unknown_field():
    with pytest.raises(ValidationError):
        MessageMetadata(**{**BASE, "trace_id": "not-a-trace"})
    with pytest.raises(ValidationError):
        MessageMetadata(**BASE, importance="high")
