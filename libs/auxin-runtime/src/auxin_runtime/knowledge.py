"""Writes to the knowledge base through the knowledge service's REST API (the LLM never writes).

URL from AUXIN_KNOWLEDGE_URL; without it nothing is recorded (local runs without the service).
"""
import json
import logging
import os

import httpx

from auxin_schemas.knowledge import Activity, DecisionRecord, Lesson, Written

log = logging.getLogger("auxin.runtime")


def knowledge_url() -> str | None:
    url = os.environ.get("AUXIN_KNOWLEDGE_URL")
    return url.rstrip("/") if url else None


async def _write(path: str, record: DecisionRecord | Lesson, kind: str) -> Written | None:
    url = knowledge_url()
    if url is None:
        log.info(json.dumps({"event": "kb_skipped", "reason": "AUXIN_KNOWLEDGE_URL not set", "id": str(record.id)}))
        return None
    async with httpx.AsyncClient(base_url=url, timeout=httpx.Timeout(15.0), trust_env=False) as http:
        response = await http.post(path, json=record.model_dump(mode="json"))
        response.raise_for_status()
    written = Written.model_validate(response.json())
    log.info(json.dumps({"event": "kb_recorded", "kind": kind, "id": str(written.id), "created": written.created}))
    return written


async def record_decision(record: DecisionRecord) -> Written | None:
    """Idempotent (same id twice is a no-op). A failed write raises: the decision log must not lose entries."""
    return await _write("/decisions", record, record.kind)


async def record_lesson(lesson: Lesson) -> Written | None:
    """Idempotent, like record_decision."""
    return await _write("/lessons", lesson, "lesson")


async def record_activity(steps: list[Activity]) -> None:
    """Best-effort (live view only): a failed write is logged and dropped, never fails the task."""
    url = knowledge_url()
    if url is None or not steps:
        return
    try:
        async with httpx.AsyncClient(base_url=url, timeout=httpx.Timeout(5.0), trust_env=False) as http:
            response = await http.post("/activity", json=[s.model_dump(mode="json") for s in steps])
            response.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning(json.dumps({"event": "activity_dropped", "steps": len(steps), "error": str(exc)[:200]}))


async def get_decisions(**params) -> list[dict]:
    """GET /decisions (kind may be a list); raises if the knowledge service is not configured or fails."""
    url = knowledge_url()
    if url is None:
        raise RuntimeError("AUXIN_KNOWLEDGE_URL is not set")
    async with httpx.AsyncClient(base_url=url, timeout=httpx.Timeout(15.0), trust_env=False) as http:
        response = await http.get("/decisions", params=params)
        response.raise_for_status()
    return response.json()
