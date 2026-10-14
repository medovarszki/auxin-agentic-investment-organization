# libs/

Importált Python kód (uv workspace tagok, 2. fázisban rögzítve). Önállóan nem fut; ezzel szemben a `services/` futó containereket tartalmaz.

- `auxin-schemas/`: pydantic modellek (üzenetboríték kötelező metaadatokkal, task, proposal, order, fill, decision_outcome) *(3. fázis)*
- `auxin-a2a/`: vékony réteg az `a2a-sdk` fölött: A2A szerver és kliens, a kötelező metaadat-extension kikényszerítése, közös Postgres task store, bearer token auth, trace-kontextus továbbítása *(5. fázis)*
- `auxin-store/`: Postgres hozzáférés és migrációk *(3. fázis)*
- `auxin-runtime/`: agent runner (`agent.yaml` betöltése, Agent SDK session, A2A szerver, költségmérés, OTel) *(4. fázis)*
