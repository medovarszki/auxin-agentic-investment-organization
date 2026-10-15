# ADR 0001 – Technológiai és adatdöntések (2. fázis)

Dátum: 2026-10-14 · Állapot: elfogadva (Mihály)

## Döntések

| Terület | Döntés | Indoklás |
|---|---|---|
| Nyelv | Python 3.12, `uv` workspace | Agent SDK Python, IBKR- és adatkönyvtárak |
| Agent runtime | **Claude Agent SDK** (Python), nem headless CLI | Programozott tool-allowlist, hookok, hívásonkénti költségmérés |
| Modell | Minden agent: Opus 5.5 (`claude-opus-5-5`) | 1. fázis döntése |
| Agent ↔ agent | **A2A 1.0**, pont-pont, minden agent saját A2A szervert futtat (`a2a-sdk`) | Szabványos interop és taszk-életciklus; a korábbi Redis bus kiesett |
| Audit | Közös Postgres task store (`a2a-sdk` `DatabaseTaskStore`) + OpenTelemetry trace-ek | Az A2A maga nem ad központi naplót; így minden task és üzenet-előzmény egy helyen, a hívásláncok trace-ben |
| Üzenet-metaadatok | Saját A2A extension a Message `metadata` mezőjében: sender, recipient, subject, type, priority, timestamp (UTC), task_id / correlation_id, trace_id, reply_to, schema_version, ttl | Mihály követelménye; a séma a 3. fázisban |
| Taszkállapotok | A2A 1.0: `SUBMITTED`, `WORKING`, `INPUT_REQUIRED`, `AUTH_REQUIRED`, `COMPLETED`, `FAILED`, `CANCELED`, `REJECTED` | A saját életciklus ezekre képeződik le (3. fázis) |
| Agent ↔ eszköz | MCP (`mcp` SDK) | Tool-szintű jogosultság |
| Tárolás | **Egy Postgres**: A2A task store, portfólió-tükör, tudásbázis, döntési napló; pgvector később | Egy auditálható igazságforrás |
| Redis | Csak az ibkrfacade árfolyam-tárolója (Redis 8, TimeSeries beépítve) | Nincs agent-forgalom Redisen |
| Ütemező | Saját `scheduler` service (APScheduler), A2A-hívással indít | Determinisztikus, naplózott triggerek |
| Hitelesítés | ~~Agentenkénti bearer token~~ → 5. fázis: **egyelőre nincs auth**, csak az `internal` Docker-hálózat (Mihály, 2026-10-15); bearer token és TLS később | **Jóváhagyott eltérés** a biztonsági alapértéktől (Mihály, 2026-10-14); a TLS bevezetése a 9. fázis checklistjén |
| IBKR | IB Gateway container (`gnzsnz/ib-gateway`, IBC, paper) ← ibkrfacade (Java, bővítve) ← `mcp-servers/ibkr` ← PM (read) / Execution (read+write) | Mihály saját projektje; a bővítést külön prompt írja le |
| Árfolyam, hírek | IBKR (élő adat-előfizetés és paper számla rendelkezésre áll) | Mihály |
| Fundamentumok | IBKR + aktív webkeresés; nincs külön fizetős API | Mihály döntése (2.b) |
| Szektor-besorolás | IBKR `ContractDetails.industry / category` a GICS helyett | Nincs külön adatszolgáltató; a szektorszabály ehhez igazítva |
| Webelérés | Szerver-oldali web search / fetch az Anthropic API-n át; a container egresse: `api.anthropic.com` + belső hálózat | Egress allowlist megtartható; az SDK-támogatást a 4. fázisban ellenőrizni kell |
| Megfigyelhetőség | OTel SDK, GenAI semconv rögzítve: `gen-ai/1.42.0` (Development státusz) | A nevek változhatnak, ezért verziót rögzítünk |

## Rögzített verziók (PyPI, 2026-10-14)

| Csomag | Verzió |
|---|---|
| `claude-agent-sdk` | 0.2.166 |
| `a2a-sdk` | 1.2.2 (A2A spec 1.0) |
| `mcp` | 2.3.0 |
| `opentelemetry-sdk` | 1.45.1 |
| `opentelemetry-semantic-conventions` | 0.66b1 |
| `pydantic` | 2.14.1 |
| `sqlalchemy` | 2.1.4 |
| `alembic` | 1.20.0 |
| `psycopg` | 3.3.6 |
| `apscheduler` | 3.11.3 |
| `fastapi` | 0.143.0 (nem használjuk; a szerver Starlette + uvicorn) |
| `uvicorn` | 0.54.0 (5. fázis) |
| `httpx` | 0.28.1 (5. fázis) |
| Postgres image | `postgres:18.6` (5. fázis) |
| `redis` (csak ha kell) | 8.1.0 |

## Következmények és kockázatok

- **Webes tartalom → prompt injection:** a webet olvasó agentek (Market & Sentiment, Research) nem kapnak IBKR-író toolt, és megbízás csak emberi jóváhagyás után megy ki.
- **Fundamentumok minősége:** webes forrásból a számok pontatlanok lehetnek; a Research verifier-ellenőrző listája megköveteli a datált forrást minden számhoz.
- **TLS hiánya:** a belső forgalom titkosítatlan; csak megbízható, izolált Docker-hálózaton elfogadható.
- **ibkrfacade:** a beépített TWS API jar 2019-es; frissítését az ibkrfacade-feladatban kell megbeszélni.
- **Egy IBKR-session userenként:** dedikált paper loginra van szükség (feltételezés).
