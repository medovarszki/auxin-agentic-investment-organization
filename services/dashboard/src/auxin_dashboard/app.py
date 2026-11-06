"""Dashboard: a JSON API and one static page (localhost only).

Postgres in read-only sessions (`default_transaction_read_only=on`: any write fails), the shared role (decision
7.); the portfolio live from the IBKR MCP server's read tools, no mirror table (decision 7.). Its two actions,
both on a PAPER account only and one flow at a time: a scan_trigger to Research, like `make scan` (Mihály,
2026-10-30), and a manually entered idea (Mihály, 2026-10-31): recorded in the decision log through the knowledge
REST, then sent to the Portfolio Manager like a Research idea. The live view follows both from the task store, the
decision log and the agents' activity steps.
"""
import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Literal

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from auxin_a2a.client import new_trace_id, send, task_summary
from auxin_a2a.store import database_url
from auxin_runtime.ibkr import read_tools
from auxin_runtime.knowledge import record_decision
from auxin_schemas.domain import InstrumentRef, ManualIdea, ReviewResult
from auxin_schemas.knowledge import DecisionKind, DecisionRecord
from auxin_schemas.metadata import MessageType

log = logging.getLogger("auxin.dashboard")
STATIC = Path(__file__).parent / "static"
JAEGER_UI_URL = os.environ.get("AUXIN_JAEGER_UI_URL", "http://localhost:16686").rstrip("/")
JAEGER_API_URL = os.environ.get("AUXIN_JAEGER_API_URL", "http://jaeger:16686").rstrip("/")

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


async def _jaeger_url(trace_id: str) -> str | None:
    """The trace's Jaeger UI link, or None when Jaeger no longer holds it (in-memory storage: lost on restart)."""
    try:
        async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
            found = (await client.get(f"{JAEGER_API_URL}/api/traces/{trace_id}")).status_code == 200
    except httpx.HTTPError:
        found = False
    return f"{JAEGER_UI_URL}/trace/{trace_id}" if found else None


async def _with_tokens(tasks: list[dict]) -> list[dict]:
    """Each task's LLM tokens (input, output, cache read / creation, total) from its task_finished activity steps;
    None for tasks without an LLM run (Execution, triggers) or from before the activity log."""
    rows = await _rows("SELECT task_id, text FROM agent_activity WHERE kind = 'task_finished' AND task_id = ANY(:ids)",
                       ids=[t["task_id"] for t in tasks])
    tokens: dict[str, dict] = {}
    for r in rows:
        try:
            used = json.loads(r["text"]).get("tokens") or {}
        except ValueError:
            continue
        if not used:
            continue
        total = tokens.setdefault(r["task_id"], {})
        for k, v in used.items():
            total[k] = total.get(k, 0) + v
    for t in tasks:
        t["tokens"] = tokens.get(t["task_id"])
    return tasks


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


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
    ideas = {r["conid"]: r["idea_id"] for r in await _rows(
        """SELECT DISTINCT ON (conid) conid, idea_id FROM decisions
           WHERE kind = 'fill' AND idea_id IS NOT NULL AND conid = ANY(:conids) ORDER BY conid, created_at DESC""",
        conids=[int(p["conid"]) for p in held])}
    nav = float(account.get("net_liquidation") or 0)
    for p in held:
        p["idea_id"] = ideas.get(int(p["conid"]))
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
    return {"trace_id": trace_id, "jaeger_url": await _jaeger_url(trace_id),
            "tasks": await _with_tokens([_task(t, detail=True) for t in tasks]), "decisions": decisions}


@app.get("/api/decisions")
async def decisions(kind: str | None = None, symbol: str | None = None, limit: int = 200) -> list[dict]:
    return await _rows(
        """SELECT id, created_at, kind, agent, symbol, conid, summary, trace_id, decision_id, idea_id
           FROM decisions WHERE (CAST(:kind AS text) IS NULL OR kind = :kind)
             AND (CAST(:symbol AS text) IS NULL OR symbol = upper(:symbol))
           ORDER BY created_at DESC LIMIT :limit""", kind=kind, symbol=symbol, limit=limit)


