# ORG_PROGRESS

Folytathatósági napló: döntések rövid indoklással, kész fázisok, nyitott kérdések, következő lépés. Minden fázis végén frissül.

Az indító brief: „Auxin – finomított indító prompt (agentic alapkezelő)” (okt. 14.), a projekt dokumentumai között.

## Állapot

| Fázis | Állapot |
|---|---|
| 0. Felderítés és célok | kész (repó-felderítés, monorepo-váz) |
| 1. Szervezeti terv | kész: `docs/ORG.md`, `org/org.yaml`, `org/rules/portfolio-rules.yaml`, `org/schema/agent.schema.json`, 4 `agent.yaml`, `scripts/validate_org.py` |
| 2. Technológiai és adatdöntések | kész: [`docs/adr/0001-tech-stack.md`](adr/0001-tech-stack.md) |
| 3. Feladat- és üzenetmodell | kész: [`docs/TASK_MODEL.md`](TASK_MODEL.md), `libs/auxin-schemas` (29 teszt) |
| 4. Agent-container sablon | kész: base image, `libs/auxin-runtime`, Market & Sentiment, egress proxy, compose; élő teszt Mihály gépén (2026-10-14): 40 teszt, egress OK, első scan `COMPLETED` (0,80 USD, 8 turn, 2 ötlet) |
| 5–9. | nincs elkezdve |

## Döntési napló

