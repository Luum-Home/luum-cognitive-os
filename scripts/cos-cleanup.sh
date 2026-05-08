#!/usr/bin/env bash
# cos-cleanup.sh — Tiered automatic cleanup for stale repo artifacts.
#
# See docs/runbooks/cos-cleanup.md for operator guidance.
#
# Tier 1 (low risk, auto): stale .git/index.lock, old validation capsules,
#                          expired ADR-116 task-claim locks, stale .current-session-* files.
# Tier 2 (medium risk, confirmed): merged worktree-agent-* branches,
#                                  orphan worktrees, dead daemon registrations.
# Tier 3 (destructive, --aggressive --apply): unmerged branches (list only),
#                                             worktrees with WIP (stash-or-bail),
#                                             live daemons (SIGTERM with grace).
set -u
set -o pipefail

# Resolve repo root (script lives in scripts/).
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
AUDIT_LOG_DEFAULT="${ROOT}/.cognitive-os/cleanup-audit.jsonl"
AUDIT_LOG="${COS_CLEANUP_AUDIT_LOG:-$AUDIT_LOG_DEFAULT}"

TIER=1
DRY_RUN=1
APPLY=0
AGGRESSIVE=0
JSON=0
NONINTERACTIVE="${COS_CLEANUP_NONINTERACTIVE:-0}"
NOW_EPOCH="$(date +%s)"
NOW_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Result accumulator (one JSON object per line in $RESULTS_FILE).
RESULTS_FILE="$(mktemp -t cos-cleanup.XXXXXX)"
trap 'rm -f "$RESULTS_FILE"' EXIT

TIER3_FOUND=0

usage() {
  cat <<'EOF'
cos-cleanup.sh — tiered automatic cleanup of stale repo artifacts.

USAGE:
  scripts/cos-cleanup.sh [--tier=N] [--dry-run|--apply] [--aggressive] [--json]

FLAGS:
  --tier=1|2|3        Highest tier to consider. Default: 1
  --dry-run           Plan only, no mutations. (Default unless --apply)
  --apply             Execute the plan. Required for any state change.
  --aggressive        Allow tier-3 destructive actions. Requires --apply.
  --json              Machine-readable JSON output.
  -h, --help          Show this help.

ENV:
  COS_CLEANUP_NONINTERACTIVE=1  Skip per-category prompts in tier-2 apply.
  COS_CLEANUP_AUDIT_LOG=path    Override audit log path.

EXIT:
  0 success
  1 tier-3 candidate exists (review needed)
  2 usage error

AUDIT LOG:
  .cognitive-os/cleanup-audit.jsonl  (one JSON object per line)
EOF
}

# --- Arg parsing ------------------------------------------------------------
for arg in "$@"; do
  case "$arg" in
    --tier=1|--tier=2|--tier=3) TIER="${arg#--tier=}" ;;
    --dry-run) DRY_RUN=1; APPLY=0 ;;
    --apply)   APPLY=1;   DRY_RUN=0 ;;
    --aggressive) AGGRESSIVE=1 ;;
    --json) JSON=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ "$AGGRESSIVE" == "1" && "$APPLY" != "1" ]]; then
  echo "--aggressive requires --apply" >&2
  exit 2
fi

mkdir -p "$(dirname "$AUDIT_LOG")" 2>/dev/null || true

# --- Helpers ----------------------------------------------------------------
json_escape() {
  # Minimal JSON string escape for the limited inputs we emit.
  python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"
}

audit() {
  # audit <tier> <action> <target> <reason> <applied:0|1> <result> [error]
  local tier="$1" action="$2" target="$3" reason="$4" applied="$5" result="$6" err="${7:-}"
  local dry="true"
  [[ "$APPLY" == "1" ]] && dry="false"
  local applied_bool="false"
  [[ "$applied" == "1" ]] && applied_bool="true"
  local err_field="null"
  if [[ -n "$err" ]]; then
    err_field="$(json_escape "$err")"
  fi
  printf '{"ts":%s,"tier":%s,"action":%s,"target":%s,"reason":%s,"dry_run":%s,"applied":%s,"result":%s,"error":%s}\n' \
    "$(json_escape "$NOW_ISO")" "$tier" "$(json_escape "$action")" \
    "$(json_escape "$target")" "$(json_escape "$reason")" \
    "$dry" "$applied_bool" "$(json_escape "$result")" "$err_field" \
    | tee -a "$RESULTS_FILE" >> "$AUDIT_LOG"
}

