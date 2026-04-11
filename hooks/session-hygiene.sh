#!/usr/bin/env bash
# Stop hook — runs hygiene + syncs work queue at session end
python3 -c "
import sys, os
sys.path.insert(0, '$(dirname "$(dirname "$0")")')

# 1. Standard hygiene (prune tasks, update catalog)
from lib.session_hygiene import run_full_hygiene
report = run_full_hygiene('.')
if report.strip():
    print(report, file=sys.stderr)

# 2. Sync work queue from plans
try:
    from lib.work_queue import WorkQueue
    q = WorkQueue()
    synced = q.sync_from_plans()
    if synced:
        print(f'Work queue: {synced} task(s) auto-completed from plans', file=sys.stderr)
except Exception:
    pass
" 2>&1 || true
exit 0
