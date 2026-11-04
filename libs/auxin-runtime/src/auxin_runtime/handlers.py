"""What each agent does with an incoming A2A message. Result dict = the task's artifact."""
import json
import logging
import os
import uuid
from pathlib import Path

import yaml

from auxin_a2a.client import send, task_summary
from auxin_a2a.server import Handler, Incoming, Rejected
from auxin_schemas.domain import (
    DecisionOutcome, Holding, IdeaReject, Instrument, LessonDraft, MarketScanResult, Order, PMDecision,
    Proposal, ProposalReject, ReviewRequest, ReviewResult, parse_idea,
)
from auxin_schemas.knowledge import DecisionKind, DecisionRecord, Lesson
from auxin_schemas.metadata import MessageType
from auxin_schemas.task import TaskState

from auxin_runtime.descriptor import AgentDescriptor, build_options, require_subscription_auth
from auxin_runtime.execution import execute, execute_pending
from auxin_runtime.ibkr import read_tools
from auxin_runtime.knowledge import get_decisions, record_decision, record_lesson
from auxin_schemas.rules import GateReject, precheck_idea, size_buy, size_sell
from auxin_runtime.runner import run_task, token_usage

log = logging.getLogger("auxin.runtime")


def _prompt(agent_dir: Path, name: str, payload: dict) -> str:
    template = (agent_dir / "prompts" / f"{name}.md").read_text()
    return f"{template}\n\n```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```\n"


def _ctx(msg: Incoming) -> dict:
    return {"correlation_id": msg.meta.correlation_id, "trace_id": msg.meta.trace_id, "task_id": msg.task_id}


async def _llm(desc: AgentDescriptor, prompt: str, options, model, msg: Incoming):
    record = await run_task(desc.name, prompt, options, model, task_id=msg.task_id, trace_id=msg.meta.trace_id)
    if record.state is not TaskState.COMPLETED:
        raise RuntimeError(record.error)
    return model.model_validate(record.output), {"cost_usd": record.cost_usd, "num_turns": record.num_turns,
                                                 "tokens": token_usage(record.usage)}


def research(desc: AgentDescriptor, agent_dir: Path) -> Handler:
    """Ideas and reviews; the PM challenges the ideas (2026-10-26). scan_trigger: market scan -> every idea recorded
    in the decision log, then handed to the PM as its own task, one after the other; review_request: re-evaluate one
    open position -> HOLD / REDUCE / CLOSE back to the PM (the task's artifact); decision_outcome: a closed position's
    result -> lesson (lessons table). The runtime writes everything to the knowledge base."""
    require_subscription_auth()
    scan_options = build_options(desc, agent_dir, MarketScanResult.model_json_schema())
    review_options = build_options(desc, agent_dir, ReviewResult.model_json_schema())
    lesson_options = build_options(desc, agent_dir, LessonDraft.model_json_schema())

    async def lesson(msg: Incoming) -> dict:
        outcome = DecisionOutcome.model_validate(msg.payload)
        out, usage = await _llm(desc, _prompt(agent_dir, "outcome", msg.payload), lesson_options, LessonDraft, msg)
        written = await record_lesson(Lesson(
            id=uuid.uuid5(outcome.decision_id, "lesson"), agent=desc.name, lesson=out.lesson,
            decision_id=outcome.decision_id, conid=outcome.conid, symbol=outcome.symbol,
            return_pct=outcome.return_pct, task_id=msg.task_id))
        return {"lesson": out.lesson, "created": written.created if written else None, **usage}

    async def review(msg: Incoming) -> dict:
        request = ReviewRequest.model_validate(msg.payload)
        inst = request.holding.instrument
        out, usage = await _llm(desc, _prompt(agent_dir, "review", msg.payload), review_options, ReviewResult, msg)
        out = out.model_copy(update={"conid": inst.conid})
        await record_decision(DecisionRecord(
            id=uuid.uuid5(uuid.NAMESPACE_URL, f"review/{msg.task_id}"), kind=DecisionKind.REVIEW, agent=desc.name,
            summary=f"{out.recommendation}"
                    f"{f' to {out.target_weight_pct:g}%' if out.recommendation == 'REDUCE' else ''}: {out.rationale}",
            conid=inst.conid, symbol=inst.symbol, payload=out.model_dump(mode="json") | usage,
            snapshot=request.holding.model_dump(mode="json"), **_ctx(msg)))
        return {"review": out.model_dump(mode="json"), **usage}

    async def scan(msg: Incoming) -> dict:
        """The scan; every idea recorded in the decision log before it goes to the PM."""
        trigger = msg.payload.get("trigger", "scan")
        prompt = (agent_dir / "prompts" / f"{trigger}.md").read_text()
        record = await run_task(desc.name, prompt, scan_options, MarketScanResult, task_id=msg.task_id,
                                trace_id=msg.meta.trace_id)
        if record.state is not TaskState.COMPLETED:
            raise RuntimeError(record.error)
        result = MarketScanResult.model_validate(record.output)

        handoffs = []
        for idea in result.ideas:
            await record_decision(DecisionRecord(
                id=idea.idea_id, kind=DecisionKind.IDEA, agent=desc.name, summary=idea.thesis,
                conid=idea.instrument.conid, symbol=idea.instrument.symbol, idea_id=idea.idea_id,
                payload=idea.model_dump(mode="json"), **_ctx(msg)))
            task = await send(
                sender=desc.name, recipient="portfolio-manager", type=MessageType.IDEA,
                subject=f"Idea: {idea.instrument.symbol}", payload=idea.model_dump(mode="json"), task_id=msg.task_id,
                correlation_id=msg.meta.correlation_id, trace_id=msg.meta.trace_id, reference_task_ids=[msg.task_id],
            )
            handoffs.append({"symbol": idea.instrument.symbol, **task_summary(task)})
        return {"scan": record.output, "cost_usd": record.cost_usd, "num_turns": record.num_turns,
                "tokens": token_usage(record.usage),
                "handoffs": handoffs}

    async def handle(msg: Incoming) -> dict:
        if msg.meta.type == MessageType.SCAN_TRIGGER:
            return await scan(msg)
        if msg.meta.type == MessageType.REVIEW_REQUEST:
            return await review(msg)
        return await lesson(msg)

    return handle


