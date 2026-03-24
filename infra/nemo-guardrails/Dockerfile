FROM python:3.11-slim

RUN pip install --no-cache-dir nemoguardrails

WORKDIR /app

# Default config — override by mounting /app/config
RUN mkdir -p /app/config

EXPOSE 8088

CMD ["nemoguardrails", "server", "--port", "8088"]
