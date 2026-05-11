#!/usr/bin/env bash
# SCOPE: os-only
# external-cache-content-leak.sh — ADR-267 Hook #2.
#
# Pre-commit gate. Uses rolling SHA-256 fingerprinting (8-line windows) to
# detect verbatim code-block matches between staged files and files in
# .cognitive-os/external-source-cache/.  Delegates to the Python companion:
#   scripts/cos_verbatim_copy_detector.py --quick
#
# More precise than token-scanning: fingerprints catch multi-line verbatim
# blocks rather than individual tokens, dramatically reducing false positives
# on common identifiers.
#
# Event:    PreToolUse
# Matcher:  Bash
# Trigger:  command contains `git commit`
# Exit:     0 = allow / 1 = block
# Bypass:   COS_ALLOW_VERBATIM_LEAK=1  (also accepts legacy COS_ALLOW_EXTERNAL_CACHE_LEAK=1)
# Log:      .cognitive-os/logs/external-cache-content-leak.jsonl
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$ROOT_DIR/.cognitive-os/logs"
LOG_FILE="$LOG_DIR/external-cache-content-leak.jsonl"
DETECTOR="$ROOT_DIR/scripts/cos_verbatim_copy_detector.py"
CACHE_DIR="$ROOT_DIR/.cognitive-os/external-source-cache"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

_log() { mkdir -p "$LOG_DIR"; printf '%s\n' "$1" >> "$LOG_FILE"; }

# ── Read hook payload ──────────────────────────────────────────────────────────
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

# ── Bypass ─────────────────────────────────────────────────────────────────────
# Accept both the new canonical env-var and the legacy one for backward compat.
if [ "${COS_ALLOW_VERBATIM_LEAK:-0}" = "1" ] || [ "${COS_ALLOW_EXTERNAL_CACHE_LEAK:-0}" = "1" ]; then
  _log "{\"timestamp\":\"$TS\",\"action\":\"bypass\",\"reason\":\"bypass env-var set\"}"
  exit 0
fi

# ── Prerequisite checks ────────────────────────────────────────────────────────
if [ ! -f "$DETECTOR" ]; then
  _log "{\"timestamp\":\"$TS\",\"action\":\"skip\",\"reason\":\"detector not found\"}"
  exit 0
fi

if [ ! -d "$CACHE_DIR" ] || [ -z "$(ls -A "$CACHE_DIR" 2>/dev/null)" ]; then
  _log "{\"timestamp\":\"$TS\",\"action\":\"skip\",\"reason\":\"cache dir absent or empty\"}"
  exit 0
fi

# ── Run fingerprint detector (quick / staged-only mode) ───────────────────────
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
  _log "{\"timestamp\":\"$TS\",\"action\":\"pass\",\"new_hits\":0}"
  exit 0
fi

# ── Block ──────────────────────────────────────────────────────────────────────
HITS_JSON="$(printf '%s' "$DETECTOR_OUTPUT" | python3 -c '
import json, sys
try:
    hits = json.load(sys.stdin).get("hits", [])
    print(json.dumps(hits[:5]))
except Exception:
    print("[]")
' 2>/dev/null || echo "[]")"

_log "{\"timestamp\":\"$TS\",\"action\":\"block\",\"new_hits\":${NEW_HITS:-?},\"sample\":$HITS_JSON}"

echo "=== EXTERNAL-CACHE-CONTENT-LEAK: BLOCKED ===" >&2
echo "" >&2
echo "Staged content contains verbatim code blocks (8-line fingerprint match)" >&2
echo "against files in:" >&2
echo "  .cognitive-os/external-source-cache/" >&2
echo "" >&2
echo "Research-only clones must NOT be copied verbatim into committed files." >&2
echo "Matched hits (${NEW_HITS} new, not in baseline):" >&2
printf '%s' "$DETECTOR_OUTPUT" | python3 -c '
import json, sys
try:
    for h in json.load(sys.stdin).get("hits", []):
        print(f"  [{h[\"risk\"]}] {h[\"cos_file\"]}:{h[\"cos_lines\"]} <- {h[\"cache_file\"]}:{h[\"cache_lines\"]}")
except Exception:
    pass
' >&2
echo "" >&2
echo "Options:" >&2
echo "  1. Remove / rewrite the verbatim block (derive behaviour, not code)." >&2
echo "  2. Legitimate snippet (MIT-attributed, proper header)?" >&2
echo "       python3 scripts/cos_verbatim_copy_detector.py --baseline" >&2
echo "     Review manifests/verbatim-detection-baseline.yaml, then commit both." >&2
echo "  3. Emergency bypass (audit-logged):" >&2
echo "       COS_ALLOW_VERBATIM_LEAK=1 git commit ..." >&2
echo "" >&2
echo "Reference: docs/adrs/ADR-267-*.md §Layer 1 Hook #2" >&2
exit 1
