#!/usr/bin/env bash
# SCOPE: os-only
# cos-weekly-config-audit.sh — local replacement for cos-config-audit.yml.
#
# Per ADR-131. Run by launchd weekly. Produces audit.json + audit.txt under
# .cognitive-os/reports/weekly/<date>/ for review. Never modifies git state.

set -uo pipefail

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "$HOME/Projects/luum/luum-agent-os")"
cd "$REPO_ROOT"

DATE_STAMP="$(date -u +%Y-%m-%d)"
OUT_DIR="$REPO_ROOT/.cognitive-os/reports/weekly/$DATE_STAMP"
mkdir -p "$OUT_DIR"

JSON_OUT="$OUT_DIR/cos-config-audit.json"
TEXT_OUT="$OUT_DIR/cos-config-audit.txt"

echo "[cos-weekly-config-audit] $(date -u +%Y-%m-%dT%H:%M:%SZ) — start"

if [ ! -x "$REPO_ROOT/scripts/cos-config-audit.sh" ]; then
  echo "  ERROR: scripts/cos-config-audit.sh not executable" >&2
  exit 1
fi

python3 "$REPO_ROOT/scripts/cos-config-audit.sh" --json > "$JSON_OUT" 2>&1
json_rc=$?

python3 "$REPO_ROOT/scripts/cos-config-audit.sh" > "$TEXT_OUT" 2>&1
text_rc=$?

# Count [DRIFT] markers; non-zero is the historical PR-fail signal.
drift=$(grep -c '\[DRIFT\]' "$TEXT_OUT" 2>/dev/null || echo 0)

cat > "$OUT_DIR/cos-config-audit-summary.json" <<EOF
{
  "ts": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "json_rc": $json_rc,
  "text_rc": $text_rc,
  "drift_count": $drift,
  "json_path": "$JSON_OUT",
  "text_path": "$TEXT_OUT"
}
EOF

echo "[cos-weekly-config-audit] drift=$drift json_rc=$json_rc text_rc=$text_rc"
echo "[cos-weekly-config-audit] outputs at $OUT_DIR"

# Exit 1 if drift detected so launchd logs reflect failure.
[ "$drift" -eq 0 ] || exit 1
[ "$json_rc" -eq 0 ] && [ "$text_rc" -eq 0 ] || exit 1
exit 0
