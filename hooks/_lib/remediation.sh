#!/usr/bin/env bash
# remediation.sh — Shared library for remediation registry operations
# Part of: auto-repair-system (ARS-1-03)
#
# Usage:
#   source "$(dirname "$0")/_lib/remediation.sh"
#
# Provides:
#   remediation_register <error_type> <service> <error_pattern> <root_cause> <fix_type> <fix_command_or_diff>
#   remediation_lookup <error_type> <service> <error_message>
#   remediation_record_failure <fingerprint>
#   remediation_gc
#
# Depends on: safe-jsonl.sh (sourced automatically if not already loaded)

# ─── Auto-source safe-jsonl.sh if not loaded ────────────────────────────────

if [ "${_SAFE_JSONL_LOADED:-}" != "true" ]; then
  _REMEDIATION_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  # shellcheck source=safe-jsonl.sh
  source "$_REMEDIATION_LIB_DIR/safe-jsonl.sh"
fi

# ─── Configuration ──────────────────────────────────────────────────────────

_REM_CONFIDENCE_THRESHOLD="${COGNITIVE_OS_REMEDIATION_CONFIDENCE:-0.8}"
_REM_DISABLE_THRESHOLD="${COGNITIVE_OS_REMEDIATION_DISABLE_RATE:-0.3}"
_REM_DISABLE_MIN_ATTEMPTS="${COGNITIVE_OS_REMEDIATION_DISABLE_MIN:-5}"
_REM_GC_STALE_DAYS="${COGNITIVE_OS_REMEDIATION_GC_DAYS:-30}"

# ─── Paths ──────────────────────────────────────────────────────────────────

_rem_project_dir() {
  echo "${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
}

_rem_registry_file() {
  local dir
  dir="$(_rem_project_dir)/.cognitive-os/metrics"
  mkdir -p "$dir" 2>/dev/null
  echo "$dir/remediation-registry.jsonl"
}

_rem_index_file() {
  local dir
  dir="$(_rem_project_dir)/.cognitive-os/metrics"
  mkdir -p "$dir" 2>/dev/null
  echo "$dir/remediation-index.json"
}

_rem_archive_file() {
  local dir
  dir="$(_rem_project_dir)/.cognitive-os/metrics"
  mkdir -p "$dir" 2>/dev/null
  echo "$dir/remediation-archive.jsonl"
}

# ─── Helpers ────────────────────────────────────────────────────────────────

_rem_fingerprint() {
  local text="$1"
  # Take first 200 chars, compute md5
  local truncated
  truncated=$(printf '%.200s' "$text")
  echo -n "$truncated" | md5 2>/dev/null || echo -n "$truncated" | md5sum 2>/dev/null | cut -d' ' -f1
}

_rem_uuid() {
  cat /proc/sys/kernel/random/uuid 2>/dev/null \
    || uuidgen 2>/dev/null \
    || echo "$(date +%s)-$$-$(od -An -N4 -tx4 /dev/urandom | tr -d ' ')"
}

_rem_now_iso() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}

_rem_init_index() {
  local index_file="$1"
  if [ ! -f "$index_file" ]; then
    local now
    now=$(_rem_now_iso)
    jq -c -n \
      --argjson version 1 \
      --arg ts "$now" \
      '{version: $version, entries: {}, stats: {total: 0, auto_applicable: 0, disabled: 0, last_updated: $ts}}' \
      > "$index_file.tmp" && mv "$index_file.tmp" "$index_file"
  fi
}