| Dátum | Döntés | Indoklás |
|---|---|---|
| 2026-10-13 | A repó üres volt, greenfield indulás | Nincs meglévő konvenció, amihez igazodni kell |
| 2026-10-14 | Domain: virtuális befektetési alapkezelő; core szerepek: Market & Sentiment, Research / Analyst, Portfolio Manager, Execution | Finomított brief |
| 2026-10-14 | ~~Agent ↔ agent kommunikáció központi Redis message buson~~ → leváltotta az A2A (lásd lent) | |
| 2026-10-14 | Portfólió = egyetlen IBKR számla (alapértelmezés: paper); írási jog csak az Execution agenté | Pénzügyi biztonság, a broker az igazságforrás |
| 2026-10-14 | Monorepo: `org/`, `agents/`, `libs/`, `mcp-servers/`, `services/`, `infra/`, `tests/`, `docs/` | Egy agent minden eleme egy könyvtárban; importált kód (`libs/`) és futó container (`services/`) külön |
| 2026-10-14 | Skillek az agentek alatt (`agents/<név>/skills/`), nincs közös skill-könyvtár | Egyelőre nincs közös skill; ha lesz, akkor jön `skills/` |
| 2026-10-14 | Agentenként `agent.yaml` + központi `org/org.yaml`, CI ellenőrzi az egyezést | Leíró az agent mellett, hierarchia egy helyen |
| 2026-10-14 | Skillek build-időben az image-be sütve; közös base image (`agents/Dockerfile`, Mihály kérésére nem alkönyvtár) + vékony agentenkénti Dockerfile | Immutable, auditálható image; biztonsági alapértékek egy helyen |
| 2026-10-14 | Nyelv: Python + `uv` workspace (verziók a 2. fázisban, webkereséssel ellenőrizve) | Agent SDK Python, IBKR- és adatkönyvtárak |
| 2026-10-14 | Git: közvetlenül `main`-re dolgozunk, nincs külön branch | Mihály kérése |
| 2026-10-14 | GitHubra egyelőre nem pusholunk; a helyi `main` mentése a projektmappában: `auxin/auxin-main.bundle` (fázisonként frissítve) | Mihály kérése; a cloud container ideiglenes |
| 2026-10-14 | 4 agent: Market & Sentiment, Research (egyben verifier), Portfolio Manager, Execution (LLM-agent) | Mihály döntése; a verifier szerep a Research része |
| 2026-10-14 | Minden agent Opus 5.5 | Mihály döntése; minőség a költség előtt |
| 2026-10-14 | Univerzum: globális részvények és ETF-ek, long only | Mihály döntése |
| 2026-10-14 | PM-szabályok külön fájlban: egyértelmű instrumentum (conid + tőzsde + deviza), ≥ 15% hozampotenciál, új pozíció ≤ 10% NAV, szektor ≤ 25% NAV (ideiglenes; besorolás: IBKR industry, lásd 2. fázis) | Mihály döntése; a szektorszabály felülvizsgálandó |
| 2026-10-14 | Legfeljebb 2 visszadobási kör tételenként | Mihály megerősítette |
| 2026-10-14 | Execution az ibkrfacade-et használja (`medovarszki/ibkrfacade`, Spring Boot REST a TWS API fölött, IB Gateway) az `mcp-servers/ibkr`-en át | Mihály döntése; a REST-nek nincs auth-ja, ezért csak belső hálózat |
| 2026-10-14 | Execution visszadobja a megbízást, ha nincs árinformáció | Mihály döntése |
| 2026-10-14 | Agent runtime: Claude Agent SDK (Python) | Programozott allowlist, hookok, költségmérés |
| 2026-10-14 | Agent ↔ agent: A2A 1.0 (`a2a-sdk` 1.2.2); audit: közös Postgres task store + OTel trace-ek; metaadatok saját A2A extensionben | Mihály: szabványos irány; a központi bus kiesett |
| 2026-10-14 | Egy Postgres mindenre; Redis csak az ibkrfacade árfolyam-tárolójaként | Egy auditálható igazságforrás |
| 2026-10-14 | Hitelesítés: agentenkénti bearer token, TLS később | **Jóváhagyott eltérés** a biztonsági alapértéktől (Mihály) |
| 2026-10-14 | Adat: IBKR (ár, hírek, contract) + szerver-oldali webkeresés; nincs külön fundamentum-API | Mihály döntése |
| 2026-10-14 | Szektor-besorolás: IBKR `industry` (nem GICS) | Nincs külön adatszolgáltató |
| 2026-10-14 | IBKR: IB Gateway (`gnzsnz/ib-gateway`) ← ibkrfacade ← `mcp-servers/ibkr`; az ibkrfacade-bővítést Mihály végzi egy külön prompt alapján (idempotens order, számlaösszesítő, historikus ár, hírek, tokenek, containerizálás) | Mihály saját projektje |
| 2026-10-14 | Verziók: lásd ADR 0001 (claude-agent-sdk 0.2.166, a2a-sdk 1.2.2, mcp 2.3.0, opentelemetry-sdk 1.45.1, GenAI semconv `gen-ai/1.42.0`) | Webes ellenőrzés, 2026-10-14 |
| 2026-10-14 | **Nincs emberi jóváhagyás** a megbízások előtt (tech demo, csak paper számla) | **Jóváhagyott eltérés** (Mihály); védelem: csak `DU` paper számla, ibkrfacade `IBKR_ALLOW_LIVE=false`; élő számlánál újra kötelező |
| 2026-10-14 | Market order az alapértelmezett megbízástípus | Mihály döntése |
| 2026-10-14 | Taszk-timeout 10 perc, nincs automatikus újrapróbálás; a hibás taszk `FAILED`, a következő ütemezett futás újra előveszi | Mihály: a lehető legegyszerűbb |
| 2026-10-14 | Taszkállapotok = A2A 1.0 állapotok (SUBMITTED, WORKING, COMPLETED, REJECTED, FAILED, CANCELED); metaadat-extension URI: `https://auxin.local/a2a/ext/message-metadata/v1` | Nincs saját állapotnév, nincs leképezési réteg |
| 2026-10-14 | Megbízás idempotencia-kulcsa: `decision_id` → ibkrfacade `client_order_id` | Egy döntésre soha nem megy ki két megbízás |
| 2026-10-14 | Python 3.12 (`.python-version`), `uv` workspace (`libs/*`), `uv.lock` a repóban; dev: pytest 9.1.1, pyyaml 6.0.3, jsonschema 4.26.0 | Reprodukálható környezet |
| 2026-10-14 | Build és futtatás Mihály gépén (Remote Control); a cloud containerben nincs Docker daemon és API-kulcs | Mihály döntése |
| 2026-10-14 | A Market & Sentiment az ibkrfacade elkészültéig csak webkereséssel fut; az MCP szerverek URL-je env-ből jön (`AUXIN_MCP_<NÉV>_URL`), ami nincs beállítva, annak a toolja kimarad | Mihály: valós IBKR-adat a facade után |
| 2026-10-14 | Egress: `internal: true` agent-hálózat + Squid proxy (`ubuntu/squid:6.6-24.04_edge`) allowlisttel (`api.anthropic.com`), minden kérés naplózva | Mihály döntése (3.a) |
| 2026-10-14 | Base image: `python:3.12.15-slim`, `astral/uv:0.13.1`, non-root uid 10001, read-only root FS + tmpfs, `cap_drop: ALL`, `no-new-privileges`, 1 CPU / 1 GB, futásonként `max_budget_usd: 2` | Biztonsági alapértékek |
| 2026-10-14 | Agent SDK: `permission_mode="dontAsk"`, `strict_mcp_config`, `setting_sources=["project"]`, skillek a `/agent/.claude/skills` alatt (root tulajdon, az agent nem módosíthatja), kimenet `output_format` JSON Schema-val; a CLI a wheelben natív binárisként érkezik (nem kell Node) | Ellenőrizve a 0.2.166 forrásában |
| 2026-10-14 | Feedback loop: `decision-evaluator` service (nem LLM) számol, a Research írja a tanulságot | Determinisztikus mérés, LLM csak az értelmezésre |
| 2026-10-14 | Host: Docker CE (docker.com apt repo), nem a snap-os docker | A snap-docker AppArmor-profilja `no-new-privileges` mellett minden container-exec-et tilt; a hardeninget nem lazítjuk |
| 2026-10-14 | Squid a `/var/log/squid/*.log`-ba naplóz, ezeket az image entrypointja a stdout-ra tail-eli | A `proxy` user nem tudja megnyitni a `/dev/stdout`-ot (a squid induláskor elhalt) |
| 2026-10-14 | A runner a `ClaudeSDKError`-t is `FAILED` taszkká alakítja | Az API-hiba eddig traceback-kel, `WORKING` állapotban hagyta a taszkot |
| 2026-10-14 | WebSearch / WebFetch szerver-oldali: ellenőrizve | Élő scan: a proxy csak `api.anthropic.com` CONNECT-et látott, a kimenet 18 forrásdomaint idéz; az allowlist marad egyetlen host |
| 2026-10-14 | `ANTHROPIC_API_KEY`: workspace-hez kötött Console-kulcs | A workspace nélküli kulcs 400-at ad (`anthropic-workspace-id` kell) |

