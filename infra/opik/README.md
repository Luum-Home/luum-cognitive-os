# Opik — LLM Observability

## Quick Start

```bash
docker compose -f docker-compose.cognitive-os.yml --profile observability up -d
```

## Architecture

- **opik-backend**: Java-based API server (port 5173 → 8080)
- **opik-frontend**: React UI (port 5174 → 5173)
- **opik-mysql**: Metadata storage
- **langfuse-clickhouse**: Shared analytics DB (reused from Langfuse)

## Python SDK

```bash
pip install opik
```

```python
import opik
opik.configure(api_url="http://localhost:5173/api")
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| OPIK_PORT | 5173 | Backend API port |
| OPIK_UI_PORT | 5174 | Frontend UI port |
| OPIK_MYSQL_USER | opik | MySQL username |
| OPIK_MYSQL_PASS | opik_pass | MySQL password |
| OPIK_CH_USER | default | ClickHouse username |
