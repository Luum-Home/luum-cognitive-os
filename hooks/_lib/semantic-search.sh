#!/usr/bin/env bash
# SCOPE: both
# semantic-search.sh — Fuzzy error matching via vector similarity
# Falls back to exact fingerprint if zvec not available

# Check if semantic search is available
_semantic_search_available() {
  command -v node >/dev/null 2>&1 && [ -f "$(dirname "${BASH_SOURCE[0]}")/../../scripts/semantic-lookup.mjs" ]
}

# Search for similar errors in the remediation registry
# Returns: JSON with match details, or empty string if no match
semantic_lookup() {
  local error_message="$1"
  local threshold="${2:-0.75}"  # similarity threshold (0-1)

  local project_dir="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local registry="$project_dir/.cognitive-os/metrics/remediation-registry.jsonl"

  [ ! -f "$registry" ] && return 1

  if _semantic_search_available; then
    # Use zvec for semantic similarity
    node "$(dirname "${BASH_SOURCE[0]}")/../../scripts/semantic-lookup.mjs" \
      --registry "$registry" \
      --query "$error_message" \
      --threshold "$threshold" \
      2>/dev/null
    return $?
  else
    # Fallback: substring matching (cheap but less accurate)
    _fuzzy_substring_match "$error_message" "$registry"
    return $?
  fi
}

# Fallback: simple substring/keyword matching
_fuzzy_substring_match() {
  local query="$1"
  local registry="$2"

  # Extract key terms from error (remove noise words)
  local keywords
  keywords=$(echo "$query" | tr -cs '[:alnum:]' '\n' | sort -u | grep -v -E '^(the|a|an|in|at|on|for|to|of|is|was|not|and|or)$' | head -10 | tr '\n' '|')
  keywords="${keywords%|}"

  [ -z "$keywords" ] && return 1

  # Find registry entries matching the most keywords
  local best_match=""
  local best_score=0

  while IFS= read -r line; do
    local pattern
    pattern=$(echo "$line" | jq -r '.error_pattern // ""' 2>/dev/null)
    [ -z "$pattern" ] && continue

    # Check auto_applicable
    local auto
    auto=$(echo "$line" | jq -r '.auto_applicable // false' 2>/dev/null)
    [ "$auto" != "true" ] && continue

    # Count keyword matches
    local matches=0
    local total=0
    while IFS= read -r kw; do
      [ -z "$kw" ] && continue
      total=$((total + 1))
      echo "$pattern" | grep -qi "$kw" && matches=$((matches + 1))
    done <<< "$(echo "$keywords" | tr '|' '\n')"

    # Simple Jaccard-like score
    if [ "$total" -gt 0 ]; then
      local score=$((matches * 100 / total))
      if [ "$score" -gt "$best_score" ] && [ "$score" -ge 30 ]; then
        best_score=$score
        best_match="$line"
      fi
    fi
  done < "$registry"

  if [ -n "$best_match" ]; then
    echo "$best_match" | jq -c '{fix_type: .fix_type, fix_command: .fix_command, fix_diff: .fix_diff, confidence: .confidence, times_applied: .times_applied, fingerprint: .fingerprint, match_type: "fuzzy"}'
    return 0
  fi

  return 1
}