async def _portfolio(conid: int) -> dict:
    """Account, positions (with industry and ETF flag), and the proposed instrument's contract and price."""
    account, positions = await read_tools([("get_account_summary", {}), ("get_positions", {})])
    held = [p for p in positions if float(p.get("quantity") or 0) != 0]
    contracts = await read_tools([("get_contract", {"conid": c}) for c in [conid, *(p["conid"] for p in held)]]
                                 + [("get_price", {"conid": conid})])
    *details, price = contracts
    by_conid = {d["conid"]: d for d in details}

    def asset_class(d: dict) -> str:
        return "etf" if d.get("stock_type") == "ETF" else "stock"

    holdings = [{"conid": p["conid"], "symbol": p.get("symbol"), "quantity": float(p["quantity"]),
                 "market_value": float(p.get("market_value") or 0), "industry": by_conid[p["conid"]].get("industry"),
                 "asset_class": asset_class(by_conid[p["conid"]])} for p in held]
    return {"account": account, "holdings": holdings, "contract": by_conid[conid], "price": price,
            "asset_class": asset_class(by_conid[conid])}


def portfolio_manager(desc: AgentDescriptor, agent_dir: Path) -> Handler:
    """idea (from Research, or entered by hand on the dashboard): deterministic pre-gate -> challenge and investment judgement (LLM: REJECT, or BUY with
    the proposal it built) -> deterministic rule gate and sizing -> order to Execution."""
    require_subscription_auth()
    options = build_options(desc, agent_dir, PMDecision.model_json_schema())
    rules = yaml.safe_load(Path(os.environ.get("AUXIN_RULES_FILE", agent_dir / "portfolio-rules.yaml")).read_text())

    async def handle(msg: Incoming) -> dict:
        if msg.meta.type == MessageType.REVIEW_TRIGGER:
            return await daily_review(desc, msg)
        if msg.meta.type == MessageType.REVIEW_RESULT:
            return await manual_review(desc, msg)
        idea = parse_idea(msg.payload)

        async def reject_idea(reason: str, rule: str | None, payload: dict, snapshot: dict | None = None) -> None:
            body = IdeaReject(idea_id=idea.idea_id, reason=reason)
            await record_decision(DecisionRecord(
                id=uuid.uuid5(idea.idea_id, "idea_reject"), kind=DecisionKind.IDEA_REJECT, agent=desc.name,
                summary=reason, payload=body.model_dump(mode="json") | {"rule": rule} | payload, snapshot=snapshot,
                conid=idea.instrument.conid, symbol=idea.instrument.symbol, idea_id=idea.idea_id, **_ctx(msg)))
            raise Rejected(f"idea_reject {idea.instrument.symbol}{f' ({rule})' if rule else ''}: {reason}")

        # Pre-gate on what the portfolio already says, before the (costly) challenge.
        account, positions = await read_tools([("get_account_summary", {}), ("get_positions", {})])
        try:
            precheck_idea(idea, rules, base_currency=account["currency"],
                          held_conids={p["conid"] for p in positions if float(p.get("quantity") or 0) != 0})
        except GateReject as exc:
            await reject_idea(f"pre-check: {exc.reason}", exc.rule, {}, {"account": account, "positions": positions})

        out, usage = await _llm(desc, _prompt(agent_dir, "idea", msg.payload), options, PMDecision, msg)
        if out.decision == "REJECT":
            await reject_idea(out.rationale, None, {"risk_bucket": out.risk_bucket, **usage})

        proposal = Proposal(idea_id=idea.idea_id, **out.proposal.model_dump())
        inst = proposal.instrument
        ref = {"conid": inst.conid, "symbol": inst.symbol, "idea_id": proposal.idea_id, **_ctx(msg)}
        await record_decision(DecisionRecord(
            id=proposal.proposal_id, kind=DecisionKind.PROPOSAL, agent=desc.name, summary=proposal.thesis,
            payload=proposal.model_dump(mode="json") | {"case": out.rationale, "risk_bucket": out.risk_bucket}, **ref))

        async def reject(reason: str, rule: str | None, snapshot: dict | None = None) -> None:
            body = ProposalReject(proposal_id=proposal.proposal_id, reason=reason, rule=rule)
            await record_decision(DecisionRecord(
                id=uuid.uuid5(proposal.proposal_id, "proposal_reject"), kind=DecisionKind.PROPOSAL_REJECT,
                agent=desc.name, summary=reason, payload=body.model_dump(mode="json") | usage, snapshot=snapshot,
                **ref))
            raise Rejected(f"proposal_reject {inst.symbol}{f' ({rule})' if rule else ''}: {reason}")

        snapshot = await _portfolio(inst.conid)
        buckets = await _risk_buckets([h["conid"] for h in snapshot["holdings"]])
        for h in snapshot["holdings"]:
            h["risk_bucket"] = buckets.get(h["conid"])
        account, quote = snapshot["account"], snapshot["price"]
        price = None if quote.get("stale") else quote.get("ask") or quote.get("last")
        if not price:
            # Closed market: size on the last daily close; Execution needs a live quote to place the order anyway.
            (history,) = await read_tools([("get_history", {"conid": inst.conid, "duration": "1 W", "bar_size": "1 day"})])
            price = history["bars"][-1][4] if history.get("bars") else None
            snapshot["price_source"] = "last_close"
        if not price:
            await reject(f"no price for {inst.symbol}: {quote}", "require_market_price", snapshot)
        try:
            quantity, sizing = size_buy(
                proposal.model_copy(update={"instrument": inst.model_copy(update={"asset_class": snapshot["asset_class"]})}),
                rules, nav=float(account["net_liquidation"]),
                cash=min(float(account["total_cash_value"]), float(account.get("available_funds") or 0)),
                base_currency=account["currency"], price=float(price), industry=snapshot["contract"].get("industry"),
                holdings=snapshot["holdings"], risk_bucket=out.risk_bucket,
            )
        except GateReject as exc:
            await reject(f"PM approved, rule gate rejected: {exc.reason}", exc.rule, snapshot)

        order = Order(decision_id=uuid.uuid4(), instrument=inst, side="BUY", quantity=quantity)
        await record_decision(DecisionRecord(
            id=order.order_id, kind=DecisionKind.ORDER, agent=desc.name, decision_id=order.decision_id,
            summary=f"BUY {quantity} {inst.symbol} (~{sizing['order_value']} {inst.currency}, "
                    f"risk bucket {out.risk_bucket}): {out.rationale}",
            payload={"order": order.model_dump(mode="json"), "proposal_id": str(proposal.proposal_id),
                     "rationale": out.rationale, "risk_bucket": out.risk_bucket, "sizing": sizing, **usage},
            snapshot=snapshot, **ref))
        task = await send(
            sender=desc.name, recipient="execution", type=MessageType.ORDER,
            subject=f"Order: BUY {quantity} {inst.symbol}", payload=order.model_dump(mode="json"),
            task_id=msg.task_id, correlation_id=msg.meta.correlation_id, trace_id=msg.meta.trace_id,
            reference_task_ids=[msg.task_id],
        )
        return {"decision": out.decision, "rationale": out.rationale, "risk_bucket": out.risk_bucket, "order": order.model_dump(mode="json"),
                "sizing": sizing, **usage, "execution": task_summary(task)}

    return handle


