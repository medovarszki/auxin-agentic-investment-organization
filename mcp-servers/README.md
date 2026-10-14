# mcp-servers/

Saját MCP szerverek (agent ↔ eszköz). A jogosultság tool-szinten szűrhető az `agent.yaml` allowlistjével.

- `market-data/`: árfolyamok, indexek, indikátorok
- `news/`: hírforrások
- `fundamentals/`: pénzügyi kimutatások
- `knowledge-base/`: Research-memória, döntés-eredmények, tanulságok (Postgres)
- `ibkr/`: broker; olvasó toolok (Portfolio Manager) és író toolok (csak Execution) külön

Az adatforrások és az IBKR-felület kiválasztása a 2. fázisban történik.