REJECT_KINDS = ("idea_reject", "proposal_reject", "order_reject")
MANUAL_AGENT = "dashboard"  # the `agent` of a manually entered idea's decision-log row
MANUAL_ROLE = "Kézi"
AGENT_ROLES = {MANUAL_AGENT: MANUAL_ROLE, "research": "Research", "market-sentiment": "Market & Sentiment", "portfolio-manager": "Portfolio Manager",
               "execution": "Execution", "scheduler": "Kiértékelő"}


def _role(row: dict) -> str:
    """The organizational role behind a decision-log row; the rule gate runs inside the PM but is its own control."""
    if row["kind"] in ("idea_reject", "proposal_reject") and (_json(row.get("payload")) or {}).get("rule"):
        return "Szabálykapu"
    return AGENT_ROLES.get(row["agent"], row["agent"])


def _idea_status(kinds: set[str], reject: dict | None) -> tuple[str, str]:
    """(category, label): category is accepted / rejected / open; the label names who decided."""
    if reject:
        return "rejected", f"Elutasítva – {_role(reject)}"
    if "fill" in kinds:
        return "accepted", "Teljesült"
    if "order_submitted" in kinds:
        return "accepted", "Leadva, teljesülésre vár"
    if "order" in kinds:
        return "accepted", "Elfogadva, megbízás függő"
    if "proposal" in kinds:
        return "open", "Javaslat, döntésre vár"
    return "open", "Nincs döntés"


def _gate_pass(row: dict) -> dict | None:
    """The rule gate passed (a BUY order with its sizing): its own control point, drawn from the PM's order row."""
    sizing = row["payload"].get("sizing") if row["kind"] == "order" else None
    if not sizing or row["payload"].get("order", {}).get("side") != "BUY":
        return None
    return {"kind": "gate_pass", "role": "Szabálykapu", "agent": row["agent"], "phase": "ötlet",
            "created_at": row["created_at"], "symbol": row["symbol"], "trace_id": row["trace_id"],
            "idea_id": row.get("idea_id"), "summary": f"Átment: {sizing.get('quantity'):g} db "
            f"(~{sizing.get('order_value')}), kötő limit: {sizing.get('binding_limit')}", "payload": sizing,
            "snapshot": None}


@app.get("/api/ideas")
async def ideas(limit: int = 500) -> list[dict]:
    """One row per generated idea with where it ended: rejected (by whom), accepted (order, fill), or open."""
    rows = await _rows(
        """SELECT i.idea_id, i.created_at, i.agent, i.symbol, i.conid, i.summary AS thesis,
                  i.payload->'instrument'->>'name' AS name, i.trace_id, e.kinds, e.last_event_at, e.reject, e.fill,
                  e.order_summary
           FROM decisions i LEFT JOIN LATERAL (
             SELECT array_agg(DISTINCT kind) AS kinds, max(created_at) AS last_event_at,
                    (array_agg(json_build_object('kind', kind, 'agent', agent, 'summary', summary, 'payload', payload)
                       ORDER BY created_at DESC) FILTER (WHERE kind IN ('idea_reject', 'proposal_reject',
                                                                        'order_reject')))[1] AS reject,
                    (array_agg(payload ORDER BY created_at DESC) FILTER (WHERE kind = 'fill'))[1] AS fill,
                    (array_agg(summary ORDER BY created_at DESC) FILTER (WHERE kind = 'order'))[1] AS order_summary
             FROM decisions d WHERE d.idea_id = i.idea_id AND d.kind <> 'idea') e ON true
           WHERE i.kind = 'idea' ORDER BY i.created_at DESC LIMIT :limit""", limit=limit)
    outcomes = await _rows("SELECT conid, payload, created_at FROM decisions WHERE kind = 'decision_outcome'")
    for r in rows:
        r["role"] = AGENT_ROLES.get(r["agent"], r["agent"])
        reject, fill = _json(r.pop("reject")), _json(r.pop("fill"))
        r["kinds"] = r["kinds"] or []
        r["category"], r["status"] = _idea_status(set(r["kinds"]), reject)
        r["reason"] = reject and reject["summary"]
        r["reject_kind"], r["reject_role"] = (reject["kind"], _role(reject)) if reject else (None, None)
        r["fill"] = fill and {k: fill.get(k) for k in ("filled_quantity", "avg_price", "filled_at")}
        r["outcome"] = None
        if fill:  # the position this fill opened, once the evaluator has closed it
            closed = [_json(o["payload"]) for o in outcomes
                      if o["conid"] == r["conid"] and _json(o["payload"])["opened_at"] >= fill["filled_at"][:19]]
            if closed:
                r["outcome"] = min(closed, key=lambda o: o["opened_at"])
                r["status"] = "Lezárva"
    return rows