async def _risk_buckets(conids: list[int]) -> dict[int, int]:
    """The PM's risk bucket per held instrument: the one recorded with its latest BUY order in the decision log.
    Positions bought before the bucket rule (or outside Auxin) have none and are left out."""
    buckets = {}
    for conid in conids:
        rows = await get_decisions(conid=conid, kind=[DecisionKind.ORDER.value], days=400, limit=50)
        bucket = next((r["payload"].get("risk_bucket") for r in rows
                       if r["payload"].get("order", {}).get("side") == "BUY" and r["payload"].get("risk_bucket")), None)
        if bucket:
            buckets[conid] = bucket
    return buckets


async def _holdings() -> tuple[dict, list[Holding]]:
    """Account summary and the open positions as review inputs (instrument details from IBKR contracts)."""
    account, positions = await read_tools([("get_account_summary", {}), ("get_positions", {})])
    held = [p for p in positions if float(p.get("quantity") or 0) > 0]
    contracts = await read_tools([("get_contract", {"conid": p["conid"]}) for p in held]) if held else []
    nav = float(account["net_liquidation"])
    holdings = []
    for p, c in zip(held, contracts, strict=True):
        instrument = Instrument(
            conid=p["conid"], symbol=c.get("symbol") or p["symbol"],
            exchange=c.get("primary_exchange") or c.get("exchange") or "SMART", currency=c.get("currency") or p["currency"],
            asset_class="etf" if c.get("stock_type") == "ETF" else "stock", industry=c.get("industry"))
        value = float(p.get("market_value") or 0)
        holdings.append(Holding(
            instrument=instrument, quantity=float(p["quantity"]), avg_cost=float(p.get("avg_cost") or 0),
            market_price=float(p["market_price"]), market_value=value, weight_pct=round(value / nav * 100, 2),
            unrealized_pnl=p.get("unrealized_pnl")))
    return account, holdings


