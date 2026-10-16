"""Execution: deterministic, no LLM. The only Auxin component with access to ibkrfacade's order endpoint.

verify (paper account, matches the PM decision in the decision log) -> market open? -> POST /order (MKT, DAY,
client_order_id = decision_id) -> one status check -> fill. A closed market leaves the order pending in the log;
`execute_pending` (15:30 run, until then make execute-pending) places it and follows up submitted orders.
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import httpx

from auxin_a2a.server import Rejected
from auxin_schemas.domain import Fill, Order, OrderReject, OrderRejectReason, is_paper_account
from auxin_schemas.knowledge import DecisionKind, DecisionRecord

from auxin_runtime.knowledge import get_decisions, record_decision

log = logging.getLogger("auxin.execution")

AGENT = "execution"
FACADE_URL = os.environ.get("IBKRFACADE_URL", "http://ibkrfacade:8082/ibkr").rstrip("/")
FINAL_KINDS = (DecisionKind.FILL.value, DecisionKind.ORDER_REJECT.value)
STATUS_CHECK_DELAY_S = 5


def _facade() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=FACADE_URL, timeout=httpx.Timeout(30.0), trust_env=False)


def _event_id(decision_id: uuid.UUID, kind: DecisionKind) -> uuid.UUID:
    """Deterministic id per (decision, event kind): recording the same event twice is a no-op."""
    return uuid.uuid5(decision_id, kind.value)


async def _record(order: Order, kind: DecisionKind, summary: str, payload: dict, ctx: dict) -> None:
    await record_decision(DecisionRecord(
        id=_event_id(order.decision_id, kind), kind=kind, agent=AGENT, summary=summary,
        conid=order.instrument.conid, symbol=order.instrument.symbol, decision_id=order.decision_id,
        idea_id=ctx.get("idea_id"), payload=payload, correlation_id=ctx.get("correlation_id"),
        trace_id=ctx.get("trace_id"), task_id=ctx.get("task_id"),
    ))


async def _reject(order: Order, reason: OrderRejectReason, detail: str, ctx: dict) -> None:
    reject = OrderReject(order_id=order.order_id, reason=reason, detail=detail)
    await _record(order, DecisionKind.ORDER_REJECT, f"{reason}: {detail}", reject.model_dump(mode="json"), ctx)
    log.info(json.dumps({"event": "order_rejected", "decision_id": str(order.decision_id), "reason": reason,
                         "detail": detail}))


async def _log_entries(order: Order) -> tuple[dict | None, set[str]]:
    """The PM's order entry for this decision and the kinds already recorded for it."""
    rows = await get_decisions(conid=order.instrument.conid, days=30, limit=200)
    mine = [r for r in rows if r.get("decision_id") == str(order.decision_id)]
    entry = next((r for r in mine if r["kind"] == DecisionKind.ORDER.value), None)
    return entry, {r["kind"] for r in mine}


async def _verify(http: httpx.AsyncClient, order: Order, entry: dict | None) -> tuple[OrderRejectReason, str] | None:
    account = (await http.get("/account/summary")).json()
    if account.get("account_mode") != "PAPER" or not is_paper_account(account.get("account", "")):
        return OrderRejectReason.NOT_PAPER_ACCOUNT, f"account {account.get('account')} {account.get('account_mode')}"
    if entry is None:
        return OrderRejectReason.MISMATCH, "no PM order entry for this decision_id in the decision log"
    logged = Order.model_validate(entry["payload"]["order"])
    if (logged.order_id, logged.instrument.conid, logged.side, logged.quantity) != (
            order.order_id, order.instrument.conid, order.side, order.quantity):
        return OrderRejectReason.MISMATCH, "order differs from the PM decision in the decision log"
    return None


