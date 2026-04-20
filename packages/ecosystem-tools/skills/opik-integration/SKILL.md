<!-- SCOPE: both -->
---
name: opik-integration
description: >
  Configure and use Opik for LLM observability, tracing, and evaluation.
  Provides agent execution tracing, quality evaluation, and monitoring dashboards.
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-26
license: MIT
metadata:
  author: luum
  tool: comet-ml/opik
  tool-license: Apache-2.0
  tool-ring: ADOPT
  tool-score: 8.95
audience: os-dev
---

## Purpose

Integrate Opik as the observability backbone for Cognitive OS. Opik traces LLM calls across agent pipelines (hooks, skills, sub-agents), evaluates agent quality via automated experiments, and feeds monitoring data into the MAPE-K self-healing loop.

## Invocation

`/opik-setup` — Initial configuration
`/opik-trace` — Start tracing an agent session
`/opik-eval` — Run evaluation experiment on agent outputs

## Setup

### Prerequisites
- Python 3.10+
- `pip install opik` (the Python SDK)
- Opik backend: either Comet hosted (recommended for start) or self-hosted (Java + ClickHouse)

### Configuration

Add to `cognitive-os.yaml` services section:
```yaml
services:
  opik:
    mode: on_demand
    idle_timeout_minutes: 30
    config:
      api_url: "${OPIK_API_URL:-https://www.comet.com/opik/api}"
      api_key: "${OPIK_API_KEY}"
      project_name: "cognitive-os"
```

### Environment Variables
```
OPIK_API_URL=https://www.comet.com/opik/api   # or self-hosted URL
OPIK_API_KEY=<your-api-key>
```

## What to Do

### Step 1: Trace Agent Executions

Wrap agent calls with Opik tracing:
```python
import opik

@opik.track
def execute_agent_skill(skill_name, input_data):
    # Agent execution logic
    pass
```

For hooks, add trace metadata via environment:
```bash
export OPIK_TRACE_ID=$(uuidgen)
export OPIK_SPAN_NAME="hook:${HOOK_NAME}"
```

### Step 2: Feed MAPE-K Loop

Use Opik traces to detect:
- High latency patterns → trigger optimization
- Error rate spikes → trigger auto-repair
- Quality degradation → trigger skill re-evaluation
- Cost anomalies → trigger model routing changes

### Step 3: Run Evaluations

Create evaluation experiments:
```python
import opik

experiment = opik.Experiment(
    name="skill-quality-eval",
    dataset="agent-outputs"
)
experiment.run(
    task=my_agent_task,
    scoring=[
        opik.metrics.Hallucination(),
        opik.metrics.AnswerRelevance(),
        opik.metrics.ContextRecall(),
    ]
)
```

## Integration Points

| Cognitive OS Component | Opik Feature | Connection |
|----------------------|-------------|------------|
| MAPE-K Monitor | Trace API | Feed error/latency signals |
| Agent KPIs | Metrics API | Track quality/cost metrics |
| Sub-agent orchestration | Span hierarchy | Trace parent→child relationships |
| Skill execution | Decorators | Auto-trace skill invocations |
| Model routing | Cost tracking | Optimize model selection |

## Rules

- NEVER log sensitive data (API keys, user PII) in traces
- Use project namespacing to isolate traces by workspace
- Default to Comet hosted for evaluation, self-host only when data residency requires it
- Trace granularity: skill-level (not token-level) to control overhead
- Batch flush traces — don't block agent execution on trace delivery
