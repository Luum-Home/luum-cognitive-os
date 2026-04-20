#!/usr/bin/env bash
# SCOPE: both
# execute-repair.sh — Core execution engine for auto-repair system
# Part of: auto-repair-system (ARS-1-04)
#
# Usage:
#   source "$(dirname "$0")/_lib/execute-repair.sh"
#
# Provides:
#   repair_execute_deterministic <fix_json>     — Fast path for known fixes (no LLM)
#   repair_execute_llm <error_context_json>     — Prepare context for LLM-based repair
#   repair_cleanup_worktree <worktree_path>     — Remove a repair worktree safely
#   repair_verify <worktree_path> <language>    — Run build/test verification
#
# Depends on: safe-jsonl.sh, circuit-breaker.sh, remediation.sh

set -uo pipefail

# ─── Auto-source dependencies ──────────────────────────────────────────────

_EXEC_REPAIR_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "${_SAFE_JSONL_LOADED:-}" != "true" ]; then
  # shellcheck source=safe-jsonl.sh
  source "$_EXEC_REPAIR_LIB_DIR/safe-jsonl.sh"
fi

# shellcheck source=circuit-breaker.sh
source "$_EXEC_REPAIR_LIB_DIR/circuit-breaker.sh"

# shellcheck source=remediation.sh
source "$_EXEC_REPAIR_LIB_DIR/remediation.sh"

# ─── Configuration ─────────────────────────────────────────────────────────

_REPAIR_TIMEOUT_DETERMINISTIC="${COGNITIVE_OS_REPAIR_TIMEOUT_DET:-120}"   # seconds
_REPAIR_TIMEOUT_LLM="${COGNITIVE_OS_REPAIR_TIMEOUT_LLM:-300}"            # seconds
_REPAIR_MAX_CONCURRENT=1

# ─── Paths ─────────────────────────────────────────────────────────────────

_repair_project_dir() {
  echo "${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
}

_repair_worktree_base() {
  local dir
  dir="$(_repair_project_dir)/.cognitive-os/repair-wt"
  mkdir -p "$dir" 2>/dev/null
  echo "$dir"
}

_repair_metrics_file() {
  local metrics_dir
  metrics_dir=$(_resolve_metrics_dir)
  echo "$metrics_dir/repair-outcomes.jsonl"
}

# ─── Concurrency guard ────────────────────────────────────────────────────

_repair_check_concurrent() {
  local wt_base
  wt_base=$(_repair_worktree_base)
  local active_count=0

  for d in "$wt_base"/repair-*; do
    [ -d "$d" ] || continue
    # Verify it's actually a git worktree (has .git file)
    [ -e "$d/.git" ] && active_count=$((active_count + 1))
  done

  if [ "$active_count" -ge "$_REPAIR_MAX_CONCURRENT" ]; then
    echo "[execute-repair] ERROR: Max concurrent repairs ($_REPAIR_MAX_CONCURRENT) reached" >&2
    return 1
  fi
  return 0
}

# ─── Worktree lifecycle ───────────────────────────────────────────────────

_repair_create_worktree() {
  local project_dir
  project_dir=$(_repair_project_dir)
  local wt_base
  wt_base=$(_repair_worktree_base)
  local wt_name="repair-$(date +%s)"
  local wt_path="$wt_base/$wt_name"
  local branch_name="auto-repair/$wt_name"

  # Create worktree from current HEAD
  if ! git -C "$project_dir" worktree add -b "$branch_name" "$wt_path" HEAD 2>&1; then
    echo "[execute-repair] ERROR: Failed to create worktree at $wt_path" >&2
    return 1
  fi

  echo "$wt_path"
  return 0
}

