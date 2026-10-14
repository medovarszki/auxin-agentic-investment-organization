# org/

A szervezet deklaratív, gépileg olvasható leírása.

- `org.yaml` *(1. fázis)*: szervezeti egységek → pozíciók → agentek, hierarchia. Most: core befektetési egység; később risk, compliance, operations, reporting.
- `schema/agent.schema.json` *(1. fázis)*: az `agents/<név>/agent.yaml` leírók JSON Schema-ja; a CI ezzel validál, és ellenőrzi, hogy `org.yaml` és az agent-könyvtárak egyeznek.
