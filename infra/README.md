# infra/

Nem-Python konfiguráció, egy helyen auditálható.

- `compose/`: `docker-compose.yml` és dev / test override-ok *(8. fázis, előtte lépésenként bővül)*
- `redis/`: `redis.conf` (AOF perzisztencia), `users.acl` (agentenként ki melyik streamre írhat / melyikből olvashat)
- `postgres/`: init scriptek
- `otel/`: collector konfiguráció
- `egress/`: egress proxy és agentenkénti allowlist
