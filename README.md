# Auxin – agentic investment organization

Az Auxin **agentekből álló befektetési alapkezelő**, amely egy valódi alapkezelő szervezetét kívánja modellezni: szervezeti egységek, pozíciók, jelentési vonalak, felelősségi körök, írott befektetési szabályok, ellenőrzési pontok és döntési napló. A szerepeket Claude-alapú (Opus) LLM-agentek és determinisztikus szolgáltatások töltik be. Minden szerep külön Docker containerben fut. Az agentek A2A 1.0 protokollon kommunikálnak, minden feladat egy közös Postgres task store-ba kerül, a döntések egy tudásbázisba. A portfólió egyetlen Interactive Brokers **paper** számla.

> Állapot: **MVP, fejlesztés alatt.** Az aktuális fázis és a döntési napló: [`docs/ORG_PROGRESS.md`](docs/ORG_PROGRESS.md).
> Az agentek kimenete nem befektetési tanácsadás.

## Szervezeti modell

Ez a fejezet a szervezet naprakész leírása. Gépileg olvasható megfelelői: [`org/org.yaml`](org/org.yaml) (egységek, pozíciók, jelentési vonalak), [`org/rules/portfolio-rules.yaml`](org/rules/portfolio-rules.yaml) (befektetési szabályok), `agents/<név>/agent.yaml` (szerepenkénti leíró). Az eredeti, 1. fázisbeli terv: [`docs/ORG.md`](docs/ORG.md).

### Egységek

| Egység | Állapot | Pozíciók |
|---|---|---|
| **Core** (befektetési egység) | működik (vétel, napi review és eladás, ütemezés, tanulság) | Market & Sentiment, Research, Portfolio Manager, Execution |
| Risk | tervezett | független kockázatkezelés, limitfelügyelet |
| Compliance | tervezett | szabálymegfelelés, audit |
| Operations | tervezett | elszámolás, egyeztetés a brokerrel |
| Reporting | részben (7.: dashboard, trace) | teljesítményjelentések; a dashboard és a Jaeger támogató szolgáltatás, nem szerep |

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
| **Research** | LLM-agent | működik (6.3) | ötlet-kritika és research (web, IBKR, tudásbázis); javaslat célárral, horizonttal, ≥3 kockázattal, ≥3 datált forrással, conviction 1–5; napi pozíció-újraértékelés (`position-review`: HOLD / REDUCE cél-súllyal / CLOSE); tanulság a lezárt pozíciókból (`lesson`, a runtime írja a `lessons` táblába) | `idea`, `review_request`, `decision_outcome` | `proposal`, `idea_reject`, `review_result`, `lesson` |
| **Portfolio Manager** | LLM-agent + determinisztikus szabálykapu | működik (6.3) | dönt a javaslatról (indoklással); a runtime ellenőrzi a szabályokat és méretez (az IBKR MCP-n át olvas; zárt piacnál az utolsó záróárral); napi review: a runtime a Research javaslatát LLM nélkül hajtja végre (REDUCE / CLOSE → SELL) | `proposal`, `review_trigger` | `order`, `proposal_reject`, `review_request`, `execute_pending` |
| **Execution** | determinisztikus service | működik (6.3) | ellenőrzés (paper számla, egyezés a PM döntésével a naplóban, SELL ≤ tartott mennyiség, friss ár), megbízás csak kereskedési időben (zárt piacnál függő, `make execute-pending` / 15:30), market / DAY, idempotens (`client_order_id = decision_id`); az egyetlen IBKR írási joggal | `order`, `execute_pending` | `fill`, `order_reject` |

### Támogató szolgáltatások (nem szerepek)

| Szolgáltatás | Állapot | Feladat |
|---|---|---|
| `services/knowledge` | működik | a tudásbázis egyetlen gazdája: döntési napló, cégjegyzetek, tanulságok; REST az írásra, MCP (csak olvasás) az agenteknek |
| `mcp-servers/ibkr` | működik | csak olvasó IBKR-toolok az agenteknek (ár, history, hírek, contract, pozíciók, számla) |
| ibkrfacade (külön repó) | működik | REST az IB Gateway fölött; paper/live védelem, idempotens order |
| `services/scheduler` | működik (6.5) | munkanapokon (hétfő–péntek, Europe/Budapest) 09:00 scan, 15:30 review, 21:00 kiértékelés; kézzel: `make run-job job=...` |
| döntés-kiértékelő (a scheduler `evaluate` jobja) | működik (6.5) | a lezárt pozíciók realizált hozama a fill-ekből (benchmark nélkül) → `decision_outcome` a naplóba és a Researchnek |
| `services/dashboard` | működik (7.) | `localhost:8080`, csak olvas: portfólió élőben (IBKR MCP) az utolsó review-val, folyamatok trace szerint (taszkok + napló-események egy idővonalon, Jaeger-link), döntési napló, taszkok, lezárt pozíciók és tanulságok. Postgres read-only sessionben |
| Jaeger (trace) | működik (7.) | `localhost:16686`, memóriában (restartkor elvész; az audit a Postgres). Spanok: A2A send / task, `invoke_agent` (modell, tokenek, turnök), `execute_tool` (az agentek tool-hívásai, pl. WebSearch, MCP), HTTP-hívások (tudásbázis, IBKR MCP, ibkrfacade). A trace id = a folyamat Auxin `trace_id`-ja |

