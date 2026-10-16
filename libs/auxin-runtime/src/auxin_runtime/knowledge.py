"""Writes to the knowledge base through the knowledge service's REST API (the LLM never writes).

URL from AUXIN_KNOWLEDGE_URL; without it nothing is recorded (local runs without the service).
"""
import json
import logging
import os

import httpx

from auxin_schemas.knowledge import DecisionRecord, Written

log = logging.getLogger("auxin.runtime")


def knowledge_url() -> str | None:
    url = os.environ.get("AUXIN_KNOWLEDGE_URL")
    return url.rstrip("/") if url else None


async def record_decision(record: DecisionRecord) -> Written | None:
    """Idempotent (same id twice is a no-op). A failed write raises: the decision log must not lose entries."""
    url = knowledge_url()
    if url is None:
        log.info(json.dumps({"event": "kb_skipped", "reason": "AUXIN_KNOWLEDGE_URL not set", "id": str(record.id)}))
        return None
    async with httpx.AsyncClient(base_url=url, timeout=httpx.Timeout(15.0), trust_env=False) as http:
        response = await http.post("/decisions", json=record.model_dump(mode="json"))
        response.raise_for_status()
    written = Written.model_validate(response.json())
    log.info(json.dumps({"event": "kb_recorded", "kind": record.kind, "id": str(written.id),
                         "created": written.created}))
    return written


async def get_decisions(**params) -> list[dict]:
    """GET /decisions (kind may be a list); raises if the knowledge service is not configured or fails."""
    url = knowledge_url()
    if url is None:
        raise RuntimeError("AUXIN_KNOWLEDGE_URL is not set")
    async with httpx.AsyncClient(base_url=url, timeout=httpx.Timeout(15.0), trust_env=False) as http:
        response = await http.get("/decisions", params=params)
        response.raise_for_status()
    return response.json()
