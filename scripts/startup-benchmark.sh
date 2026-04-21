#!/usr/bin/env bash
# SCOPE: both
# startup-benchmark.sh — ADR-028 D-stream: session startup latency + payload benchmark
#
# Measures:
#   1. Each SessionStart hook in isolation (wall-clock timing)
#   2. Total serial SessionStart time (sum of all hooks)
#   3. Payload sizes: global CLAUDE.md, project CLAUDE.md, rules always-active,
#      skills catalog, hooks that emit text
#   4. Estimated initial prompt tokens (bytes / 4, rough approximation)
#
# Output:
#   - JSON line appended to .cognitive-os/metrics/startup-benchmark.jsonl
#   - Human-readable markdown summary on stdout
#
# Usage:
#   bash scripts/startup-benchmark.sh [--project-dir <dir>]
#
# Exit codes:
#   0 = benchmark complete (always)
#   The script is idempotent — safe to run repeatedly.

set -uo pipefail

# ── Configuration ──────────────────────────────────────────────────────────────
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}}"
source "$(cd "$(dirname "$0")/.." && pwd)/hooks/_lib/portable.sh"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    *) echo "Usage: $0 [--project-dir <dir>]" >&2; exit 0 ;;
  esac
done

METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
OUTPUT_JSONL="$METRICS_DIR/startup-benchmark.jsonl"
SETTINGS="$PROJECT_DIR/.claude/settings.json"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_DATE="$(date -u +%Y-%m-%d)"

mkdir -p "$METRICS_DIR"

# ── Helpers ─────────────────────────────────────────────────────────────────────
epoch_ms() {
  # Returns milliseconds since epoch. Falls back to seconds*1000 on macOS < 10.14
  python3 -c "import time; print(int(time.time()*1000))" 2>/dev/null || \
    echo $(( $(date +%s) * 1000 ))
}

file_bytes() {
  local f="$1"
  if [[ -f "$f" ]]; then
    portable_stat_size "$f" 2>/dev/null || echo 0
  else
    echo 0
  fi
}

dir_bytes() {
  local d="$1"
  if [[ -d "$d" ]]; then
    python3 -c "
import os
total = 0
for root, dirs, files in os.walk('$d'):
    for f in files:
        try: total += os.path.getsize(os.path.join(root, f))
        except OSError: pass
print(total)
" 2>/dev/null || echo 0
  else
    echo 0
  fi
}

bytes_to_tokens() {
  # Rough approximation: 1 token ≈ 4 bytes
  echo $(( ($1 + 2) / 4 ))
}

# ── Emit header ─────────────────────────────────────────────────────────────────
echo ""
echo "# Session Startup Benchmark — $RUN_DATE"
echo ""
echo "Project: $PROJECT_DIR"
echo "Run at:  $TIMESTAMP"
echo ""

# ── Section 1: Hook timing ───────────────────────────────────────────────────────
echo "## 1. SessionStart Hook Timing"
echo ""
echo "| # | Hook | Duration (ms) | Exit |"
echo "|---|------|---------------|------|"

# Set up environment that hooks expect
export CLAUDE_PROJECT_DIR="$PROJECT_DIR"
export COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR"
export TOOL_NAME="Bash"
export TOOL_INPUT='{"command":"echo benchmark-probe"}'
export SESSION_ID="benchmark-$$"
export RESULT_TEXT="benchmark output"
export EXIT_CODE="0"

# Extract SessionStart hooks from settings.json into a temp file
HOOKS_TMP="$(mktemp /tmp/startup-bench-hooks.XXXXXX)"
if [[ -f "$SETTINGS" ]] && command -v python3 >/dev/null 2>&1; then
  python3 - "$SETTINGS" >"$HOOKS_TMP" 2>/dev/null <<'PYEOF'
import json, sys
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    for grp in data.get("hooks", {}).get("SessionStart", []):
        for h in grp.get("hooks", []):
            cmd = h.get("command", "")
            if cmd:
                print(cmd)
except Exception:
    pass
PYEOF
fi

TOTAL_HOOK_MS=0
HOOK_RESULTS_JSON="["
HOOK_NUM=0

while IFS= read -r cmd; do
  [[ -z "$cmd" ]] && continue
  HOOK_NUM=$(( HOOK_NUM + 1 ))

  # Extract hook name
  hook_name=$(echo "$cmd" | sed 's|.*hooks/||' | sed 's|"||g' | sed 's|[[:space:]].*||')

  # Time the hook (5s timeout, silent)
  t_start=$(epoch_ms)
  timeout 8 bash -c "cd '$PROJECT_DIR' && $cmd" </dev/null >/dev/null 2>/dev/null
  exit_code=$?
  t_end=$(epoch_ms)
  duration_ms=$(( t_end - t_start ))

  # Handle timeout (exit 124)
  [[ $exit_code -eq 124 ]] && duration_ms=8000

  TOTAL_HOOK_MS=$(( TOTAL_HOOK_MS + duration_ms ))

  printf "| %d | %-40s | %6d | %d |\n" "$HOOK_NUM" "$hook_name" "$duration_ms" "$exit_code"

  # Accumulate JSON
  [[ "$HOOK_RESULTS_JSON" != "[" ]] && HOOK_RESULTS_JSON="${HOOK_RESULTS_JSON},"
  HOOK_RESULTS_JSON="${HOOK_RESULTS_JSON}{\"hook\":\"${hook_name}\",\"duration_ms\":${duration_ms},\"exit_code\":${exit_code}}"
