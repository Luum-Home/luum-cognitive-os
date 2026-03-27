FROM python:3.11-slim

LABEL maintainer="luum-agent-os"
LABEL description="GitHub Webhook Trigger for Cognitive OS SDD Pipeline"

# Install gh CLI
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl git && \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends gh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Claude CLI (assumes it's available in PATH or mounted)
# For production, install via npm or mount the binary
RUN npm install -g @anthropic-ai/claude-code 2>/dev/null || true

WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn

# Copy application code
COPY lib/ /app/lib/

ENV WEBHOOK_PORT=8001
ENV WEBHOOK_PROJECT_DIR=/workspace
ENV PYTHONPATH=/app

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "-m", "lib.webhook_trigger"]
