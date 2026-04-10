#!/usr/bin/env bash
# Stop hook — runs hygiene at session end to clean stale state
python3 -c "
import sys
sys.path.insert(0, '$(dirname "$(dirname "$0")")')
from lib.session_hygiene import run_full_hygiene
report = run_full_hygiene('.')
if report.strip():
    print(report, file=sys.stderr)
" 2>&1 || true
exit 0