async def _entry(conid: int) -> dict | None:
    """The latest BUY proposal and order for the instrument from the decision log (the thesis being reviewed)."""
    rows = await get_decisions(conid=conid, kind=[DecisionKind.PROPOSAL.value, DecisionKind.ORDER.value],
                               days=400, limit=50)
    proposal = next((r for r in rows if r["kind"] == DecisionKind.PROPOSAL.value), None)
    order = next((r for r in rows if r["kind"] == DecisionKind.ORDER.value
                  and r["payload"].get("order", {}).get("side") == "BUY"), None)
    if not proposal and not order:
        return None
    return {"proposal": proposal and {"created_at": proposal["created_at"], **proposal["payload"]},
            "order": order and {"created_at": order["created_at"], "summary": order["summary"],
                                "sizing": order["payload"].get("sizing")}}


async def _sell_after_review(desc: AgentDescriptor, msg: Incoming, review: ReviewResult, holding: Holding,
                             account: dict, holdings: list[Holding], send_ctx: dict) -> dict:
    """REDUCE / CLOSE -> deterministic SELL sizing -> order record -> Execution (HOLD / no room: no order)."""
    inst, nav = holding.instrument, float(account["net_liquidation"])
    quantity, sizing = size_sell(review, holding, nav=nav, price=holding.market_price)
    item = {"recommendation": review.recommendation, "sizing": sizing}
    if quantity < 1:
        return item
    order = Order(decision_id=uuid.uuid4(), instrument=inst, side="SELL", quantity=quantity)
    await record_decision(DecisionRecord(
        id=order.order_id, kind=DecisionKind.ORDER, agent=desc.name, decision_id=order.decision_id,
        summary=f"SELL {quantity} {inst.symbol} (~{sizing['order_value']} {inst.currency}, {review.recommendation}): "
                f"{review.rationale}",
        conid=inst.conid, symbol=inst.symbol,
        payload={"order": order.model_dump(mode="json"), "review": review.model_dump(mode="json"),
                 "sizing": sizing},
        snapshot={"account": account, "holdings": [h.model_dump(mode="json") for h in holdings]}, **_ctx(msg)))
    item["execution"] = task_summary(await send(
        sender=desc.name, recipient="execution", type=MessageType.ORDER,
        subject=f"Order: SELL {quantity} {inst.symbol}", payload=order.model_dump(mode="json"), **send_ctx))
    return item


