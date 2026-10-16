# Shared base image for every Auxin agent, MCP server and Python service (auxin-agent-base). It does not run on its own;
# each agents/<name>/Dockerfile (and mcp-servers/<name>/, services/<name>/ Dockerfile) builds on it.
# Build from the repo root: docker build -f agents/Dockerfile -t auxin-agent-base .
FROM python:3.12.15-slim

COPY --from=astral/uv:0.13.1 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /src
COPY pyproject.toml uv.lock .python-version ./
COPY libs ./libs
COPY mcp-servers/ibkr ./mcp-servers/ibkr
COPY services/knowledge ./services/knowledge
COPY services/scheduler ./services/scheduler
RUN uv sync --frozen --no-dev --no-editable \
    && rm -rf /src /root/.cache

# Non-root user. Its home holds the Claude Code session files; mount it as tmpfs at runtime.
RUN useradd --uid 10001 --create-home --home-dir /home/agent --shell /usr/sbin/nologin agent
ENV HOME=/home/agent \
    DISABLE_TELEMETRY=1 \
    DISABLE_ERROR_REPORTING=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

WORKDIR /agent
USER agent
HEALTHCHECK --interval=60s --timeout=5s CMD ["python", "-c", "import auxin_runtime"]
ENTRYPOINT ["auxin-agent"]
