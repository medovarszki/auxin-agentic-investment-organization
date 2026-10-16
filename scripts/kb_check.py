"""Knowledge service smoke test (make kb-check): health, recent rejections, MCP tools and a search. Read-only."""
import asyncio
import json
import os

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = os.environ.get("AUXIN_KNOWLEDGE_URL", "http://knowledge:8000")


def _text(result) -> str:
    return "\n".join(c.text for c in result.content if getattr(c, "text", None))


async def main() -> None:
    async with httpx.AsyncClient(base_url=URL, trust_env=False) as http:
        print("health ->", (await http.get("/health")).json())
        decisions = (await http.get("/decisions", params={"limit": 5})).json()
        print(f"latest decisions ({len(decisions)}):")
        for d in decisions:
            print("  ", d["created_at"][:19], d["kind"], d.get("symbol"), d.get("conid"), "-", d["summary"][:90])
        print("rejections (30 d) ->", json.dumps((await http.get("/rejections")).json()))
    async with streamable_http_client(f"{URL}/mcp") as (read, write, *_):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("mcp tools:", ", ".join(t.name for t in (await session.list_tools()).tools))
            query = decisions[0]["symbol"] if decisions and decisions[0].get("symbol") else "market"
            print(f"mcp search {query!r} ->", _text(await session.call_tool("search", {"query": query, "limit": 3})))


asyncio.run(main())
