COMPOSE = docker compose --env-file .env -f infra/compose/docker-compose.yml
# Broker: the ibkrfacade project's own stack, run from its checkout with its own .env (and COMPOSE_FILE mode)
IBKRFACADE_DIR ?= ../ibkrfacade
IBKR = cd $(IBKRFACADE_DIR) && docker compose
PSQL = $(COMPOSE) exec -T postgres sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -P pager=off -c "$$0"'

.PHONY: test validate base build up ibkr-up ibkr-down ibkr-check mcp-check kb-check scan review run-job tasks decisions db-revision execute-pending logs \
	ui scan-local egress-test down

test:            ## unit tests
	uv run pytest -q

validate:        ## agent.yaml / org.yaml consistency
	uv run python scripts/validate_org.py

base:            ## shared agent base image
	docker build -f agents/Dockerfile -t auxin-agent-base .

build: base      ## agent, MCP server and service images
	$(COMPOSE) build

up: ibkr-up      ## broker stack, egress proxy, Postgres, knowledge service, agent A2A servers, Jaeger, dashboard
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
	$(IBKR) exec -T ibkrfacade sh -c 'B=http://localhost:8082/ibkr; curl -fsS $$B/actuator/health && echo && \
	  curl -fsS $$B/account/summary | head -c 600 && echo && curl -fsS $$B/price/265598 && echo'

mcp-check: up    ## IBKR MCP server: tool list, AAPL contract and price, account summary (no orders)
	$(COMPOSE) run --rm -T --entrypoint python operator - < scripts/mcp_check.py

review: up       ## daily review: PM -> execute_pending, then one Research review per open position, SELL on REDUCE / CLOSE
	$(COMPOSE) run --rm operator trigger --to portfolio-manager --type review_trigger

run-job: up      ## run a scheduler job now: make run-job job=scan|review|evaluate
	$(COMPOSE) run --rm --no-deps scheduler run-job $(job)

execute-pending: up  ## Execution: place the orders pending since a closed market, follow up the submitted ones
	$(COMPOSE) run --rm operator trigger --to execution --type execute_pending

kb-check: up     ## knowledge service: health, latest decisions, rejections, MCP tools and a search (read-only)
	$(COMPOSE) run --rm -T -e AUXIN_KNOWLEDGE_URL=http://knowledge:8000 --entrypoint python operator - < scripts/kb_check.py

decisions:       ## the decision log (knowledge base), newest first
	$(PSQL) "SELECT created_at, kind, agent, symbol, conid, left(summary, 70) AS summary, left(trace_id, 8) AS trace \
	  FROM decisions ORDER BY created_at DESC LIMIT 30"

# Schema change: edit services/knowledge/src/auxin_knowledge/db.py, then make db-revision m="what changed";
# review the generated file under migrations/versions and commit it. The service applies it on start.
db-revision: build up
	$(COMPOSE) run --rm --no-deps --user $$(id -u):$$(id -g) \
	  -v $(CURDIR)/services/knowledge/src/auxin_knowledge/migrations:/migrations \
	  --entrypoint alembic knowledge -c /migrations/alembic.ini revision --autogenerate -m "$(m)"

logs:            ## agent, Execution, MCP, knowledge, scheduler and dashboard logs (JSON events)
	$(COMPOSE) logs -f market-sentiment research portfolio-manager execution mcp-ibkr knowledge scheduler dashboard

ui: up           ## dashboard and Jaeger, localhost only
	@echo "dashboard: http://localhost:8080   Jaeger: http://localhost:16686"

scan-local: up   ## phase 4 one-shot run without A2A
	$(COMPOSE) run --rm market-sentiment run --trigger scan

egress-test: up  ## example.com must be blocked, api.anthropic.com must pass
	$(COMPOSE) run --rm -T --entrypoint python market-sentiment - < scripts/egress_check.py

down:            ## Auxin services only; the broker stack: make ibkr-down
	$(COMPOSE) down
