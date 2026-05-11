#!/usr/bin/env bash
# SCOPE: os-only
# clean-room-ast-similarity-gate.sh — ADR-271 Hook #8.
#
# Pre-commit gate. Uses AST-normalized similarity (Tier 2) to detect
# symbol-renamed clones of external-source-cache Python content in staged files.
# Delegates to the Python companion:
#   scripts/cos_clean_room_ast_similarity.py --quick
#
# Complements external-cache-content-leak.sh (T1 verbatim hash). This hook
# catches the "s/foo/bar/g" rename attack that T1 misses.
#
# Event:    PreToolUse
# Matcher:  Bash
# Trigger:  command contains `git commit`
# Exit:     0 = allow / 1 = block
# Bypass:   COS_ALLOW_AST_SIMILARITY=1   (specific bypass, logged)
#           COS_ALLOW_CLEAN_ROOM_BYPASS=1 (shared bypass with T1 hook, logged)
# Log:      .cognitive-os/logs/clean-room-ast-similarity-gate.jsonl
#
# NOTE: This hook is manual_trigger pending ADR-271 acceptance + soak per
# ADR-271 §Phase 3. It is listed in hooks/_lib/registration-allowlist.txt
# until promoted to an active efficiency/security profile.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$ROOT_DIR/.cognitive-os/logs"
LOG_FILE="$LOG_DIR/clean-room-ast-similarity-gate.jsonl"
DETECTOR="$ROOT_DIR/scripts/cos_clean_room_ast_similarity.py"
CACHE_DIR="$ROOT_DIR/.cognitive-os/external-source-cache"
BASELINE="$ROOT_DIR/manifests/ast-similarity-baseline.yaml"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

_log() { mkdir -p "$LOG_DIR"; printf '%s\n' "$1" >> "$LOG_FILE"; }

# -- Read hook payload ----------------------------------------------------------
INPUT="$(cat 2>/dev/null || true)"
CMD="$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    print(json.load(sys.stdin).get("tool_input", {}).get("command", ""))
except Exception:
    pass
' 2>/dev/null || true)"

# Only act on git commit invocations
[[ "$CMD" != *"git commit"* ]] && exit 0

# -- Bypass --------------------------------------------------------------------
if [ "${COS_ALLOW_AST_SIMILARITY:-0}" = "1" ]; then
  _log "{\"timestamp\":\"$TS\",\"tier\":\"T2\",\"action\":\"bypass\",\"reason\":\"COS_ALLOW_AST_SIMILARITY=1\"}"
  exit 0
fi
if [ "${COS_ALLOW_CLEAN_ROOM_BYPASS:-0}" = "1" ]; then
  _log "{\"timestamp\":\"$TS\",\"tier\":\"T2\",\"action\":\"bypass\",\"reason\":\"COS_ALLOW_CLEAN_ROOM_BYPASS=1\"}"
  exit 0
fi

# -- Prerequisite checks -------------------------------------------------------
if [ ! -f "$DETECTOR" ]; then
  _log "{\"timestamp\":\"$TS\",\"tier\":\"T2\",\"action\":\"skip\",\"reason\":\"detector not found: $DETECTOR\"}"
  exit 0
fi

if [ ! -d "$CACHE_DIR" ] || [ -z "$(find "$CACHE_DIR" -name '*.py' -maxdepth 5 2>/dev/null | head -1)" ]; then
  _log "{\"timestamp\":\"$TS\",\"tier\":\"T2\",\"action\":\"skip\",\"reason\":\"cache dir absent or has no .py files\"}"
  exit 0
fi

# -- Run AST similarity detector (staged-only / quick mode) --------------------
DETECTOR_OUTPUT="$(
  cd "$ROOT_DIR"
  python3 "$DETECTOR" --quick --format json 2>/dev/null || true
)"
DETECTOR_EXIT=$?

NEW_HITS="$(printf '%s' "$DETECTOR_OUTPUT" | python3 -c '
import json, sys
try:
    print(json.load(sys.stdin).get("new_hits", 0))
except Exception:
    print(0)
' 2>/dev/null || echo 0)"

if [ "${NEW_HITS:-0}" -eq 0 ] && [ "$DETECTOR_EXIT" -eq 0 ]; then
  _log "{\"timestamp\":\"$TS\",\"tier\":\"T2\",\"action\":\"pass\",\"new_hits\":0}"
  exit 0
fi

# -- Extract match details for error message -----------------------------------
MATCH_SUMMARY="$(printf '%s' "$DETECTOR_OUTPUT" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    new = [m for m in data.get("matches", []) if "baselined" not in m.get("classification", "")]
    for m in new[:5]:
        print(f"  {m[\"cos_file\"]}:{m.get(\"cos_lineno\",\"?\")} {m[\"cos_unit\"]} <- {m[\"cache_file\"]} {m[\"cache_unit\"]} [{m[\"classification\"]}]")
    if len(new) > 5:
        print(f"  ... and {len(new)-5} more")
except Exception as e:
    print(f"  (could not parse detector output: {e})")
' 2>/dev/null || echo "  (could not parse detector output)")"

_log "{\"timestamp\":\"$TS\",\"tier\":\"T2\",\"action\":\"block\",\"new_hits\":${NEW_HITS:-0}}"

cat >&2 <<EOF

=============================================================================
  CLEAN-ROOM GATE -- Tier 2: AST Similarity  (ADR-271)
=============================================================================

  Symbol-renamed clone(s) of external-source-cache content detected in staged
  Python files. These AST-normalized hashes match upstream functions/classes
  even though identifiers were renamed.

  Matches:
$MATCH_SUMMARY

  Resolution options:
  1. If this is expected (boilerplate, common idiom, reviewed reuse):
       python3 scripts/cos_clean_room_ast_similarity.py --baseline
       git add manifests/ast-similarity-baseline.yaml && git commit ...
  2. If this is a derivative work requiring documentation:
       Create/update the per-tool Annex F at docs/research/<tool>-annex-f-*.md
  3. Emergency bypass (creates audit trail):
       COS_ALLOW_AST_SIMILARITY=1 git commit ...        (T2-specific bypass)
       COS_ALLOW_CLEAN_ROOM_BYPASS=1 git commit ...     (shared T1+T2 bypass)

  Baseline: $BASELINE
  Audit log: $LOG_FILE

  Tiers T3-T5 are not enforced by this hook. If your change involves
  paraphrased adaptation or design-level reuse from an upstream tool, file
  or update the per-tool Annex F (docs/research/<tool>-annex-f-*.md) before
  commit. See rules/clean-room-detection-limits.md for the full matrix.

EOF

exit 1
