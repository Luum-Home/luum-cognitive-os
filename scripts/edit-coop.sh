#!/usr/bin/env bash
# SCOPE: both
# edit-coop.sh — ADR-098 Layer 4: file-level edit coordination
#
# Builds on ADR-089 Layer 2 primitives (git-coop.sh atomic mkdir + PID-based
# stale detection) but locks a SPECIFIC FILE rather than the git index.
#
# USAGE (standalone):
#   scripts/edit-coop.sh acquire <file-path> [--purpose "..."] [--intent exclusive-edit|shared-read|append-only]
#   scripts/edit-coop.sh release <file-path>
#   scripts/edit-coop.sh check <file-path>           # exit 0 if lockable, 2 if held by other
#   scripts/edit-coop.sh status                      # print all active locks as JSON
#   scripts/edit-coop.sh heartbeat <file-path>       # refresh own lock TTL
#   scripts/edit-coop.sh release-mine                # release every lock owned by this session
#
# LOCK LOCATION:
#   .cognitive-os/runtime/edit-locks/<safe-path>/         (POSIX-atomic mkdir)
#   .cognitive-os/runtime/edit-locks/<safe-path>/meta.yaml (rich data — see schema)
#
# RICH SCHEMA (so other agents can introspect and respond):
#   session_id, agent_id, agent_role, worktree
#   target_file, intent, since, heartbeat, expires_at
#   purpose, related_adr, related_files
#   allows_concurrent_read, allows_concurrent_edit_below_line
#   on_conflict_other_agent_should   (park | retry | negotiate | escalate)
#   status (active | parking | released | stale)
#
# STALE DETECTION (same rule as git-coop.sh):
#   - timestamp older than COS_EDIT_LOCK_TTL (default 1800s = 30min), OR
#   - PID is not running on this machine
#
# IDEMPOTENT:
#   Re-acquiring own lock refreshes heartbeat + expires_at, succeeds.
#
# ESCAPE HATCH:
#   COS_BYPASS_EDIT_LOCK=1 — skip all locks (emergency only; logged to history).
#
# POSIX / macOS compatible.
set -uo pipefail
_SESSION_ID_LIB="$(dirname "${BASH_SOURCE[0]}")/_lib/session-id.sh"
if [ -f "$_SESSION_ID_LIB" ]; then
  # shellcheck source=/dev/null
  source "$_SESSION_ID_LIB"
else
  cos_session_id() { printf '%s' "${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-default-session}}"; }
fi

LOCK_TTL_SECONDS="${COS_EDIT_LOCK_TTL:-1800}"      # 30 minutes
LOCK_HEARTBEAT_SECONDS="${COS_EDIT_LOCK_HEARTBEAT:-300}"  # refresh every 5min

# ── Path resolution ─────────────────────────────────────────────────────────

