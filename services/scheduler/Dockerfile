# Scheduler: timed A2A triggers (09:00 scan, 15:30 review, 21:00 evaluate) on workdays, Europe/Budapest.
# Deterministic, no Claude token, no IBKR access. The shared base image already holds the package.
# Build from the repo root after the base image:
#   docker build -f services/scheduler/Dockerfile -t auxin-scheduler .
ARG BASE_IMAGE=auxin-agent-base:latest
FROM ${BASE_IMAGE}

HEALTHCHECK --interval=60s --timeout=5s CMD ["python", "-c", "import auxin_scheduler"]
ENTRYPOINT ["auxin-scheduler"]
CMD ["serve"]
