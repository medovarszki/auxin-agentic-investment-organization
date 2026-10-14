# infra/

Nem-Python konfiguráció, egy helyen auditálható.

- `compose/`: `docker-compose.yml` és dev / test override-ok *(8. fázis, előtte lépésenként bővül)*
- `redis/`: csak az ibkrfacade árfolyam-tárolójához (Redis 8, TimeSeries)
- `postgres/`: init scriptek
- `otel/`: collector konfiguráció
- `egress/`: egress proxy és agentenkénti allowlist
