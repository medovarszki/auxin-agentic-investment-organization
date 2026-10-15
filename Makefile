COMPOSE = docker compose --env-file .env -f infra/compose/docker-compose.yml -f infra/compose/ibkr.yml
IBKRFACADE_DIR ?= ../ibkrfacade
PSQL = $(COMPOSE) exec -T postgres sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -P pager=off -c "$$0"'

.PHONY: test validate base build ibkrfacade-image up scan tasks logs ibkr-check scan-local egress-test down

test:            ## unit tests
	uv run pytest -q

validate:        ## agent.yaml / org.yaml consistency
	uv run python scripts/validate_org.py

base:            ## shared agent base image
	docker build -f agents/Dockerfile -t auxin-agent-base .

build: base      ## agent images
	$(COMPOSE) build

ibkrfacade-image: ## broker REST facade image from the ibkrfacade checkout (IBKRFACADE_DIR)
	docker build -t ibkrfacade:local -t ibkrfacade:$$(git -C $(IBKRFACADE_DIR) rev-parse --short HEAD) $(IBKRFACADE_DIR)

up:              ## egress proxy, Postgres, the agent A2A servers and the broker stack
	$(COMPOSE) up -d

scan: up         ## A2A scan_trigger to Market & Sentiment; follows the task, prints the result JSON
	$(COMPOSE) run --rm operator trigger --to market-sentiment

tasks:           ## the shared task table: who did what, in which state, in which flow
	$(PSQL) "SELECT last_updated, owner AS agent, metadata->>'sender' AS sender, metadata->>'type' AS type, \
	  metadata->>'subject' AS subject, status->>'state' AS state, left(metadata->>'trace_id', 8) AS trace \
	  FROM a2a_tasks ORDER BY last_updated"

ibkr-check:      ## broker stack: health, paper account, one price (AAPL); never places an order
	$(COMPOSE) exec -T ibkrfacade sh -c 'H="Authorization: Bearer $$IBKR_SECURITY_READ_TOKEN"; B=http://localhost:8082/ibkr; \
	  curl -fsS $$B/actuator/health && echo && \
	  curl -fsS -H "$$H" $$B/account/summary | head -c 600 && echo && \
	  curl -fsS -H "$$H" $$B/subscribe/265598 >/dev/null && sleep 3 && curl -fsS -H "$$H" $$B/price/265598 && echo'

logs:            ## agent logs (JSON events)
	$(COMPOSE) logs -f market-sentiment research

scan-local: up   ## phase 4 one-shot run without A2A
	$(COMPOSE) run --rm market-sentiment run --trigger scan

egress-test: up  ## example.com must be blocked, api.anthropic.com must pass
	$(COMPOSE) run --rm -T --entrypoint python market-sentiment - < scripts/egress_check.py

down:
	$(COMPOSE) down
