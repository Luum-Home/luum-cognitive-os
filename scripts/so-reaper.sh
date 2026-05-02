#!/usr/bin/env bash
# SCOPE: both
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

# ── Fix 3 (ADR-097): Sweep active-tasks.json for zombie/stale records ─────
# - in_progress with dead PID → cancelled-zombie
# - in_progress with pid=null and age > 30 min → cancelled-stale
# - pending with pid=null, age > 30 min → cancelled-stale
# - pending with pid=null, age < 30 min → leave (might still be starting)
# NOTE: never kills processes; marks records only.
python3 - <<PYEOF 2>&1 | head -20
import fcntl, json, os, sys, tempfile
from datetime import datetime, timezone

sys.path.insert(0, "$PROJECT_DIR")

TASKS_PATH = os.path.join("$PROJECT_DIR", ".cognitive-os", "tasks", "active-tasks.json")
LOCK_PATH   = os.path.join("$PROJECT_DIR", ".cognitive-os", "tasks", ".active-tasks.lock")
STALE_SECS  = 30 * 60  # 30 minutes grace for pending with no PID

def _now_utc():
    return datetime.now(timezone.utc)

def _age_secs(ts_str):
    if not ts_str:
        return None
    try:
        s = ts_str.rstrip("Z")
        dt = datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
        return (_now_utc() - dt).total_seconds()
    except Exception:
        return None

def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False

if not os.path.isfile(TASKS_PATH):
    print("[so-reaper] active-tasks.json not found, skipping zombie sweep")
    sys.exit(0)

os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)

reaped = []
try:
    with open(LOCK_PATH, "w") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)
        try:
            data = json.loads(open(TASKS_PATH).read())
            tasks = data.get("tasks", [])
            now_iso = _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
            changed = False

            for t in tasks:
                status = t.get("status")
                if status not in ("in_progress", "pending"):
                    continue

                pid = t.get("pid")
                age = _age_secs(t.get("started_at") or t.get("launchedAt") or t.get("requested_at"))

                if status == "in_progress" and pid is not None:
                    # PID set — check liveness
                    if not _pid_alive(pid):
                        t["status"] = "cancelled-zombie"
                        t["completedAt"] = now_iso
                        t["outputSummary"] = f"reaped: pid {pid} not alive"
                        changed = True
                        reaped.append(("zombie", t["id"], pid))

                elif status == "in_progress" and pid is None:
                    if age is not None and age > STALE_SECS:
                        t["status"] = "cancelled-stale"
                        t["completedAt"] = now_iso
                        t["outputSummary"] = f"reaped: in_progress without pid for {int(age)}s"
                        changed = True
                        reaped.append(("stale-in-progress", t["id"], None))

                elif status == "pending" and pid is None:
                    if age is not None and age > STALE_SECS:
                        t["status"] = "cancelled-stale"
                        t["completedAt"] = now_iso
                        t["outputSummary"] = f"reaped: no pid captured within {int(age)}s"
                        changed = True
                        reaped.append(("stale", t["id"], None))
                    # else: too young — leave alone

            if changed:
                data["lastUpdated"] = now_iso
                tmp_fd, tmp_str = tempfile.mkstemp(
                    dir=os.path.dirname(TASKS_PATH),
                    prefix=".active-tasks-tmp-", suffix=".json"
                )
                with os.fdopen(tmp_fd, "w") as fh:
                    json.dump(data, fh, indent=2)
                os.replace(tmp_str, TASKS_PATH)
        finally:
            fcntl.flock(lock_fh, fcntl.LOCK_UN)
except Exception as e:
    print(f"[so-reaper] zombie sweep error: {e}")
    sys.exit(0)

print(f"[so-reaper] zombie-sweep: {len(reaped)} record(s) reaped")
for kind, tid, pid in reaped:
    print(f"  {kind}: id={tid} pid={pid}")
PYEOF
