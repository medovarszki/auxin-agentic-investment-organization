"""Deterministic IBKR reads for the runtime (PM gate) through the read-only IBKR MCP server.

The PM container is not on the ibkr-backend network, so it cannot reach ibkrfacade (and its order endpoint)
directly; only Execution can.
"""
import json
import os
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


class IbkrReadError(RuntimeError):
    pass


async def read_tools(calls: list[tuple[str, dict]]) -> list[Any]:
    """Calls several read-only IBKR MCP tools in one session; returns their JSON results in order."""
    url = os.environ.get("AUXIN_MCP_IBKR_URL", "http://mcp-ibkr:8000/mcp")
    results, error = [], None
    async with streamable_http_client(url) as (read, write, *_):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for tool, args in calls:
                res = await session.call_tool(tool, args)
                text = "\n".join(c.text for c in res.content if getattr(c, "text", None))
                if res.is_error:
                    error = f"{tool}: {text}"  # raised outside the MCP task group, so it is not wrapped
                    break
                if res.structured_content is not None:
                    data = res.structured_content
                    results.append(data.get("result", data) if set(data) == {"result"} else data)
                else:
                    results.append(json.loads(text))
    if error:
        raise IbkrReadError(error)
    return results
