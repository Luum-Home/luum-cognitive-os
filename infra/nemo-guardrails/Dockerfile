FROM python:3.11-slim

RUN pip install --no-cache-dir nemoguardrails

WORKDIR /app

# Copy Colang rules and NeMo config
COPY config/ /app/config/

EXPOSE 8088

CMD ["nemoguardrails", "server", "--port", "8088", "--config", "/app/config"]