_rem_update_index() {
  # Atomically update the index file with a jq expression.
  # Usage: _rem_update_index <index_file> [jq_args...] <jq_filter>
  # The LAST argument is always the jq filter; everything between
  # index_file and the filter are --arg/--argjson pairs passed to jq.
  local index_file="$1"
  shift

  _rem_init_index "$index_file"

  # Collect all args: last one is the filter, rest are jq flags
  local args=("$@")
  local last_idx=$(( ${#args[@]} - 1 ))
  local jq_filter="${args[$last_idx]}"
  unset 'args[last_idx]'

  jq "${args[@]}" "$jq_filter" "$index_file" > "$index_file.tmp" && mv "$index_file.tmp" "$index_file"
}

_rem_count_lines() {
  local file="$1"
  [ ! -f "$file" ] && echo 0 && return
  wc -l < "$file" | tr -d ' '
}

# Replace a single line in a file (atomic write to .tmp then mv)
_rem_replace_line() {
  local file="$1"
  local line_num="$2"
  local new_content="$3"

  local total_lines
  total_lines=$(_rem_count_lines "$file")
  {
    if [ "$line_num" -gt 1 ]; then
      sed -n "1,$(( line_num - 1 ))p" "$file"
    fi
    echo "$new_content"
    if [ "$line_num" -lt "$total_lines" ]; then
      sed -n "$(( line_num + 1 )),\$p" "$file"
    fi
  } > "$file.tmp" && mv "$file.tmp" "$file"
}

# ─── remediation_register ──────────────────────────────────────────────────

remediation_register() {
  local error_type="$1"
  local service="$2"
  local error_pattern="$3"
  local root_cause="$4"
  local fix_type="$5"
  local fix_command_or_diff="$6"

  local registry_file index_file
  registry_file=$(_rem_registry_file)
  index_file=$(_rem_index_file)

  # Generate fingerprint from error_pattern (first 200 chars)
  local fingerprint
  fingerprint=$(_rem_fingerprint "$error_pattern")

  _rem_init_index "$index_file"

  # Check if fingerprint already exists in index
  local existing
  existing=$(jq -c --arg fp "$fingerprint" '.entries[$fp] // empty' "$index_file" 2>/dev/null)

  local now
  now=$(_rem_now_iso)

  if [ -n "$existing" ]; then
    # ── Update existing entry ──
    local line_num
    line_num=$(echo "$existing" | jq -r '.line')

    # Read existing entry from registry (one compact JSON line)
    local old_entry
    old_entry=$(sed -n "${line_num}p" "$registry_file" 2>/dev/null)
    if [ -z "$old_entry" ]; then
      echo "[remediation] WARNING: index references line $line_num but entry not found" >&2
      return 1
    fi

    # Update: increment times_applied, update last_applied, recalc success_rate
    local new_entry
    new_entry=$(echo "$old_entry" | jq -c \
      --arg now "$now" \
      '.times_applied += 1 |
       .last_applied = $now |
       .success_rate = ((.times_applied) / ((.times_applied) + .times_failed)) |
       .confidence = ((.times_applied) / ((.times_applied) + .times_failed))')

    # Replace line in registry
    _rem_replace_line "$registry_file" "$line_num" "$new_entry"

    # Update index entry
    local new_confidence
    new_confidence=$(echo "$new_entry" | jq -r '.confidence')
    local new_auto
    new_auto=$(echo "$new_entry" | jq -r '.auto_applicable')

    _rem_update_index "$index_file" \
      --arg fp "$fingerprint" \
      --argjson conf "$new_confidence" \
      --argjson auto "$new_auto" \
      --arg ts "$now" \
      '.entries[$fp].confidence = $conf |
       .entries[$fp].auto_applicable = $auto |
       .stats.last_updated = $ts'

  else
    # ── New entry ──
    local id
    id=$(_rem_uuid)
    local truncated_pattern
    truncated_pattern=$(printf '%.200s' "$error_pattern")

    # Determine fix_command vs fix_diff based on fix_type
    local fix_cmd_val="null"
    local fix_diff_val="null"
    if [ "$fix_type" = "code_change" ]; then
      # Base64 encode the diff
      local encoded
      encoded=$(echo -n "$fix_command_or_diff" | base64 2>/dev/null)
      fix_diff_val="\"$encoded\""
    else
      fix_cmd_val="\"$fix_command_or_diff\""
    fi

    # Build compact JSON entry (MUST be single line for JSONL)
    local entry
    entry=$(jq -cn \
      --arg id "$id" \
      --arg fp "$fingerprint" \
      --arg et "$error_type" \
      --arg svc "$service" \
      --arg ep "$truncated_pattern" \
      --arg rc "$root_cause" \
      --arg ft "$fix_type" \
      --argjson fc "$fix_cmd_val" \
      --argjson fd "$fix_diff_val" \
      --arg now "$now" \
      '{
        id: $id,
        fingerprint: $fp,
        error_type: $et,
        service: $svc,
        error_pattern: $ep,
        root_cause: $rc,
        fix_type: $ft,
        fix_command: $fc,
        fix_diff: $fd,
        success_rate: 1.0,
        times_applied: 1,
        times_failed: 0,
        auto_applicable: true,
        confidence: 1.0,
        created_at: $now,
        last_applied: $now,
        last_failed: null,
        phase_restriction: null
      }')

    # Append to registry via safe_jsonl_append
    safe_jsonl_append "$registry_file" "$entry"

    # Calculate new line number (line count after append)
    local new_line
    new_line=$(_rem_count_lines "$registry_file")

    # Update index
    _rem_update_index "$index_file" \
      --arg fp "$fingerprint" \
      --argjson ln "$new_line" \
      --arg et "$error_type" \
      --arg svc "$service" \
      --arg ts "$now" \
      '.entries[$fp] = {line: $ln, error_type: $et, service: $svc, confidence: 1.0, auto_applicable: true} |
       .stats.total += 1 |
       .stats.auto_applicable += 1 |
       .stats.last_updated = $ts'
  fi
}

# ─── remediation_lookup ────────────────────────────────────────────────────

remediation_lookup() {
  local error_type="$1"
  local service="$2"
  local error_message="$3"

  local index_file registry_file
  index_file=$(_rem_index_file)
  registry_file=$(_rem_registry_file)

  # No index = no known fixes
  [ ! -f "$index_file" ] && return 1

  # Generate fingerprint
  local fingerprint
  fingerprint=$(_rem_fingerprint "$error_message")

  # Look up in index (exact match)
  local index_entry
  index_entry=$(jq -c --arg fp "$fingerprint" '.entries[$fp] // empty' "$index_file" 2>/dev/null)

  if [ -z "$index_entry" ]; then
    # Exact fingerprint miss — try fuzzy/semantic match
    if type semantic_lookup >/dev/null 2>&1 || source "$(dirname "${BASH_SOURCE[0]}")/semantic-search.sh" 2>/dev/null; then
      local semantic_result
      semantic_result=$(semantic_lookup "$error_message" 2>/dev/null)
      if [ $? -eq 0 ] && [ -n "$semantic_result" ]; then
        echo "$semantic_result"
        return 0
      fi
    fi
    return 1
  fi

  # Check auto_applicable
  local auto_applicable
  auto_applicable=$(echo "$index_entry" | jq -r '.auto_applicable')
  [ "$auto_applicable" != "true" ] && return 1

  # Check confidence threshold
  local confidence
  confidence=$(echo "$index_entry" | jq -r '.confidence')
  local meets_threshold
  meets_threshold=$(echo "$confidence >= $_REM_CONFIDENCE_THRESHOLD" | bc -l 2>/dev/null || echo 0)
  [ "$meets_threshold" != "1" ] && return 1

  # Read full entry from registry (single compact JSON line)
  local line_num
  line_num=$(echo "$index_entry" | jq -r '.line')
  local full_entry
  full_entry=$(sed -n "${line_num}p" "$registry_file" 2>/dev/null)

  [ -z "$full_entry" ] && return 1

  # Output the fix as JSON
  echo "$full_entry" | jq -c '{
    fix_type: .fix_type,
    fix_command: .fix_command,
    fix_diff: .fix_diff,
    confidence: .confidence,
    times_applied: .times_applied,
    fingerprint: .fingerprint
  }'

  return 0
}

# ─── remediation_record_failure ─────────────────────────────────────────────

remediation_record_failure() {
  local fingerprint="$1"

  local index_file registry_file
  index_file=$(_rem_index_file)
  registry_file=$(_rem_registry_file)

  [ ! -f "$index_file" ] && return 1

  # Look up line number from index
  local index_entry
  index_entry=$(jq -c --arg fp "$fingerprint" '.entries[$fp] // empty' "$index_file" 2>/dev/null)
  [ -z "$index_entry" ] && return 1

  local line_num
  line_num=$(echo "$index_entry" | jq -r '.line')

  # Read existing entry
  local old_entry
  old_entry=$(sed -n "${line_num}p" "$registry_file" 2>/dev/null)
  [ -z "$old_entry" ] && return 1

  local now
  now=$(_rem_now_iso)

  # Update: increment times_failed, recalculate success_rate
  local new_entry
  new_entry=$(echo "$old_entry" | jq -c \
    --arg now "$now" \
    '.times_failed += 1 |
     .last_failed = $now |
     .success_rate = (.times_applied / (.times_applied + .times_failed)) |
     .confidence = (.times_applied / (.times_applied + .times_failed))')

  # Check if we should disable auto_applicable
  local total_attempts new_rate
  total_attempts=$(echo "$new_entry" | jq '.times_applied + .times_failed')
  new_rate=$(echo "$new_entry" | jq -r '.success_rate')

  local should_disable
  should_disable=$(echo "$total_attempts >= $_REM_DISABLE_MIN_ATTEMPTS" | bc -l 2>/dev/null || echo 0)
  local rate_too_low
  rate_too_low=$(echo "$new_rate < $_REM_DISABLE_THRESHOLD" | bc -l 2>/dev/null || echo 0)

  if [ "$should_disable" = "1" ] && [ "$rate_too_low" = "1" ]; then
    new_entry=$(echo "$new_entry" | jq -c '.auto_applicable = false')
  fi

  # Replace line in registry
  _rem_replace_line "$registry_file" "$line_num" "$new_entry"

  # Update index
  local new_confidence
  new_confidence=$(echo "$new_entry" | jq -r '.confidence')
  local new_auto
  new_auto=$(echo "$new_entry" | jq -r '.auto_applicable')

  local index_update_filter
  index_update_filter='.entries[$fp].confidence = ($conf | tonumber) | .entries[$fp].auto_applicable = ($auto | test("true")) | .stats.last_updated = $ts'

  # If auto_applicable changed to false, update disabled count
  if [ "$new_auto" = "false" ]; then
    index_update_filter="$index_update_filter | .stats.auto_applicable -= 1 | .stats.disabled += 1"
  fi

  _rem_update_index "$index_file" \
    --arg fp "$fingerprint" \
    --arg conf "$new_confidence" \
    --arg auto "$new_auto" \
    --arg ts "$now" \
    "$index_update_filter"
}

# ─── remediation_gc ─────────────────────────────────────────────────────────

remediation_gc() {
  local registry_file index_file archive_file
  registry_file=$(_rem_registry_file)
  index_file=$(_rem_index_file)
  archive_file=$(_rem_archive_file)

  [ ! -f "$registry_file" ] && echo "No registry to GC" && return 0

  _rem_init_index "$index_file"

  local now_epoch
  now_epoch=$(date +%s)
  local stale_seconds=$(( _REM_GC_STALE_DAYS * 86400 ))

  local archived=0
  local kept_lines=""
  local new_line=0
  local new_entries="{}"
  local total=0
  local auto_count=0
  local disabled_count=0

  # Read each line from registry (each line is compact JSON)
  while IFS= read -r line; do
    [ -z "$line" ] && continue

    local auto_applicable last_applied_str
    auto_applicable=$(echo "$line" | jq -r '.auto_applicable // true')
    last_applied_str=$(echo "$line" | jq -r '.last_applied // .created_at')

    # Convert last_applied to epoch for comparison
    local last_epoch
    last_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$last_applied_str" +%s 2>/dev/null \
      || date -d "$last_applied_str" +%s 2>/dev/null \
      || echo "$now_epoch")

    local age=$(( now_epoch - last_epoch ))

    if [ "$auto_applicable" = "false" ] && [ "$age" -ge "$stale_seconds" ]; then
      # Archive this entry
      safe_jsonl_append "$archive_file" "$line"
      archived=$((archived + 1))
    else
      # Keep this entry
      new_line=$((new_line + 1))
      total=$((total + 1))

      if [ -n "$kept_lines" ]; then
        kept_lines="$kept_lines
$line"
      else
        kept_lines="$line"
      fi

      # Rebuild index entry for this line
      local fp et svc conf auto
      fp=$(echo "$line" | jq -r '.fingerprint')
      et=$(echo "$line" | jq -r '.error_type')
      svc=$(echo "$line" | jq -r '.service')
      conf=$(echo "$line" | jq -r '.confidence')
      auto=$(echo "$line" | jq -r '.auto_applicable')

      new_entries=$(echo "$new_entries" | jq -c \
        --arg fp "$fp" \
        --argjson ln "$new_line" \
        --arg et "$et" \
        --arg svc "$svc" \
        --arg conf "$conf" \
        --arg auto "$auto" \
        '.[$fp] = {line: $ln, error_type: $et, service: $svc, confidence: ($conf | tonumber), auto_applicable: ($auto | test("true"))}')

      if [ "$auto" = "true" ]; then
        auto_count=$((auto_count + 1))
      else
        disabled_count=$((disabled_count + 1))
      fi
    fi
  done < "$registry_file"

  # Write kept lines to registry (atomic)
  if [ -n "$kept_lines" ]; then
    echo "$kept_lines" > "$registry_file.tmp" && mv "$registry_file.tmp" "$registry_file"
  else
    > "$registry_file.tmp" && mv "$registry_file.tmp" "$registry_file"
  fi

  # Rebuild index (atomic)
  local now
  now=$(_rem_now_iso)
  jq -c -n \
    --argjson version 1 \
    --argjson entries "$new_entries" \
    --argjson total "$total" \
    --argjson auto "$auto_count" \
    --argjson disabled "$disabled_count" \
    --arg ts "$now" \
    '{version: $version, entries: $entries, stats: {total: $total, auto_applicable: $auto, disabled: $disabled, last_updated: $ts}}' \
    > "$index_file.tmp" && mv "$index_file.tmp" "$index_file"

  echo "[remediation-gc] Archived $archived entries, kept $total"
}
