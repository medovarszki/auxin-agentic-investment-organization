# Dashboard: read-only JSON API (task store, decision log, lessons; portfolio live through the IBKR MCP server)
# and one static page. The shared base image already holds the package.
# Build from the repo root after the base image:
#   docker build -f services/dashboard/Dockerfile -t auxin-dashboard .
ARG BASE_IMAGE=auxin-agent-base:latest
FROM ${BASE_IMAGE}

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
ENTRYPOINT ["auxin-dashboard"]
CMD []