is_safe_path() {
  # Refuse to act on protected globs.
  local p="$1"
  case "$p" in
    *"/.git/"*|*"/.git") return 1 ;;
    *"/node_modules/"*) return 1 ;;
    *"/.cognitive-os/private/"*) return 1 ;;
    *"/.engram/exports/"*) return 1 ;;
  esac
  return 0
}

mtime_epoch() {
  # Cross-platform mtime in seconds since epoch. Empty on missing.
  local p="$1"
  [[ -e "$p" ]] || { echo ""; return; }
  if stat -f %m "$p" >/dev/null 2>&1; then
    stat -f %m "$p"
  else
    stat -c %Y "$p"
  fi
}

confirm() {
  local prompt="$1"
  if [[ "$NONINTERACTIVE" == "1" ]]; then
    return 0
  fi
  read -r -p "$prompt [y/N] " ans || ans=""
  [[ "$ans" == "y" || "$ans" == "Y" ]]
}

# --- Tier 1 -----------------------------------------------------------------
tier1_index_lock() {
  local lock="${ROOT}/.git/index.lock"
  [[ -f "$lock" ]] || return 0
  local m; m="$(mtime_epoch "$lock")"
  [[ -z "$m" ]] && return 0
  local age=$(( NOW_EPOCH - m ))
  if (( age <= 300 )); then
    return 0
  fi
  if pgrep -f '\bgit\b' >/dev/null 2>&1; then
    audit 1 "rm-file" "$lock" "git process alive — skip" 0 "skipped" ""
    return 0
  fi
  if [[ "$APPLY" == "1" ]]; then
    if rm -f "$lock" 2>/dev/null; then
      audit 1 "rm-file" "$lock" "stale git index lock (age=${age}s)" 1 "ok" ""
    else
      audit 1 "rm-file" "$lock" "stale git index lock (age=${age}s)" 1 "error" "rm failed"
    fi
  else
    audit 1 "rm-file" "$lock" "stale git index lock (age=${age}s)" 0 "ok" ""
  fi
}

tier1_validation_capsules() {
  local roots=("/tmp" "/private/tmp")
  local cutoff=$(( NOW_EPOCH - 7*24*3600 ))
  for r in "${roots[@]}"; do
    [[ -d "$r" ]] || continue
    while IFS= read -r p; do
      [[ -z "$p" ]] && continue
      is_safe_path "$p" || continue
      local m; m="$(mtime_epoch "$p")"
      [[ -z "$m" ]] && continue
      if (( m < cutoff )); then
        if [[ "$APPLY" == "1" ]]; then
          if rm -rf "$p" 2>/dev/null; then
            audit 1 "rm-file" "$p" "validation capsule mtime>7d" 1 "ok" ""
          else
            audit 1 "rm-file" "$p" "validation capsule mtime>7d" 1 "error" "rm -rf failed"
          fi
        else
          audit 1 "rm-file" "$p" "validation capsule mtime>7d" 0 "ok" ""
        fi
      fi
    done < <(find "$r" -maxdepth 1 -name 'luum-agent-os-*' 2>/dev/null)
  done
}

tier1_task_claim_locks() {
  local runtime="${ROOT}/.cognitive-os/runtime"
  [[ -d "$runtime" ]] || return 0
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    is_safe_path "$f" || continue
    # Look for expires_at field in JSON.
    local exp
    exp="$(python3 - "$f" <<'PY' 2>/dev/null || true
import json, sys, datetime
try:
    with open(sys.argv[1]) as fh:
        d = json.load(fh)
    e = d.get("expires_at")
    if not e:
        sys.exit(0)
    # Accept ISO 8601 with optional Z suffix.
    e2 = e.replace("Z", "+00:00")
    dt = datetime.datetime.fromisoformat(e2)
    print(int(dt.timestamp()))
except Exception:
    pass
PY
)"
    [[ -z "$exp" ]] && continue
    if (( exp < NOW_EPOCH )); then
      if [[ "$APPLY" == "1" ]]; then
        if rm -f "$f" 2>/dev/null; then
          audit 1 "rm-file" "$f" "task-claim lock expired" 1 "ok" ""
        else
          audit 1 "rm-file" "$f" "task-claim lock expired" 1 "error" "rm failed"
        fi
      else
        audit 1 "rm-file" "$f" "task-claim lock expired" 0 "ok" ""
      fi
    fi
  done < <(find "$runtime" -type f -name '*.json' 2>/dev/null)
}