@app.get("/api/ideas/{idea_id}")
async def idea(idea_id: str) -> dict:
    """An idea's full history: its own decision-log rows (Research -> PM -> rule gate -> Execution), then, once
    filled, the position's follow-up (reviews, SELL orders and fills, the evaluator's outcome, lessons)."""
    try:
        uuid.UUID(idea_id)
    except ValueError:
        raise HTTPException(404, "unknown idea") from None
    rows = await _rows("SELECT * FROM decisions WHERE idea_id = CAST(:id AS uuid) ORDER BY created_at", id=idea_id)
    head = next((r for r in rows if r["kind"] == "idea"), None)
    if not head:
        raise HTTPException(404, "unknown idea")
    for r in rows:
        r["phase"] = "ötlet"
    fill = next((r for r in reversed(rows) if r["kind"] == "fill"), None)
    lessons = []
    if fill:
        after = await _rows("SELECT * FROM decisions WHERE conid = :conid AND idea_id IS NULL AND created_at > :t "
                            "ORDER BY created_at", conid=fill["conid"], t=fill["created_at"])
        close = next((i for i, r in enumerate(after) if r["kind"] == "decision_outcome"), None)
        after = after if close is None else after[:close + 1]
        for r in after:
            r["phase"] = "utókövetés"
        rows += after
        outcome_ids = [r["decision_id"] for r in after if r["kind"] == "decision_outcome"]
        if outcome_ids:
            lessons = await _rows("SELECT created_at, agent, lesson, return_pct, decision_id FROM lessons "
                                  "WHERE decision_id = ANY(:ids) ORDER BY created_at", ids=outcome_ids)
    events = []
    for r in rows:
        r.pop("search", None)
        r["payload"], r["snapshot"] = _json(r["payload"]), _json(r["snapshot"])
        r["role"] = _role(r)
        events.append(r)
        if r["phase"] == "ötlet" and (gate := _gate_pass(r)):
            events.append(gate)
    for lesson in lessons:
        events.append({"kind": "lesson", "role": AGENT_ROLES.get(lesson["agent"], lesson["agent"]),
                       "agent": lesson["agent"], "phase": "utókövetés", "created_at": lesson["created_at"],
                       "symbol": head["symbol"], "trace_id": None, "summary": lesson["lesson"],
                       "payload": {"return_pct": lesson["return_pct"]}, "snapshot": None})
    reject = next((r for r in rows if r["kind"] in REJECT_KINDS and r["phase"] == "ötlet"), None)
    category, status = _idea_status({r["kind"] for r in rows if r["phase"] == "ötlet"}, reject)
    if any(r["kind"] == "decision_outcome" for r in rows):
        status = "Lezárva"
    traces = [{"trace_id": t, "jaeger_url": await _jaeger_url(t)}
              for t in dict.fromkeys(r["trace_id"] for r in rows if r["trace_id"])]
    return {"idea": head, "category": category, "status": status, "events": events, "traces": traces}


