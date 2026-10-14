# Feladat- és üzenetmodell, állapotgép (3. fázis)

Állapot: elfogadva 2026-10-14. Kód: [`libs/auxin-schemas`](../libs/auxin-schemas).

## Alapelvek

- **Tech demo, csak paper számla.** Nincs emberi jóváhagyás (Mihály döntése, jóváhagyott eltérés). Védelem helyette: az Execution csak paper számlán ad le megbízást (`DU`-val kezdődő account ID), és az ibkrfacade `IBKR_ALLOW_LIVE=false` alapértelmezéssel tiltja a live számlát. **Élő számlánál az emberi jóváhagyás újra kötelező.**
- **Nincs automatikus újrapróbálás**, csak timeout. A hibás taszk `FAILED`, naplózódik; a következő ütemezett futás (napi scan, heti review) úgyis újra előveszi a témát.
- **Idempotencia:** minden megbízás `decision_id`-t kap, ez az ibkrfacade `client_order_id`-ja (IBKR `orderRef`). Ugyanarra a döntésre soha nem megy ki két megbízás.

## Taszk-állapotgép (A2A 1.0)

Minden agent-feladat egy A2A taszk; az állapotai közvetlenül az A2A 1.0 állapotai (saját állapotnév nincs):

```
SUBMITTED ──► WORKING ──► COMPLETED
    │            ├──────► REJECTED   (tartalmi visszadobás, indoklással)
    │            ├──────► FAILED     (hiba vagy timeout)
    └────────────┴──────► CANCELED
```

| Állapot | Jelentés |
|---|---|
| `TASK_STATE_SUBMITTED` | A címzett agent megkapta, még nem dolgozik rajta |
| `TASK_STATE_WORKING` | Folyamatban |
| `TASK_STATE_COMPLETED` | Kész, van eredmény (artifact) |
| `TASK_STATE_REJECTED` | Tartalmilag visszadobva (pl. gyenge ötlet, szabálysértés, nincs ár) |
| `TASK_STATE_FAILED` | Technikai hiba vagy **10 perces timeout** |
| `TASK_STATE_CANCELED` | Megszakítva |

Az `INPUT_REQUIRED` és `AUTH_REQUIRED` állapotot nem használjuk (nincs emberi kapu). A végállapotokból nincs átmenet.

**Timeout:** 10 perc a `WORKING` állapotba lépéstől; utána a taszk `FAILED` (`reason: timeout`).

## Visszadobási körök

Ugyanarra a tételre (ötlet, javaslat) legfeljebb **2** visszadobás jöhet; a 2. után a tétel lezárul, és csak új információval (új ötletként) kerülhet újra sorra.

## Domain-életciklus

```
Idea ──► Proposal ──► Order ──► Fill ──► Position ──► ReviewResult ──► (reduce/close) Order ──► Fill
  │         │           │                                                                       │
  ▼         ▼           ▼                                                                       ▼
reject    reject      reject                                                          DecisionOutcome ──► lesson
```

| Objektum | Ki hozza létre | Lényeges mezők |
|---|---|---|
| `Idea` | Market & Sentiment | instrumentum-hivatkozás (`InstrumentRef`: symbol, név, eszközosztály; a `conid` még hiányozhat), tézis, indoklás, források. A napi kimenet: `MarketScanResult` = `MarketView` + ötletlista |
| `Proposal` | Research | BUY, piaci ár, célár, horizont (hét), ≥ 3 kockázat, ≥ 3 datált forrás, conviction 1–5, invalidációs feltétel; a hozampotenciál számolt |
| `Order` | Portfolio Manager | `decision_id` (idempotencia-kulcs), BUY / SELL, mennyiség, **market order** |
| `Fill` / `OrderReject` | Execution | IBKR order ID, teljesült mennyiség, átlagár, jutalék / ok: `NO_PRICE`, `MISMATCH`, `NOT_PAPER_ACCOUNT`, `BROKER_ERROR` |
| `ReviewResult` | Research | HOLD / REDUCE / CLOSE, cél-súly (REDUCE-nál kötelező), indoklás |
| `DecisionOutcome` | decision-evaluator | P&L, hozam, benchmark-hozam, elérte-e a célárat, lejárt-e a horizont |

Az instrumentum egyértelmű azonosítása: IBKR `conid` + symbol + tőzsde + deviza (+ ISIN, ha van), eszközosztály: `stock` | `etf`.

## Üzenet-metaadatok (A2A extension)

Minden A2A Message `metadata` mezőjében, az extension URI kulcsa alatt:

```
https://auxin.local/a2a/ext/message-metadata/v1
```

| Mező | Típus | Kötelező |
|---|---|---|
| `message_id` | UUID | igen |
| `sender`, `recipient` | agent név | igen |
| `subject` | szöveg | igen |
| `type` | üzenettípus (lásd `MessageType`) | igen |
| `priority` | `low` / `normal` / `high` / `urgent` | igen (alapért.: `normal`) |
| `timestamp` | UTC, időzónával | igen |
| `task_id`, `correlation_id` | azonosító | igen |
| `trace_id` | W3C trace ID (32 hex) | igen |
| `reply_to` | szülő-üzenet ID | nem |
| `schema_version` | `"1"` | igen |
| `ttl_seconds` | egész | nem |

A metaadatot a közös A2A-réteg (`libs/auxin-a2a`, 5. fázis) kényszeríti ki: metaadat nélküli üzenetet nem küld és nem fogad.