_resolve_project_dir() {
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    printf '%s' "$CLAUDE_PROJECT_DIR"
    return
  fi
  if [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then
    printf '%s' "$COGNITIVE_OS_PROJECT_DIR"
    return
  fi
  local dir
  dir="$(pwd)"
  while [ "$dir" != "/" ]; do
    if [ -f "$dir/cognitive-os.yaml" ] || [ -d "$dir/.claude" ]; then
      printf '%s' "$dir"
      return
    fi
    dir="$(dirname "$dir")"
  done
  printf '%s' "$(pwd)"
}

_locks_root() {
  printf '%s/.cognitive-os/runtime/edit-locks' "$(_resolve_project_dir)"
}

# Convert "tests/conftest.py" → "tests--conftest.py" (filesystem-safe key).
_safe_path() {
  printf '%s' "$1" | sed 's|/|--|g; s|\.\.||g'
}

_lock_dir_for() {
  printf '%s/%s' "$(_locks_root)" "$(_safe_path "$1")"
}

_meta_file_for() {
  printf '%s/meta.yaml' "$(_lock_dir_for "$1")"
}

# ── Identity ────────────────────────────────────────────────────────────────

_session_id() {
  cos_session_id
}

_agent_id() {
  printf '%s' "${COS_AGENT_ID:-${CLAUDE_AGENT_ID:-unknown-agent}}"
}

_agent_role() {
  printf '%s' "${COS_AGENT_ROLE:-orchestrator}"
}

_worktree() {
  git -C "$(_resolve_project_dir)" rev-parse --show-toplevel 2>/dev/null \
    || _resolve_project_dir
}

_iso8601() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

_iso8601_plus() {
  # Add N seconds to current UTC time. POSIX-portable.
  local seconds="$1"
  local now_epoch
  now_epoch=$(date -u +%s)
  local target=$(( now_epoch + seconds ))
  date -u -r "$target" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
    || date -u -d "@$target" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
    || _iso8601
}

_pid_alive() {
  # `kill -0` returns failure for BOTH "no such process" (ESRCH) and "not
  # yours" (EPERM), and bash cannot tell them apart. On macOS every pid owned
  # by another user — pid 1 included — therefore read as dead, and a LIVE
  # lock held by another user's agent was cleared as stale. `ps -p` answers
  # existence without permission to signal, so ask it before concluding death.
  kill -0 "$1" 2>/dev/null && return 0
  ps -p "$1" >/dev/null 2>&1
}

# ── Stale detection ─────────────────────────────────────────────────────────

_lock_is_stale() {
  local file_path="$1"
  local meta_file
  meta_file="$(_meta_file_for "$file_path")"
  [ -f "$meta_file" ] || return 0

  local pid timestamp_raw expires_raw
  pid=$(sed -n 's/^pid: *\([0-9]*\)$/\1/p' "$meta_file" | head -1)
  timestamp_raw=$(sed -n 's/^heartbeat: *"\(.*\)"$/\1/p' "$meta_file" | head -1)
  [ -z "$timestamp_raw" ] && timestamp_raw=$(sed -n 's/^since: *"\(.*\)"$/\1/p' "$meta_file" | head -1)

  # The writer stamps expires_at on every acquire and refreshes it on every
  # heartbeat, so the lock already declares when it dies. Until 2026-08-20
  # nothing read the field: it was written by the birth commit (bca8fb7c6) and
  # never wired to a reader, so a lock that declared a 30-minute life kept
  # producing EDIT-LOCK CONFLICT for months (measured: 1296 of 1316 locks past
  # their own expires_at, the oldest by 96 days). Honour the declaration first
  # — it beats any heuristic about age, because the owner wrote it.
  # `status: "active"` is NOT consulted: it is stamped once and never updated,
  # so every expired lock still claims to be active.
  expires_raw=$(sed -n 's/^expires_at: *"\(.*\)"$/\1/p' "$meta_file" | head -1)
  if [ -n "$expires_raw" ]; then
    local now_epoch expires_epoch
    now_epoch=$(date -u +%s)
    expires_epoch=$(date -d "$expires_raw" +%s 2>/dev/null) \
      || expires_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$expires_raw" +%s 2>/dev/null) \
      || expires_epoch=""
    if [ -n "$expires_epoch" ] && [ "$now_epoch" -gt "$expires_epoch" ]; then
      return 0
    fi
  fi

  [ -z "$pid" ] && return 0
  # Skip PID liveness when explicitly disabled (used by unit tests where each
  # bash invocation is a fresh subprocess that exits immediately, making every
  # lock look stale by PID). Production keeps the check.
  if [ "${COS_EDIT_LOCK_NO_PID_CHECK:-}" != "1" ]; then
    _pid_alive "$pid" || return 0
  fi
  [ -z "$timestamp_raw" ] && return 0

  local now lock_time
  now=$(date -u +%s)
  lock_time=$(date -d "$timestamp_raw" +%s 2>/dev/null) \
    || lock_time=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$timestamp_raw" +%s 2>/dev/null) \
    || return 0
  local age=$(( now - lock_time ))
  [ "$age" -gt "$LOCK_TTL_SECONDS" ] && return 0
  return 1
}

# ── Lock metadata read helpers (for introspection by sub-agents) ────────────

_read_field() {
  local file="$1" field="$2"
  sed -n "s/^${field}: *\"\\(.*\\)\"\$/\\1/p" "$file" | head -1
}

# Returns the session_id holding the lock, or empty string.
_lock_holder() {
  local meta_file
  meta_file="$(_meta_file_for "$1")"
  [ -f "$meta_file" ] || { printf ''; return; }
  _read_field "$meta_file" "session_id"
}

# ── Public commands ─────────────────────────────────────────────────────────

cmd_acquire() {
  if [ "${COS_BYPASS_EDIT_LOCK:-}" = "1" ]; then
    echo "[edit-coop] BYPASS: COS_BYPASS_EDIT_LOCK=1, no lock taken on $1" >&2

    # ── D3: Bypass audit log ──────────────────────────────────────────────────
    # If a live lock exists and a bypass is being used, record to the audit log.
    # The log is append-only and NEVER deleted automatically.
    local _bypass_file_path="$1"
    local _bypass_lock_dir
    _bypass_lock_dir="$(_lock_dir_for "$_bypass_file_path")"
    if [ -d "$_bypass_lock_dir" ] && ! _lock_is_stale "$_bypass_file_path"; then
      local _bypassed_session
      _bypassed_session="$(_lock_holder "$_bypass_file_path")"
      if [ -n "$_bypassed_session" ] && [ "$_bypassed_session" != "$(_session_id)" ]; then
        local _audit_dir
        _audit_dir="$(_resolve_project_dir)/.cognitive-os/runtime"
        mkdir -p "$_audit_dir"
        local _audit_file="$_audit_dir/edit-locks-audit.jsonl"
        local _entry
        _entry="$(printf '{"timestamp":"%s","bypassed_session":"%s","bypasser_session":"%s","file_path":"%s","reason":"%s","agent_id":"%s","pid":%s}\n' \
          "$(_iso8601)" \
          "$_bypassed_session" \
          "$(_session_id)" \
          "$_bypass_file_path" \
          "${COS_BYPASS_EDIT_LOCK_REASON:-no reason given}" \
          "$(_agent_id)" \
          "$$")"
        printf '%s\n' "$_entry" >> "$_audit_file"
        echo "[edit-coop] BYPASS AUDIT: logged bypass of session=$_bypassed_session on $_bypass_file_path" >&2
      fi
    fi
    # ─────────────────────────────────────────────────────────────────────────
    return 0
  fi

  local file_path="$1" purpose="${2:-unspecified}" intent="${3:-exclusive-edit}"
  local lock_dir meta_file
  lock_dir="$(_lock_dir_for "$file_path")"
  meta_file="$(_meta_file_for "$file_path")"

  mkdir -p "$(_locks_root)"

  # Stale auto-clear before attempting acquire.
  if [ -d "$lock_dir" ] && _lock_is_stale "$file_path"; then
    echo "[edit-coop] auto-clearing stale lock on $file_path" >&2
    rm -rf "$lock_dir"
  fi

  # Atomic acquire via mkdir.
  if mkdir "$lock_dir" 2>/dev/null; then
    _write_meta "$file_path" "$purpose" "$intent" "active"
    echo "[edit-coop] acquired $file_path (intent=$intent)" >&2
    return 0
  fi

  # Already exists. Check if it's ours.
  if [ -f "$meta_file" ]; then
    local holder
    holder="$(_lock_holder "$file_path")"
    if [ "$holder" = "$(_session_id)" ]; then
      _write_meta "$file_path" "$purpose" "$intent" "active"
      echo "[edit-coop] re-acquired (own lock) $file_path" >&2
      return 0
    fi
    # Held by other session.
    echo "[edit-coop] BLOCKED — $file_path held by session=$holder" >&2
    return 2
  fi
  return 2
}

_write_meta() {
  local file_path="$1" purpose="$2" intent="$3" status="$4"
  local meta_file
  meta_file="$(_meta_file_for "$file_path")"
  cat > "$meta_file" <<EOF
session_id: "$(_session_id)"
agent_id: "$(_agent_id)"
agent_role: "$(_agent_role)"
worktree: "$(_worktree)"
pid: $$
target_file: "$file_path"
intent: "$intent"
since: "$(_iso8601)"
heartbeat: "$(_iso8601)"
expires_at: "$(_iso8601_plus "$LOCK_TTL_SECONDS")"
purpose: "$purpose"
related_adr: "${COS_RELATED_ADR:-}"
related_files: []
allows_concurrent_read: true
on_conflict_other_agent_should: "park"
status: "$status"
EOF
}

cmd_release() {
  local file_path="$1"
  local lock_dir meta_file
  lock_dir="$(_lock_dir_for "$file_path")"
  meta_file="$(_meta_file_for "$file_path")"

  [ -d "$lock_dir" ] || { echo "[edit-coop] no lock on $file_path" >&2; return 0; }

  local holder
  holder="$(_lock_holder "$file_path")"
  if [ -n "$holder" ] && [ "$holder" != "$(_session_id)" ]; then
    echo "[edit-coop] refusing to release $file_path — held by $holder, not us" >&2
    return 2
  fi
  rm -rf "$lock_dir"
  echo "[edit-coop] released $file_path" >&2
}

cmd_check() {
  local file_path="$1"
  local lock_dir
  lock_dir="$(_lock_dir_for "$file_path")"

  if [ ! -d "$lock_dir" ]; then
    echo "[edit-coop] FREE — no lock on $file_path"
    return 0
  fi
  if _lock_is_stale "$file_path"; then
    echo "[edit-coop] STALE — lock on $file_path is stale, will be auto-cleared on next acquire"
    return 0
  fi
  local holder
  holder="$(_lock_holder "$file_path")"
  if [ "$holder" = "$(_session_id)" ]; then
    echo "[edit-coop] OWN — you hold the lock on $file_path"
    return 0
  fi
  echo "[edit-coop] HELD — $file_path locked by session=$holder"
  cat "$(_meta_file_for "$file_path")" 2>/dev/null
  return 2
}

cmd_status() {
  local locks_root
  locks_root="$(_locks_root)"
  [ -d "$locks_root" ] || { echo "{}"; return 0; }

  printf '{"locks":['
  local first=1
  for d in "$locks_root"/*/; do
    [ -d "$d" ] || continue
    local meta="$d/meta.yaml"
    [ -f "$meta" ] || continue
    [ "$first" -eq 1 ] || printf ','
    first=0
    printf '\n  {'
    printf '"target":"%s","session":"%s","agent":"%s","intent":"%s","since":"%s","heartbeat":"%s","purpose":"%s","status":"%s"' \
      "$(_read_field "$meta" target_file)" \
      "$(_read_field "$meta" session_id)" \
      "$(_read_field "$meta" agent_id)" \
      "$(_read_field "$meta" intent)" \
      "$(_read_field "$meta" since)" \
      "$(_read_field "$meta" heartbeat)" \
      "$(_read_field "$meta" purpose)" \
      "$(_read_field "$meta" status)"
    printf '}'
  done
  printf '\n]}\n'
}

cmd_heartbeat() {
  local file_path="$1"
  local meta_file
  meta_file="$(_meta_file_for "$file_path")"
  [ -f "$meta_file" ] || { echo "[edit-coop] no lock to heartbeat on $file_path" >&2; return 1; }
  local holder
  holder="$(_lock_holder "$file_path")"
  [ "$holder" = "$(_session_id)" ] || { echo "[edit-coop] cannot heartbeat — not owner" >&2; return 2; }

  # Refresh heartbeat + expires_at lines in place.
  local now expires
  now="$(_iso8601)"
  expires="$(_iso8601_plus "$LOCK_TTL_SECONDS")"
  local tmp="$meta_file.tmp"
  awk -v now="$now" -v expires="$expires" '
    /^heartbeat: / { print "heartbeat: \"" now "\""; next }
    /^expires_at: / { print "expires_at: \"" expires "\""; next }
    { print }
  ' "$meta_file" > "$tmp" && mv "$tmp" "$meta_file"
  echo "[edit-coop] heartbeat refreshed on $file_path" >&2
}

cmd_release_mine() {
  local locks_root
  locks_root="$(_locks_root)"
  [ -d "$locks_root" ] || return 0
  local me released=0
  me="$(_session_id)"
  for d in "$locks_root"/*/; do
    [ -d "$d" ] || continue
    local meta="$d/meta.yaml"
    [ -f "$meta" ] || continue
    local holder
    holder="$(_read_field "$meta" session_id)"
    if [ "$holder" = "$me" ]; then
      rm -rf "$d"
      released=$(( released + 1 ))
    fi
  done
  echo "[edit-coop] released $released own lock(s)" >&2
}

# ── Bulk hygiene reaper (ADR-098 + ADR-199 surface `edit-locks`) ───────────
#
# cmd_acquire clears an expired lock only when SOMEBODY RE-ACQUIRES THAT SAME
# FILE. A lock on a file nobody touches again therefore stays on disk forever:
# measured 2026-08-20, 1316 lock dirs / 5.1 MiB, 1296 of them past their own
# expires_at. Nothing in the tree ever removed one.
#
# The reap criterion is the lock's OWN declared deadline — expires_at, written
# by the acquirer and refreshed by `edit-coop.sh heartbeat` — plus a grace
# window (COS_EDIT_LOCK_REAP_GRACE, default 3600s = 2x the 1800s TTL) so clock
# skew and a session about to heartbeat are never raced.
#
# This is deliberately the SAME predicate the enforcement path now uses, which
# is what makes bulk deletion safe: after _lock_is_stale honours expires_at, an
# expired lock no longer blocks anybody, so removing it changes disk and not
# semantics. Reaping is hygiene, not the fix.
#
# Sacrificed case: a long-lived session that never calls `heartbeat` loses its
# lock directory. It had already lost the lock — the enforcement predicate frees
# an expired lock whether or not this reaper runs — and the refresh path exists
# precisely so a long session can keep its claim alive.
#
# Fallback when expires_at is absent or unparseable (no such lock exists today,
# but old metas and half-written files are reachable states): require BOTH a
# dead owner pid AND a heartbeat past grace. `status` is never consulted — it is
# stamped once at acquire and never updated, so it reads "active" on every
# corpse.
#
# Usage: edit-coop.sh reap-stale [--dry-run] [--json]
cmd_reap_stale() {
  local dry_run=0 as_json=0
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --dry-run) dry_run=1 ;;
      --json)    as_json=1 ;;
      *) echo "[edit-coop] reap-stale: unknown option $1" >&2; return 64 ;;
    esac
    shift
  done

  local locks_root
  locks_root="$(_locks_root)"
  if [ ! -d "$locks_root" ]; then
    [ "$as_json" -eq 1 ] && echo '{"dry_run":true,"kept":0,"reaped":0,"reaped_samples":[],"scanned":0}'
    return 0
  fi

  # One python pass for the whole sweep: 1300+ lock dirs times sed/kill
  # subprocesses would be thousands of spawns on a SessionEnd path.
  LOCKS_ROOT="$locks_root" \
  COS_EDIT_LOCK_REAP_GRACE="${COS_EDIT_LOCK_REAP_GRACE:-3600}" \
  REAP_DRY_RUN="$dry_run" REAP_JSON="$as_json" \
  python3 - <<'PYEOF'
