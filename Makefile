COMPOSE = docker compose --env-file .env -f infra/compose/docker-compose.yml
# Broker: the ibkrfacade project's own stack, run from its checkout with its own .env (and COMPOSE_FILE mode)
IBKRFACADE_DIR ?= ../ibkrfacade
IBKR = cd $(IBKRFACADE_DIR) && docker compose
PSQL = $(COMPOSE) exec -T postgres sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -P pager=off -c "$$0"'

.PHONY: test validate base build up ibkr-up ibkr-down ibkr-check scan tasks logs scan-local egress-test down

test:            ## unit tests
	uv run pytest -q

validate:        ## agent.yaml / org.yaml consistency
	uv run python scripts/validate_org.py

base:            ## shared agent base image
	docker build -f agents/Dockerfile -t auxin-agent-base .

build: base      ## agent images
	$(COMPOSE) build

up: ibkr-up      ## broker stack, egress proxy, Postgres and the agent A2A servers
	$(COMPOSE) up -d

ibkr-up:         ## the ibkrfacade stack (gateway, Redis, facade), built from its checkout
	$(IBKR) up -d --build

ibkr-down:
	$(IBKR) down

scan: up         ## A2A scan_trigger to Market & Sentiment; follows the task, prints the result JSON
	$(COMPOSE) run --rm operator trigger --to market-sentiment

tasks:           ## the shared task table: who did what, in which state, in which flow
	$(PSQL) "SELECT last_updated, owner AS agent, metadata->>'sender' AS sender, metadata->>'type' AS type, \
	  metadata->>'subject' AS subject, status->>'state' AS state, left(metadata->>'trace_id', 8) AS trace \
	  FROM a2a_tasks ORDER BY last_updated"

ibkr-check:      ## broker stack: health, paper account, one price (AAPL); never places an order
	$(IBKR) exec -T ibkrfacade sh -c 'H="Authorization: Bearer $$IBKR_SECURITY_READ_TOKEN"; B=http://localhost:8082/ibkr; \
	  curl -fsS $$B/actuator/health && echo && \
	  curl -fsS -H "$$H" $$B/account/summary | head -c 600 && echo && \
	  curl -fsS -H "$$H" $$B/subscribe/265598 >/dev/null && sleep 3 && curl -fsS -H "$$H" $$B/price/265598 && echo'

logs:            ## agent logs (JSON events)
	$(COMPOSE) logs -f market-sentiment research

scan-local: up   ## phase 4 one-shot run without A2A
	$(COMPOSE) run --rm market-sentiment run --trigger scan

egress-test: up  ## example.com must be blocked, api.anthropic.com must pass
	$(COMPOSE) run --rm -T --entrypoint python market-sentiment - < scripts/egress_check.py

down:            ## Auxin services only; the broker stack: make ibkr-down
	$(COMPOSE) down