_scans: set[asyncio.Task] = set()  # flows started here (scan or manual idea), still followed (the send returns at the final state)


def _scan_done(task: asyncio.Task) -> None:
    _scans.discard(task)
    error = None if task.cancelled() else task.exception()
    log.info(json.dumps({"event": "flow_finished", "name": task.get_name(), "error": str(error) if error else None,
                         "result": None if error or task.cancelled() else task_summary(task.result())["state"]}))


async def _paper_account() -> dict:
    """The account summary; 503 when the broker is down, 409 unless it is a PAPER account (the dashboard's writes)."""
    try:
        (account,) = await read_tools([("get_account_summary", {})])
    except Exception as exc:  # noqa: BLE001 - broker down: no flow
        raise HTTPException(503, f"broker not reachable: {type(exc).__name__}: {exc}") from None
    if account.get("account_mode") != "PAPER":
        raise HTTPException(409, {"message": f"not a PAPER account: {account.get('account_mode')}"})
    return account


async def _require_idle(*types: str) -> None:
    """409 (with the running flow's trace_id) when a flow started here, or a task of these types, is still running."""
    running = await _rows(
        """SELECT metadata->>'trace_id' AS trace_id FROM a2a_tasks WHERE metadata->>'type' = ANY(:types)
             AND status->>'state' ~ '(SUBMITTED|WORKING)$' AND last_updated > now() - interval '1 hour'
           ORDER BY last_updated DESC LIMIT 1""", types=list(types))
    if _scans or running:
        raise HTTPException(409, {"message": "a flow is already running",
                                  "trace_id": running[0]["trace_id"] if running else None})


def _start_flow(name: str, flow_id: str, trace_id: str, **message) -> None:
    """Sends the A2A message in the background (one flow = one trace) and follows it to its final state."""
    flow = asyncio.create_task(send(sender="dashboard", task_id=flow_id, correlation_id=flow_id, trace_id=trace_id,
                                    **message), name=name)
    _scans.add(flow)
    flow.add_done_callback(_scan_done)


@app.post("/api/scan", status_code=202)
async def start_scan() -> dict:
    """scan_trigger -> Research (the buy flow), on a PAPER account, one at a time."""
    account = await _paper_account()
    await _require_idle("scan_trigger")
    flow_id, trace_id = str(uuid.uuid4()), new_trace_id()
    _start_flow("scan", flow_id, trace_id, recipient="research", type=MessageType.SCAN_TRIGGER,
                subject="scan_trigger (dashboard)", payload={})
    log.info(json.dumps({"event": "scan_started", "trace_id": trace_id, "account": account.get("account")}))
    return {"trace_id": trace_id}


class ManualIdeaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=20)  # the ticker; resolved to an IBKR conid
    thesis: str = Field(min_length=1, max_length=2000)
    rationale: str = Field(default="", max_length=4000)  # background, sources, links: optional


def pick_listing(matches: list[dict], symbol: str, currency: str) -> dict | None:
    """The IBKR search match for a manually entered ticker: an exact symbol match, preferring the account's base
    currency (otherwise IBKR's own order). None when the ticker has no exact match (a company name is not guessed)."""
    exact = [m for m in matches if str(m.get("symbol", "")).upper() == symbol.upper() and m.get("conid")]
    exact.sort(key=lambda m: m.get("currency") != currency)
    return exact[0] if exact else None


