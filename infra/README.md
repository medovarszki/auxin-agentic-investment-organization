# infra/

Nem-Python konfiguráció, egy helyen auditálható.

- `compose/`: `docker-compose.yml` és dev / test override-ok *(8. fázis, előtte lépésenként bővül)*
- `redis/`: csak az ibkrfacade árfolyam-tárolójához (Redis 8, TimeSeries)
- `postgres/`: init scriptek
- ~~`otel/`~~: nincs collector (7.): a containerek OTLP/HTTP-n közvetlenül a Jaegerbe küldenek (`OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318`); Jaeger 2.20 all-in-one, memóriában, UI `localhost:16686`
- `egress/`: egress proxy és agentenkénti allowlist