async def manual_review(desc: AgentDescriptor, msg: Incoming) -> dict:
    """review_result entered by hand on the dashboard (already in the decision log as a `review`): the same
    deterministic SELL sizing and order as after Research's review, for the one position. No LLM call."""
    review = ReviewResult.model_validate(msg.payload)
    account, holdings = await _holdings()
    holding = next((h for h in holdings if h.instrument.conid == review.conid), None)
    if holding is None:
        raise Rejected(f"no open position with conid {review.conid}")
    send_ctx = {"task_id": msg.task_id, "correlation_id": msg.meta.correlation_id, "trace_id": msg.meta.trace_id,
                "reference_task_ids": [msg.task_id]}
    return {"symbol": holding.instrument.symbol, "weight_pct": holding.weight_pct,
            **await _sell_after_review(desc, msg, review, holding, account, holdings, send_ctx)}


async def daily_review(desc: AgentDescriptor, msg: Incoming) -> dict:
    """review_trigger (15:30): place the pending orders, then one Research review per open position, one after
    the other; REDUCE / CLOSE -> deterministic SELL sizing -> order to Execution (decision 6.4: no PM LLM call)."""
    send_ctx = {"task_id": msg.task_id, "correlation_id": msg.meta.correlation_id, "trace_id": msg.meta.trace_id,
                "reference_task_ids": [msg.task_id]}
    pending = task_summary(await send(sender=desc.name, recipient="execution", type=MessageType.EXECUTE_PENDING,
                                      subject="Execute pending orders (daily review)", payload={}, **send_ctx))
    account, holdings = await _holdings()
    nav = float(account["net_liquidation"])
    results = []
    for holding in holdings:
        inst = holding.instrument
        request = ReviewRequest(holding=holding, entry=await _entry(inst.conid))
        task = task_summary(await send(
            sender=desc.name, recipient="research", type=MessageType.REVIEW_REQUEST,
            subject=f"Review: {inst.symbol} ({holding.weight_pct:g}% NAV)", payload=request.model_dump(mode="json"),
            **send_ctx))
        item = {"symbol": inst.symbol, "weight_pct": holding.weight_pct, "research": task}
        results.append(item)
        if task["state"] != "TASK_STATE_COMPLETED" or not task["artifacts"]:
            continue  # a failed review leaves the position as it is; the task store has the error
        review = ReviewResult.model_validate(task["artifacts"][0]["review"])
        item |= await _sell_after_review(desc, msg, review, holding, account, holdings, send_ctx)
    return {"execute_pending": pending, "nav": nav, "positions": results}


def execution(desc: AgentDescriptor, agent_dir: Path) -> Handler:
    """order: deterministic verify and placement; execute_pending: the pending / submitted orders."""

    async def handle(msg: Incoming) -> dict:
        if msg.meta.type == MessageType.EXECUTE_PENDING:
            return await execute_pending(_ctx(msg))
        return await execute(Order.model_validate(msg.payload), _ctx(msg))

    return handle


HANDLERS = {
    "research": research,
    "portfolio-manager": portfolio_manager,
    "execution": execution,
}
