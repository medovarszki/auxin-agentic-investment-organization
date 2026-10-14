# mcp-servers/

Saját MCP szerverek (agent ↔ eszköz). A jogosultság tool-szinten szűrhető az `agent.yaml` allowlistjével.

- `knowledge-base/`: Research-memória, döntés-eredmények, tanulságok (Postgres)
- `ibkr/`: az ibkrfacade REST-jét hívja. Piaci adat (ár, historikus, hírek, contract), számla és pozíciók (olvasó toolok), megbízás (író toolok, csak Execution)

Webes keresés: szerver-oldali web search / fetch az Anthropic API-n át, nem saját MCP (ADR 0001).