repair_cleanup_worktree() {
  local wt_path="$1"

  [ -z "$wt_path" ] && return 0
  [ ! -d "$wt_path" ] && return 0

  local project_dir
  project_dir=$(_repair_project_dir)

  # Detect the branch name used by this worktree
  local branch_name=""
  if [ -f "$wt_path/.git" ]; then
    branch_name=$(git -C "$wt_path" rev-parse --abbrev-ref HEAD 2>/dev/null || true)
  fi

  # Remove worktree via git
  if ! git -C "$project_dir" worktree remove --force "$wt_path" 2>/dev/null; then
    # Fallback: manual removal
    rm -rf "$wt_path" 2>/dev/null
    git -C "$project_dir" worktree prune 2>/dev/null
  fi

  # Clean up the branch if it was auto-created
  if [ -n "$branch_name" ] && [[ "$branch_name" == auto-repair/* ]]; then
    git -C "$project_dir" branch -D "$branch_name" 2>/dev/null || true
  fi
}

# ─── Verification ─────────────────────────────────────────────────────────

repair_verify() {
  local wt_path="$1"
  local language="${2:-auto}"
  local output=""
  local rc=0

  # Auto-detect language if needed
  if [ "$language" = "auto" ]; then
    language=$(_repair_detect_language "$wt_path")
  fi

  case "$language" in
    go)
      output=$(cd "$wt_path" && go build ./... 2>&1) || rc=1
      if [ "$rc" -eq 0 ] && [ -n "$(find "$wt_path" -name '*_test.go' -newer "$wt_path/.git" 2>/dev/null | head -1)" ]; then
        output+=$'\n'"$(cd "$wt_path" && go test ./... 2>&1)" || rc=1
      fi
      ;;
    ts|typescript)
      if [ -f "$wt_path/node_modules/.bin/tsc" ]; then
        output=$(cd "$wt_path" && npx tsc --noEmit 2>&1) || rc=1
      elif [ -f "$wt_path/package.json" ]; then
        output=$(cd "$wt_path" && npm run build 2>&1) || rc=1
      fi
      ;;
    js|javascript)
      if [ -f "$wt_path/package.json" ]; then
        # Check for build script
        local has_build
        has_build=$(jq -r '.scripts.build // empty' "$wt_path/package.json" 2>/dev/null)
        if [ -n "$has_build" ]; then
          output=$(cd "$wt_path" && npm run build 2>&1) || rc=1
        fi
      fi
      ;;
    py|python)
      # Compile-check all modified .py files
      local py_files
      py_files=$(cd "$wt_path" && git diff --name-only HEAD~1 2>/dev/null | grep '\.py$' || true)
      if [ -n "$py_files" ]; then
        output=$(cd "$wt_path" && echo "$py_files" | xargs python -m py_compile 2>&1) || rc=1
      fi
      ;;
    rust)
      output=$(cd "$wt_path" && cargo check 2>&1) || rc=1
      ;;
    *)
      # Unknown language — skip build, just return success
      output="[verify] No build command for language: $language"
      ;;
  esac

  # Run linter if available
  if [ "$rc" -eq 0 ]; then
    if [ -f "$wt_path/.golangci.yml" ] && command -v golangci-lint >/dev/null 2>&1; then
      output+=$'\n'"$(cd "$wt_path" && golangci-lint run 2>&1)" || rc=1
    elif [ -f "$wt_path/.eslintrc.json" ] || [ -f "$wt_path/.eslintrc.js" ]; then
      if [ -f "$wt_path/node_modules/.bin/eslint" ]; then
        output+=$'\n'"$(cd "$wt_path" && npx eslint . 2>&1)" || rc=1
      fi
    fi
  fi

  # Store output for caller to read
  _REPAIR_VERIFY_OUTPUT="$output"
  return "$rc"
}

_repair_detect_language() {
  local wt_path="$1"

  if [ -f "$wt_path/go.mod" ]; then
    echo "go"
  elif [ -f "$wt_path/tsconfig.json" ]; then
    echo "ts"
  elif [ -f "$wt_path/package.json" ]; then
    echo "js"
  elif [ -f "$wt_path/Cargo.toml" ]; then
    echo "rust"
  elif [ -f "$wt_path/setup.py" ] || [ -f "$wt_path/pyproject.toml" ] || [ -f "$wt_path/requirements.txt" ]; then
    echo "py"
  else
    echo "unknown"
  fi
}

# ─── Metrics logging ─────────────────────────────────────────────────────

_repair_log_outcome() {
  local repair_type="$1"
  local error_type="$2"
  local service="$3"
  local fingerprint="$4"
  local fix_type="$5"
  local outcome="$6"
  local duration_ms="$7"
  local wt_path="$8"
  local verify_output="${9:-}"

  local metrics_file
  metrics_file=$(_repair_metrics_file)

  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  local now_epoch
  now_epoch=$(date +%s)

  # Truncate verification output to 500 chars
  local truncated_output
  truncated_output=$(printf '%.500s' "$verify_output")

  local entry
  if command -v jq >/dev/null 2>&1; then
    entry=$(jq -cn \
      --arg ts "$now" \
      --argjson te "$now_epoch" \
      --arg rt "$repair_type" \
      --arg et "$error_type" \
      --arg svc "$service" \
      --arg fp "$fingerprint" \
      --arg ft "$fix_type" \
      --arg out "$outcome" \
      --argjson dur "$duration_ms" \
      --arg wt "$wt_path" \
      --arg vo "$truncated_output" \
      '{
        timestamp: $ts,
        timestamp_epoch: $te,
        repair_type: $rt,
        error_type: $et,
        service: $svc,
        fingerprint: $fp,
        fix_type: $ft,
        outcome: $out,
        duration_ms: $dur,
        worktree: $wt,
        verification_output: $vo
      }')
  else
    entry="{\"timestamp\":\"$now\",\"timestamp_epoch\":$now_epoch,\"repair_type\":\"$repair_type\",\"error_type\":\"$error_type\",\"service\":\"$service\",\"fingerprint\":\"$fingerprint\",\"fix_type\":\"$fix_type\",\"outcome\":\"$outcome\",\"duration_ms\":$duration_ms,\"worktree\":\"$wt_path\",\"verification_output\":\"$truncated_output\"}"
  fi

  safe_jsonl_append "$metrics_file" "$entry"
}

# ─── Deterministic repair ─────────────────────────────────────────────────

repair_execute_deterministic() {
  local fix_json="$1"

  local start_epoch
  start_epoch=$(date +%s)

  # Parse fix parameters
  local fix_type fix_command fix_diff fingerprint error_type service
  fix_type=$(echo "$fix_json" | jq -r '.fix_type // "command"')
  fix_command=$(echo "$fix_json" | jq -r '.fix_command // empty')
  fix_diff=$(echo "$fix_json" | jq -r '.fix_diff // empty')
  fingerprint=$(echo "$fix_json" | jq -r '.fingerprint // "unknown"')
  error_type=$(echo "$fix_json" | jq -r '.error_type // "UNKNOWN"')
  service=$(echo "$fix_json" | jq -r '.service // "unknown"')

  # Check circuit breaker
  if ! cb_check "$error_type" "$service"; then
    echo "[execute-repair] Circuit breaker OPEN for $error_type/$service — skipping" >&2
    local duration_ms=$(( ($(date +%s) - start_epoch) * 1000 ))
    _repair_log_outcome "deterministic" "$error_type" "$service" "$fingerprint" "$fix_type" "skipped" "$duration_ms" "" "circuit breaker open"
    return 1
  fi

  # Check global budget
  if ! cb_global_budget_ok; then
    echo "[execute-repair] Global hourly repair budget exhausted — skipping" >&2
    local duration_ms=$(( ($(date +%s) - start_epoch) * 1000 ))
    _repair_log_outcome "deterministic" "$error_type" "$service" "$fingerprint" "$fix_type" "skipped" "$duration_ms" "" "hourly budget exhausted"
    return 1
  fi

  # Check concurrent repairs
  if ! _repair_check_concurrent; then
    local duration_ms=$(( ($(date +%s) - start_epoch) * 1000 ))
    _repair_log_outcome "deterministic" "$error_type" "$service" "$fingerprint" "$fix_type" "skipped" "$duration_ms" "" "concurrent repair limit"
    return 1
  fi

  # For restart type, no worktree needed
  if [ "$fix_type" = "restart" ]; then
    _repair_execute_restart "$service" "$error_type" "$fingerprint" "$start_epoch"
    return $?
  fi

  # Create worktree
  local wt_path
  wt_path=$(_repair_create_worktree)
  if [ $? -ne 0 ] || [ -z "$wt_path" ]; then
    local duration_ms=$(( ($(date +%s) - start_epoch) * 1000 ))
    _repair_log_outcome "deterministic" "$error_type" "$service" "$fingerprint" "$fix_type" "failure" "$duration_ms" "" "worktree creation failed"
    cb_record_failure "$error_type" "$service"
    return 1
  fi

  local outcome="failure"
  local verify_output=""

  # Apply fix with timeout
  (
    _repair_apply_fix "$wt_path" "$fix_type" "$fix_command" "$fix_diff"
  ) &
  local apply_pid=$!

  # Wait with timeout
  local waited=0
  while kill -0 "$apply_pid" 2>/dev/null; do
    sleep 1
    waited=$((waited + 1))
    if [ "$waited" -ge "$_REPAIR_TIMEOUT_DETERMINISTIC" ]; then
      kill -9 "$apply_pid" 2>/dev/null
      wait "$apply_pid" 2>/dev/null
      local duration_ms=$(( ($(date +%s) - start_epoch) * 1000 ))
      _repair_log_outcome "deterministic" "$error_type" "$service" "$fingerprint" "$fix_type" "timeout" "$duration_ms" "$wt_path" "repair timed out after ${_REPAIR_TIMEOUT_DETERMINISTIC}s"
      cb_record_failure "$error_type" "$service"
      remediation_record_failure "$fingerprint"
      repair_cleanup_worktree "$wt_path"
      return 1
    fi
  done

  wait "$apply_pid"
  local apply_rc=$?

  if [ "$apply_rc" -ne 0 ]; then
    local duration_ms=$(( ($(date +%s) - start_epoch) * 1000 ))
    _repair_log_outcome "deterministic" "$error_type" "$service" "$fingerprint" "$fix_type" "failure" "$duration_ms" "$wt_path" "fix application failed (exit $apply_rc)"
    cb_record_failure "$error_type" "$service"
    remediation_record_failure "$fingerprint"
    # Log failure details for learning
    local failure_detail="Fix command: $fix_command | Fix type: $fix_type | Exit code: $apply_rc"
    local outcomes_file
    outcomes_file=$(_repair_metrics_file)
    safe_jsonl_append "$outcomes_file" "$(jq -cn --arg d "$failure_detail" --arg fp "$fingerprint" '{failure_detail: $d, fingerprint: $fp}')"
    repair_cleanup_worktree "$wt_path"
    return 1
  fi

  # Verify
  _REPAIR_VERIFY_OUTPUT=""
  if repair_verify "$wt_path" "auto"; then
    verify_output="$_REPAIR_VERIFY_OUTPUT"
    outcome="success"

    # Merge changes back to the original branch
    if _repair_merge_back "$wt_path"; then
      # Record success in remediation registry (re-register to increment times_applied)
      local error_pattern
      error_pattern=$(echo "$fix_json" | jq -r '.error_pattern // ""')
      local root_cause
      root_cause=$(echo "$fix_json" | jq -r '.root_cause // "auto-repair"')
      if [ -n "$error_pattern" ]; then
        remediation_register "$error_type" "$service" "$error_pattern" "$root_cause" "$fix_type" "${fix_command:-$fix_diff}"
      fi
      cb_record_success "$error_type" "$service"
    else
      outcome="failure"
      verify_output="merge back failed"
      cb_record_failure "$error_type" "$service"
      remediation_record_failure "$fingerprint"
    fi
  else
    verify_output="$_REPAIR_VERIFY_OUTPUT"
    outcome="failure"
    cb_record_failure "$error_type" "$service"
    remediation_record_failure "$fingerprint"
    # Log failure details for learning
    local failure_detail="Fix command: $fix_command | Verification output: ${verify_output:0:200}"
    local outcomes_file
    outcomes_file=$(_repair_metrics_file)
    safe_jsonl_append "$outcomes_file" "$(jq -cn --arg d "$failure_detail" --arg fp "$fingerprint" '{failure_detail: $d, fingerprint: $fp}')"
  fi

  local duration_ms=$(( ($(date +%s) - start_epoch) * 1000 ))
  _repair_log_outcome "deterministic" "$error_type" "$service" "$fingerprint" "$fix_type" "$outcome" "$duration_ms" "$wt_path" "$verify_output"

  repair_cleanup_worktree "$wt_path"

  [ "$outcome" = "success" ] && return 0 || return 1
}

# ─── LLM repair (context preparation) ────────────────────────────────────

repair_execute_llm() {
  local error_context_json="$1"

  local start_epoch
  start_epoch=$(date +%s)

  local error_type service error_message file_context
  error_type=$(echo "$error_context_json" | jq -r '.error_type // "UNKNOWN"')
  service=$(echo "$error_context_json" | jq -r '.service // "unknown"')
  error_message=$(echo "$error_context_json" | jq -r '.error_message // ""')
  file_context=$(echo "$error_context_json" | jq -r '.file_context // ""')

  # Phase gate: only allow during reconstruction/stabilization
  local current_phase
  current_phase="${COGNITIVE_OS_PHASE:-stabilization}"
  case "$current_phase" in
    reconstruction|stabilization)
      # Allowed
      ;;
    *)
      echo "[execute-repair] LLM repair blocked — phase '$current_phase' not allowed (need reconstruction|stabilization)" >&2
      local duration_ms=$(( ($(date +%s) - start_epoch) * 1000 ))
      _repair_log_outcome "llm" "$error_type" "$service" "" "" "skipped" "$duration_ms" "" "phase gate: $current_phase"
      return 1
      ;;
  esac

  # Check circuit breaker
  if ! cb_check "$error_type" "$service"; then
    echo "[execute-repair] Circuit breaker OPEN for $error_type/$service — skipping LLM repair" >&2
    local duration_ms=$(( ($(date +%s) - start_epoch) * 1000 ))
    _repair_log_outcome "llm" "$error_type" "$service" "" "" "skipped" "$duration_ms" "" "circuit breaker open"
    return 1
  fi

  # Check global budget
  if ! cb_global_budget_ok; then
    echo "[execute-repair] Global hourly repair budget exhausted — skipping LLM repair" >&2
    local duration_ms=$(( ($(date +%s) - start_epoch) * 1000 ))
    _repair_log_outcome "llm" "$error_type" "$service" "" "" "skipped" "$duration_ms" "" "hourly budget exhausted"
    return 1
  fi

  # Check concurrent repairs
  if ! _repair_check_concurrent; then
    local duration_ms=$(( ($(date +%s) - start_epoch) * 1000 ))
    _repair_log_outcome "llm" "$error_type" "$service" "" "" "skipped" "$duration_ms" "" "concurrent repair limit"
    return 1
  fi

  # Create worktree
  local wt_path
  wt_path=$(_repair_create_worktree)
  if [ $? -ne 0 ] || [ -z "$wt_path" ]; then
    local duration_ms=$(( ($(date +%s) - start_epoch) * 1000 ))
    _repair_log_outcome "llm" "$error_type" "$service" "" "" "failure" "$duration_ms" "" "worktree creation failed"
    return 1
  fi

  # Write error context to temp file in worktree
  local context_file="$wt_path/.repair-context.json"
  echo "$error_context_json" | jq '.' > "$context_file" 2>/dev/null \
    || echo "$error_context_json" > "$context_file"

  # Write structured prompt for the dispatcher
  local wt_base
  wt_base=$(_repair_worktree_base)
  local pending_file="$wt_base/pending-repair.json"

  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  jq -cn \
    --arg ts "$now" \
    --arg et "$error_type" \
    --arg svc "$service" \
    --arg msg "$error_message" \
    --arg fc "$file_context" \
    --arg wt "$wt_path" \
    --arg ctx "$context_file" \
    --argjson timeout "$_REPAIR_TIMEOUT_LLM" \
    '{
      timestamp: $ts,
      error_type: $et,
      service: $svc,
      error_message: $msg,
      file_context: $fc,
      worktree_path: $wt,
      context_file: $ctx,
      timeout_seconds: $timeout,
      instructions: "Analyze the error in .repair-context.json. Fix the issue in this worktree. Run verification before committing."
    }' > "$pending_file"

  local duration_ms=$(( ($(date +%s) - start_epoch) * 1000 ))
  _repair_log_outcome "llm" "$error_type" "$service" "" "" "pending" "$duration_ms" "$wt_path" "context prepared for LLM dispatcher"

  # Return the worktree path for the dispatcher
  echo "$wt_path"
  return 0
}

# ─── Internal helpers ─────────────────────────────────────────────────────

_repair_apply_fix() {
  local wt_path="$1"
  local fix_type="$2"
  local fix_command="$3"
  local fix_diff="$4"

  cd "$wt_path" || return 1

  case "$fix_type" in
    command)
      if [ -z "$fix_command" ]; then
        echo "[execute-repair] ERROR: fix_type=command but no fix_command provided" >&2
        return 1
      fi
      eval "$fix_command" 2>&1
      return $?
      ;;

    config_change|code_change)
      if [ -z "$fix_diff" ]; then
        echo "[execute-repair] ERROR: fix_type=$fix_type but no fix_diff provided" >&2
        return 1
      fi
      # Base64 decode and apply as patch
      local decoded
      decoded=$(echo "$fix_diff" | base64 -d 2>/dev/null || echo "$fix_diff" | base64 --decode 2>/dev/null)
      if [ -z "$decoded" ]; then
        echo "[execute-repair] ERROR: Failed to base64-decode fix_diff" >&2
        return 1
      fi
      echo "$decoded" | git apply --check 2>&1 || {
        echo "[execute-repair] ERROR: Patch does not apply cleanly" >&2
        return 1
      }
      echo "$decoded" | git apply 2>&1
      return $?
      ;;

    *)
      echo "[execute-repair] ERROR: Unknown fix_type: $fix_type" >&2
      return 1
      ;;
  esac
}

_repair_execute_restart() {
  local service="$1"
  local error_type="$2"
  local fingerprint="$3"
  local start_epoch="$4"

  local outcome="failure"
  local verify_output=""

  if command -v docker >/dev/null 2>&1; then
    verify_output=$(docker compose restart "$service" 2>&1) && outcome="success"
  else
    verify_output="docker not available"
  fi

  local duration_ms=$(( ($(date +%s) - start_epoch) * 1000 ))

  if [ "$outcome" = "success" ]; then
    cb_record_success "$error_type" "$service"
  else
    cb_record_failure "$error_type" "$service"
    remediation_record_failure "$fingerprint"
  fi

  _repair_log_outcome "deterministic" "$error_type" "$service" "$fingerprint" "restart" "$outcome" "$duration_ms" "" "$verify_output"

  [ "$outcome" = "success" ] && return 0 || return 1
}

_repair_merge_back() {
  local wt_path="$1"

  local project_dir
  project_dir=$(_repair_project_dir)

  # Stage and commit changes in worktree
  cd "$wt_path" || return 1

  # Check if there are changes to commit
  if git diff --quiet && git diff --cached --quiet; then
    # No changes — nothing to merge
    return 0
  fi

  git add -A 2>/dev/null
  git commit -m "auto-repair: deterministic fix applied" 2>/dev/null || return 1

  # Get the commit hash
  local repair_commit
  repair_commit=$(git rev-parse HEAD 2>/dev/null)
  [ -z "$repair_commit" ] && return 1

  # Cherry-pick onto the original branch
  local original_branch
  original_branch=$(git -C "$project_dir" rev-parse --abbrev-ref HEAD 2>/dev/null)
  [ -z "$original_branch" ] && return 1

  cd "$project_dir" || return 1
  git cherry-pick "$repair_commit" 2>&1 || {
    # If cherry-pick fails, abort
    git cherry-pick --abort 2>/dev/null
    return 1
  }

  return 0
}
