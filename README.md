# Auxin – agentic investment organization

Egy virtuális befektetési alapkezelő, amelyet Claude-alapú agentek modelleznek. Minden agent külön Docker containerben fut, saját szereppel és skillekkel; az agentek egy központi, perzisztált message buson (Redis Streams) kommunikálnak. A portfólió egy IBKR (alapértelmezésben paper) számla.

> Állapot: **váz**. A fejlesztés fázisonként halad, az aktuális állapot és a döntési napló: [`docs/ORG_PROGRESS.md`](docs/ORG_PROGRESS.md).

## Struktúra

| Könyvtár | Mi van benne |
|---|---|
| `org/` | A szervezet deklaratív leírása (`org.yaml`) és az agent-leírók sémája |
| `agents/` | 4 agent (market-sentiment, research, portfolio-manager, execution); 1 könyvtár = 1 agent = 1 container: `agent.yaml`, `CLAUDE.md`, saját `skills/`, `Dockerfile`, tesztek |
| `libs/` | Importált Python kód (sémák, bus-kliens, store, agent runtime); önállóan nem fut |
| `mcp-servers/` | Saját MCP szerverek: adatforrások, tudásbázis, IBKR |
| `services/` | Futó, nem-agent containerek: scheduler, portfolio-sync, bus-archiver, approval-gateway, mock-broker, dashboard |
| `infra/` | Compose, Redis, Postgres, OTel collector, egress allowlist konfiguráció |
| `tests/` | Végponttól végpontig futó füsttesztek |
| `docs/` | Haladási napló, szervezeti terv, ADR-ek, runbook |

Az agentek kimenete nem befektetési tanácsadás.
