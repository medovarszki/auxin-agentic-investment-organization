# libs/

Importált Python kód (uv workspace tagok, 2. fázisban rögzítve). Önállóan nem fut; ezzel szemben a `services/` futó containereket tartalmaz.

- `auxin-schemas/`: pydantic modellek (A2A metaadat-extension, taszk-állapotgép, Idea, Proposal, Order, Fill, ReviewResult, DecisionOutcome, belépési szabályok); lásd `docs/TASK_MODEL.md`
- `auxin-a2a/`: vékony réteg az `a2a-sdk` fölött: A2A szerver (Agent Card, JSON-RPC + SSE) és kliens, a kötelező metaadat-extension kikényszerítése, közös Postgres task store (`a2a_tasks`), 10 perces timeout *(5. fázis; auth később)*
- `auxin-store/`: Postgres hozzáférés és migrációk *(3. fázis)*
- `auxin-runtime/`: agent runner (`agent.yaml` betöltése, Agent SDK session, A2A szerver, költségmérés, OTel) *(4. fázis)*
