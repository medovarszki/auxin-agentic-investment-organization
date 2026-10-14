# services/

Futó, nem-agent containerek (determinisztikus kód, nincs LLM-döntés), mindegyik saját Dockerfile-lal.

- `scheduler/`: időzített triggerek A2A-hívással (napi piaci scan, heti pozíció-review, feedback kiértékelés)
- `portfolio-sync/`: IBKR számla → portfólió-tükör (a broker az igazságforrás)
- `approval-gateway/`: emberi jóváhagyási kapu
- `decision-evaluator/`: feedback loop: döntések kiértékelése (P&L, benchmark, célár-teljesülés) → `decision_outcome`
- `ibkrfacade/`: az [ibkrfacade](https://github.com/medovarszki/ibkrfacade) és az IB Gateway futtatása (csak belső hálózat)
- `mock-broker/`: tesztekhez és offline futáshoz
- `dashboard/`: feladatok, üzenetek, portfólió, döntések eredményessége
