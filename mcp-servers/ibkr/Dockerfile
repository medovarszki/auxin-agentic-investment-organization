# IBKR MCP server (read-only tools over ibkrfacade). The shared base image already holds the package.
# Build from the repo root after the base image:
#   docker build -f mcp-servers/ibkr/Dockerfile -t auxin-mcp-ibkr .
ARG BASE_IMAGE=auxin-agent-base:latest
FROM ${BASE_IMAGE}

EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s CMD ["python", "-c", "import auxin_mcp_ibkr.server"]
ENTRYPOINT ["auxin-mcp-ibkr"]
CMD []