import json, os, re, shutil, time
from datetime import datetime, timezone

root = os.environ["LOCKS_ROOT"]
grace = int(os.environ.get("COS_EDIT_LOCK_REAP_GRACE") or 3600)
dry = os.environ.get("REAP_DRY_RUN") == "1"
as_json = os.environ.get("REAP_JSON") == "1"

PID_RE = re.compile(r'^pid: *(\d+)\s*$', re.M)
EXP_RE = re.compile(r'^expires_at: *"(.*)"\s*$', re.M)
HB_RE = re.compile(r'^heartbeat: *"(.*)"\s*$', re.M)
SINCE_RE = re.compile(r'^since: *"(.*)"\s*$', re.M)
now = time.time()


def epoch_of(stamp):
    try:
        return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc).timestamp()
    except (ValueError, TypeError):
        return None


def pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True   # exists, owned by someone else
    except OSError:
        return True   # unknown -> assume alive, never reap on doubt
    return True


scanned = reaped = kept = 0
samples = []
try:
    entries = sorted(os.scandir(root), key=lambda e: e.name)
except OSError:
    entries = []

for entry in entries:
    if not entry.is_dir(follow_symlinks=False):
        continue
    scanned += 1
    meta_path = os.path.join(entry.path, "meta.yaml")
    reason = None
    if not os.path.isfile(meta_path):
        # mkdir succeeded, meta write did not: no holder can ever release it.
        try:
            dir_age = now - entry.stat().st_mtime
        except OSError:
            dir_age = None
        if dir_age is not None and dir_age > grace:
            reason = "no-meta-past-grace"
    else:
        try:
            text = open(meta_path, encoding="utf-8", errors="replace").read()
        except OSError:
            text = ""
        m_exp = EXP_RE.search(text)
        expires = epoch_of(m_exp.group(1)) if m_exp else None
        if expires is not None:
            if now > expires + grace:
                reason = "expired-past-grace"
        else:
            m_pid = PID_RE.search(text)
            m_hb = HB_RE.search(text) or SINCE_RE.search(text)
            hb = epoch_of(m_hb.group(1)) if m_hb else None
            owner_dead = (m_pid is None) or (not pid_alive(int(m_pid.group(1))))
            if owner_dead and hb is not None and now - hb > grace:
                reason = "no-expires-owner-dead-past-grace"

    if reason is None:
        kept += 1
        continue
    if not dry:
        try:
            shutil.rmtree(entry.path)
        except OSError:
            kept += 1
            continue
    reaped += 1
    if len(samples) < 5:
        samples.append({"lock": entry.name, "reason": reason})