## Feltételezések (megerősítésre várnak)

- Lokális `docker compose` futtatás, később szerverre vihető.
- Nincs short eladás; a „tanulás” memóriát jelent, nem finomhangolást; skill-módosítást csak Mihály hagy jóvá.

## Nyitott kérdések

- Sikerkritérium (benchmarkhoz mért teljesítmény, döntések indokolhatósága)?
- A szektorszabály felülvizsgálata (jelenleg ideiglenes).
- ibkrfacade-bővítés (Mihály, külön session): idempotens `POST /order`, számlaösszesítő, historikus ár, hírek, contract-besorolás, tokenek, containerizálás; a TWS API jar 2019-es.
- A `usage.server_tool_use.web_search_requests` 0, holott volt keresés: a Claude Code a WebSearch-öt külön al-hívásban futtatja. A valódi keresés- és költségszámot a runtime-nak kell majd gyűjtenie (a `cost_usd` tartalmazza-e az al-hívást? ellenőrizendő).
- Forrásminőség: az első scan gyenge forrásokat is idézett (pl. babypips.com, gokhshtein.com); kell-e forrásminőségi szabály vagy domain-preferencia a skillbe?
- Költség: kb. 0,80 USD / scan; az ütemezés gyakoriságát az `AUXIN_DAILY_COST_CAP_USD`-hez kell igazítani.
- TLS bevezetése a belső A2A-forgalomra (9. fázis).
- A verifier a Research része, így a saját javaslatát nem független szem ellenőrzi; később a risk egységbe költöztethető.

## Következő lépés

5. fázis (holnap, 2026-10-15): A2A réteg, közös Postgres task store.

Előfeltétel Mihály gépén: Docker CE, `make`, `uv`, kitöltött `.env` (workspace-hez kötött `ANTHROPIC_API_KEY`). Az ibkrfacade ugyanezen a gépen külön compose-projektben fut.

Ellenőrzés: `uv sync && make test && make validate`; élő: `make build && make egress-test && make scan`.
