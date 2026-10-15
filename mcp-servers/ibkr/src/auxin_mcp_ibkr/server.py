"""IBKR MCP server: read-only tools over the ibkrfacade REST API (streamable HTTP).

A thin translation layer: no business logic (that lives in ibkrfacade), no order tools (orders go through
the deterministic Execution service). Responses are trimmed to what an agent needs, to save tokens.
No auth for now (Mihály): ibkrfacade is reachable only on the internal ibkr-backend network.
"""
import os
from typing import Any

import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

FACADE_URL = os.environ.get("IBKRFACADE_URL", "http://ibkrfacade:8082/ibkr").rstrip("/")

CONTRACT_FIELDS = ("conid", "symbol", "sec_type", "exchange", "primary_exchange", "currency", "long_name")
CONTRACT_DETAIL_FIELDS = CONTRACT_FIELDS + (
    "industry", "category", "subcategory", "isin", "stock_type", "time_zone", "min_tick", "liquid_hours")

server = MCPServer(
    name="ibkr",
    instructions="Read-only Interactive Brokers data (paper account) through ibkrfacade: instrument search and "
    "details, prices, price history, news, positions and the account summary. Instruments are identified by "
    "their IBKR conid; resolve a ticker with search_contract first.",
)
_client = httpx.AsyncClient(base_url=FACADE_URL, timeout=httpx.Timeout(30.0), trust_env=False)


async def _get(path: str, **params: Any) -> Any:
    try:
        response = await _client.get(path, params={k: v for k, v in params.items() if v is not None})
    except httpx.HTTPError as e:
        raise ToolError(f"BROKER_UNREACHABLE: ibkrfacade is not reachable ({type(e).__name__})") from e
    if response.is_success:
        return response.json()
    try:
        problem = response.json()
        message = f"{problem.get('code', 'HTTP_' + str(response.status_code))}: {problem.get('detail', '')}"
    except ValueError:
        message = f"HTTP_{response.status_code}: {response.text[:200]}"
    raise ToolError(message)


def _pick(data: dict, fields: tuple[str, ...]) -> dict:
    return {k: data[k] for k in fields if data.get(k) not in (None, "")}


@server.tool()
async def search_contract(query: str) -> list[dict]:
    """Find stocks and ETFs by ticker or company name. Returns at most 10 matches with conid, exchange and
    currency; pick the listing on the primary exchange in the instrument's home currency."""
    results = await _get("/search", query=query)
    matches = [_pick(c, CONTRACT_FIELDS) for c in results if c.get("sec_type") in ("STK", "ETF", None)]
    return matches[:10]


@server.tool()
async def get_contract(conid: int) -> dict:
    """Instrument details by conid: exchange, currency, industry / category (used by the sector rule), ISIN if
    known, and the liquid (regular) trading hours."""
    return _pick(await _get(f"/contract/{conid}"), CONTRACT_DETAIL_FIELDS)


@server.tool()
async def get_price(conid: int) -> dict:
    """Latest bid / ask / last for a conid, with the quote time, its age in seconds, `stale` and the market data
    type (LIVE, DELAYED, FROZEN). Do not rely on a stale price."""
    price = await _get(f"/price/{conid}")
    fields = ("bid", "ask", "last", "quote_time", "quote_age_seconds", "stale", "market_data_type", "stream_error")
    return {"conid": conid, **_pick(price, fields)} | {"stale": bool(price.get("stale"))}


@server.tool()
async def get_history(conid: int, duration: str = "6 M", bar_size: str = "1 day") -> dict:
    """Historical OHLCV bars. duration: '<n> D|W|M|Y' (eg. '6 M'); bar_size: eg. '1 day', '1 week', '1 hour'.
    Bars are returned as [time, open, high, low, close, volume] rows."""
    history = await _get(f"/history/{conid}", duration=duration, barSize=bar_size)
    bars = [[b.get("time"), b.get("open"), b.get("high"), b.get("low"), b.get("close"), b.get("volume")]
            for b in history.get("bars", [])]
    return {"conid": conid, "time_zone": history.get("time_zone"), "columns": "time,open,high,low,close,volume",
            "bars": bars}


@server.tool()
async def get_news(conid: int, limit: int = 15) -> list[dict]:
    """Recent news headlines for a conid from the IBKR news providers (empty if the account has no news
    subscription)."""
    headlines = await _get(f"/news/{conid}", limit=max(1, min(limit, 50)))
    return [_pick(h, ("time", "provider_code", "headline")) for h in headlines]


@server.tool()
async def get_positions() -> list[dict]:
    """Open positions of the paper account with quantity, average cost, market value and P&L."""
    return await _get("/positions")


@server.tool()
async def get_account_summary() -> dict:
    """Account summary of the paper account: NAV, cash, available funds, buying power (base currency)."""
    summary = await _get("/account/summary")
    summary.pop("values", None)  # every raw TWS tag; the parsed fields cover what agents need
    return {k: v for k, v in summary.items() if v is not None}


def main() -> None:
    server.run("streamable-http", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), stateless_http=True,
               json_response=True)


if __name__ == "__main__":
    main()
