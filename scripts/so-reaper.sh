#!/usr/bin/env bash
# so-reaper.sh — ADR-028 D1.B reaper
#
# Runs cleanup_expired() + detect_orphans() via the Python process registry.
#
# Called by:
#   - hooks/session-end-reap.sh  (SessionEnd)
#   - User-level cron every 5 min (optional)
#
# Feature flag: runtime.reaper.enabled in cognitive-os.yaml (default: true)
# Safe-kill guarantee: only kills PIDs present in the registry.
# Phase A: orphans are logged only, never auto-killed.

set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
cd "$PROJECT_DIR" || exit 0

# ── Feature flag check ─────────────────────────────────────────────────────
ENABLED=$(python3 - <<'PYEOF' 2>/dev/null
import yaml, sys
try:
    with open("cognitive-os.yaml") as f:
        cfg = yaml.safe_load(f) or {}
    val = cfg.get("runtime", {}).get("reaper", {}).get("enabled", True)
    print("true" if val else "false")
except Exception:
    print("true")
PYEOF
)

if [ "${ENABLED:-true}" = "false" ]; then
    echo "[so-reaper] disabled via runtime.reaper.enabled=false" >&2
    exit 0
fi

# ── Collect hook basenames for orphan detection ────────────────────────────
HOOK_BASENAMES=""
if [ -d "$PROJECT_DIR/hooks" ]; then
    # shellcheck disable=SC2012
    HOOK_BASENAMES=$(ls "$PROJECT_DIR/hooks/"*.sh 2>/dev/null \
        | xargs -n1 basename 2>/dev/null \
        | tr '\n' ',' \
        | sed 's/,$//' || true)
fi

# ── Run registry cleanup + orphan detection ────────────────────────────────
python3 - <<PYEOF 2>&1 | head -40
import sys
sys.path.insert(0, "$PROJECT_DIR")
from lib.process_registry import cleanup_expired, detect_orphans

expired = cleanup_expired(dry_run=False)

hooks_raw = "$HOOK_BASENAMES"
hooks = [h.strip() for h in hooks_raw.split(",") if h.strip()]
orphans = detect_orphans(hooks)

print(f"[so-reaper] expired={len(expired)} orphans_logged={len(orphans)}")
if expired:
    for r in expired:
        print(f"  reaped pid={r.pid} owner={r.owner} kind={r.kind}")
if orphans:
    for o in orphans:
        print(f"  orphan pid={o['pid']} ppid={o['ppid']} cmd={o['command'][:80]}")
PYEOF
