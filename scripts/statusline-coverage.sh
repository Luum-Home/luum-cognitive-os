#!/usr/bin/env bash
# SCOPE: os-only
# ROLE: observability
# CANONICAL: scripts/statusline-coverage.sh
# @on-demand: Emit ACC coverage segment for statusline integrations.
#
# Reads from cache file ONLY — never runs live computation.
# Safe to call every second from a statusline loop: pure read, <50ms.
#
# Output:
#   ACC: 85.3% | REAL: 1860 DORM: 1393    (when cache is fresh, <=5min)
#   ACC: ? (run cos-coverage to refresh)   (when cache is stale or absent)
#
# Opt-in wiring examples:
#
#   Zsh/bash PROMPT_COMMAND (refresh every 30s with background job):
#     _cos_coverage_refresh() {
#       local cache="$(scripts/cos-root project)/.cognitive-os/runtime/coverage-snapshot.json"
#       local ts
#       ts=$(python3 -c "import json,time; d=json.load(open('${cache}')); print(d.get('_cached_at',0))" 2>/dev/null || echo 0)
#       if (( $(date +%s) - ts > 30 )); then
#         (python3 "$(dirname "$0")/cos_coverage.py" --refresh >/dev/null 2>&1 &)
#       fi
#     }
#     export PS1='$(bash scripts/statusline-coverage.sh) '$PS1
#
#   Tmux status-right (add to ~/.tmux.conf):
#     set -g status-right '#(bash /path/to/statusline-coverage.sh)'
#     set -g status-interval 30
#
#   hook-stream integration (add to shell that sources hook-stream-statusline.sh):
#     # After sourcing hook-stream-statusline.sh, append coverage segment:
#     bash scripts/statusline-coverage.sh
#
# Environment:
#   COGNITIVE_OS_PROJECT_DIR / CODEX_PROJECT_DIR / CLAUDE_PROJECT_DIR — project root override
#   COS_COVERAGE_STALE_MAX — seconds before showing "ACC: ?" (default: 300)

set -uo pipefail

# ── Locate project root ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$("$SCRIPT_DIR/cos-root" project)"

CACHE_FILE="${PROJECT_DIR}/.cognitive-os/runtime/coverage-snapshot.json"
STALE_MAX="${COS_COVERAGE_STALE_MAX:-300}"

# ── Read cache (read-only, no computation) ─────────────────────────────────────
emit_coverage_segment() {
  if [ ! -f "$CACHE_FILE" ]; then
    echo "ACC: ? (run cos-coverage to refresh)"
    return
  fi

  python3 - "$CACHE_FILE" "$STALE_MAX" <<'PYEOF'
import json
import sys
import time

cache_file = sys.argv[1]
stale_max = float(sys.argv[2])

ARROW = {"up": "↑", "down": "↓", "flat": "→"}

try:
    data = json.loads(open(cache_file).read())
except (OSError, json.JSONDecodeError):
    print("ACC: ? (run cos-coverage to refresh)")
    sys.exit(0)

cached_at = data.get("_cached_at", 0)
age = time.time() - cached_at

if age > stale_max:
    print("ACC: ? (run cos-coverage to refresh)")
    sys.exit(0)

pct = data.get("coverage_pct", "?")
real = data.get("real", "?")
dorm = data.get("dormant", "?")
trend = data.get("trend", {})
pct_arrow = ARROW.get(trend.get("coverage_pct", ""), "")

print(f"ACC: {pct}%{pct_arrow} | REAL: {real} DORM: {dorm}")
PYEOF
}

emit_coverage_segment
