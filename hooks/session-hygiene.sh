#!/usr/bin/env bash
# SCOPE: both
# Stop hook — runs hygiene at session end to clean stale state
python3 -c "
import sys
sys.path.insert(0, '$(dirname "$(dirname "$0")")')
from lib.session_hygiene import run_full_hygiene
report = run_full_hygiene('.')
if report.strip():
    print(report, file=sys.stderr)
" 2>&1 || true

# Warn about pending work-queue items
python3 - <<'PYEOF' 2>/dev/null || true
import sys, os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
try:
    from lib.work_queue import WorkQueue
    q = WorkQueue(queue_path=os.path.join(PROJECT_ROOT, '.cognitive-os', 'work-queue.json'))
    pending = q.get_pending()
    if pending:
        print(f"\n⚠ WORK QUEUE: {len(pending)} pending task(s) not completed this session:", file=sys.stderr)
        for t in pending[:5]:
            desc = t.get('description', '')[:80]
            print(f"  - [{t.get('id','')}] {desc}", file=sys.stderr)
        if len(pending) > 5:
            print(f"  ... and {len(pending) - 5} more. Check .cognitive-os/work-queue.json", file=sys.stderr)
except Exception:
    pass
PYEOF

exit 0