tier1_stale_session_pointers() {
  local sdir="${ROOT}/.cognitive-os/sessions"
  [[ -d "$sdir" ]] || return 0
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    is_safe_path "$f" || continue
    local sid
    sid="$(basename "$f")"
    sid="${sid#.current-session-}"
    # If a process referencing this session id is alive, keep.
    if [[ -n "$sid" ]] && pgrep -f "$sid" >/dev/null 2>&1; then
      audit 1 "rm-file" "$f" "session $sid still running — skip" 0 "skipped" ""
      continue
    fi
    if [[ "$APPLY" == "1" ]]; then
      if rm -f "$f" 2>/dev/null; then
        audit 1 "rm-file" "$f" "stale session pointer (sid=$sid)" 1 "ok" ""
      else
        audit 1 "rm-file" "$f" "stale session pointer (sid=$sid)" 1 "error" "rm failed"
      fi
    else
      audit 1 "rm-file" "$f" "stale session pointer (sid=$sid)" 0 "ok" ""
    fi
  done < <(find "$sdir" -maxdepth 1 -type f -name '.current-session-*' 2>/dev/null)
}

run_tier1() {
  tier1_index_lock
  tier1_validation_capsules
  tier1_task_claim_locks
  tier1_stale_session_pointers
}

# --- Tier 2 -----------------------------------------------------------------
tier2_merged_branches() {
  command -v git >/dev/null 2>&1 || return 0
  ( cd "$ROOT" && git rev-parse --git-dir >/dev/null 2>&1 ) || return 0
  local branches
  branches="$(cd "$ROOT" && git for-each-ref --format='%(refname:short)' refs/heads/ 2>/dev/null \
    | grep -E '^(worktree-agent-|codex/agent/task-desc-|feat/cos-)' || true)"
  [[ -z "$branches" ]] && return 0
  local default_branch="main"
  local candidates=()
  while IFS= read -r b; do
    [[ -z "$b" ]] && continue
    [[ "$b" == "$default_branch" ]] && continue
    # Skip currently checked-out branch.
    local cur; cur="$(cd "$ROOT" && git rev-parse --abbrev-ref HEAD 2>/dev/null)"
    [[ "$b" == "$cur" ]] && continue
    local count
    count="$(cd "$ROOT" && git rev-list --count "$b" "^$default_branch" 2>/dev/null || echo "?")"
    if [[ "$count" == "0" ]]; then
      candidates+=("$b")
      audit 2 "rm-branch" "$b" "merged or empty vs $default_branch" 0 "ok" ""
    fi
  done <<< "$branches"
  if [[ "$APPLY" == "1" && ${#candidates[@]} -gt 0 ]]; then
    if confirm "Delete ${#candidates[@]} merged/empty branch(es)?"; then
      for b in "${candidates[@]}"; do
        if (cd "$ROOT" && git branch -d "$b" >/dev/null 2>&1); then
          audit 2 "rm-branch" "$b" "merged or empty vs $default_branch" 1 "ok" ""
        else
          audit 2 "rm-branch" "$b" "merged or empty vs $default_branch" 1 "error" "git branch -d failed"
        fi
      done
    fi
  fi
}

tier2_orphan_worktrees() {
  command -v git >/dev/null 2>&1 || return 0
  ( cd "$ROOT" && git rev-parse --git-dir >/dev/null 2>&1 ) || return 0
  local out
  out="$(cd "$ROOT" && git worktree list --porcelain 2>/dev/null || true)"
  [[ -z "$out" ]] && return 0
  local wpath="" wbranch=""
  local orphans=()
  while IFS= read -r line; do
    case "$line" in
      worktree\ *) wpath="${line#worktree }" ;;
      branch\ *)   wbranch="${line#branch }" ;;
      "")
        if [[ -n "$wpath" && -n "$wbranch" ]]; then
          if ! (cd "$ROOT" && git show-ref --verify --quiet "$wbranch"); then
            local dirty=""
            if [[ -d "$wpath" ]]; then
              dirty="$(cd "$wpath" && git status --porcelain 2>/dev/null || true)"
            fi
            if [[ -n "$dirty" ]]; then
              TIER3_FOUND=1
              audit 3 "rm-worktree" "$wpath" "branch $wbranch missing but WIP exists — manual Tier 3 review" 0 "skipped" ""
            else
              orphans+=("$wpath")
              audit 2 "rm-worktree" "$wpath" "branch $wbranch missing and worktree clean" 0 "ok" ""
            fi
          fi
        fi
        wpath=""; wbranch=""
        ;;
    esac
  done <<< "$out"$'\n'
  if [[ "$APPLY" == "1" && ${#orphans[@]} -gt 0 ]]; then
    if confirm "Prune ${#orphans[@]} orphan worktree(s)?"; then
      for w in "${orphans[@]}"; do
        if (cd "$ROOT" && git worktree remove --force "$w" >/dev/null 2>&1); then
          audit 2 "rm-worktree" "$w" "orphan branch" 1 "ok" ""
        else
          audit 2 "rm-worktree" "$w" "orphan branch" 1 "error" "git worktree remove failed"
        fi
      done
    fi
  fi
}

tier2_dead_daemons() {
  # Find cos_executor.py --daemon processes whose --working-dir is gone.
  local pids
  pids="$(pgrep -f 'cos_executor\.py.*--daemon' 2>/dev/null || true)"
  [[ -z "$pids" ]] && return 0
  for pid in $pids; do
    local cmd
    cmd="$(ps -o command= -p "$pid" 2>/dev/null || true)"
    [[ -z "$cmd" ]] && continue
    # Extract --working-dir <path>
    local wd
    wd="$(printf '%s' "$cmd" | sed -nE 's/.*--working-dir[= ]([^ ]+).*/\1/p')"
    [[ -z "$wd" ]] && continue
    if [[ ! -d "$wd" ]]; then
      audit 2 "sigterm-daemon" "pid=$pid wd=$wd" "working-dir missing" 0 "ok" ""
      if [[ "$APPLY" == "1" ]]; then
        if confirm "SIGTERM dead daemon pid=$pid?"; then
          if kill -TERM "$pid" 2>/dev/null; then
            audit 2 "sigterm-daemon" "pid=$pid wd=$wd" "working-dir missing" 1 "ok" ""
          else
            audit 2 "sigterm-daemon" "pid=$pid wd=$wd" "working-dir missing" 1 "error" "kill failed"
          fi
        fi
      fi
    fi
  done
}

run_tier2() {
  tier2_merged_branches
  tier2_orphan_worktrees
  tier2_dead_daemons
}

# --- Tier 3 -----------------------------------------------------------------
tier3_unmerged_branches() {
  command -v git >/dev/null 2>&1 || return 0
  ( cd "$ROOT" && git rev-parse --git-dir >/dev/null 2>&1 ) || return 0
  local default_branch="main"
  local branches
  branches="$(cd "$ROOT" && git for-each-ref --format='%(refname:short)' refs/heads/ 2>/dev/null \
    | grep -E '^(worktree-agent-|codex/agent/task-desc-|feat/cos-)' || true)"
  while IFS= read -r b; do
    [[ -z "$b" ]] && continue
    [[ "$b" == "$default_branch" ]] && continue
    local cur; cur="$(cd "$ROOT" && git rev-parse --abbrev-ref HEAD 2>/dev/null)"
    [[ "$b" == "$cur" ]] && continue
    local count
    count="$(cd "$ROOT" && git rev-list --count "$b" "^$default_branch" 2>/dev/null || echo "0")"
    if [[ "$count" != "0" && "$count" != "?" ]]; then
      TIER3_FOUND=1
      audit 3 "rm-branch" "$b" "unmerged ($count commit(s)) — REVIEW: rebase or cherry-pick before deletion" 0 "skipped" ""
    fi
  done <<< "$branches"
}

tier3_wip_worktrees() {
  command -v git >/dev/null 2>&1 || return 0
  ( cd "$ROOT" && git rev-parse --git-dir >/dev/null 2>&1 ) || return 0
  local out
  out="$(cd "$ROOT" && git worktree list --porcelain 2>/dev/null || true)"
  [[ -z "$out" ]] && return 0
  local wpath=""
  while IFS= read -r line; do
    case "$line" in
      worktree\ *) wpath="${line#worktree }" ;;
      "")
        if [[ -n "$wpath" && -d "$wpath" ]]; then
          local dirty
          dirty="$(cd "$wpath" && git status --porcelain 2>/dev/null || true)"
          if [[ -n "$dirty" ]]; then
            TIER3_FOUND=1
            audit 3 "stash-wip" "$wpath" "uncommitted WIP detected" 0 "ok" ""
            if [[ "$AGGRESSIVE" == "1" && "$APPLY" == "1" ]]; then
              local msg="cos-cleanup-stash-${NOW_EPOCH}"
              if (cd "$wpath" && git stash push -u -m "$msg" >/dev/null 2>&1); then
                audit 3 "stash-wip" "$wpath" "stashed as $msg" 1 "ok" ""
              else
                audit 3 "stash-wip" "$wpath" "stash failed (bail)" 1 "error" "git stash push failed"
              fi
            fi
          fi
        fi
        wpath=""
        ;;
    esac
  done <<< "$out"$'\n'
}

tier3_live_daemons() {
  local pids
  pids="$(pgrep -f 'cos_executor\.py.*--daemon' 2>/dev/null || true)"
  [[ -z "$pids" ]] && return 0
  for pid in $pids; do
    local cmd
    cmd="$(ps -o command= -p "$pid" 2>/dev/null || true)"
    [[ -z "$cmd" ]] && continue
    local wd
    wd="$(printf '%s' "$cmd" | sed -nE 's/.*--working-dir[= ]([^ ]+).*/\1/p')"
    # Skip those already handled by tier2 (working-dir missing).
    if [[ -n "$wd" && ! -d "$wd" ]]; then
      continue
    fi
    TIER3_FOUND=1
    audit 3 "sigterm-daemon" "pid=$pid" "live daemon (wd=$wd) — manual review" 0 "ok" ""
    if [[ "$AGGRESSIVE" == "1" && "$APPLY" == "1" ]]; then
      if kill -TERM "$pid" 2>/dev/null; then
        # Wait up to 10s for graceful exit.
        local i=0
        while (( i < 10 )) && kill -0 "$pid" 2>/dev/null; do
          sleep 1
          i=$(( i + 1 ))
        done
        if kill -0 "$pid" 2>/dev/null; then
          audit 3 "sigterm-daemon" "pid=$pid" "still alive after 10s; NOT escalating to SIGKILL" 1 "error" "grace period exhausted"
        else
          audit 3 "sigterm-daemon" "pid=$pid" "graceful exit" 1 "ok" ""
        fi
      else
        audit 3 "sigterm-daemon" "pid=$pid" "kill -TERM failed" 1 "error" "kill failed"
      fi
    fi
  done
}

run_tier3() {
  tier3_unmerged_branches
  tier3_wip_worktrees
  tier3_live_daemons
}

# --- Main -------------------------------------------------------------------
case "$TIER" in
  1) run_tier1 ;;
  2) run_tier1; run_tier2 ;;
  3) run_tier1; run_tier2; run_tier3 ;;
