# services/

Futó, nem-agent containerek (determinisztikus kód, nincs LLM-döntés), mindegyik saját Dockerfile-lal.

- `scheduler/` (6.5, kész): APScheduler 3.11, munkanapokon (hétfő–péntek, Europe/Budapest, tőzsdei ünnepnap-naptár nélkül) 09:00 `scan_trigger` → Research (Market & Sentiment funkció), 15:30 `review_trigger` → Portfolio Manager, 21:00 kiértékelés; jobonként egy példány, kimaradt futás nem pótlódik. Kézi futtatás: `make run-job job=scan|review|evaluate`. Determinisztikus, nincs Claude-token, nincs IBKR-hozzáférés
- `knowledge/` (6.2, kész): a tudásbázis egyetlen gazdája (`decisions`, `company_notes`, `lessons`, Postgres full-text). REST az írásra (runtime, Execution, evaluator): `POST /decisions | /company-notes | /lessons` (idempotens: azonos `id` → no-op), `GET /decisions`, `/rejections`, `/search`; MCP csak olvasó toolokkal az agenteknek (`http://knowledge:8000/mcp`: `search`, `get_company_history`, `get_recent_rejections`). Séma: SQLAlchemy-modellek (`db.py`) + Alembic, induláskor `upgrade head`; új migráció: `make db-revision m="..."`. Ellenőrzés: `make kb-check`, `make decisions`.
- ~~`portfolio-sync/`~~: portfólió-tükör egyelőre nincs (Mihály, 2026-10-16); a pozíció és a számla élőben az ibkrfacade-ből
- ~~`decision-evaluator/`~~: a scheduler `evaluate` jobja (Mihály, 6.5, 1.a): a döntési napló fill-jeiből a lezárt pozíciók (az eladások kiadják a vett mennyiséget) realizált hozama, benchmark nélkül → `decision_outcome` (napló) → Research → tanulság a `lessons` táblába
- `ibkrfacade/`: az [ibkrfacade](https://github.com/medovarszki/ibkrfacade) és az IB Gateway futtatása (csak belső hálózat)
- `mock-broker/`: tesztekhez és offline futáshoz
- `dashboard/` (7., kész): `http://localhost:8080` (csak localhost). FastAPI JSON API (`/api/portfolio`, `/api/flows`, `/api/flows/{trace_id}`, `/api/decisions`, `/api/tasks`, `/api/outcomes`) + egy statikus oldal (vanilla JS, CDN nélkül). Postgres a közös role-lal, de `default_transaction_read_only=on` sessionben (írás hibát dob); a portfólió élőben az IBKR MCP olvasó tooljaiból, tükör-tábla nincs. Nincs Claude-token, nincs ibkrfacade-hozzáférés
