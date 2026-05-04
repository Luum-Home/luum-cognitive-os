FROM python:3.11-slim

LABEL org.opencontainers.image.title="Luum Cognitive OS worker"
LABEL org.opencontainers.image.description="Containerized COS worker runtime for ADR-140 cloud-worker surfaces"

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

ENV COGNITIVE_OS_CONTAINER=1
ENV COGNITIVE_OS_PROJECT_DIR=/workspace
ENV COGNITIVE_OS_RUNTIME_DIR=/workspace/.cognitive-os/runtime
ENV COGNITIVE_OS_HARNESS=barecli

WORKDIR /workspace

COPY docker/cos-worker/entrypoint.sh /opt/cos-worker/entrypoint.sh
RUN chmod +x /opt/cos-worker/entrypoint.sh

ENTRYPOINT ["/opt/cos-worker/entrypoint.sh"]
CMD ["--self-test"]