### Folyamatok

**Vétel (naponta 09:00):**
```
scheduler ─scan_trigger─► Market & Sentiment ─idea─► Research ─proposal─► Portfolio Manager ─order─► Execution ─► IBKR
                                                        │ idea_reject          │ proposal_reject        │ fill / order_reject
                                                        ▼                      ▼                        ▼
                                                                 döntési napló (tudásbázis)
```

**Felülvizsgálat és eladás (naponta 15:30):**
```
scheduler ─review_trigger─► Portfolio Manager ─execute_pending─► Execution   (a reggel függőben maradt megbízások)
                                   │ pozíciónként, egymás után
                                   ├─review_request─► Research ─► HOLD / REDUCE (cél-súly) / CLOSE ─► döntési napló
                                   └─ REDUCE / CLOSE: determinisztikus méretezés ─SELL order─► Execution ─► IBKR
```
Minden nyitott pozíció minden nap teljes Research-újraértékelést kap (a frissen vett is). A Research javaslatát a PM runtime LLM nélkül hajtja végre: CLOSE = a teljes pozíció, REDUCE = lefelé kerekítve (jelenlegi súly − cél-súly) × NAV / ár, legalább 1 db. Nincs veszteség-trigger és stop-loss.

**Feedback (naponta 21:00):**
```
scheduler (evaluate) ─► döntési napló fill-jei ─► lezárt pozíció? ─decision_outcome─► Research ─► tanulság (lessons)
```
Lezárt egy pozíció, ha az eladások kiadják a vett mennyiséget; hozam = (bevétel − költség − jutalék) / költség, benchmark nélkül. A tanulságokat a Research a következő ötleteknél, javaslatoknál és review-knál a tudásbázisból olvassa. Szabály-, skill- vagy promptmódosítást csak Mihály hagy jóvá.

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
| Execution (determinisztikus) | megbízást | nem paper számla, eltér a PM döntésétől, SELL több a tartottnál, nincs friss ár |

## Struktúra

| Könyvtár | Mi van benne |
|---|---|
| `org/` | A szervezet deklaratív leírása (`org.yaml`), a befektetési szabályok és az agent-leírók sémája |
| `agents/` | 1 könyvtár = 1 szerep = 1 container: `agent.yaml`, `CLAUDE.md`, saját `skills/`, `Dockerfile` (az Execution determinisztikus, ugyanazzal a runtime-mal) |
| `libs/` | Importált Python kód (sémák, A2A-réteg, agent runtime); önállóan nem fut |
| `mcp-servers/` | Saját MCP szerverek (IBKR) |
| `services/` | Futó, nem-agent containerek (tudásbázis, scheduler a döntés-kiértékelővel, dashboard) |
| `infra/` | Compose (Jaeger is), egress allowlist |
| `docs/` | Haladási napló, szervezeti terv, ADR-ek |

## Futtatás

Előfeltétel: Docker CE, `make`, `uv`, a repó mellett az [ibkrfacade](https://github.com/medovarszki/ibkrfacade) checkoutja a saját `.env`-jével, és a gyökérben kitöltött `.env` (lásd `.env.example`).

```
make build && make up     # broker stack, Postgres, tudásbázis, agentek, Jaeger, dashboard
make ui                   # dashboard: http://localhost:8080, Jaeger: http://localhost:16686
make scan                 # egy napi scan kézi indítása
make tasks                # a közös task tábla
make decisions            # a döntési napló
make run-job job=evaluate  # egy scheduler-job kézi indítása (scan | review | evaluate)
make review               # napi review kézi indítása (függő megbízások, pozíciónkénti újraértékelés, eladás)
make execute-pending      # zárt piac miatt függő megbízások leadása
```
