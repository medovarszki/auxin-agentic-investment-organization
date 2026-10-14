COMPOSE = docker compose -f infra/compose/docker-compose.yml

.PHONY: test validate base build up scan egress-test down

test:            ## unit tests
	uv run pytest -q

validate:        ## agent.yaml / org.yaml consistency
	uv run python scripts/validate_org.py

base:            ## shared agent base image
	docker build -f agents/Dockerfile -t auxin-agent-base .

build: base      ## agent images
	$(COMPOSE) build

up:              ## egress proxy
	$(COMPOSE) up -d egress-proxy

scan: up         ## one Market & Sentiment run; result JSON on stdout
	$(COMPOSE) run --rm market-sentiment

egress-test: up  ## example.com must be blocked, api.anthropic.com must pass
	$(COMPOSE) run --rm -T --entrypoint python market-sentiment - < scripts/egress_check.py

down:
	$(COMPOSE) down
