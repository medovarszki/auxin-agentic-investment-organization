# Build from the repo root after the base image:
#   docker build -f agents/market-sentiment/Dockerfile -t auxin-market-sentiment .
ARG BASE_IMAGE=auxin-agent-base:latest
FROM ${BASE_IMAGE}

# Files stay owned by root: the agent can read but not change its own role, prompts or skills.
USER root
COPY agents/market-sentiment/agent.yaml agents/market-sentiment/CLAUDE.md /agent/
COPY agents/market-sentiment/prompts /agent/prompts
COPY agents/market-sentiment/skills /agent/.claude/skills
USER agent

CMD ["run", "--trigger", "scan"]