payload = {"scanned": scanned, "reaped": reaped, "kept": kept,
           "dry_run": dry, "grace_seconds": grace, "reaped_samples": samples}
if as_json:
    print(json.dumps(payload, sort_keys=True))
else:
    verb = "would reap" if dry else "reaped"
    print(f"[edit-coop] reap-stale: scanned={scanned} {verb}={reaped} "
          f"kept={kept} grace={grace}s")
PYEOF
}

# ── Entry point ─────────────────────────────────────────────────────────────

cmd="${1:-}"
shift || true
case "$cmd" in
  acquire)        cmd_acquire "$@" ;;
  release)        cmd_release "$@" ;;
  check)          cmd_check "$@" ;;
  status)         cmd_status ;;
  heartbeat)      cmd_heartbeat "$@" ;;
  release-mine|release_mine) cmd_release_mine ;;
  reap-stale|reap_stale) cmd_reap_stale "$@" ;;
  *)
    cat <<EOF >&2
edit-coop.sh — file-level edit coordination (ADR-098)
Usage:
  edit-coop.sh acquire <file> [purpose] [intent]
  edit-coop.sh release <file>
  edit-coop.sh check <file>          (exit 0 lockable, 2 held)
  edit-coop.sh status                (JSON of all active locks)
  edit-coop.sh heartbeat <file>      (refresh own lock TTL)
  edit-coop.sh release-mine          (release every lock owned by this session)
  edit-coop.sh reap-stale [--dry-run] [--json]
                                     (drop every lock past its own expires_at
                                      by more than COS_EDIT_LOCK_REAP_GRACE)
EOF
    exit 64
    ;;
esac
