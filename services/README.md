# services/

Futó, nem-agent containerek (determinisztikus kód, nincs LLM-döntés), mindegyik saját Dockerfile-lal.

- `scheduler/`: időzített triggerek A2A-hívással (napi piaci scan, napi pozíció-review, feedback kiértékelés)
- `knowledge/` (6.2, kész): a tudásbázis egyetlen gazdája (`decisions`, `company_notes`, `lessons`, Postgres full-text). REST az írásra (runtime, Execution, evaluator): `POST /decisions | /company-notes | /lessons` (idempotens: azonos `id` → no-op), `GET /decisions`, `/rejections`, `/search`; MCP csak olvasó toolokkal az agenteknek (`http://knowledge:8000/mcp`: `search`, `get_company_history`, `get_recent_rejections`). Séma: SQLAlchemy-modellek (`db.py`) + Alembic, induláskor `upgrade head`; új migráció: `make db-revision m="..."`. Ellenőrzés: `make kb-check`, `make decisions`.
- ~~`portfolio-sync/`~~: portfólió-tükör egyelőre nincs (Mihály, 2026-10-16); a pozíció és a számla élőben az ibkrfacade-ből
- `decision-evaluator/`: feedback loop: döntések kiértékelése (P&L, benchmark, célár-teljesülés) → `decision_outcome`
- `ibkrfacade/`: az [ibkrfacade](https://github.com/medovarszki/ibkrfacade) és az IB Gateway futtatása (csak belső hálózat)
- `mock-broker/`: tesztekhez és offline futáshoz
- `dashboard/`: feladatok, üzenetek, portfólió, döntések eredményessége
