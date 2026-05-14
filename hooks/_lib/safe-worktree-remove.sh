#!/usr/bin/env bash
# SCOPE: os-only
# safe-worktree-remove.sh — shared helper for safe git worktree removal.
#
# Per ADR-129. Replaces the pattern:
#   git worktree remove --force "$PATH" 2>/dev/null || rm -rf "$PATH"
# which silently destroys in-progress work when git refuses removal.
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/_lib/safe-worktree-remove.sh"
#   safe_worktree_remove <project_dir> <target_path> <caller_label>
#
# Behaviour:
#   - Idempotent: missing target_path returns 0 silently.
#   - Captures git stderr instead of discarding it.
#   - On success: logs `removed` to .cognitive-os/metrics/worktree-removals.jsonl,
#     returns 0.
#   - On failure: logs `remove_failed` with captured stderr, runs
#     `git worktree prune` (non-destructive), leaves directory on disk,
#     returns git's exit code.
#   - COS_WORKTREE_REMOVE_ALLOW_RM_RF=1 enables explicit rm -rf fallback;
#     logged as `force_rm_rf` for visibility. Default off.
#
# Never blocks the caller. Always returns; never exits the caller's process.

# Guard against double-source.
if [ -n "${_SAFE_WORKTREE_REMOVE_LOADED:-}" ]; then
  return 0 2>/dev/null || true
fi
_SAFE_WORKTREE_REMOVE_LOADED=1

safe_worktree_remove() {
  local project_dir="${1:-}"
  local target="${2:-}"
  local caller="${3:-unknown}"

  if [ -z "$project_dir" ] || [ -z "$target" ]; then
    return 2
  fi

  # Idempotent: nothing to remove.
  if [ ! -e "$target" ]; then
    return 0
  fi

  local metrics_dir="$project_dir/.cognitive-os/metrics"
  local log_file="$metrics_dir/worktree-removals.jsonl"
  mkdir -p "$metrics_dir" 2>/dev/null || true

  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  # Try git removal, capturing stderr.
  local stderr_file
  stderr_file="$(mktemp 2>/dev/null || echo "/tmp/safe-wt-rm.$$.err")"
  local rc=0
  git -C "$project_dir" worktree remove --force "$target" >/dev/null 2>"$stderr_file" || rc=$?

  if [ "$rc" -eq 0 ]; then
    _safe_wtr_log "$log_file" "$ts" "removed" "$target" "$caller" ""
    rm -f "$stderr_file" 2>/dev/null || true
    return 0
  fi

  local stderr_content=""
  if [ -s "$stderr_file" ]; then
    stderr_content="$(cat "$stderr_file")"
  fi
  rm -f "$stderr_file" 2>/dev/null || true

  # Run prune to clear any dangling registration. Non-destructive.
  git -C "$project_dir" worktree prune 2>/dev/null || true

  # Escape hatch: ONLY if explicitly requested by env var.
  if [ "${COS_WORKTREE_REMOVE_ALLOW_RM_RF:-0}" = "1" ]; then
    rm -rf "$target" 2>/dev/null || true
    _safe_wtr_log "$log_file" "$ts" "force_rm_rf" "$target" "$caller" "$stderr_content"
    return 0
  fi

  _safe_wtr_log "$log_file" "$ts" "remove_failed" "$target" "$caller" "$stderr_content"
  return "$rc"
}

# Internal: append a single JSONL line to the audit log.
# Args: log_file, ts, action, target, caller, stderr_content
_safe_wtr_log() {
  local log_file="$1"
  local ts="$2"
  local action="$3"
  local target="$4"
  local caller="$5"
  local stderr_content="$6"

  if ! command -v python3 >/dev/null 2>&1; then
    # Fallback: append a minimal line without escaping. Better than silence.
    printf '{"ts":"%s","action":"%s","target":"%s","caller":"%s"}\n' \
      "$ts" "$action" "$target" "$caller" >> "$log_file" 2>/dev/null || true
    return 0
  fi

  python3 - "$log_file" "$ts" "$action" "$target" "$caller" "$stderr_content" <<'PY' 2>/dev/null || true
import json, sys
log_file, ts, action, target, caller, stderr_content = sys.argv[1:]
entry = {
    "ts": ts,
    "action": action,
    "target": target,
    "caller": caller,
}
if stderr_content:
    entry["git_stderr"] = stderr_content.strip()
with open(log_file, "a") as f:
    f.write(json.dumps(entry) + "\n")
PY
}
