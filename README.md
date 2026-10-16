# Auxin – agentic investment organization

Az Auxin **agentekből álló befektetési alapkezelő**, amely egy valódi alapkezelő szervezetét kívánja modellezni: szervezeti egységek, pozíciók, jelentési vonalak, felelősségi körök, írott befektetési szabályok, ellenőrzési pontok és döntési napló. A szerepeket Claude-alapú (Opus) LLM-agentek és determinisztikus szolgáltatások töltik be. Minden szerep külön Docker containerben fut. Az agentek A2A 1.0 protokollon kommunikálnak, minden feladat egy közös Postgres task store-ba kerül, a döntések egy tudásbázisba. A portfólió egyetlen Interactive Brokers **paper** számla.

> Állapot: **MVP, fejlesztés alatt.** Az aktuális fázis és a döntési napló: [`docs/ORG_PROGRESS.md`](docs/ORG_PROGRESS.md).
> Az agentek kimenete nem befektetési tanácsadás.

## Szervezeti modell

Ez a fejezet a szervezet naprakész leírása. Gépileg olvasható megfelelői: [`org/org.yaml`](org/org.yaml) (egységek, pozíciók, jelentési vonalak), [`org/rules/portfolio-rules.yaml`](org/rules/portfolio-rules.yaml) (befektetési szabályok), `agents/<név>/agent.yaml` (szerepenkénti leíró). Az eredeti, 1. fázisbeli terv: [`docs/ORG.md`](docs/ORG.md).

### Egységek

| Egység | Állapot | Pozíciók |
|---|---|---|
| **Core** (befektetési egység) | működik (vétel); a review és eladás épül | Market & Sentiment, Research, Portfolio Manager, Execution |
| Risk | tervezett | független kockázatkezelés, limitfelügyelet |
| Compliance | tervezett | szabálymegfelelés, audit |
| Operations | tervezett | elszámolás, egyeztetés a brokerrel |
| Reporting | tervezett | teljesítményjelentések, dashboard |

### Szervezeti ábra

```
                         Mihály (ember)
              jóváhagyja: szabály-, skill-, promptmódosítás
                               │
                      Portfolio Manager (LLM)
          ┌────────────────────┼────────────────────┐
 Market & Sentiment (LLM)  Research (LLM)   Execution (determinisztikus)
```

### Pozíciók

| Pozíció | Típus | Állapot | Felelősség | Fogad | Küld |
|---|---|---|---|---|---|
| **Market & Sentiment** | LLM-agent | működik | napi piaci összkép, sentiment, narratíva; legfeljebb 3 ötlet IBKR conidra oldva; kihagyja, ami a portfólióban van vagy 30 napon belül elutasított | `scan_trigger` | `idea` |
| **Research** | LLM-agent | működik (6.3) | ötlet-kritika és research (web, IBKR, tudásbázis); javaslat célárral, horizonttal, ≥3 kockázattal, ≥3 datált forrással, conviction 1–5; napi pozíció-újraértékelés; tanulság a lezárt pozíciókból | `idea`, `review_request`, `decision_outcome` | `proposal`, `idea_reject`, `review_result`, `lesson` |
| **Portfolio Manager** | LLM-agent + determinisztikus szabálykapu | működik (6.3) | dönt a javaslatról (indoklással); a runtime ellenőrzi a szabályokat és méretez (az IBKR MCP-n át olvas; zárt piacnál az utolsó záróárral); napi review (6.4) | `proposal`, `review_result` | `order`, `proposal_reject`, `review_request` |
| **Execution** | determinisztikus service | működik (6.3) | ellenőrzés (paper számla, egyezés a PM döntésével a naplóban, friss ár), megbízás csak kereskedési időben (zárt piacnál függő, `make execute-pending` / 15:30), market / DAY, idempotens (`client_order_id = decision_id`); az egyetlen IBKR írási joggal | `order`, `execute_pending` | `fill`, `order_reject` |

### Támogató szolgáltatások (nem szerepek)

