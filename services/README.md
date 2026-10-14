# services/

Futó, nem-agent containerek (determinisztikus kód, nincs LLM-döntés), mindegyik saját Dockerfile-lal.

- `scheduler/`: időzített triggerek a busra (napi piaci scan, heti pozíció-review, feedback kiértékelés)
- `portfolio-sync/`: IBKR számla → portfólió-tükör (a broker az igazságforrás)
- `bus-archiver/`: minden bus-üzenet → Postgres audit-archívum
- `approval-gateway/`: emberi jóváhagyási kapu
- `mock-broker/`: tesztekhez és offline futáshoz
- `dashboard/`: feladatok, üzenetek, portfólió, döntések eredményessége
