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
| 5. Kommunikációs réteg | kész: `libs/auxin-a2a`, A2A szerverek, Postgres task store, `make scan` / `make tasks`; élő teszt OK (2026-10-15) |
| 6. Döntési hurkok | 6.1 kész (IBKR MCP, élő teszt OK); 6.2 kész (`services/knowledge`, élő teszt OK); 6.3 kész (élő teszt OK: első paper fill); 6.4 kész (élő teszt: HOLD, a SELL-ág élesben még nem futott); 6.5 kész (scheduler élesben fut; a tanulság-ág az első zárásnál fut először) |
| 7–9. | nincs elkezdve |

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
| 2026-10-14 | Push csak Mihály kifejezett kérésére; a helyi `main` mentése a projektmappában: `auxin/auxin-main.bundle` | Mihály kérése; a cloud container ideiglenes |
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
| 2026-10-14 | ~~Hitelesítés: agentenkénti bearer token, TLS később~~ → lásd 2026-10-15 | |
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
| 2026-10-14 | ~~`ANTHROPIC_API_KEY`: workspace-hez kötött Console-kulcs~~ → lásd 2026-10-15 | |
| 2026-10-15 | **Egyelőre nincs A2A auth** (se token, se TLS); védelem csak az `internal` Docker-hálózat | **Jóváhagyott eltérés** (Mihály): előbb működő agent-hálózat, a jogosultságkezelés később |
| 2026-10-15 | Az 5. fázisban nincs új unit teszt; bizonyíték a futó rendszer és a task tábla | Mihály döntése: később építjük be |
| 2026-10-15 | Minden agent A2A szerver (`auxin-agent serve`, JSON-RPC + SSE, port 8000, Agent Card az `agent.yaml`-ból: a `messages.consumes` lesz a skill-lista); a kliens `trust_env=False`-szal megy, így a belső forgalom nem a proxyn át | Az A2A 1.0 alapértelmezése; a proxy csak a Claude API-é |
| 2026-10-15 | Közös task store: egy Postgres tábla (`a2a_tasks`, `a2a-sdk` `DatabaseTaskStore`), egy role; `owner` = a végrehajtó agent, a `metadata` mezőben a routing (sender, type, subject, correlation_id, trace_id) | Mihály döntése (3.b); egy lekérdezés mutatja a teljes folyamatot |
| 2026-10-15 | Metaadat: `task_id` = a küldő saját taszkja, `correlation_id` = a folyamat (scan) azonosítója, `trace_id` a teljes láncon közös; az átadott ötlet A2A `reference_task_ids`-ben hivatkozik a scan-taszkra | Az A2A-ban a címzett nyit új taszkot, a küldő nem adhat neki ID-t |
| 2026-10-15 | Rossz címzett, nem fogadott típus vagy hiányzó metaadat → `REJECTED`; handler-hiba vagy 10 perces timeout → `FAILED`; tartalmi elutasítás (`Rejected`) → `REJECTED` | TASK_MODEL szerint |
| 2026-10-15 | A Research az 5. fázisban LLM nélküli stub: validálja és elmenti az ötletet (`COMPLETED`); a valódi Research a 6. fázisban | Olcsó, az A2A-t önmagában bizonyítja |
| 2026-10-15 | A scant egyelőre a `make scan` indítja (egy rövid életű `operator` container küldi a `scan_trigger`-t); a `scheduler` service a 6. fázisban | Mihály döntése (2.a) |
| 2026-10-15 | Containerenként csak a szükséges env változó (a compose a gyökér `.env`-ből interpolál; a Research és a Postgres nem kapja meg az API-kulcsot) | Legkisebb jogosultság |
| 2026-10-15 | A PM pozíció-review-ja **napi** (munkanapokon, 15:30), nem heti | Mihály döntése |
| 2026-10-15 | ibkrfacade-bővítés kész (Mihály, `d744047`): Spring Boot 4.1.1, TWS API 10.50.01, Docker + compose (`gnzsnz/ib-gateway:10.50.1f`, Redis 8.8.3), idempotens `POST /order`, account summary, history, positions P&L, contract industry/category, hírek, read/write token, paper/live védelem; 54 unit teszt zöld (ellenőrizve) | Az Execution és a PM IBKR-oldala erre épül |
| 2026-10-15 | IBKR MCP: egy szerver mindkét ibkrfacade-tokennel, a jogosultság a tool-allowlist (Execution: írás) | Mihály döntése (1.b) |
| 2026-10-15 | Piaci adat: élő (`IBKR_MARKET_DATA_TYPE=1`, a live számla előfizetései megosztva a paperrel) | Mihály (2.a) |
| 2026-10-15 | **Execution: determinisztikus service, nem LLM-agent** | Mihály (3.a): olcsóbb, kiszámítható, nincs prompt injection az író jog mellett |
| 2026-10-15 | **Verify: determinisztikus ellenőrzés** (a megbízás egyezik a PM döntésével, a javaslattal és a szabályfájllal); nincs Research `verify_request` kör | Mihály (4.a) |
| 2026-10-15 | Max. 3 ötlet / scan; kimarad, ami a portfólióban van vagy 30 napon belül elutasított (új információ nélkül) | Mihály (5.a) |
| 2026-10-15 | Pozícióméret conviction szerint: 1–5 → 2 / 4 / 6 / 8 / 10% NAV, a szabályok és a szabad cash korlátjával | Mihály (6.a) |
| 2026-10-15 | Csak szabad cash, nincs margin / tőkeáttétel | Mihály (7.a) |
| 2026-10-15 | Deviza: az IBKR automatikus deviza-kölcsöne elfogadott (nincs külön FX-megbízás) | Mihály (8.a) |
| 2026-10-15 | Megbízás csak az instrumentum kereskedési idejében megy ki; zárt piacnál a task store-ban vár a nyitásig | Mihály (9.a); az ibkrfacade 15 percnél régebbi árral 422-t ad |
| 2026-10-15 | DAY megbízás; a zárásig nem teljesült rész törlődik, a PM új döntéssel (új `decision_id`) próbálhatja újra | Mihály (10.a) |
| 2026-10-15 | **Napi review: minden nyitott pozíció teljes LLM-es Research-újraértékelést kap** | Mihály (11.b); ez a fő költségtényező |
| 2026-10-15 | Ütemezés (Europe/Budapest, munkanapokon): **09:00 scan, 15:30 review** (US nyitás), **21:00 kiértékelés** | Mihály (12) |
| 2026-10-15 | Nincs kötelező veszteség-trigger és nincs automatikus stop-loss | Mihály (13.c) |
| 2026-10-15 | Az `idea_reject` a tudásbázisba kerül; a Market & Sentiment új információ nélkül nem javasolja újra | Mihály (14.a) |
| 2026-10-15 | Hibáknál nincs értesítés, csak napló és dashboard | Mihály (16.a) |
| 2026-10-15 | Feedback loop: **nincs benchmark**, a kiértékelés csak a pozíció lezárásakor történik; sikerkritérium: a hozam | Mihály (17, 18.b, 26.b) |
| 2026-10-15 | Tudásbázis-keresés: Postgres full-text, pgvector később | Mihály (19.a) |
| 2026-10-15 | Egyelőre nincs árhatás-számítás a cégmemóriában és nincs skill-/szabálymódosítási javaslat-folyamat | Mihály (20, 21) |
| 2026-10-15 | Dashboard: saját egyszerű web UI, Postgres read-only, csak localhostra publikálva | Mihály (22.a) |
| 2026-10-15 | Most nincs tesztelés (e2e, mock broker, rögzített LLM-kimenetek) | Mihály (24, 25) |
| 2026-10-15 | Szektorszabály marad; forrásminőség a modellre bízva; futtatás Mihály gépén, lokális compose | Mihály (27.a, 28.b, 29.a) |
| 2026-10-15 | ibkrfacade: ISIN és `subcategory` pótlása a contract-válaszban (prompt: `auxin/ibkrfacade-prompt-isin.md`) | Mihály (30.b) |
| 2026-10-15 | **Claude-hozzáférés: csak Mihály előfizetésének kerete** (`CLAUDE_CODE_OAUTH_TOKEN`, `claude setup-token`); `ANTHROPIC_API_KEY` sehol, a runtime megáll, ha be van állítva; nincs USD-költségplafon | Mihály döntése (15.); az Anthropic support szerint (2026-06) az Agent SDK saját belépéssel az előfizetés keretéből fogy. Kockázat: a heti keret közös Mihály saját Claude-használatával |
| 2026-10-15 | Trace-backend: Jaeger all-in-one, lokálisan (7. fázis) | Mihály (23.a) |
| 2026-10-15 | **Portfolio Manager: LLM-agent marad** (a szabálykaput és a conviction-méretezést a runtime determinisztikusan ellenőrzi a kimenetén, a döntés indoklása az LLM-é) | Mihály döntése (6. fázis terv, 1.b) |
| 2026-10-15 | **Tudásbázis-írás: a runtime menti** a Research strukturált kimenetéből (javaslat, elutasítás, tanulság, cégjegyzet); az LLM-agentek csak olvasnak (MCP) | Mihály (6. fázis terv, 2.a): nincs író tool az LLM kezében |
| 2026-10-15 | **5. fázis élő teszt kész** Mihály gépén (Docker CE): `make scan` → 1 `scan_trigger` (market-sentiment) + 2 `idea` (research: VLO, XLV), mind `COMPLETED`, közös trace, közös Postgres task store; 1 p 30 mp, 7 turn. A `CLAUDE_CODE_OAUTH_TOKEN` az Agent SDK-val a containerből működik (a proxy csak `api.anthropic.com`-ot látott) | Lezárja az 5. fázist; a `cost_usd` előfizetésnél csak névleges |
| 2026-10-15 | **A tőzsdei kapcsolat teljes egészében az ibkrfacade-ra épül**: az ibkrfacade saját stackje (IB Gateway, Redis, facade) a saját checkoutjából és `.env`-jével fut (`make ibkr-up`, a `make up` is elindítja; `IBKRFACADE_DIR`, alapérték `../ibkrfacade`). Gateway-mód, login, tokenek és image az ibkrfacade repó felelőssége; az Auxin csak a REST-et látja (`http://ibkrfacade:8082/ibkr`, `ibkr-backend` hálózat). Broker-oldali üzleti logika az ibkrfacade-be kerül (Mihály); `make ibkr-check`: health, paper számla, egy ár, megbízás nélkül | Mihály döntése |
| 2026-10-15 | **Broker élő**: az ibkrfacade beépített ib-gateway-e fut (az ibkrfacade `.env`-jében a host-TWS `COMPOSE_FILE` kikommentelve), health UP, `PAPER`, `DU…` számla; account summary, search, contract (industry/category) működik. Hiány: a `/price` előfizetés nélkül elavult (Redis) árat ad frissesség-jelzés nélkül → ibkrfacade-feladat (`auxin/ibkrfacade-prompt-price.md`) | A megbízást az ibkrfacade 15 percnél régebbi árral úgyis elutasítja; a kockázat a PM méretezése |
| 2026-10-15 | ibkrfacade `7c2ac19` (Mihály): account summary egyetlen tartós előfizetésből (a Gateway 10.50 figyelmen kívül hagyja a protobuf `cancelAccountSummary`-t → 322), `updated_at`; `/price` automatikus subscribe, `quote_age_seconds`, `stale`, `market_data_type`, `max_age` → 422 `STALE_MARKET_DATA`. 68 unit teszt zöld (ellenőrizve) | A PM a NAV-ot és a friss árat ebből kapja |
| 2026-10-15 | **Nincs token az ibkrfacade felé**: az ibkrfacade `.env`-jében `IBKR_SECURITY_ENABLED=false`; a facade csak a belső `ibkr-backend` hálózaton érhető el | Mihály döntése: egyelőre csak működjön a kommunikáció (mint az A2A-nál) |
| 2026-10-15 | **6.1 IBKR MCP szerver** (`mcp-servers/ibkr`, `mcp` 2.3.0 – a PyPI legfrissebb, 2026-10-02 –, `MCPServer`, stateless streamable HTTP, JSON-válasz): 7 olvasó tool, tömörített válaszok, a facade-hibák `KÓD: részletek` tool-hibaként; csak az MCP container van az `ibkr-backend` hálózaton. A Market & Sentiment megkapja (`AUXIN_MCP_IBKR_URL`), az ötletek IBKR conidra oldva, max. 3 ötlet (a séma is) | Az Execution determinisztikus, ezért nincs író tool; a portfólió- és tiltólista-szűrés (5.a) a 6.2 után |
| 2026-10-15 | **6.1 élő teszt kész** Mihály gépén: make scan → 2 ötlet (XLV conid 4215205, XLE conid 4215217, ARCA, USD), mind COMPLETED, közös trace; az agent az MCP-n át token nélkül hívta a facade-et (search, history, price, contract, account); 10 turn | Az ötletekben először van valódi IBKR conid |
| 2026-10-16 | **ETF = külön kategória szektorlimit nélkül**, csak a 10% NAV pozíciólimit; részvényeknél marad az IBKR `industry` a 25%-os szektorszabályhoz | Mihály (1.b) |
| 2026-10-16 | **Tudásbázis: külön `services/knowledge` szolgáltatás** (Python, egy containerben REST az írásra – runtime, Execution, evaluator – és MCP olvasó toolok az LLM-eknek); a `mcp-servers/knowledge-base` kimarad; csak ez a service ír a tudásbázis-táblákba | Mihály (2.a): egy gazda a sémának; Python, hogy a `libs/auxin-schemas` Pydantic-modelljei ne duplikálódjanak Java DTO-kban |
| 2026-10-16 | Sémakezelés: **SQLAlchemy-modellek + Alembic autogenerate** (a Flyway megfelelője, de a migrációt a modellből generálja: `make db-revision m="..."`, átnézés, commit); a service induláskor `upgrade head`; saját verziótábla (`knowledge_alembic_version`), az autogenerate csak a saját tábláit nézi (az `a2a_tasks` az A2A rétegé). A generált tsvector-oszlopot és GIN-indexet is felismeri | Mihály: ne kelljen kézzel SQL-t karbantartani; Python-stack marad |
| 2026-10-16 | Verziók (PyPI, `uv` feloldás 2026-10-16): alembic 1.20.0, fastapi 0.143.2; meglévő: sqlalchemy 2.1.4, asyncpg 0.32.0, mcp 2.3.0, uvicorn 0.54.0 | A webkeresés régebbit mutatott (1.18.4 / 0.136.3); a PyPI-index a mérvadó |
| 2026-10-16 | **6.2 tudásbázis** (`services/knowledge`): táblák `decisions` (eseménynapló: idea, idea_reject, proposal, proposal_reject, order, order_reject, fill, review; `id` = a domain-objektum azonosítója, `idea_id` a láncot, `decision_id` a PM-döntést köti; `payload` és `snapshot` jsonb), `company_notes`, `lessons`; mindegyikben generált `tsvector` (english) + GIN. Írás csak REST-en, idempotensen (`ON CONFLICT DO NOTHING`); közös rekordmodellek: `auxin_schemas.knowledge`. A runtime minden ötletet a kiküldés előtt beír (`kind=idea`); sikertelen írásnál a scan `FAILED` (a napló nem veszíthet bejegyzést). MCP-szerver neve `knowledge-base` (`AUXIN_MCP_KNOWLEDGE_BASE_URL`). A Market & Sentiment kiszűri a portfólióban lévőt (`get_positions`) és a 30 napon belül elutasítottat (`get_recent_rejections`), kivéve új, forrással igazolt információnál | Terv 6.2; az (5.a) szűrés ezzel kész |
| 2026-10-16 | **6.2 élő teszt kész** Mihály gépén (Docker CE): a `knowledge` container `healthy`, induláskor `upgrade -> 0001`; `make scan` → 1 ötlet (XLE, conid 4215217), a runtime beírta (`kb_recorded`, `kind=idea`, közös trace a task store-ral), mind `COMPLETED`, 16 turn; `make kb-check`: REST health, `decisions`, `rejections` (üres), 3 MCP tool, a `search` megtalálja az ötletet. Hogy az agent ténylegesen hívta-e a `get_positions` / `get_recent_rejections` toolt, a log nem mutatja (portfólió és tiltólista most üres) | A tudásbázis és a szűrés működik |
| 2026-10-16 | Host: a snap-docker eltávolítva (letörölte a `/run/docker.sock`-ot; `systemctl restart docker.socket docker` után OK); a régi containerek hálózatai elvesztek, `make down` / `ibkr-down` után újraépültek | Csak Docker CE fut |
| 2026-10-16 | Egy közös Postgres-role marad: az „egyedül a knowledge service ír” megállapodás, DB-jogosultsággal még nincs kikényszerítve | Mint az A2A-auth: később |
| 2026-10-16 | Szabályfájl: `etf_treatment` → minden ETF `diversified` | Az ETF-döntés (1.b) rögzítése |
| 2026-10-16 | **A szervezeti modell a README-ben**, naprakészen tartva (egységek, pozíciók, folyamatok, szabályok, ellenőrzési pontok); a `docs/ORG.md` történeti | Mihály kérése |
| 2026-10-16 | **MVP-szemlélet**: opcióknál az implementációban legegyszerűbb az alapértelmezés; a meglévő (MVP-n túli) elemeket nem bontjuk vissza | Mihály |
| 2026-10-16 | 6.3: a lánc szinkron marad, `TASK_TIMEOUT` 10 → 60 perc; a PM-kapu az IBKR MCP-n át olvas (csak az MCP és az Execution van az `ibkr-backend` hálózaton); zárt piacnál függő megbízás, a 15:30-as futás (addig `make execute-pending`) adja le; azonnal éles paper megbízás; nincs visszadobási kör (MVP-eltérés a „max. 2 kör” szabálytól); Research cégjegyzet nélkül, Execution egyszeri státusz-lekérdezéssel | Mihály (1: legegyszerűbb, 2: magyarázat után, 3.b, 4.b) |
| 2026-10-16 | **6.3 vételi hurok (kód)**: Research (LLM, `idea-challenge` skill) → `ResearchOutput` (propose / reject); PM (LLM, `proposal-review` skill) → `PMDecision` (BUY / REJECT) → a runtime-kapu (`auxin_schemas.rules.size_buy`) az IBKR MCP-n át olvas (számla, pozíciók, contract, ár) és méretez; Execution: determinisztikus handler ugyanabban a runtime-ban (`agents/execution`, `kind: deterministic`, nincs Claude-token), egyedül ő van az `ibkr-backend`-en. Napló-események: idea, idea_reject, proposal, proposal_reject, order (`snapshot`-tal), `order_submitted` (új), fill, order_reject; determinisztikus esemény-id (`uuid5(decision_id, kind)`) → idempotens | Terv 6.3 |
| 2026-10-16 | Az Execution `agents/execution` alatt marad (nem `services/execution`), mert ugyanazt az A2A runtime-ot használja; az `agent.schema.json` kapott egy `kind` mezőt (`llm` / `deterministic`) | Legegyszerűbb: nincs külön A2A-szerverkód |
| 2026-10-16 | PM-kapu ár: friss quote (ask, különben last); zárt piacnál / `stale` esetén az utolsó napi záróár (`get_history`), `snapshot.price_source = last_close`; a leadáshoz az ibkrfacade úgyis friss bid/askot kér (422 → `order_reject NO_PRICE`) | A 09:00-s scan az US-piac nyitása előtt fut |
| 2026-10-16 | MVP-korlátok a kapuban: csak bázisdevizás instrumentum (nincs FX-adat; a többi `proposal_reject currency`), meglévő pozíció nem növelhető (`already_held`); a szabad cash = min(`total_cash_value`, `available_funds`) | Egyszerűség; nyitott kérdés lesz, ha nem-USD ötletek jönnek |
| 2026-10-16 | A Research verifier-szerepe és a `verify_request` / `verify_result` / `order_draft` üzenetek kikerültek az `agent.yaml`-okból (a verify determinisztikus, 2026-10-15) | Leíró = valóság |
| 2026-10-16 | Élő teszt akadálya: az IBKR `10197 No market data during competing live session` / „Trading TWS session is connected from a different IP address”: amíg a live felhasználó máshol (TWS, Client Portal, mobil) be van lépve, a paper Gateway nem kap árat és historikus adatot | Mihálynak ki kell lépnie a másik sessionből |
| 2026-10-16 | **Nincs portfólió-tükör** (`positions_mirror`, `account_mirror` kimarad): pozíció és számla élőben az ibkrfacade-ből; minden döntés mellé pillanatkép (NAV, cash, érintett pozíciók) a `decisions` sorban; tükör a 7. fázisban, a dashboarddal | Mihály (3.a): egyszerűség |
| 2026-10-16 | A competing-session hiba (10197) magától megszűnt; helyette `10089 requires additional subscription for API` a NYSE Arca ETF-ekre (XLE, XLV, SPY). Az ibkrfacade `.env`: `IBKR_MARKET_DATA_TYPE=3` (Mihály lokális fájlja, nem a repó): ahol van élő előfizetés, élő adat jön (AAPL, MSFT `LIVE`), egyébként 15 perccel késleltetett (`DELAYED`, nem `stale`) | Mihály: a fő US részvényekre van élő előfizetés |
| 2026-10-16 | Első élő scan (Mihály, trace `3acce09d`): XLV → `idea_reject` (nincs 15% upside); SU (Schneider Electric, EUR) → `proposal` → PM BUY → kapu `proposal_reject` (EUR ≠ USD). Javítás: a Market & Sentiment `idea-generation` és a Research `idea-challenge` skillje csak USD-s instrumentumot (US listing / ADR) enged (a kapu szabályának a promptban is meg kell jelennie) | Ne menjen kör nem kereskedhető ötletre |
| 2026-10-16 | **6.3 élő teszt kész** (trace `443e36c5`, 15:41 CEST): TSM (TSMC ADR, conid 6223250) idea → proposal (conviction 3) → PM BUY → kapu: 144 db, ~59 993 USD (6% NAV) → Execution: paper számla OK, piac nyitva, `POST /order` MKT DAY → IBKR order 1 → **Filled 144 @ 416.62 USD**, jutalék ~1.00 USD (4 részletben, ~5 s alatt). Pozíció az IBKR-ben: 144 TSM | Az első paper megbízás Mihály 4.b döntése alapján |
| 2026-10-16 | Javítások a teszt után: az Execution 5 s után egyszer nézett státuszt (még `working`) → most legfeljebb 6 × 5 s-ig; a fillt a `make execute-pending` rögzítette, de trace nélkül, mert a `GET /decisions` nem adta vissza a `trace_id` / `correlation_id` / `task_id` mezőt → a részletes lekérdezés most visszaadja. A fill sor trace-ét egyszeri SQL `UPDATE` pótolta az order sorból | A lánc egy trace-en látszik |
| 2026-10-16 | 6.4 döntések: a Research review-javaslatát a PM runtime LLM-hívás nélkül hajtja végre (1.a); minden nyitott pozíció minden nap review-t kap, a frisseket is (2.b); a review-k egymás után, egy `review_trigger` taszkban, timeout 4 óra (3.a); REDUCE = floor((jelenlegi súly − cél-súly) × NAV / ár), legalább 1 db, legfeljebb a tartott mennyiség, a nem kisebb cél-súly HOLD (4.a) | Mihály |
| 2026-10-16 | **6.4 napi review és eladás (kód)**: `review_trigger` → PM runtime: `execute_pending` az Executionnek, majd pozíciónként (IBKR MCP: számla, pozíciók, contract) `review_request` (`ReviewRequest`: `Holding` + a vételi javaslat és order a naplóból) a Researchnek → Research (LLM, `position-review` skill) → `ReviewResult` (HOLD / REDUCE / CLOSE), `review` napló-bejegyzés → `auxin_schemas.rules.size_sell` → SELL `order` (napló, pillanatkép) → Execution (új ellenőrzés: SELL ≤ tartott mennyiség, különben `MISMATCH`). A Research eredménye a taszk artifactja (nincs külön `review_result` üzenet). Timeout taszktípusonként (`auxin_schemas.task.task_timeout`): `review_trigger` 4 óra, a többi 60 perc; a `portfolio-rules.yaml` `task_timeout_minutes` 10 → 60. `make review` | Terv 6.4 |
| 2026-10-16 | **6.4 élő teszt** (trace `02a888cc`, 18:12 CEST): `execute_pending` (üres) → TSM review (5.97% NAV) → Research: **HOLD** (célár 490 USD, ~18% upside, egyik exit-trigger sem teljesült; 5 datált forrás, 6 turn, ~0.23 nominál USD) → nincs megbízás; mind `COMPLETED`, a `review` a naplóban. A REDUCE / CLOSE → SELL ág és az Execution SELL-ellenőrzése élesben még nem futott (a méretezés offline ellenőrizve: CLOSE 144, REDUCE 6→3% 71 db) | Az első valódi eladás az első REDUCE / CLOSE javaslatnál |
| 2026-10-16 | 6.5 döntések: a kiértékelés a scheduler containerben fut, nincs külön `decision-evaluator` (1.a); lezárt pozíció = az eladások kiadják a vett mennyiséget, hozam = (bevétel − költség − jutalék) / költség, a részleges REDUCE csak a zárással értékelődik (2.a); hétfő–péntek, tőzsdei ünnepnap-naptár nélkül (3.a); élő teszt kézi jobokkal, a tanulság-ág az első valódi zárásnál (4.a) | Mihály |
| 2026-10-16 | Verzió: APScheduler **3.11.3** (`uv` feloldás és webkeresés, piwheels: 3.11.3, 2026-06-28; a 4.0 csak alpha), függőségei tzlocal 5.4.4, tzdata 2026.5 | 3.x stabil API (`AsyncIOScheduler`, `CronTrigger`) |
| 2026-10-16 | **6.5 (kód)**: `services/scheduler` (`auxin-scheduler`, workspace-tag, a közös base image-ben): `CronTrigger(day_of_week=mon-fri, Europe/Budapest)`, 09:00 `scan` → Market & Sentiment, 15:30 `review` → PM, 21:00 `evaluate`; `max_instances=1`, `coalesce`, `misfire_grace_time` 5 perc; minden futás saját trace, `sender=scheduler`. `evaluate`: a napló fill-jeiből (`ibkr.action` BUY / SELL, időrendben) a lezárt ciklusok → `DecisionOutcome` (benchmark nélkül: költség, bevétel, jutalék, P&L, hozam, nyitás / zárás, napok; `decision_id` = a záró SELL döntése) → `decision_outcome` bejegyzés (id = `uuid5(decision_id, "decision_outcome")`, a már kiértékelt kimarad) → `decision_outcome` üzenet a Researchnek → `lesson` skill → `LessonDraft` → a runtime a `lessons` táblába írja (`POST /lessons`, id = `uuid5(decision_id, "lesson")`). Container: hardening, csak `agents` hálózat, nincs Claude-token. `make run-job job=scan\|review\|evaluate` | Terv 6.5 |
| 2026-10-16 | **6.5 élő teszt**: a scheduler fut, a következő futások: `evaluate` 2026-10-16 21:00, `scan` 2026-10-19 09:00, `review` 2026-10-19 15:30 (CEST). Kézi jobok: `evaluate` → `closed_positions: []` (nincs lezárt pozíció); `review` → TSM HOLD (trace `a1797b12`, `bdcc5dab`); `scan` → GDX (`8eef668f`) és BNY (`dc947d83`), mindkettő `idea_reject` (nincs 15% upside), megbízás nem lett. A review és a scan véletlenül kétszer futott (egy hibás kimenet-feldolgozás után újraindítottam, holott az első futás sikeres volt). Az evaluator számítása offline ellenőrizve (100 db vétel, két részeladás: +137 USD, +13,7%, 19 nap; az újranyitott pozíció nyitva marad) | A tanulság-ág és a SELL-ág élesben még nem futott |

