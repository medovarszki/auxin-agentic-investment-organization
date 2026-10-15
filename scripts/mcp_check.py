"""IBKR MCP smoke test (make mcp-check): list the tools, resolve AAPL, read its price. Never places an order."""
import asyncio
import json
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = os.environ.get("AUXIN_MCP_IBKR_URL", "http://mcp-ibkr:8000/mcp")


def _text(result) -> str:
    return "\n".join(c.text for c in result.content if getattr(c, "text", None))


async def main() -> None:
    async with streamable_http_client(URL) as (read, write, *_):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", ", ".join(t.name for t in tools.tools))
            search = await session.call_tool("search_contract", {"query": "AAPL"})
            first = json.loads(search.content[0].text)
            print("search_contract AAPL ->", json.dumps(first))
            for name in ("get_contract", "get_price"):
                print(f"{name} ->", _text(await session.call_tool(name, {"conid": first["conid"]})))
            print("get_account_summary ->", _text(await session.call_tool("get_account_summary", {})))


asyncio.run(main())
