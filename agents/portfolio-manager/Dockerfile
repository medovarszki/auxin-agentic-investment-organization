# Build from the repo root after the base image:
#   docker build -f agents/portfolio-manager/Dockerfile -t auxin-portfolio-manager .
ARG BASE_IMAGE=auxin-agent-base:latest
FROM ${BASE_IMAGE}

# Files stay owned by root: the agent can read but not change its role, prompts, skills or the portfolio rules.
USER root
COPY agents/portfolio-manager/agent.yaml agents/portfolio-manager/CLAUDE.md /agent/
COPY agents/portfolio-manager/prompts /agent/prompts
COPY agents/portfolio-manager/skills /agent/.claude/skills
COPY org/rules/portfolio-rules.yaml /agent/portfolio-rules.yaml
USER agent

CMD ["serve"]