done < "$HOOKS_TMP"
rm -f "$HOOKS_TMP"

HOOK_RESULTS_JSON="${HOOK_RESULTS_JSON}]"

echo ""
echo "**Total serial SessionStart time: ${TOTAL_HOOK_MS} ms**"
echo ""

# ── Section 2: Payload sizes ─────────────────────────────────────────────────────
echo "## 2. Initial Context Payload Sizes"
echo ""
echo "| Component | Path | Bytes | Est. Tokens |"
echo "|-----------|------|-------|-------------|"

PAYLOAD_JSON="{"
TOTAL_PAYLOAD_BYTES=0

# Helper: print table row and set LAST_MEASURED_BYTES
print_file_row() {
  local label="$1"
  local path="$2"
  local bytes
  bytes=$(file_bytes "$path")
  local tokens
  tokens=$(bytes_to_tokens "$bytes")
  printf "| %-40s | %-50s | %8d | %8d |\n" "$label" "${path#$PROJECT_DIR/}" "$bytes" "$tokens"
  LAST_MEASURED_BYTES="$bytes"
}

# Global CLAUDE.md
GLOBAL_CLAUDE="${HOME}/.claude/CLAUDE.md"
print_file_row "Global CLAUDE.md" "$GLOBAL_CLAUDE"
GLOBAL_CLAUDE_BYTES="$LAST_MEASURED_BYTES"
TOTAL_PAYLOAD_BYTES=$(( TOTAL_PAYLOAD_BYTES + GLOBAL_CLAUDE_BYTES ))
PAYLOAD_JSON="${PAYLOAD_JSON}\"global_claude_md_bytes\":${GLOBAL_CLAUDE_BYTES},"

# Project CLAUDE.md (may not exist)
PROJECT_CLAUDE="$PROJECT_DIR/CLAUDE.md"
print_file_row "Project CLAUDE.md" "$PROJECT_CLAUDE"
PROJECT_CLAUDE_BYTES="$LAST_MEASURED_BYTES"
TOTAL_PAYLOAD_BYTES=$(( TOTAL_PAYLOAD_BYTES + PROJECT_CLAUDE_BYTES ))
PAYLOAD_JSON="${PAYLOAD_JSON}\"project_claude_md_bytes\":${PROJECT_CLAUDE_BYTES},"

# Rules always-active (RULES-COMPACT.md is the loaded index)
RULES_COMPACT="$PROJECT_DIR/rules/RULES-COMPACT.md"
print_file_row "Rules RULES-COMPACT.md" "$RULES_COMPACT"
RULES_COMPACT_BYTES="$LAST_MEASURED_BYTES"
TOTAL_PAYLOAD_BYTES=$(( TOTAL_PAYLOAD_BYTES + RULES_COMPACT_BYTES ))
PAYLOAD_JSON="${PAYLOAD_JSON}\"rules_compact_bytes\":${RULES_COMPACT_BYTES},"