@app.post("/api/ideas", status_code=202)
async def add_idea(body: ManualIdeaIn) -> dict:
    """A manually entered idea: resolved to an IBKR instrument, recorded in the decision log (agent `dashboard`),
    then sent to the Portfolio Manager as an `idea` message, which challenges it like a Research idea. PAPER only,
    one flow at a time."""
    account = await _paper_account()
    await _require_idle("scan_trigger", "idea", "review_trigger")
    symbol = body.symbol.strip().upper()
    try:
        (matches,) = await read_tools([("search_contract", {"query": symbol})])
        listing = pick_listing(matches, symbol, account.get("currency", "USD"))
        (contract,) = await read_tools([("get_contract", {"conid": listing["conid"]})]) if listing else (None,)
    except Exception as exc:  # noqa: BLE001 - broker down: no idea
        raise HTTPException(503, f"broker not reachable: {type(exc).__name__}: {exc}") from None
    if not listing:
        raise HTTPException(422, {"message": f"no IBKR stock or ETF with the ticker {symbol}"})
    idea = ManualIdea(
        instrument=InstrumentRef(
            symbol=listing["symbol"], name=contract.get("long_name") or listing.get("long_name") or listing["symbol"],
            asset_class="etf" if contract.get("stock_type") == "ETF" else "stock",
            exchange=contract.get("primary_exchange") or contract.get("exchange") or listing.get("exchange"),
            currency=contract.get("currency") or listing.get("currency"), conid=listing["conid"]),
        thesis=body.thesis.strip(), rationale=body.rationale.strip())
    flow_id, trace_id = str(uuid.uuid4()), new_trace_id()
    payload = idea.model_dump(mode="json")
    # The decision log first (as Research's scan does): an idea the PM never saw would still show up as "no decision".
    await record_decision(DecisionRecord(
        id=idea.idea_id, kind=DecisionKind.IDEA, agent=MANUAL_AGENT, summary=idea.thesis,
        conid=idea.instrument.conid, symbol=idea.instrument.symbol, idea_id=idea.idea_id, payload=payload,
        correlation_id=flow_id, trace_id=trace_id, task_id=flow_id))
    _start_flow("manual_idea", flow_id, trace_id, recipient="portfolio-manager", type=MessageType.IDEA,
                subject=f"Idea: {idea.instrument.symbol} (manual)", payload=payload)
    log.info(json.dumps({"event": "manual_idea_started", "trace_id": trace_id, "idea_id": str(idea.idea_id),
                         "symbol": idea.instrument.symbol, "conid": idea.instrument.conid,
                         "account": account.get("account")}))
    return {"trace_id": trace_id, "idea_id": str(idea.idea_id), "instrument": payload["instrument"]}


class ManualReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation: Literal["REDUCE", "CLOSE"]
    target_weight_pct: float | None = Field(default=None, ge=0, le=100)  # REDUCE: the weight to go down to
    rationale: str = Field(min_length=1, max_length=4000)


@app.post("/api/positions/{conid}/review", status_code=202)
async def manual_review(conid: int, body: ManualReviewIn) -> dict:
    """A manual review of an open position (REDUCE / CLOSE with a rationale): recorded in the decision log as a
    `review` (agent `dashboard`), then sent to the Portfolio Manager as a `review_result`, which sizes the SELL
    deterministically and hands the order to Execution, like after Research's review. PAPER only, one flow at a time."""
    account = await _paper_account()
    await _require_idle("scan_trigger", "idea", "review_trigger", "review_result")
    try:
        (positions,) = await read_tools([("get_positions", {})])
    except Exception as exc:  # noqa: BLE001 - broker down: no review
        raise HTTPException(503, f"broker not reachable: {type(exc).__name__}: {exc}") from None
    position = next((p for p in positions if int(p["conid"]) == conid and float(p.get("quantity") or 0) > 0), None)
    if not position:
        raise HTTPException(422, {"message": f"no open position with conid {conid}"})
    try:
        review = ReviewResult(conid=conid, recommendation=body.recommendation, rationale=body.rationale.strip(),
                              target_weight_pct=body.target_weight_pct if body.recommendation == "REDUCE" else None)
    except ValueError:
        raise HTTPException(422, {"message": "REDUCE needs a target weight (%)"}) from None
    flow_id, trace_id = str(uuid.uuid4()), new_trace_id()
    payload = review.model_dump(mode="json")
    await record_decision(DecisionRecord(
        id=uuid.uuid4(), kind=DecisionKind.REVIEW, agent=MANUAL_AGENT,
        summary=f"{review.recommendation}{f' to {review.target_weight_pct:g}%' if review.target_weight_pct is not None else ''}: "
                f"{review.rationale}",
        conid=conid, symbol=position["symbol"], payload=payload,
        correlation_id=flow_id, trace_id=trace_id, task_id=flow_id))
    _start_flow("manual_review", flow_id, trace_id, recipient="portfolio-manager", type=MessageType.REVIEW_RESULT,
                subject=f"Review: {position['symbol']} {review.recommendation} (manual)", payload=payload)
    log.info(json.dumps({"event": "manual_review_started", "trace_id": trace_id, "symbol": position["symbol"],
                         "conid": conid, "recommendation": review.recommendation, "account": account.get("account")}))
    return {"trace_id": trace_id}


