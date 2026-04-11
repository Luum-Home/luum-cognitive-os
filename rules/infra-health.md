# Infrastructure Health Check

## Purpose

The `infra-health.sh` SessionStart hook auto-detects Docker availability and reports on the status of infrastructure services defined in `cognitive-os.yaml`. It is advisory only -- it never blocks session startup.

## Behavior

1. **Docker check**: If Docker is not running, outputs an advisory message and exits cleanly (exit 0).
2. **Config read**: Reads `cognitive-os.yaml -> resources.infrastructure.services` to determine expected services.
3. **Status comparison**: Queries `docker compose ps` against the compose file and compares running vs expected services.
4. **Report**: Outputs a summary line (`Infrastructure: N/M services running`) and lists missing services with their profiles.
5. **Auto-start (opt-in)**: If `INFRA_AUTO_START=true`, automatically starts missing services. Otherwise, suggests the commands.
6. **Metrics**: Logs every check to `.cognitive-os/metrics/infra-health.jsonl`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `INFRA_AUTO_START` | `false` | Set to `true` to auto-start missing Docker services on session start |

`INFRA_AUTO_START` defaults to `false` (safe default). Auto-starting services consumes resources and may not be desired in all environments.

## Pip-Installed Services (not checked as Docker containers)

The following services have been migrated to pip packages. The infra-health hook does NOT
check for their Docker containers — they run as Python libraries or local processes.

| Service | pip package | How to run |
|---------|-------------|------------|
| langfuse-web + deps | `pip install mlflow>=2.0` | `mlflow server --backend-store-uri sqlite:///mlflow.db` |
| litellm | `pip install litellm>=1.0` | `litellm --config infra/litellm/config.yaml` or Python API |
| nemo-guardrails | `pip install nemoguardrails>=0.10` | `from nemoguardrails import RailsConfig, LLMRails` |
| memu | `pip install memu>=2.0` | `python -m memu.server` |
| jupyter | `pip install jupyter>=1.0 notebook>=7.0` | `jupyter lab` |
| opik | `pip install opik>=1.0` | Uses Comet cloud API — no local server needed |

## Services and Profiles

Services are defined in `docker-compose.cognitive-os.yml`. Some run by default, others require specific Docker Compose profiles.

### Default Profile (no profile needed)

| Service | Purpose | When Needed | Status |
|---------|---------|-------------|--------|
| langfuse-web | LLM observability and tracing | Metrics, agent KPIs | **MIGRATED TO PIP** (mlflow) |
| langfuse-pg | Langfuse PostgreSQL database | Required by langfuse-web | **MIGRATED TO PIP** |
| langfuse-valkey | Langfuse cache | Required by langfuse-web | **MIGRATED TO PIP** |
| langfuse-clickhouse | Langfuse analytics | Required by langfuse-web | **MIGRATED TO PIP** |
| langfuse-seaweedfs | Langfuse object storage | Required by langfuse-web | **MIGRATED TO PIP** |
| langfuse-worker | Langfuse background worker | Required by langfuse-web | **MIGRATED TO PIP** |
| litellm | LLM proxy and model routing | Model routing, cost tracking | **MIGRATED TO PIP** |
| nemo-guardrails | NeMo Guardrails for content safety | PII detection, content filtering | **MIGRATED TO PIP** |
| paperclip | Governance and compliance dashboard | Squad reports, governance reviews | Docker (no pip equiv) |
| paperclip-pg | Paperclip PostgreSQL database | Required by paperclip | Docker (no pip equiv) |
| jupyter | Jupyter notebook environment | Data analysis, experimentation | **MIGRATED TO PIP** |

### Profile: `memory`

| Service | Purpose | When Needed | Status |
|---------|---------|-------------|--------|
| memu | Memory management service | Cross-session memory sync | **MIGRATED TO PIP** |
| cognee | Knowledge graph and RAG engine | Advanced memory, knowledge retrieval | Docker (pip API available) |

### Profile: `observability`

| Service | Purpose | When Needed | Status |
|---------|---------|-------------|--------|
| opik-backend | Opik tracing backend | LLM evaluation and tracing | **MIGRATED TO PIP** (cloud) |
| opik-mysql | Opik MySQL database | Required by opik-backend | **MIGRATED TO PIP** |
| opik-frontend | Opik web UI | Trace visualization | **MIGRATED TO PIP** (Comet UI) |

### Profile: `ui`

| Service | Purpose | When Needed |
|---------|---------|-------------|
| automaker | UI automation service | UI-based workflows |

### Profile: `automation`

| Service | Purpose | When Needed |
|---------|---------|-------------|
| webhook-trigger | Webhook event listener | Event-driven automation, singularity triggers |

## Smart Start (Lazy Loading)

When `smart_start: true` is set in `cognitive-os.yaml`, Docker services start automatically when a skill or hook needs them, instead of requiring manual startup or `INFRA_AUTO_START=true`.

### How It Works

1. A skill or hook triggers (e.g., `/agent-kpis`)
2. `lib/smart_infra.py` looks up the skill→service map
3. If the required service (e.g., langfuse) is not running, it starts via `docker compose up -d`
4. The system polls for healthy status (up to 120s)
5. Once healthy, the skill proceeds normally
6. On session exit, `idle-service-cleanup.sh` stops services past their `idle_timeout_minutes`

### Skill-to-Service Map

| Skill/Hook | Required Service |
|---|---|
| agent-kpis, observability-trace | langfuse |
| sdd-apply, sdd-verify, sdd-pipeline, model-routing | litellm |
| guardrails-validator, content-policy | nemo-guardrails |
| squad-report, paperclip-sync | paperclip |
| memu-sync | memu |
| cognee-search | cognee |
| jupyter-sandbox | jupyter |

This map is configurable in `cognitive-os.yaml` under `resources.infrastructure.skill_service_map`.

### Graceful Degradation

If Docker is not available or a service fails to start, the system logs a warning and continues. Skills still execute — they may produce degraded results (e.g., no traces sent to Langfuse) but never crash.

### Usage in Python

```python
from lib.smart_infra import ensure_service, requires_service

# Explicit
ensure_service("langfuse")

# Decorator
@requires_service("langfuse")
def send_trace(...):
    ...
```

### Usage in Bash Hooks

```bash
python3 -c "from lib.smart_infra import ensure_service; ensure_service('langfuse')" 2>/dev/null || true
```

## Configuration

In `cognitive-os.yaml`, services are configured under `resources.infrastructure.services`:

```yaml
resources:
  infrastructure:
    services:
      langfuse:
        mode: on_demand
        idle_timeout_minutes: 30
      litellm:
        mode: always
      # ... etc
```

The `mode` field indicates the expected availability:
- `always`: Service should be running at all times. The hook flags these as priority when missing.
- `on_demand`: Service starts when needed. Missing is reported but not critical.

## Metrics

Every health check is logged to `.cognitive-os/metrics/infra-health.jsonl`:

```json
{
  "timestamp": "2026-03-26T12:00:00Z",
  "docker": true,
  "running": 8,
  "expected": 12,
  "missing": "nemo-guardrails (profile: default), memu (profile: memory)",
  "action": "suggest"
}
```

## Integration

- **Hook**: `hooks/infra-health.sh` (SessionStart)
- **Related**: `hooks/cognitive-os-health.sh` also checks Docker services as part of overall health
- **Resource governance**: `rules/resource-governance.md` manages infrastructure auto-scaling during sessions
- **Infra intent**: `rules/infra-intent.md` detects infrastructure needs in agent prompts
