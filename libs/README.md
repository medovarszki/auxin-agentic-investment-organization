# libs/

Importált Python kód (uv workspace tagok, 2. fázisban rögzítve). Önállóan nem fut; ezzel szemben a `services/` futó containereket tartalmaz.

- `auxin-schemas/`: pydantic modellek (üzenetboríték kötelező metaadatokkal, task, proposal, order, fill, decision_outcome) *(3. fázis)*
- `auxin-bus/`: Redis Streams kliens (send / receive / ack, dead-letter, metaadat-kényszerítés, trace propagáció) *(5. fázis)*
- `auxin-store/`: Postgres hozzáférés és migrációk *(3. fázis)*
- `auxin-runtime/`: agent runner (`agent.yaml` betöltése, Agent SDK session, bus-hurok, költségmérés, OTel) *(4. fázis)*
