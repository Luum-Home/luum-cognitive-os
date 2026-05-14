<!-- SCOPE: both -->
<!-- TIER: 2 -->
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
| Phoenix (LLM trace UI) | `pip install arize-phoenix` | `uv run phoenix serve` (UI at http://localhost:6006) |
| mlflow (agent metrics) | `pip install mlflow-skinny>=2.0` | `mlflow server --backend-store-uri sqlite:///mlflow.db` |
| litellm | `pip install litellm>=1.0` | `litellm --config infra/litellm/config.yaml` or Python API |
| nemo-guardrails | `pip install nemoguardrails>=0.10` | `from nemoguardrails import RailsConfig, LLMRails` |
| memu | `pip install memu>=2.0` | `python -m memu.server` |
| jupyter | `pip install jupyter>=1.0 notebook>=7.0` | `jupyter lab` |

## Services and Profiles

Services are defined in `docker-compose.cognitive-os.yml`. Some run by default, others require specific Docker Compose profiles.

### Default Profile (no profile needed)

| Service | Purpose | When Needed | Status |
|---------|---------|-------------|--------|
| Phoenix (pip) | LLM trace UI — replaces the former observability stack | Metrics, agent KPIs, LLM evals | **PIP** (ADR-058) |
| litellm | LLM proxy and model routing | Model routing, cost tracking | **MIGRATED TO PIP** |
| nemo-guardrails | NeMo Guardrails for content safety | PII detection, content filtering | **MIGRATED TO PIP** |
| jupyter | Jupyter notebook environment | Data analysis, experimentation | **MIGRATED TO PIP** |

### Profile: `memory`

| Service | Purpose | When Needed | Status |
|---------|---------|-------------|--------|
| memu | Memory management service | Cross-session memory sync | **MIGRATED TO PIP** |
| cognee | Knowledge graph and RAG engine | Advanced memory, knowledge retrieval | Docker (pip API available) |

### Profile: `observability`

ADR-060 (2026-04-24): the cloud-only observability trace UI was removed under
the local-only optional-services policy. LLM observability is now provided by
Arize Phoenix (pip, Apache 2.0) — see ADR-058 and ADR-060.

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
4. The system polls for healthy status (up to 120s)
5. Once healthy, the skill proceeds normally
6. On session exit, `idle-service-cleanup.sh` stops services past their `idle_timeout_minutes`

### Skill-to-Service Map

| Skill/Hook | Required Service |
|---|---|
| agent-kpis, observability-trace | phoenix (pip) + mlflow (pip) |
| sdd-apply, sdd-verify, sdd-pipeline, model-routing | litellm |
| guardrails-validator, content-policy | nemo-guardrails |
| memu-sync | memu |
| cognee-search | cognee |
| jupyter-sandbox | jupyter |

This map is configurable in `cognitive-os.yaml` under `resources.infrastructure.skill_service_map`.

### Graceful Degradation

If Docker is not available or a service fails to start, the system logs a warning and continues. Skills still execute — they may produce degraded results (e.g., no traces sent to Phoenix) but never crash.

### Usage in Python

```python
from lib.smart_infra import ensure_service, requires_service

# Explicit

# Decorator
def send_trace(...):
    ...
```

### Usage in Bash Hooks

```bash
```

## Configuration

In `cognitive-os.yaml`, services are configured under `resources.infrastructure.services`:

```yaml
resources:
  infrastructure:
    services:
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

## Contextual Trigger

- When work relates to Infrastructure Health Check.
