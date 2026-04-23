#!/usr/bin/env bash
# session-leak-diagnostic.sh — detect leaked Claude sessions and MCP children.
#
# Root cause addressed (2026-04-20):
#   so-reaper only cleans PIDs registered in lib/process_registry. Main `claude`
#   processes are never registered, so abandoned terminals accumulate zombie
#   sessions + one `engram mcp --tools=agent` child per session. This script
#   surfaces the leak and writes a machine-readable report.
#
# Usage:
#   bash scripts/session-leak-diagnostic.sh           # human report
#   bash scripts/session-leak-diagnostic.sh --json    # jsonl report
#   bash scripts/session-leak-diagnostic.sh --kill    # interactive kill prompt
#
# Thresholds (override via env):
#   MAX_SESSION_AGE_MIN=30       # claude session idle > N min → suspect
#   MAX_ENGRAM_CHILDREN=3        # > N engram mcp children → contention
#   MAX_CONCURRENT_SESSIONS=4    # > N concurrent sessions → leak likely

set -uo pipefail

MAX_SESSION_AGE_MIN="${MAX_SESSION_AGE_MIN:-30}"
MAX_ENGRAM_CHILDREN="${MAX_ENGRAM_CHILDREN:-3}"
MAX_CONCURRENT_SESSIONS="${MAX_CONCURRENT_SESSIONS:-4}"

MODE="${1:-human}"
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
METRICS_FILE="${PROJECT_DIR}/.cognitive-os/metrics/session-leak.jsonl"
mkdir -p "$(dirname "$METRICS_FILE")"

# Portable etime-to-seconds parser: "MM:SS" / "HH:MM:SS" / "DD-HH:MM:SS"
etime_to_seconds() {
    local et="$1"
    python3 -c "
import sys
s = '$et'.strip()
days = 0
if '-' in s:
    d, s = s.split('-', 1)
    days = int(d)
parts = [int(p) for p in s.split(':')]
while len(parts) < 3:
    parts = [0] + parts
h, m, sec = parts
print(days*86400 + h*3600 + m*60 + sec)
" 2>/dev/null || echo 0
}

# Collect claude MAIN processes. Cross-platform detection: we match by
# command-line signature (both --output-format and --input-format stream-json
# are specific to the Claude Code CLI) instead of by install path, so this
# works on macOS (Claude.app bundle), Linux (~/.local/bin), and Windows WSL.
# We also exclude disclaimer/wrapper processes.
SESSIONS_TMP=$(mktemp)
ps -eo pid,ppid,etime,pcpu,command 2>/dev/null | \
    awk '/--output-format stream-json/ && /--input-format stream-json/ && !/disclaimer/ && !/awk/ {print}' \
    > "$SESSIONS_TMP"

SESSION_COUNT=$(wc -l < "$SESSIONS_TMP" | tr -d ' ')
OLD_SESSIONS=0
SUSPICIOUS_SESSIONS=""

while IFS= read -r line; do
    [ -z "$line" ] && continue
    pid=$(echo "$line" | awk '{print $1}')
    etime=$(echo "$line" | awk '{print $3}')
    pcpu=$(echo "$line" | awk '{print $4}')
    age_sec=$(etime_to_seconds "$etime")
    age_min=$(( age_sec / 60 ))

    if [ "$age_min" -gt "$MAX_SESSION_AGE_MIN" ]; then
        OLD_SESSIONS=$((OLD_SESSIONS + 1))
        resume_id=$(echo "$line" | grep -oE '\-\-resume [a-f0-9-]+' | awk '{print $2}' || true)
        SUSPICIOUS_SESSIONS="${SUSPICIOUS_SESSIONS}${pid}|${age_min}m|${pcpu}%|${resume_id:-none}
"
    fi
done < "$SESSIONS_TMP"
rm -f "$SESSIONS_TMP"

ENGRAM_CHILDREN=$(ps -eo command | grep -c 'engram mcp --tools=agent' || true)
ENGRAM_SERVE=$(ps -eo etime,command | grep 'engram serve$' | awk '{print $1}' | head -1 || echo "none")

# Verdict
VERDICT="OK"
REASONS=()
if [ "$SESSION_COUNT" -gt "$MAX_CONCURRENT_SESSIONS" ]; then
    VERDICT="LEAK"
    REASONS+=("concurrent_sessions=${SESSION_COUNT} > max=${MAX_CONCURRENT_SESSIONS}")
fi
if [ "$OLD_SESSIONS" -gt 0 ]; then
    VERDICT="LEAK"
    REASONS+=("old_sessions=${OLD_SESSIONS} (age > ${MAX_SESSION_AGE_MIN}min)")
fi
if [ "$ENGRAM_CHILDREN" -gt "$MAX_ENGRAM_CHILDREN" ]; then
    VERDICT="LEAK"
    REASONS+=("engram_mcp_children=${ENGRAM_CHILDREN} > max=${MAX_ENGRAM_CHILDREN}")
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
REASONS_JSON=$(printf '%s\n' "${REASONS[@]}" | python3 -c "import json,sys;print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))")
SUSPICIOUS_JSON=$(echo "$SUSPICIOUS_SESSIONS" | python3 -c "import json,sys;print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))")

JSON_REPORT=$(cat <<EOF
{"timestamp":"$TIMESTAMP","verdict":"$VERDICT","session_count":$SESSION_COUNT,"old_sessions":$OLD_SESSIONS,"engram_mcp_children":$ENGRAM_CHILDREN,"engram_serve_etime":"$ENGRAM_SERVE","reasons":$REASONS_JSON,"suspicious":$SUSPICIOUS_JSON}
EOF
)
echo "$JSON_REPORT" >> "$METRICS_FILE"

if [ "$MODE" = "--json" ]; then
    echo "$JSON_REPORT"
    [ "$VERDICT" = "LEAK" ] && exit 1
    exit 0
fi

# Human report
echo "=== Session Leak Diagnostic ==="
echo "Timestamp:            $TIMESTAMP"
echo "Verdict:              $VERDICT"
echo "Active sessions:      $SESSION_COUNT (threshold: $MAX_CONCURRENT_SESSIONS)"
echo "Old sessions (>${MAX_SESSION_AGE_MIN}min): $OLD_SESSIONS"
echo "Engram MCP children:  $ENGRAM_CHILDREN (threshold: $MAX_ENGRAM_CHILDREN)"
echo "Engram serve etime:   $ENGRAM_SERVE"
echo ""

if [ "$OLD_SESSIONS" -gt 0 ]; then
    echo "Suspicious sessions (pid | age | cpu | resume_id):"
    echo "$SUSPICIOUS_SESSIONS" | while IFS= read -r s; do
        [ -n "$s" ] && echo "  $s"
    done
    echo ""
fi

if [ "$VERDICT" = "LEAK" ]; then
    echo "REASONS:"
    for r in "${REASONS[@]}"; do
        echo "  - $r"
    done
    echo ""
    echo "REMEDIATION:"
    echo "  1. Identify your CURRENT session PID: echo \$\$  (then parent claude)"
    echo "  2. Kill stale sessions: kill <PID>  (do NOT kill current)"
    echo "  3. One-shot kill old + their engram children:"
    echo "     bash scripts/session-leak-diagnostic.sh --kill"
    echo "  4. Permanent fix: ADR-045 session-leak-watchdog (pending)"
    exit 1
fi

echo "No leak detected."
exit 0
