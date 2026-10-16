# Knowledge service: REST (writes) + MCP (read-only tools) over the knowledge base tables; applies the
# Alembic migrations on start. The shared base image already holds the package.
# Build from the repo root after the base image:
#   docker build -f services/knowledge/Dockerfile -t auxin-knowledge .
ARG BASE_IMAGE=auxin-agent-base:latest
FROM ${BASE_IMAGE}

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
ENTRYPOINT ["auxin-knowledge"]
CMD []
