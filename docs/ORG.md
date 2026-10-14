# Auxin szervezeti terv (1. fázis)

Állapot: elfogadva 2026-10-14. A gépileg olvasható megfelelői: [`org/org.yaml`](../org/org.yaml), [`org/rules/portfolio-rules.yaml`](../org/rules/portfolio-rules.yaml), `agents/<név>/agent.yaml`.

## Szervezeti egységek

| Egység | Állapot | Tartalom |
|---|---|---|
| **core** (befektetési egység) | most épül | Market & Sentiment, Research / Analyst, Portfolio Manager, Execution |
| risk | később | független kockázatkezelés, limitfelügyelet |
| compliance | később | szabálymegfelelés, audit |
| operations | később | elszámolás, egyeztetés a brokerrel |
| reporting | később | teljesítményjelentések |

Befektetési univerzum: **globális részvények és ETF-ek**, long only (nincs short). Horizont: néhány héttől kb. egy évig. A portfólió egyetlen IBKR számla (alapértelmezés: paper), amelyet az [ibkrfacade](https://github.com/medovarszki/ibkrfacade) ér el.

Minden agent modellje **Opus 5.5** (a pontos modell-ID a 2. fázisban rögzül).

## Szerepek

### Market & Sentiment
- **Felelősség:** időzítetten (naponta) piaci összkép: hírek, indexek, indikátorok, sentiment, domináns narratíva; ebből befektetési ötletek.
- **Bemenet:** scheduler trigger; ibkr (ár, hírek) MCP, szerver-oldali webkeresés.
- **Kimenet:** `market_view` (összkép), `idea` üzenetek a Researchnek (instrumentum, tézis, indoklás, források).
- **Skillek:** `market-scan`, `narrative-and-sentiment`, `idea-generation`.

### Research / Analyst (egyben a verifier)
- **Felelősség:**
  1. Ötlet-kritika és háttér-research: pénzügyek, kapcsolódó cégek, ellátási lánc és partnerkockázat, iparág, a cég helye az iparágban. Kimenet: `proposal` (buy / pass) vagy indokolt elutasítás.
  2. Cégenkénti memória: események időbélyeggel és árhatással a tudásbázisban; tanulságok a feedback loopból.
  3. Pozíció-újraértékelés a PM kérésére: indokolt-e a súly → `review_result` (hold / reduce / close).
  4. **Verifier szerep:** minden megbízás-tervezetet leadás előtt ellenőriz, hogy egyezik-e a jóváhagyott döntéssel (instrumentum, irány, mennyiség, limitár), és a saját javaslatain egy kötelező ellenőrző listát futtat (források elérhetők és datáltak, számok konzisztensek, hozampotenciál helyesen számolt).
- **Bemenet:** `idea`, `review_request`, `verify_request`, `decision_outcome`; ibkr (ár, hírek, contract-adatok) és knowledge-base MCP, szerver-oldali webkeresés.
- **Kimenet:** `proposal`, `idea_reject`, `review_result`, `verify_result`, `lesson`.
- **Skillek:** `idea-challenge`, `fundamental-analysis`, `supply-chain-and-peers`, `company-memory`, `position-review`, `order-verification`, `lesson-writing`.
- **Megjegyzés (kockázat):** mivel a verifier a Research része, a saját javaslatát nem független szem ellenőrzi. A függetlenséget a PM szabálykapuja (determinisztikus szabályfájl) és az emberi jóváhagyás adja. Ha a risk egység elkészül, a verifier szerep oda átköltöztethető.

### Portfolio Manager
- **Felelősség:** portfóliókapu: a javaslat megfelel-e a [szabályoknak](../org/rules/portfolio-rules.yaml), pozícióméret, megbízás-tervezet. Időzített (heti) review: minden nyitott pozícióra `review_request` a Researchnek, a válasz alapján tart / csökkent / zár.
- **Bemenet:** `proposal`, `review_result`, `verify_result`, `fill`; ibkr MCP (csak olvasó toolok), portfólió-tükör.
- **Kimenet:** `proposal_reject`, `order_draft`, `review_request`, `approval_request`.
- **Skillek:** `rule-check`, `position-sizing`, `portfolio-review`.

### Execution
- **Felelősség:** kizárólag jóváhagyott (verifikált és emberileg jóváhagyott) megbízások végrehajtása az ibkrfacade-en át, és a teljesülés visszajelzése. **Visszadobja a megbízást, ha az instrumentumra nincs árinformáció**, vagy ha a megbízás nem egyezik a jóváhagyottal.
- **Bemenet:** `order` (jóváhagyott); ibkr MCP (író és olvasó toolok).
- **Kimenet:** `fill`, `order_reject`.
- **Skillek:** `order-execution`.
- Az egyetlen agent IBKR írási joggal.

## Folyamatok

### 1. Vétel
```
scheduler ─► Market & Sentiment ─idea─► Research ─proposal─► Portfolio Manager
                                          │ (idea_reject)        │ (proposal_reject)
                                          ▼                      ▼ order_draft
                                                         Research (verify) ─verify_result─► PM
                                                                                     │ approval_request
                                                                                     ▼
                                                                         ember (approval-gateway)
                                                                                     │ order
                                                                                     ▼
                                                                          Execution ─► ibkrfacade
                                                                                     │ fill / order_reject
                                                                                     ▼
                                                                    PM, portfolio-sync, döntési napló
```

### 2. Felülvizsgálat és eladás
Heti scheduler trigger (vagy jelentős hír) → PM: minden nyitott pozícióra `review_request` → Research: `review_result` (hold / reduce / close, indoklással) → PM dönt → reduce / close esetén `order_draft` → Research verify → emberi jóváhagyás → Execution. Short nincs: az eladás csak csökkentés vagy zárás.

### 3. Feedback loop
A `decision-evaluator` service (determinisztikus, nem LLM) időzítetten kiértékeli a döntéseket: realizált és nem realizált P&L, hozam benchmarkhoz képest, elérte-e a célárat a horizonton belül, kockázattal korrigált hozam. Az eredményt `decision_outcome` üzenetben küldi a döntést hozó agentnek (Research), aki tanulságot ír a tudásbázisba (`lesson`). A tanulság automatikusan bővítheti a memóriát; skill-, szabály- vagy promptmódosítást csak **javasolhat**, azt Mihály hagyja jóvá.

## Ellenőrzési szabály

| Ki | Kit dobhat vissza | Mi alapján |
|---|---|---|
| Research | Market & Sentiment ötletét | gyenge tézis, hiányzó adat, nem éri el a 15%-os hozampotenciált |
| Research (verifier) | PM megbízás-tervezetét | nem egyezik a jóváhagyott döntéssel |
| Portfolio Manager | Research javaslatát | [portfolio-rules.yaml](../org/rules/portfolio-rules.yaml) |
| Execution | jóváhagyott megbízást | nincs árinformáció, vagy eltér a jóváhagyottól |
| Ember | bármely megbízást | saját döntés |

- Minden visszadobás indoklással történik, és a döntési naplóba kerül.
- **Legfeljebb 2 visszadobási kör** ugyanarra a tételre; utána a tétel `failed`, és nem kerül újra sorra, amíg új információ nem jön.
- **Minden megbízás előtt kötelező emberi jóváhagyás**, paper számlán is.

## Jogosultságok összefoglalója

| Agent | IBKR | Tudásbázis | A2A: kit hívhat |
|---|---|---|---|
| Market & Sentiment | csak piaci adat (ár, historikus, hírek) | olvas | Research |
| Research | csak piaci adat és contract | ír / olvas | Portfolio Manager, Market & Sentiment |
| Portfolio Manager | csak olvas (pozíciók, ár, számla) | olvas | Research, approval-gateway |
| Execution | ír / olvas | nincs | Portfolio Manager |

Az agentek A2A 1.0-n kommunikálnak (ADR 0001); a közös Postgres task store és az OTel trace-ek adják az auditot. Az üzenetsémák a 3. fázisban, az A2A-réteg az 5. fázisban rögzül; a fenti üzenettípus-nevek munkanevek.

## Ismert korlátok és nyitott pontok

- **Subagentek:** a subagentek nem indíthatnak további subagenteket. Ha a Research egy ötletet párhuzamos subagentekkel elemez (pl. pénzügyek, ellátási lánc), azok tovább már nem bonthatnak. A tervet ez nem akadályozza.
- **ibkrfacade:** nincs számlaösszesítő végpont (NAV, cash, margin), ez kell a 10%-os súlyszabályhoz; a 4. fázisban pótoljuk. A REST-nek nincs auth-ja, ezért csak a belső hálózaton, az `mcp-servers/ibkr`-en át érhető el.
- **Szektor-besorolás:** az IBKR `industry` mezője (nem GICS), mert nincs külön adatszolgáltató (ADR 0001).