| Szolgáltatás | Állapot | Feladat |
|---|---|---|
| `services/knowledge` | működik | a tudásbázis egyetlen gazdája: döntési napló, cégjegyzetek, tanulságok; REST az írásra, MCP (csak olvasás) az agenteknek |
| `mcp-servers/ibkr` | működik | csak olvasó IBKR-toolok az agenteknek (ár, history, hírek, contract, pozíciók, számla) |
| ibkrfacade (külön repó) | működik | REST az IB Gateway fölött; paper/live védelem, idempotens order |
| `services/scheduler` | tervezett (6.5) | munkanapokon 09:00 scan, 15:30 review, 21:00 kiértékelés (Europe/Budapest) |
| `services/decision-evaluator` | tervezett (6.5) | a lezárt pozíciók realizált hozama → `decision_outcome` a Researchnek |
| dashboard, trace (Jaeger) | tervezett (7.) | feladatok, döntések, portfólió áttekintése |

### Folyamatok

**Vétel (naponta 09:00):**
```
scheduler ─scan_trigger─► Market & Sentiment ─idea─► Research ─proposal─► Portfolio Manager ─order─► Execution ─► IBKR
                                                        │ idea_reject          │ proposal_reject        │ fill / order_reject
                                                        ▼                      ▼                        ▼
                                                                 döntési napló (tudásbázis)
```

**Felülvizsgálat és eladás (naponta 15:30):** minden nyitott pozícióra teljes Research-újraértékelés → HOLD / REDUCE (cél-súllyal) / CLOSE → REDUCE / CLOSE esetén SELL `order` az Executionnek. Nincs veszteség-trigger és stop-loss.

**Feedback (naponta 21:00):** a lezárt pozíciók realizált hozama → Research → tanulság a tudásbázisba. Szabály-, skill- vagy promptmódosítást csak Mihály hagy jóvá.

### Befektetési szabályok (röviden)

- Univerzum: globális részvények és ETF-ek, long only; horizont: hetektől kb. egy évig.
- Belépés: legalább 15% hozampotenciál a célárig.
- Méret conviction szerint: 1–5 → 2 / 4 / 6 / 8 / 10% NAV; új pozíció ≤ 10% NAV.
- Szektor ≤ 25% NAV (IBKR `industry`, csak részvények; az ETF-ekre szektorlimit nincs).
- Csak szabad cash, nincs tőkeáttétel; market order, DAY; csak paper (`DU…`) számla.
- MVP-korlátok: csak a számla bázisdevizájában (USD) jegyzett instrumentum, nem-US cégnél ADR (nincs FX-átváltás), meglévő pozíció nem növelhető, nincs visszadobási kör (az elutasítás végleges).
- Megbízás előtt nincs emberi jóváhagyás (tech demo, paper számla); élő számlánál újra kötelező.

### Ellenőrzési pontok

| Ki | Mit dobhat vissza | Mi alapján |
|---|---|---|
| Research | Market & Sentiment ötletét | gyenge tézis, hiányzó adat, < 15% hozampotenciál |
| Portfolio Manager (LLM) | Research javaslatát | befektetési ítélet, indoklással |
| PM szabálykapu (determinisztikus) | a PM döntését | `portfolio-rules.yaml`: upside, pozíció-, szektorlimit, szabad cash; bázisdeviza, már tartott pozíció |
| Execution (determinisztikus) | megbízást | nem paper számla, eltér a PM döntésétől, nincs friss ár |

## Struktúra

| Könyvtár | Mi van benne |
|---|---|
| `org/` | A szervezet deklaratív leírása (`org.yaml`), a befektetési szabályok és az agent-leírók sémája |
| `agents/` | 1 könyvtár = 1 szerep = 1 container: `agent.yaml`, `CLAUDE.md`, saját `skills/`, `Dockerfile` (az Execution determinisztikus, ugyanazzal a runtime-mal) |
| `libs/` | Importált Python kód (sémák, A2A-réteg, agent runtime); önállóan nem fut |
| `mcp-servers/` | Saját MCP szerverek (IBKR) |
| `services/` | Futó, nem-agent containerek (tudásbázis; később scheduler, decision-evaluator) |
| `infra/` | Compose, egress allowlist |
| `docs/` | Haladási napló, szervezeti terv, ADR-ek |

## Futtatás

Előfeltétel: Docker CE, `make`, `uv`, a repó mellett az [ibkrfacade](https://github.com/medovarszki/ibkrfacade) checkoutja a saját `.env`-jével, és a gyökérben kitöltött `.env` (lásd `.env.example`).

```
make build && make up     # broker stack, Postgres, tudásbázis, agentek
make scan                 # egy napi scan kézi indítása
make tasks                # a közös task tábla
make decisions            # a döntési napló
make execute-pending      # zárt piac miatt függő megbízások leadása
```
