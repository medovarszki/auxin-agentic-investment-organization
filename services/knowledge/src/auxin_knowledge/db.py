"""Knowledge base tables. The models are the schema's source: `make db-revision` generates the Alembic
migration from them, the service applies it on start.

Full-text search: every table has a generated `search` tsvector column with a GIN index (English stemming).
"""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Computed, DateTime, Float, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from auxin_a2a.store import database_url


class Base(DeclarativeBase):
    pass


def _tsvector(*columns: str) -> Computed:
    text = " || ' ' || ".join(f"coalesce({c}, '')" for c in columns)
    return Computed(f"to_tsvector('english', {text})", persisted=True)


class Decision(Base):
    """Decision log: ideas, rejections, proposals, orders, fills, reviews (one row per event)."""

    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, index=True)
    agent: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    conid: Mapped[int | None] = mapped_column(BigInteger, index=True)
    symbol: Mapped[str | None] = mapped_column(Text)
    idea_id: Mapped[uuid.UUID | None] = mapped_column(UUID, index=True)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(UUID, index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    snapshot: Mapped[dict | None] = mapped_column(JSONB)
    correlation_id: Mapped[str | None] = mapped_column(Text)
    trace_id: Mapped[str | None] = mapped_column(Text)
    task_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    search: Mapped[str] = mapped_column(TSVECTOR, _tsvector("symbol", "summary"))

    __table_args__ = (Index("ix_decisions_search", "search", postgresql_using="gin"),)


class CompanyNoteRow(Base):
    """What Research learned about a company (company memory)."""

    __tablename__ = "company_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    conid: Mapped[int] = mapped_column(BigInteger, index=True)
    symbol: Mapped[str] = mapped_column(Text)
    agent: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSONB)
    task_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    search: Mapped[str] = mapped_column(TSVECTOR, _tsvector("symbol", "note"))

    __table_args__ = (Index("ix_company_notes_search", "search", postgresql_using="gin"),)


class LessonRow(Base):
    """Lessons from closed positions (feedback loop)."""

    __tablename__ = "lessons"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    agent: Mapped[str] = mapped_column(Text)
    lesson: Mapped[str] = mapped_column(Text)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(UUID, index=True)
    conid: Mapped[int | None] = mapped_column(BigInteger, index=True)
    symbol: Mapped[str | None] = mapped_column(Text)
    return_pct: Mapped[float | None] = mapped_column(Float)
    task_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    search: Mapped[str] = mapped_column(TSVECTOR, _tsvector("symbol", "lesson"))

    __table_args__ = (Index("ix_lessons_search", "search", postgresql_using="gin"),)


def make_engine() -> AsyncEngine:
    return create_async_engine(database_url(), pool_pre_ping=True)
