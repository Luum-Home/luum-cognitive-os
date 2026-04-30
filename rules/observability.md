<!-- SCOPE: both -->
<!-- TIER: 2 -->
# Observability — MLflow Integration

## Always Active (when mlflow installed)

MLflow provides zero-Docker LLM observability. Install: `pip install mlflow`.

### Automatic behavior
- Session end: `hooks/mlflow-sync.sh` syncs cost-events and skill-metrics to MLflow
- All data stored in `mlflow.db` (SQLite, no server needed)

### Manual
- Start UI: `mlflow server --host 127.0.0.1 --port 5000`
- View traces: `http://localhost:5000`

### Graceful degradation
If mlflow is not installed, all observability hooks are silent no-ops.
Existing JSONL metrics continue working regardless.

### Python API
```python
from lib.mlflow_bridge import MLflowBridge
b = MLflowBridge()
b.log_agent_run("my-agent", "sonnet", tokens=1200, duration_ms=3000, success=True, cost_usd=0.07)
b.log_session_summary("session-123", agents_launched=5, total_cost=0.35, total_tokens=8000)
```
