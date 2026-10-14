# ORG_PROGRESS

Folytathatósági napló: döntések rövid indoklással, kész fázisok, nyitott kérdések, következő lépés. Minden fázis végén frissül.

Az indító brief: „Auxin – finomított indító prompt (agentic alapkezelő)” (okt. 14.), a projekt dokumentumai között.

## Állapot

| Fázis | Állapot |
|---|---|
| 0. Felderítés és célok | kész (repó-felderítés, monorepo-váz) |
| 1. Szervezeti terv | kész: `docs/ORG.md`, `org/org.yaml`, `org/rules/portfolio-rules.yaml`, `org/schema/agent.schema.json`, 4 `agent.yaml`, `scripts/validate_org.py` |
| 2. Technológiai és adatdöntések | következik |
| 3–9. | nincs elkezdve |

## Döntési napló

| Dátum | Döntés | Indoklás |
|---|---|---|
| 2026-10-13 | A repó üres volt, greenfield indulás | Nincs meglévő konvenció, amihez igazodni kell |
| 2026-10-14 | Domain: virtuális befektetési alapkezelő; core szerepek: Market & Sentiment, Research / Analyst, Portfolio Manager, Execution | Finomított brief |
| 2026-10-14 | Agent ↔ agent kommunikáció központi, perzisztált Redis message buson, kötelező metaadatokkal | Minden kommunikáció látható, naplózott, visszajátszható |
| 2026-10-14 | Portfólió = egyetlen IBKR számla (alapértelmezés: paper); írási jog csak az Execution agenté | Pénzügyi biztonság, a broker az igazságforrás |
| 2026-10-14 | Monorepo: `org/`, `agents/`, `libs/`, `mcp-servers/`, `services/`, `infra/`, `tests/`, `docs/` | Egy agent minden eleme egy könyvtárban; importált kód (`libs/`) és futó container (`services/`) külön |
| 2026-10-14 | Skillek az agentek alatt (`agents/<név>/skills/`), nincs közös skill-könyvtár | Egyelőre nincs közös skill; ha lesz, akkor jön `skills/` |
| 2026-10-14 | Agentenként `agent.yaml` + központi `org/org.yaml`, CI ellenőrzi az egyezést | Leíró az agent mellett, hierarchia egy helyen |
| 2026-10-14 | Skillek build-időben az image-be sütve; közös `_base` image + vékony agentenkénti Dockerfile | Immutable, auditálható image; biztonsági alapértékek egy helyen |
| 2026-10-14 | Nyelv: Python + `uv` workspace (verziók a 2. fázisban, webkereséssel ellenőrizve) | Agent SDK Python, IBKR- és adatkönyvtárak |
| 2026-10-14 | Git: közvetlenül `main`-re dolgozunk, nincs külön branch | Mihály kérése |
| 2026-10-14 | GitHubra egyelőre nem pusholunk; a helyi `main` mentése a projektmappában: `auxin/auxin-main.bundle` (fázisonként frissítve) | Mihály kérése; a cloud container ideiglenes |
| 2026-10-14 | 4 agent: Market & Sentiment, Research (egyben verifier), Portfolio Manager, Execution (LLM-agent) | Mihály döntése; a verifier szerep a Research része |
| 2026-10-14 | Minden agent Opus 5.5 | Mihály döntése; minőség a költség előtt |
| 2026-10-14 | Univerzum: globális részvények és ETF-ek, long only | Mihály döntése |
| 2026-10-14 | PM-szabályok külön fájlban: egyértelmű instrumentum (conid + tőzsde + deviza), ≥ 15% hozampotenciál, új pozíció ≤ 10% NAV, GICS-szektor ≤ 25% NAV (ideiglenes) | Mihály döntése; a szektorszabály felülvizsgálandó |
| 2026-10-14 | Legfeljebb 2 visszadobási kör tételenként; emberi jóváhagyás minden megbízás előtt | Mihály megerősítette |
| 2026-10-14 | Execution az ibkrfacade-et használja (`medovarszki/ibkrfacade`, Spring Boot REST a TWS API fölött, IB Gateway) az `mcp-servers/ibkr`-en át | Mihály döntése; a REST-nek nincs auth-ja, ezért csak belső hálózat |
| 2026-10-14 | Execution visszadobja a megbízást, ha nincs árinformáció | Mihály döntése |
| 2026-10-14 | Feedback loop: `decision-evaluator` service (nem LLM) számol, a Research írja a tanulságot | Determinisztikus mérés, LLM csak az értelmezésre |

## Feltételezések (megerősítésre várnak)

- Lokális `docker compose` futtatás, később szerverre vihető.
- A2A egyelőre nincs; a bus üzenetborítéka A2A-kompatibilis alakú.
- Nincs short eladás; a „tanulás” memóriát jelent, nem finomhangolást; skill-módosítást csak Mihály hagy jóvá.
- Emberi jóváhagyás minden megbízás előtt.

## Nyitott kérdések

- Melyik piac és eszközosztály (US részvény, EU, ETF)?
- Sikerkritérium (benchmarkhoz mért teljesítmény, döntések indokolhatósága)?
- A szektorszabály felülvizsgálata (jelenleg ideiglenes).
- ibkrfacade: hiányzik a számlaösszesítő végpont (NAV, cash, margin); a 4. fázisban pótolni kell.
- GICS-besorolás adatforrása (2. fázis).
- A verifier a Research része, így a saját javaslatát nem független szem ellenőrzi; később a risk egységbe költöztethető.

## Következő lépés

2. fázis: technológiai és adatdöntések (Agent SDK vs headless Claude Code, task store, ütemező, Redis Streams, adatforrások, IBKR-integráció részletei, verziók webkereséssel ellenőrizve).

Ellenőrzés: `python3 scripts/validate_org.py` (PyYAML, jsonschema).