async def _outcome(trace_id: str) -> dict | None:
    """How a finished flow ended: its error, or for a scan the number of ideas and the market summary."""
    rows = await _rows(f"SELECT {TASK_COLUMNS}, status, artifacts FROM a2a_tasks WHERE metadata->>'trace_id' = :t "
                       "ORDER BY last_updated", t=trace_id)
    tasks = [_task(r, detail=True) for r in rows]
    if not tasks:
        return None
    failed = next((t for t in tasks if t["state"] == "FAILED"), None)
    scan = next((a["scan"] for t in tasks for a in t["artifacts"] if isinstance(a, dict) and "scan" in a), None)
    return {"failed": failed is not None, "error": failed["status_message"] if failed else None,
            "scan": scan and {"ideas": len(scan.get("ideas") or []),
                              "summary": (scan.get("market_view") or {}).get("summary")}}


@app.get("/api/live/{trace_id}")
async def live(trace_id: str) -> dict:
    """One flow as it runs: its tasks, its decision-log rows (with roles) and every LLM step recorded so far."""
    tasks = await _rows(f"SELECT {TASK_COLUMNS}, last_updated FROM a2a_tasks WHERE metadata->>'trace_id' = :t "
                        "ORDER BY last_updated", t=trace_id)
    decisions = await _rows("SELECT id, created_at, kind, agent, symbol, summary, idea_id, payload, trace_id "
                            "FROM decisions WHERE trace_id = :t ORDER BY created_at", t=trace_id)
    activity = await _rows("SELECT created_at, agent, task_id, seq, kind, name, text, is_error FROM agent_activity "
                           "WHERE trace_id = :t ORDER BY created_at, seq", t=trace_id)
    tasks = await _with_tokens([_task(t) for t in tasks])
    events = []
    for d in decisions:
        d["payload"] = _json(d["payload"])
        d["role"], d["phase"], d["snapshot"] = _role(d), "ötlet", None
        events += [d, *filter(None, [_gate_pass(d)])]
    starting = any(not s.done() for s in _scans) and not tasks
    running = starting or any(t["state"] in ("SUBMITTED", "WORKING") for t in tasks)
    return {"trace_id": trace_id, "running": running, "outcome": None if running else await _outcome(trace_id),
            "tasks": tasks, "decisions": events, "activity": activity}


@app.get("/api/tasks")
async def tasks(limit: int = 200) -> list[dict]:
    rows = await _rows(f"SELECT {TASK_COLUMNS}, last_updated FROM a2a_tasks ORDER BY last_updated DESC LIMIT :limit",
                       limit=limit)
    return await _with_tokens([_task(r) for r in rows])


@app.get("/api/outcomes")
async def outcomes() -> dict:
    """Closed positions (decision_outcome events) and the lessons drawn from them."""
    closed = await _rows("SELECT created_at, symbol, conid, decision_id, payload, trace_id FROM decisions "
                         "WHERE kind = 'decision_outcome' ORDER BY created_at DESC")
    lessons = await _rows("SELECT created_at, symbol, conid, decision_id, return_pct, lesson FROM lessons "
                          "ORDER BY created_at DESC")
    return {"closed": closed, "lessons": lessons}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), log_level="warning")  # noqa: S104
    return 0