## Feltételezések (megerősítésre várnak)

- Lokális `docker compose` futtatás, később szerverre vihető.
- Nincs short eladás; a „tanulás” memóriát jelent, nem finomhangolást; skill-módosítást csak Mihály hagy jóvá.

## Nyitott kérdések

- A szektorszabály felülvizsgálata (jelenleg ideiglenes).
- A `usage.server_tool_use.web_search_requests` 0, holott volt keresés: a Claude Code a WebSearch-öt külön al-hívásban futtatja. A valódi keresés- és költségszámot a runtime-nak kell majd gyűjtenie (a `cost_usd` tartalmazza-e az al-hívást? ellenőrizendő).
- Előfizetési keret: kell-e napi taszk-limit, hogy az agentek ne fogyasszák el a heti keretet (a napi teljes review pozíciónként fut)?
- A2A auth (agentenkénti token, ki kitől mit fogadhat el) és TLS a belső forgalomra: később (Mihály).
- Unit tesztek az `auxin-a2a`-hoz (metaadat-elutasítás, timeout): később (Mihály).
- A verifier a Research része, így a saját javaslatát nem független szem ellenőrzi; később a risk egységbe költöztethető.

## Következő lépés

A 6. fázis kész: a szervezet önállóan fut (09:00 scan, 15:30 review, 21:00 kiértékelés). Figyelendő az első REDUCE / CLOSE (SELL-ág) és az első zárás (tanulság-ág). Következő: 7. fázis (dashboard, trace), előtte döntés és kérdések.

Előfeltétel Mihály gépén: Docker CE, `make`, `uv`, kitöltött `.env` (`CLAUDE_CODE_OAUTH_TOKEN`, `POSTGRES_PASSWORD`; `ANTHROPIC_API_KEY` nincs). Az ibkrfacade ugyanezen a gépen külön compose-projektben fut.
