#!/usr/bin/env bash
# timing.sh — Hook timing wrapper for Cognitive OS performance monitoring
#
# Usage:
#   source "$(dirname "$0")/_lib/timing.sh"
#   start_timer
#   # ... hook logic ...
#   end_timer "hook-name" "true"   # name, success (true/false)
#
# Records hook execution time to the performance monitor.
# Timing is best-effort: failures in recording do NOT affect hook execution.
#
# Author: luum

# Guard: only load once
[ "${_TIMING_SH_LOADED:-}" = "true" ] && return 0
_TIMING_SH_LOADED="true"

_HOOK_START_TIME=""

start_timer() {
    # Use Python for millisecond precision, fall back to date
    _HOOK_START_TIME=$(python3 -c "import time; print(int(time.time()*1000))" 2>/dev/null \
        || date +%s%3N 2>/dev/null \
        || echo "0")
}

end_timer() {
    local hook_name="${1:-unknown}"
    local success="${2:-true}"
    local end_time
    end_time=$(python3 -c "import time; print(int(time.time()*1000))" 2>/dev/null \
        || date +%s%3N 2>/dev/null \
        || echo "0")

    # Calculate duration
    if [ "$_HOOK_START_TIME" = "0" ] || [ "$end_time" = "0" ]; then
        return 0
    fi
    local duration=$((end_time - _HOOK_START_TIME))

    # Convert success to Python bool
    local py_success="True"
    [ "$success" = "false" ] && py_success="False"

    # Resolve project directory for Python path
    local project_dir="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-}}"
    if [ -z "$project_dir" ]; then
        project_dir="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
    fi

    # Record to performance metrics (best effort, don't fail the hook)
    python3 -c "
import sys
sys.path.insert(0, '$project_dir')
from lib.performance_monitor import PerformanceMonitor
monitor = PerformanceMonitor('$project_dir/.cognitive-os/metrics/performance.jsonl')
monitor.record('hook:$hook_name', 'execute', $duration, $py_success)
" 2>/dev/null || true
}
