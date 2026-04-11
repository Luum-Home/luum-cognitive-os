#!/usr/bin/env bash
# Stop hook: sync session metrics to MLflow
# Always exits 0 — never blocks session cleanup.

python3 -c "
from lib.mlflow_bridge import MLflowBridge
import sys

b = MLflowBridge()
if b.is_available():
    r1 = b.sync_cost_events()
    r2 = b.sync_skill_metrics()
    merged = {k: r1.get(k, 0) + r2.get(k, 0) for k in ('synced', 'skipped', 'errors')}
    print(b.format_sync_report(merged), file=sys.stderr)
" 2>&1 || true

exit 0
