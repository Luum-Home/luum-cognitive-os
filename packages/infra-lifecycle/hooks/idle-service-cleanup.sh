#!/usr/bin/env bash
# SCOPE: os-only
# @manual-trigger: run by cron or operator on demand; not a default Claude event hook
# idle-service-cleanup.sh — Stop idle Docker services on session exit
# Type: Stop hook
# Runs stop_idle_services() from smart_infra to clean up services
# that exceeded their idle timeout during this session.
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Source timing if available
TIMING_LIB="$(dirname "$0")/_lib/timing.sh"
[ -f "$TIMING_LIB" ] && source "$TIMING_LIB" && start_timer

# Stop idle services via smart_infra
if command -v python3 >/dev/null 2>&1; then
  stopped=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR/lib')
from smart_infra import stop_idle_services
result = stop_idle_services('$PROJECT_DIR')
if result:
    print(', '.join(result))
" 2>/dev/null || true)
  if [ -n "$stopped" ]; then
    echo "Stopped idle services: $stopped"
  fi
fi

[ -f "$TIMING_LIB" ] && end_timer "idle-service-cleanup" "true"
exit 0
