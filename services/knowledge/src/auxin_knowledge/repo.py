"""Reads and idempotent writes over the knowledge base tables."""
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from auxin_knowledge.db import CompanyNoteRow, Decision, LessonRow
from auxin_schemas.knowledge import REJECTION_KINDS, Written

# Columns returned to readers; payload / snapshot / trace context only where the detail is asked for.
DECISION_COLUMNS = ("id", "created_at", "kind", "agent", "conid", "symbol", "summary", "idea_id", "decision_id")


def _row(row: Any) -> dict:
    out = {}
    for key, value in row._mapping.items():
        if value is None:
            continue
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, UUID):
            value = str(value)
        out[key] = value
    return out


async def write(engine: AsyncEngine, table: type, record: BaseModel) -> Written:
    """Insert; the same id twice is a no-op (created=False), so retries never duplicate a record."""
    stmt = (
        insert(table)
        .values(**record.model_dump(mode="json"))
        .on_conflict_do_nothing(index_elements=["id"])
        .returning(table.id)
    )
    async with engine.begin() as conn:
        inserted = (await conn.execute(stmt)).scalar_one_or_none()
    return Written(id=record.id, created=inserted is not None)


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


async def decisions(
    engine: AsyncEngine,
    *,
    conid: int | None = None,
    kinds: tuple[str, ...] | None = None,
    days: int | None = None,
    limit: int = 50,
    with_payload: bool = False,
) -> list[dict]:
    columns = [getattr(Decision, c) for c in DECISION_COLUMNS]
    if with_payload:
        columns += [Decision.payload, Decision.snapshot, Decision.correlation_id, Decision.trace_id, Decision.task_id]
    stmt = select(*columns).order_by(Decision.created_at.desc()).limit(limit)
    if conid is not None:
        stmt = stmt.where(Decision.conid == conid)
    if kinds:
        stmt = stmt.where(Decision.kind.in_(kinds))
    if days is not None:
        stmt = stmt.where(Decision.created_at >= _since(days))
    async with engine.connect() as conn:
        return [_row(r) for r in await conn.execute(stmt)]


async def rejections(engine: AsyncEngine, days: int = 30) -> list[dict]:
    return await decisions(engine, kinds=tuple(k.value for k in REJECTION_KINDS), days=days, limit=200)


async def search(engine: AsyncEngine, query: str, limit: int = 10) -> list[dict]:
    """Full-text search (English stemming, web-search syntax: words, "phrases", -exclude, or) over the
    decision log, company notes and lessons; best matches first."""
    tsquery = func.websearch_to_tsquery("english", query)
    sources = [
        (Decision, "decision", Decision.summary, [Decision.kind, Decision.agent]),
        (CompanyNoteRow, "company_note", CompanyNoteRow.note, [CompanyNoteRow.agent]),
        (LessonRow, "lesson", LessonRow.lesson, [LessonRow.agent, LessonRow.return_pct]),
    ]
    results: list[dict] = []
    async with engine.connect() as conn:
        for table, label, text, extra in sources:
            rank = func.ts_rank(table.search, tsquery).label("rank")
            stmt = (
                select(table.id, table.created_at, table.conid, table.symbol, text.label("text"), *extra, rank)
                .where(table.search.op("@@")(tsquery))
                .order_by(rank.desc())
                .limit(limit)
            )
            results += [{"source": label, **_row(r)} for r in await conn.execute(stmt)]
    results.sort(key=lambda r: r["rank"], reverse=True)
    return results[:limit]


async def company_history(engine: AsyncEngine, conid: int) -> dict:
    """Everything recorded about one instrument: decisions, company notes, lessons (newest first)."""
    async with engine.connect() as conn:
        notes = await conn.execute(
            select(CompanyNoteRow.created_at, CompanyNoteRow.agent, CompanyNoteRow.note, CompanyNoteRow.sources)
            .where(CompanyNoteRow.conid == conid)
            .order_by(CompanyNoteRow.created_at.desc())
            .limit(20)
        )
        lessons = await conn.execute(
            select(LessonRow.created_at, LessonRow.lesson, LessonRow.return_pct, LessonRow.decision_id)
            .where(LessonRow.conid == conid)
            .order_by(LessonRow.created_at.desc())
            .limit(20)
        )
        notes, lessons = [_row(r) for r in notes], [_row(r) for r in lessons]
    return {
        "conid": conid,
        "decisions": await decisions(engine, conid=conid, limit=30),
        "company_notes": notes,
        "lessons": lessons,
    }
