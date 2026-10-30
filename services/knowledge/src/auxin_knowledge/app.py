"""Knowledge service: the only writer of the knowledge base.

- REST (FastAPI) for the deterministic writers and checks: the agent runtime, Execution, the evaluator.
- MCP (streamable HTTP, /mcp) with read-only tools for the LLM agents; they never write.
- On start it applies the Alembic migrations (upgrade head).
No auth for now (Mihály): reachable only on the internal agents network.
"""
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Query
from mcp.server import MCPServer

from auxin_knowledge import repo
from auxin_knowledge.db import ActivityRow, CompanyNoteRow, Decision, LessonRow, make_engine
from auxin_schemas.knowledge import Activity, CompanyNote, DecisionKind, DecisionRecord, Lesson, Written

log = logging.getLogger("auxin.knowledge")
MIGRATIONS = Path(__file__).parent / "migrations" / "alembic.ini"

engine = make_engine()

# --- MCP: read-only tools for the agents -------------------------------------------------------------------

mcp = MCPServer(
    name="knowledge-base",
    instructions="Auxin's memory (read-only): the decision log (ideas, rejections with reasons, proposals, orders, "
    "fills, reviews), company notes and lessons from closed positions. Instruments are identified by IBKR conid.",
)


@mcp.tool()
async def search(query: str, limit: int = 10) -> list[dict]:
    """Full-text search over the decision log, company notes and lessons. Web-search syntax: words,
    "exact phrase", -exclude, or. Returns the best matches with source, date, conid, symbol and text."""
    return await repo.search(engine, query, max(1, min(limit, 50)))


@mcp.tool()
async def get_company_history(conid: int) -> dict:
    """Everything Auxin recorded about one instrument (by IBKR conid): past decisions with reasons, company
    notes and lessons, newest first."""
    return await repo.company_history(engine, conid)


@mcp.tool()
async def get_recent_rejections(days: int = 30) -> list[dict]:
    """Ideas and proposals rejected in the last `days` days, with conid, symbol and the reason. Do not propose
    them again without new information."""
    return await repo.rejections(engine, max(1, min(days, 365)))


mcp_app = mcp.streamable_http_app(streamable_http_path="/mcp", stateless_http=True, json_response=True,
                                  host="0.0.0.0")  # noqa: S104 - no localhost-only DNS-rebinding filter

# --- REST: writes and deterministic reads ------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with mcp.session_manager.run():
        yield
    await engine.dispose()


api = FastAPI(title="Auxin knowledge", version="0.1.0", lifespan=lifespan)


def _logged(table: str, written: Written) -> Written:
    log.info(json.dumps({"event": "kb_write", "table": table, "id": str(written.id), "created": written.created}))
    return written


@api.get("/health")
async def health() -> dict:
    async with engine.connect() as conn:
        await conn.exec_driver_sql("SELECT 1")
    return {"status": "UP"}


@api.post("/decisions", status_code=201)
async def post_decision(record: DecisionRecord) -> Written:
    return _logged("decisions", await repo.write(engine, Decision, record))


@api.post("/company-notes", status_code=201)
async def post_company_note(note: CompanyNote) -> Written:
    return _logged("company_notes", await repo.write(engine, CompanyNoteRow, note))


@api.post("/lessons", status_code=201)
async def post_lesson(lesson: Lesson) -> Written:
    return _logged("lessons", await repo.write(engine, LessonRow, lesson))


@api.post("/activity", status_code=201)
async def post_activity(steps: list[Activity]) -> dict:
    """A batch of live LLM steps; idempotent per id, not logged one by one (high volume)."""
    for step in steps:
        await repo.write(engine, ActivityRow, step)
    return {"written": len(steps)}


@api.get("/decisions")
async def get_decisions(
    conid: int | None = None,
    kind: list[DecisionKind] | None = Query(default=None),
    days: int | None = None,
    limit: int = Query(default=50, le=500),
) -> list[dict]:
    kinds = tuple(k.value for k in kind) if kind else None
    return await repo.decisions(engine, conid=conid, kinds=kinds, days=days, limit=limit, with_payload=True)


@api.get("/rejections")
async def get_rejections(days: int = 30) -> list[dict]:
    return await repo.rejections(engine, days)


@api.get("/search")
async def get_search(q: str, limit: int = 10) -> list[dict]:
    return await repo.search(engine, q, limit)


api.mount("/", mcp_app)  # serves /mcp; mounted last so the REST routes win


def migrate() -> None:
    command.upgrade(Config(str(MIGRATIONS)), "head")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    migrate()
    log.info(json.dumps({"event": "kb_migrated"}))
    uvicorn.run(api, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), log_level="warning")  # noqa: S104


if __name__ == "__main__":
    main()
