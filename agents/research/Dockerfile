# Build from the repo root after the base image:
#   docker build -f agents/research/Dockerfile -t auxin-research .
ARG BASE_IMAGE=auxin-agent-base:latest
FROM ${BASE_IMAGE}

# Files stay owned by root: the agent can read but not change its own role, prompts or skills.
USER root
COPY agents/research/agent.yaml agents/research/CLAUDE.md /agent/
COPY agents/research/prompts /agent/prompts
COPY agents/research/skills /agent/.claude/skills
USER agent

CMD ["serve"]
