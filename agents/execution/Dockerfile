# Execution: deterministic, no LLM (auxin_runtime.execution). Build from the repo root after the base image:
#   docker build -f agents/execution/Dockerfile -t auxin-execution .
ARG BASE_IMAGE=auxin-agent-base:latest
FROM ${BASE_IMAGE}

USER root
COPY agents/execution/agent.yaml /agent/
USER agent

CMD ["serve"]