esac

# Output
if [[ "$JSON" == "1" ]]; then
  printf '{"tier":%s,"dry_run":%s,"apply":%s,"aggressive":%s,"audit_log":%s,"results":[' \
    "$TIER" "$([[ $DRY_RUN == 1 ]] && echo true || echo false)" \
    "$([[ $APPLY == 1 ]] && echo true || echo false)" \
    "$([[ $AGGRESSIVE == 1 ]] && echo true || echo false)" \
    "$(json_escape "$AUDIT_LOG")"
  first=1
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    if [[ "$first" == "1" ]]; then
      printf '%s' "$line"; first=0
    else
      printf ',%s' "$line"
    fi
  done < "$RESULTS_FILE"
  printf ']}\n'
else
  echo "cos-cleanup: tier=$TIER dry_run=$([[ $DRY_RUN == 1 ]] && echo true || echo false) apply=$([[ $APPLY == 1 ]] && echo true || echo false) aggressive=$([[ $AGGRESSIVE == 1 ]] && echo true || echo false)"
  echo "audit log: $AUDIT_LOG"
  count=$(wc -l < "$RESULTS_FILE" | tr -d ' ')
  echo "candidates/actions: $count"
  if (( count > 0 )); then
    cat "$RESULTS_FILE"
  fi
fi

if [[ "$TIER3_FOUND" == "1" ]]; then
  exit 1
fi
exit 0
