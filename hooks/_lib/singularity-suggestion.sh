#!/usr/bin/env bash
# _singularity_suggestion — Advisory singularity run suggestion.
# Sourced by session-init.sh; also sourced directly by tests.
# Pure bash, no Python calls, always exits 0.

# SCOPE: cognitive-os/session

_singularity_suggestion() {
  local metrics_dir="$PROJECT_DIR/.cognitive-os/metrics"
  local events_file="$metrics_dir/singularity-events.jsonl"
  local errors_file="$metrics_dir/error-learning.jsonl"
  local stale_file="$metrics_dir/stale-docs.jsonl"

  # Collect signals
  # bash-specific: arrays require bash (#!/usr/bin/env bash)
  local signals=()
  local never_ran=false

  # Signal 1: Singularity has never been run
  if [ ! -f "$events_file" ]; then
    never_ran=true
  fi

  # Signal 2: 3+ errors in last 24 hours (check line count as a proxy — cheap)
  if [ -f "$errors_file" ]; then
    local cutoff
    cutoff=$(( $(date +%s) - 86400 ))
    # POSIX awk: extract timestamp_epoch value and compare (no gawk capture groups)
    local recent_errors
    recent_errors=$(awk -v cutoff="$cutoff" '
      /timestamp_epoch/ {
        n = split($0, parts, /timestamp_epoch":[[:space:]]*/);
        if (n >= 2) {
          val = parts[2] + 0;
          if (val >= cutoff) print;
        }
      }
    ' "$errors_file" 2>/dev/null | wc -l | tr -d ' ')
    if [ "${recent_errors:-0}" -ge 3 ]; then
      signals+=("${recent_errors} errors in last 24h")
    fi
  fi

  # Signal 3: stale docs pending
  if [ -f "$stale_file" ] && [ -s "$stale_file" ]; then
    local stale_count
    stale_count=$(wc -l < "$stale_file" | tr -d ' ')
    signals+=("${stale_count} stale doc(s) pending")
  fi

  # No signals and already ran — nothing to say
  if [ "$never_ran" = false ] && [ "${#signals[@]}" -eq 0 ]; then
    return 0
  fi

  # Check for user opt-out (config flag or sentinel file)
  local config_file="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
  if grep -q 'singularity_suggestion:[[:space:]]*false' "$config_file" 2>/dev/null; then
    return 0
  fi
  if [ -f "$PROJECT_DIR/.cognitive-os/.singularity-suggestion-dismissed" ]; then
    return 0
  fi

  # Emit suggestion block to stderr
  {
    echo ""
    echo "=== SINGULARITY SUGGESTION ==="
    if [ "$never_ran" = true ]; then
      echo "Singularity has never been run in this project."
    else
      # Build comma-space separated string without relying on IFS join semantics
      local signal_str=""
      for s in "${signals[@]}"; do
        [[ -n "$signal_str" ]] && signal_str="$signal_str, $s" || signal_str="$s"
      done
      echo "Detected: $signal_str"
      echo "Consider activating Singularity for autonomous monitoring."
    fi
    echo "Try: SINGULARITY_ENABLED=true python3 lib/singularity.py dry-run"
    echo "=== END SINGULARITY ==="
    echo ""
  } >&2
}
