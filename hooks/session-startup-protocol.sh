#!/usr/bin/env bash
# SCOPE: both
# SessionStart hook: Startup Protocol Reminder
#
# Formalizes the 5-step session-startup protocol documented in
# rules/startup-protocol.md:
#   1. Engram memory context
#   2. Plans <-> ADRs cross-reference
#   3. Work queue state
#   4. Runtime validator (cos-config-audit.sh)
#   5. Only then execute
#
# This hook runs a *fast* version of those checks (filesystem-only, no heavy
# commands) and emits a compact summary to stdout so the orchestrator sees it
# as SessionStart additionalContext.
#
# Budget: < 500ms total. Advisory only — always exits 0 even on failures.
# p95 latency target: <300ms (pure filesystem scans, no subprocess fan-out).

set -uo pipefail

# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
KILLSWITCH_LIB="$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
if [ -f "$KILLSWITCH_LIB" ]; then
  # shellcheck disable=SC1090
  source "$KILLSWITCH_LIB" 2>/dev/null || true
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# ── Helper: count .md files in a directory (0 if missing) ───────────────────
_count_md() {
  local dir="$1"
  if [ -d "$dir" ]; then
    # shellcheck disable=SC2012
    ls -1 "$dir" 2>/dev/null | grep -c '\.md$' || echo 0
  else
    echo 0
  fi
}

# ── Helper: count .md files in a directory, excluding README/templates/archive
# Scans top-level only (no recursion into subdirs) to stay within budget.
_count_md_plans() {
  local dir="$1"
  if [ ! -d "$dir" ]; then
    echo 0
    return
  fi
  local count=0
  local f
  while IFS= read -r f; do
    # Skip README.md, *.template.md, and any archive-named file
    case "$f" in
      README.md|*.template.md|*archive*|*ARCHIVE*) continue ;;
      *.md) count=$((count + 1)) ;;
    esac
  done < <(ls -1 "$dir" 2>/dev/null)
  echo "$count"
}

# ── 1. Engram memory (filesystem heuristic only — no live query) ───────────
# We don't call mem_search from a hook (too slow, would need MCP). Instead we
# report whether the Engram DB file appears to exist under the usual paths.
ENGRAM_STATUS="unknown"
ENGRAM_HINT=""
for candidate in \
  "$HOME/.engram/engram.db" \
  "$HOME/.local/share/engram/engram.db" \
  "$PROJECT_DIR/.engram/engram.db"; do
  if [ -f "$candidate" ]; then
    local_size=$(wc -c < "$candidate" 2>/dev/null || echo 0)
    ENGRAM_STATUS="present (${local_size}B)"
    ENGRAM_HINT="run mem_search for project context"
    break
  fi
done
if [ "$ENGRAM_STATUS" = "unknown" ]; then
  ENGRAM_HINT="mem_search anyway — DB path heuristic may be wrong"
fi

# ── 2. Plans <-> ADRs cross-reference ───────────────────────────────────────
PLANS_DIR="$PROJECT_DIR/.cognitive-os/plans/features"
RESEARCH_PLANS_DIR="$PROJECT_DIR/.cognitive-os/plans/research"
ARCH_PLANS_DIR="$PROJECT_DIR/.cognitive-os/plans/architecture"
ROADMAPS_DIR="$PROJECT_DIR/.cognitive-os/plans/roadmaps"
ADRS_DIR="$PROJECT_DIR/docs/adrs"
PLAN_COUNT=$(_count_md "$PLANS_DIR")
RESEARCH_PLAN_COUNT=$(_count_md_plans "$RESEARCH_PLANS_DIR")
ARCH_PLAN_COUNT=$(_count_md_plans "$ARCH_PLANS_DIR")
ROADMAP_COUNT=$(_count_md_plans "$ROADMAPS_DIR")
ADR_COUNT=$(_count_md "$ADRS_DIR")

# ── 3. Work queue state ────────────────────────────────────────────────────
WQ_FILE="$PROJECT_DIR/.cognitive-os/work-queue.json"
LIVE_COUNT="n/a"
PARKED_COUNT="n/a"
if [ -f "$WQ_FILE" ] && command -v python3 >/dev/null 2>&1; then
  read -r LIVE_COUNT PARKED_COUNT < <(python3 -c '
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    live = d.get("live") or d.get("active") or d.get("in_progress") or []
    parked = d.get("parked") or d.get("paused") or d.get("blocked") or []
    print(len(live) if isinstance(live, list) else 0,
          len(parked) if isinstance(parked, list) else 0)
except Exception:
    print("?", "?")
' "$WQ_FILE" 2>/dev/null || echo "? ?")
elif [ ! -f "$WQ_FILE" ]; then
  LIVE_COUNT="no-queue"
  PARKED_COUNT="no-queue"
fi

# ── 4. Runtime validator (lightweight probe — don't run full audit) ────────
AUDIT_SCRIPT="$PROJECT_DIR/scripts/cos-config-audit.sh"
VALIDATOR_LINE="validator not available"
VALIDATOR_CACHE="$PROJECT_DIR/.cognitive-os/metrics/cos-config-audit-latest.json"
if [ -f "$VALIDATOR_CACHE" ] && command -v python3 >/dev/null 2>&1; then
  VALIDATOR_LINE=$(python3 -c '
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    s = d.get("summary") or {}
    impl = s.get("implemented", "?")
    partial = s.get("partial", "?")
    aspir = s.get("aspirational", "?")
    print(f"{impl} IMPL / {partial} PARTIAL / {aspir} ASPIR (from cache)")
except Exception:
    print("validator cache unparseable")
' "$VALIDATOR_CACHE" 2>/dev/null || echo "validator cache unparseable")
elif [ -f "$AUDIT_SCRIPT" ]; then
  VALIDATOR_LINE="run: python3 scripts/cos-config-audit.sh (no cached result)"
fi

# ── 5. Suggested first action ──────────────────────────────────────────────
SUGGESTION="consult Engram + plans before drafting new ADRs/plans"
if [ "$PLAN_COUNT" != "0" ] && [ "$LIVE_COUNT" != "0" ] && [ "$LIVE_COUNT" != "?" ] && [ "$LIVE_COUNT" != "n/a" ] && [ "$LIVE_COUNT" != "no-queue" ]; then
  SUGGESTION="live work items present — reconcile before starting new work"
fi

# ── Emit compact summary (stdout = SessionStart additionalContext) ─────────
cat <<SUMMARY
[startup-protocol] Context check (rules/startup-protocol.md):
  - Engram: ${ENGRAM_STATUS} — ${ENGRAM_HINT}
  - Plans: ${PLAN_COUNT} features + ${RESEARCH_PLAN_COUNT} research + ${ARCH_PLAN_COUNT} arch + ${ROADMAP_COUNT} roadmaps (cross-ref ${ADR_COUNT} ADRs)
  - Work queue: ${LIVE_COUNT} live, ${PARKED_COUNT} parked
  - Validator: ${VALIDATOR_LINE}
  - Suggested first action: ${SUGGESTION}
SUMMARY

exit 0