# Total rules directory (all .md files — upper bound if all loaded)
RULES_DIR="$PROJECT_DIR/rules"
ALL_RULES_BYTES=$(dir_bytes "$RULES_DIR")
ALL_RULES_COUNT=$(find "$RULES_DIR" -maxdepth 1 -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
ALL_RULES_TOKENS=$(bytes_to_tokens "$ALL_RULES_BYTES")
printf "| %-40s | %-50s | %8d | %8d |\n" "Rules total (all ${ALL_RULES_COUNT} .md)" "rules/" "$ALL_RULES_BYTES" "$ALL_RULES_TOKENS"
PAYLOAD_JSON="${PAYLOAD_JSON}\"rules_all_bytes\":${ALL_RULES_BYTES},\"rules_count\":${ALL_RULES_COUNT},"

# Skills catalog (compact)
SKILLS_CATALOG="$PROJECT_DIR/skills/CATALOG-COMPACT.md"
print_file_row "Skills CATALOG-COMPACT.md" "$SKILLS_CATALOG"
SKILLS_CATALOG_BYTES="$LAST_MEASURED_BYTES"
TOTAL_PAYLOAD_BYTES=$(( TOTAL_PAYLOAD_BYTES + SKILLS_CATALOG_BYTES ))
PAYLOAD_JSON="${PAYLOAD_JSON}\"skills_catalog_bytes\":${SKILLS_CATALOG_BYTES},"

# session-init.sh output (hooks that emit text on SessionStart)
# Measure the hook file sizes as a proxy for stdout size
SESSION_HOOK_EMIT_BYTES=0
for hook in session-init.sh self-install.sh ecosystem-check.sh usage-health-check.sh; do
  hpath="$PROJECT_DIR/hooks/$hook"
  if [[ -f "$hpath" ]]; then
    h_bytes=$(file_bytes "$hpath")
    SESSION_HOOK_EMIT_BYTES=$(( SESSION_HOOK_EMIT_BYTES + h_bytes ))
    printf "| %-40s | %-50s | %8d | %8d |\n" "Hook (text-emitting): $hook" "hooks/$hook" "$h_bytes" "$(bytes_to_tokens $h_bytes)"
  fi
done
PAYLOAD_JSON="${PAYLOAD_JSON}\"hook_text_emitting_bytes\":${SESSION_HOOK_EMIT_BYTES},"

# cognitive-os.yaml
COS_YAML="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
if [[ ! -f "$COS_YAML" ]]; then
  COS_YAML="$PROJECT_DIR/cognitive-os.yaml"
fi
print_file_row "cognitive-os.yaml" "$COS_YAML"
COS_YAML_BYTES="$LAST_MEASURED_BYTES"
PAYLOAD_JSON="${PAYLOAD_JSON}\"cognitive_os_yaml_bytes\":${COS_YAML_BYTES},"

echo ""

# Total payload estimate (RULES-COMPACT + skills catalog + global CLAUDE.md + project CLAUDE.md)
CORE_PAYLOAD_BYTES=$(( GLOBAL_CLAUDE_BYTES + PROJECT_CLAUDE_BYTES + RULES_COMPACT_BYTES + SKILLS_CATALOG_BYTES ))
CORE_PAYLOAD_TOKENS=$(bytes_to_tokens "$CORE_PAYLOAD_BYTES")
ALL_RULES_PAYLOAD_BYTES=$(( GLOBAL_CLAUDE_BYTES + PROJECT_CLAUDE_BYTES + ALL_RULES_BYTES + SKILLS_CATALOG_BYTES ))
ALL_RULES_PAYLOAD_TOKENS=$(bytes_to_tokens "$ALL_RULES_PAYLOAD_BYTES")

echo "**Core payload** (CLAUDE.md + RULES-COMPACT + skills catalog): ${CORE_PAYLOAD_BYTES} bytes (~${CORE_PAYLOAD_TOKENS} tokens)"
echo ""
echo "**Full rules payload** (CLAUDE.md + all rules + skills catalog): ${ALL_RULES_PAYLOAD_BYTES} bytes (~${ALL_RULES_PAYLOAD_TOKENS} tokens)"
echo ""

PAYLOAD_JSON="${PAYLOAD_JSON}\"core_payload_bytes\":${CORE_PAYLOAD_BYTES},\"core_payload_tokens\":${CORE_PAYLOAD_TOKENS},\"full_payload_bytes\":${ALL_RULES_PAYLOAD_BYTES},\"full_payload_tokens\":${ALL_RULES_PAYLOAD_TOKENS}}"

# ── Section 3: SLO status ────────────────────────────────────────────────────────
echo "## 3. SLO Status"
echo ""
SLO_1_STATUS="PASS"
[[ $TOTAL_HOOK_MS -gt 2000 ]] && SLO_1_STATUS="BREACH"
SLO_10_STATUS="PASS"
[[ $CORE_PAYLOAD_TOKENS -gt 50000 ]] && SLO_10_STATUS="BREACH"

echo "| SLO | Description | Target | Measured | Status |"
echo "|-----|-------------|--------|----------|--------|"
printf "| 1   | SessionStart p95 duration          | < 2000 ms | %5d ms | %s |\n" "$TOTAL_HOOK_MS" "$SLO_1_STATUS"
printf "| 10  | Initial context payload tokens     | < 50000   | %5d   | %s |\n" "$CORE_PAYLOAD_TOKENS" "$SLO_10_STATUS"
echo ""

# ── Emit JSON record ─────────────────────────────────────────────────────────────
JSON_RECORD=$(python3 - <<PYEOF
import json, sys

record = {
    "timestamp": "$TIMESTAMP",
    "run_date": "$RUN_DATE",
    "project_dir": "$PROJECT_DIR",
    "session_start": {
        "hook_count": $HOOK_NUM,
        "total_duration_ms": $TOTAL_HOOK_MS,
        "hooks": $HOOK_RESULTS_JSON
    },
    "payload": $PAYLOAD_JSON,
    "slo": {
        "session_start_target_ms": 2000,
        "session_start_measured_ms": $TOTAL_HOOK_MS,
        "session_start_status": "$SLO_1_STATUS",
        "payload_token_target": 50000,
        "payload_token_measured": $CORE_PAYLOAD_TOKENS,
        "payload_token_status": "$SLO_10_STATUS"
    }
}

print(json.dumps(record, separators=(',', ':')))
PYEOF
)

echo "$JSON_RECORD" >> "$OUTPUT_JSONL"

echo "## 4. Output"
echo ""
echo "JSON record appended to: \`$OUTPUT_JSONL\`"
echo ""
echo "---"
echo "Benchmark complete. $(date -u +%H:%M:%SZ)"

exit 0
