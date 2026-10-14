# org/

A szervezet deklaratív, gépileg olvasható leírása.

- `org.yaml`: szervezeti egységek → pozíciók → agentek, hierarchia. Most: core befektetési egység; később risk, compliance, operations, reporting.
- `schema/agent.schema.json`: az `agents/<név>/agent.yaml` leírók JSON Schema-ja; a CI ezzel validál, és ellenőrzi, hogy `org.yaml` és az agent-könyvtárak egyeznek.
- `rules/portfolio-rules.yaml`: a Portfolio Manager kapujának szabályai (instrumentum, 15% hozampotenciál, 10% pozíciólimit, 25% szektorlimit). Módosítás csak jóváhagyással.
