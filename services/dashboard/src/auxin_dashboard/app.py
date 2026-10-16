"""Dashboard: a read-only JSON API and one static page (localhost only).

Postgres in read-only sessions (`default_transaction_read_only=on`: any write fails), the shared role (decision
7.); the portfolio live from the IBKR MCP server's read tools, no mirror table (decision 7.).
"""
import json
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from auxin_a2a.store import database_url
from auxin_runtime.ibkr import read_tools

STATIC = Path(__file__).parent / "static"
JAEGER_UI_URL = os.environ.get("AUXIN_JAEGER_UI_URL", "http://localhost:16686").rstrip("/")

engine = create_async_engine(database_url(), pool_pre_ping=True,
                             connect_args={"server_settings": {"default_transaction_read_only": "on"}})
app = FastAPI(title="Auxin dashboard", docs_url=None, redoc_url=None)


def _json(value):
    """a2a_tasks stores JSON (not jsonb) columns; asyncpg returns them as text."""
    return json.loads(value) if isinstance(value, str) else value


async def _rows(sql: str, **params) -> list[dict]:
    async with engine.connect() as conn:
        result = await conn.execute(text(sql), params)
        return [dict(r._mapping) for r in result]


TASK_COLUMNS = """id AS task_id, owner AS agent, metadata->>'sender' AS sender, metadata->>'type' AS type,
    metadata->>'subject' AS subject, status->>'state' AS state, status->>'timestamp' AS updated_at,
    metadata->>'trace_id' AS trace_id, metadata->>'correlation_id' AS correlation_id"""


def _task(row: dict, detail: bool = False) -> dict:
    row["state"] = (row.get("state") or "").removeprefix("TASK_STATE_")
    if detail:
        status, artifacts = _json(row.pop("status")), _json(row.pop("artifacts")) or []
        row["status_message"] = " ".join(p.get("text", "") for p in (status.get("message") or {}).get("parts", []))
        row["artifacts"] = [p.get("data") for a in artifacts for p in a.get("parts", []) if "data" in p]
    return row


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/config")
async def config() -> dict:
    return {"jaeger_ui_url": JAEGER_UI_URL}


@app.get("/health")
async def health() -> dict:
    await _rows("SELECT 1")
    return {"status": "ok"}


@app.get("/api/portfolio")
async def portfolio() -> dict:
    """Live account and positions (IBKR MCP), with each position's latest review from the decision log."""
    try:
        account, positions = await read_tools([("get_account_summary", {}), ("get_positions", {})])
    except Exception as exc:  # noqa: BLE001 - broker down: the page shows the error, the rest still works
        return {"error": f"{type(exc).__name__}: {exc}", "account": None, "positions": []}
    held = [p for p in positions if float(p.get("quantity") or 0) != 0]
    reviews = {r["conid"]: r for r in await _rows(
        """SELECT DISTINCT ON (conid) conid, created_at, payload->>'recommendation' AS recommendation, summary
           FROM decisions WHERE kind = 'review' AND conid = ANY(:conids) ORDER BY conid, created_at DESC""",
        conids=[int(p["conid"]) for p in held])}
    nav = float(account.get("net_liquidation") or 0)
    for p in held:
        p["weight_pct"] = round(float(p.get("market_value") or 0) / nav * 100, 2) if nav else None
        p["last_review"] = reviews.get(int(p["conid"]))
    return {"error": None, "account": account, "positions": held}


@app.get("/api/flows")
async def flows(limit: int = 50) -> list[dict]:
    """One row per trace (a scan, a review, an evaluation, a manual trigger): its tasks and decision events."""
    return await _rows(
        """WITH t AS (
             SELECT metadata->>'trace_id' AS trace_id, min(last_updated) AS started_at, max(last_updated) AS ended_at,
                    count(*) AS tasks,
                    (array_agg(metadata->>'type' ORDER BY last_updated) FILTER (
                        WHERE metadata->>'sender' IN ('scheduler', 'operator')))[1] AS trigger,
                    (array_agg(metadata->>'sender' ORDER BY last_updated) FILTER (
                        WHERE metadata->>'sender' IN ('scheduler', 'operator')))[1] AS sender,
                    count(*) FILTER (WHERE status->>'state' LIKE '%FAILED') AS failed,
                    count(*) FILTER (WHERE status->>'state' ~ '(SUBMITTED|WORKING)$') AS running
             FROM a2a_tasks WHERE metadata->>'trace_id' IS NOT NULL GROUP BY 1
             ORDER BY started_at DESC LIMIT :limit)
           SELECT t.*, d.kinds, d.symbols FROM t LEFT JOIN LATERAL (
             SELECT array_agg(DISTINCT kind) AS kinds, array_agg(DISTINCT symbol) FILTER (WHERE symbol IS NOT NULL)
                    AS symbols
             FROM decisions WHERE decisions.trace_id = t.trace_id) d ON true
           ORDER BY t.started_at DESC""", limit=limit)


@app.get("/api/flows/{trace_id}")
async def flow(trace_id: str) -> dict:
    tasks = await _rows(f"SELECT {TASK_COLUMNS}, last_updated, status, artifacts FROM a2a_tasks "
                        "WHERE metadata->>'trace_id' = :trace_id ORDER BY last_updated", trace_id=trace_id)
    decisions = await _rows("SELECT * FROM decisions WHERE trace_id = :trace_id ORDER BY created_at",
                            trace_id=trace_id)
    if not tasks and not decisions:
        raise HTTPException(404, "unknown trace")
    for d in decisions:
        d.pop("search", None)
    return {"trace_id": trace_id, "jaeger_url": f"{JAEGER_UI_URL}/trace/{trace_id}",
            "tasks": [_task(t, detail=True) for t in tasks], "decisions": decisions}


@app.get("/api/decisions")
async def decisions(kind: str | None = None, symbol: str | None = None, limit: int = 200) -> list[dict]:
    return await _rows(
        """SELECT id, created_at, kind, agent, symbol, conid, summary, trace_id, decision_id, idea_id
           FROM decisions WHERE (CAST(:kind AS text) IS NULL OR kind = :kind)
             AND (CAST(:symbol AS text) IS NULL OR symbol = upper(:symbol))
           ORDER BY created_at DESC LIMIT :limit""", kind=kind, symbol=symbol, limit=limit)


@app.get("/api/tasks")
async def tasks(limit: int = 200) -> list[dict]:
    rows = await _rows(f"SELECT {TASK_COLUMNS}, last_updated FROM a2a_tasks ORDER BY last_updated DESC LIMIT :limit",
                       limit=limit)
    return [_task(r) for r in rows]


@app.get("/api/outcomes")
async def outcomes() -> dict:
    """Closed positions (decision_outcome events) and the lessons drawn from them."""
    closed = await _rows("SELECT created_at, symbol, conid, decision_id, payload, trace_id FROM decisions "
                         "WHERE kind = 'decision_outcome' ORDER BY created_at DESC")
    lessons = await _rows("SELECT created_at, symbol, conid, decision_id, return_pct, lesson FROM lessons "
                          "ORDER BY created_at DESC")
    return {"closed": closed, "lessons": lessons}


def main() -> int:
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), log_level="warning")  # noqa: S104
    return 0