async def _follow_up(http: httpx.AsyncClient, order: Order, ctx: dict) -> dict:
    """One status check of a submitted order: Filled -> fill; inactive unfilled -> order_reject."""
    found = (await http.get("/orders", params={"client_order_id": order.client_order_id})).json()
    if not found:
        return {"status": "unknown"}
    state = found[0]
    filled = float(state.get("filled_quantity") or 0)
    if state.get("status") == "Filled" or (filled > 0 and not state.get("active")):
        fill = Fill(
            order_id=order.order_id, ibkr_order_id=state["order_id"], filled_quantity=filled,
            avg_price=state["avg_fill_price"], commission=state.get("commission") or 0.0,
            filled_at=state.get("updated_at") or datetime.now(timezone.utc),
        )
        await _record(order, DecisionKind.FILL,
                      f"{order.side} {filled:g} {order.instrument.symbol} @ {fill.avg_price}",
                      fill.model_dump(mode="json") | {"ibkr": state}, ctx)
        return {"status": "filled", "fill": fill.model_dump(mode="json")}
    if not state.get("active"):
        await _reject(order, OrderRejectReason.CANCELLED, f"IBKR status {state.get('status')} "
                      f"{state.get('error_message') or ''}".strip(), ctx)
        return {"status": "cancelled", "ibkr_status": state.get("status")}
    return {"status": "working", "ibkr_status": state.get("status")}


async def execute(order: Order, ctx: dict) -> dict:
    """Handles one order; raises Rejected for an order_reject (the task ends REJECTED)."""
    entry, done = await _log_entries(order)
    ctx = {"idea_id": entry.get("idea_id") if entry else None, **ctx}
    async with _facade() as http:
        if DecisionKind.FILL.value in done or DecisionKind.ORDER_REJECT.value in done:
            return {"status": "already_final", "decision_id": str(order.decision_id)}
        if DecisionKind.ORDER_SUBMITTED.value in done:
            return await _follow_up(http, order, ctx)

        problem = await _verify(http, order, entry)
        if problem:
            await _reject(order, *problem, ctx)
            raise Rejected(f"{problem[0]}: {problem[1]}")
        session = (await http.get(f"/contract/{order.instrument.conid}/session")).json()
        if not session.get("open"):
            log.info(json.dumps({"event": "order_pending", "decision_id": str(order.decision_id),
                                 "next_open": session.get("next_open")}))
            return {"status": "pending", "decision_id": str(order.decision_id), "next_open": session.get("next_open")}

        response = await http.post("/order", json={
            "client_order_id": order.client_order_id, "conid": order.instrument.conid, "action": order.side,
            "quantity": order.quantity, "order_type": order.order_type, "tif": "DAY",
        })
        if response.status_code not in (200, 201):
            body = response.text[:300]
            reason = OrderRejectReason.NO_PRICE if response.status_code == 422 else OrderRejectReason.BROKER_ERROR
            await _reject(order, reason, f"HTTP {response.status_code} {body}", ctx)
            raise Rejected(f"{reason}: HTTP {response.status_code} {body}")
        placed = response.json()
        await _record(order, DecisionKind.ORDER_SUBMITTED,
                      f"{order.side} {order.quantity:g} {order.instrument.symbol} MKT DAY submitted "
                      f"(IBKR order {placed.get('order_id')}, {placed.get('status')})", placed, ctx)
        log.info(json.dumps({"event": "order_submitted", "decision_id": str(order.decision_id),
                             "ibkr_order_id": placed.get("order_id"), "status": placed.get("status")}))
        await asyncio.sleep(STATUS_CHECK_DELAY_S)
        return {"submitted": placed.get("order_id"), **await _follow_up(http, order, ctx)}


async def execute_pending(ctx: dict) -> dict:
    """Places the orders still pending (market was closed) and follows up the submitted ones (last 7 days)."""
    rows = await get_decisions(kind=[DecisionKind.ORDER.value, DecisionKind.ORDER_SUBMITTED.value, *FINAL_KINDS],
                               days=7, limit=500)
    kinds: dict[str, set[str]] = {}
    for r in rows:
        kinds.setdefault(r["decision_id"], set()).add(r["kind"])
    results = []
    for r in rows:
        if r["kind"] != DecisionKind.ORDER.value or kinds[r["decision_id"]] & set(FINAL_KINDS):
            continue
        order = Order.model_validate(r["payload"]["order"])
        try:
            result = await execute(order, {**ctx, "trace_id": r.get("trace_id"), "correlation_id": r.get("correlation_id")})
        except Rejected as exc:
            result = {"status": "rejected", "reason": str(exc)}
        results.append({"symbol": order.instrument.symbol, "decision_id": r["decision_id"], **result})
    return {"orders": results}
