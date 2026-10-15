# Build from the repo root after the base image:
#   docker build -f agents/research/Dockerfile -t auxin-research .
# Phase 5: LLM-free stub that accepts and records ideas; the real Research agent comes in phase 6.
ARG BASE_IMAGE=auxin-agent-base:latest
FROM ${BASE_IMAGE}

USER root
COPY agents/research/agent.yaml /agent/
USER agent

CMD ["serve"]
