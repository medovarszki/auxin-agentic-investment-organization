# mcp-servers/

Saját MCP szerverek (agent ↔ eszköz). A jogosultság tool-szinten szűrhető az `agent.yaml` allowlistjével.

- `knowledge-base`: nem külön szerver; a `services/knowledge` szolgálja ki (`/mcp`, csak olvasás)
- `ibkr/` (6.1, kész): az ibkrfacade REST-jét hívja token nélkül, a `ibkr-backend` hálózaton. Csak olvasó toolok: `search_contract`, `get_contract`, `get_price`, `get_history`, `get_news`, `get_positions`, `get_account_summary`. Megbízás-tool nincs: a megbízást a determinisztikus Execution service adja le közvetlenül a REST-en (6.3). Streamable HTTP: `http://mcp-ibkr:8000/mcp`; ellenőrzés: `make mcp-check`.

Webes keresés: szerver-oldali web search / fetch az Anthropic API-n át, nem saját MCP (ADR 0001).
