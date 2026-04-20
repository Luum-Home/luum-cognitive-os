#!/usr/bin/env bash
# so-emergency-stop.sh — ADR-028 D5 kill-switch
#
# Disables all non-critical hooks, kills registry-tracked expired processes,
# and switches to the minimal security profile.
#
# Usage:
#   bash scripts/so-emergency-stop.sh [reason]
#
# Idempotent — safe to run multiple times.
# Exits 0 always.
#
# To restore:
#   rm -f .cognitive-os/runtime/hook-killswitch.flag
#   cp .claude/settings.json.bak .claude/settings.json
#   bash scripts/apply-efficiency-profile.sh default   # optional: re-apply full profile

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Respect PROJECT_DIR override for tests; otherwise derive from script location.
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"

RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
FLAG_FILE="$RUNTIME_DIR/hook-killswitch.flag"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"
SETTINGS_BAK="$PROJECT_DIR/.claude/settings.json.bak"

REASON="${1:-manual invocation}"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── 1. Ensure runtime dir exists ─────────────────────────────────────
mkdir -p "$RUNTIME_DIR"

# ── 2. Write (or update) killswitch flag — idempotent ────────────────
printf '{"timestamp":"%s","reason":"%s","activated_by":"so-emergency-stop.sh"}\n' \
  "$TIMESTAMP" "$REASON" > "$FLAG_FILE"
echo "[so-emergency-stop] Kill-switch flag written: $FLAG_FILE"

# ── 3. Kill registry-tracked expired processes via reaper ────────────
# Prefer PROJECT_DIR/scripts so tests can stub the call with local scripts.
_scripts_dir="$PROJECT_DIR/scripts"
REAPER="$_scripts_dir/so-reaper.sh"
if [ ! -f "$REAPER" ]; then REAPER="$SCRIPT_DIR/so-reaper.sh"; fi
if [ -f "$REAPER" ]; then
  echo "[so-emergency-stop] Invoking reaper (registry-tracked orphans only)..."
  bash "$REAPER" || true   # reaper exits non-zero when nothing to kill — ignore
  echo "[so-emergency-stop] Reaper done."
else
  echo "[so-emergency-stop] WARNING: so-reaper.sh not found at $REAPER — skipping reaper step."
fi

# ── 4. Backup current settings and apply minimal profile ─────────────
SET_PROFILE="$_scripts_dir/set-security-profile.sh"
if [ ! -f "$SET_PROFILE" ]; then SET_PROFILE="$SCRIPT_DIR/set-security-profile.sh"; fi
if [ -f "$SET_PROFILE" ]; then
  if [ -f "$SETTINGS_FILE" ] && [ ! -f "$SETTINGS_BAK" ]; then
    cp "$SETTINGS_FILE" "$SETTINGS_BAK"
    echo "[so-emergency-stop] settings.json backed up to settings.json.bak"
  elif [ -f "$SETTINGS_FILE" ] && [ -f "$SETTINGS_BAK" ]; then
    echo "[so-emergency-stop] settings.json.bak already exists — skipping backup (idempotent)."
  fi
  echo "[so-emergency-stop] Applying minimal security profile..."
  bash "$SET_PROFILE" minimal || true
  echo "[so-emergency-stop] Minimal profile applied."
else
  echo "[so-emergency-stop] WARNING: set-security-profile.sh not found — settings not changed."
fi

# ── 5. Print restoration instructions ───────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════"
echo "  EMERGENCY STOP ACTIVE — $(date -u)"
echo "  Reason: $REASON"
echo ""
echo "  Critical hooks still firing:"
echo "    credential-guard.sh, license-guard.sh,"
echo "    pre-compaction-flush.sh, session-cleanup.sh,"
echo "    self-install.sh, session-init.sh"
echo ""
echo "  To restore normal operation:"
echo "    1. Resolve the underlying issue"
echo "    2. rm -f $FLAG_FILE"
echo "    3. cp $SETTINGS_BAK $SETTINGS_FILE"
echo "       OR: bash scripts/apply-efficiency-profile.sh default"
echo "    4. pytest tests/contracts/ -v --tb=short"
echo "════════════════════════════════════════════════════════"

exit 0

# ── manual-invoke only ───────────────────────────────────────────────
# so-emergency-stop.sh  (manual CLI — NOT wired into any hook matcher)
