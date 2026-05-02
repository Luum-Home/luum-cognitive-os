#!/usr/bin/env bash
# SCOPE: both
# verify-archived.sh — Bilateral archive verification tool.
#
# Verifies that files declared as "archived" are truly archived:
#   1. Archive copy is PRESENT in --archive-dir
#   2. Original is ABSENT from --source-dir (it was removed)
#   3. No stale config references remain (if --config-globs provided)
#
# Designed to catch the "archive-presence fallacy" (ADR-105): an agent copies
# a file to the archive dir but forgets to remove the original, then declares
# the task "archived". This script detects that trap.
#
# Part of: red-team-harness Wave W0
# Usage:
#   verify-archived.sh \
#     --archive-dir <path> \
#     --source-dir <path> \
#     --manifest <comma-list | @file> \
#     [--config-globs <glob1,glob2,...>] \
#     [--quiet] \
#     [--json]
#
# Exit codes:
#   0 — all manifest entries pass bilateral check
#   1 — at least one entry: source still present
#   2 — at least one entry: archive missing
#   3 — at least one entry: stale config reference found
#   4 — invalid arguments / missing required flags
set -uo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
ARCHIVE_DIR=""
SOURCE_DIR=""
MANIFEST_ARG=""
CONFIG_GLOBS=""
QUIET=false
JSON_MODE=false

# ── Argument parsing ──────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
  case "$1" in
    --archive-dir)
      ARCHIVE_DIR="$2"; shift 2 ;;
    --archive-dir=*)
      ARCHIVE_DIR="${1#--archive-dir=}"; shift ;;
    --source-dir)
      SOURCE_DIR="$2"; shift 2 ;;
    --source-dir=*)
      SOURCE_DIR="${1#--source-dir=}"; shift ;;
    --manifest)
      MANIFEST_ARG="$2"; shift 2 ;;
    --manifest=*)
      MANIFEST_ARG="${1#--manifest=}"; shift ;;
    --config-globs)
      CONFIG_GLOBS="$2"; shift 2 ;;
    --config-globs=*)
      CONFIG_GLOBS="${1#--config-globs=}"; shift ;;
    --quiet)
      QUIET=true; shift ;;
    --json)
      JSON_MODE=true; shift ;;
    -h|--help)
      grep '^#' "$0" | grep -v '^#!/' | sed 's/^# \?//'
      exit 0 ;;
    *)
      echo "ERROR: Unknown argument '$1'" >&2
      exit 4 ;;
  esac
done

# ── Validate required flags ───────────────────────────────────────────────────
if [ -z "$ARCHIVE_DIR" ] || [ -z "$SOURCE_DIR" ] || [ -z "$MANIFEST_ARG" ]; then
  echo "ERROR: --archive-dir, --source-dir, and --manifest are required." >&2
  echo "Usage: verify-archived.sh --archive-dir <path> --source-dir <path> --manifest <list>" >&2
  exit 4
fi

# ── Resolve manifest entries ──────────────────────────────────────────────────
declare -a MANIFEST_FILES=()
if [[ "$MANIFEST_ARG" == @* ]]; then
  # Read from file, one entry per line
  manifest_file="${MANIFEST_ARG:1}"
  if [ ! -f "$manifest_file" ]; then
    echo "ERROR: Manifest file not found: $manifest_file" >&2
    exit 4
  fi
  while IFS= read -r line; do
    line="${line%%#*}"        # strip comments
    line="${line// /}"        # strip spaces
    [ -n "$line" ] && MANIFEST_FILES+=("$line")
  done < "$manifest_file"
else
  # Comma-separated list
  IFS=',' read -ra MANIFEST_FILES <<< "$MANIFEST_ARG"
fi

if [ ${#MANIFEST_FILES[@]} -eq 0 ]; then
  echo "ERROR: Manifest is empty." >&2
  exit 4
fi

# ── Resolve config globs list ─────────────────────────────────────────────────
declare -a CONFIG_GLOB_LIST=()
if [ -n "$CONFIG_GLOBS" ]; then
  IFS=',' read -ra CONFIG_GLOB_LIST <<< "$CONFIG_GLOBS"
fi

# ── Per-entry verification ────────────────────────────────────────────────────
# Track worst exit code per category (priority: 1 > 2 > 3, then 0)
HAS_SOURCE_PRESENT=false
HAS_ARCHIVE_MISSING=false
HAS_CONFIG_REF=false

# JSON accumulator
JSON_RESULTS=""

for entry in "${MANIFEST_FILES[@]}"; do
  # Normalize: strip leading slashes (entries should be relative filenames)
  name="${entry##*/}"      # basename — manifest entries are filenames, not paths
  [ -z "$name" ] && continue

  archive_path="$ARCHIVE_DIR/$name"
  source_path="$SOURCE_DIR/$name"

  # Check 1: archive present?
  if [ -f "$archive_path" ]; then
    archive_present=true
    archive_status="present"
  else
    archive_present=false
    archive_status="missing"
    HAS_ARCHIVE_MISSING=true
  fi

  # Check 2: source absent?
  if [ -f "$source_path" ]; then
    source_absent=false
    source_status="present"
    HAS_SOURCE_PRESENT=true
  else
    source_absent=true
    source_status="absent"
  fi

  # Check 3: stale config references?
  declare -a stale_refs=()
  if [ ${#CONFIG_GLOB_LIST[@]} -gt 0 ]; then
    for glob_pattern in "${CONFIG_GLOB_LIST[@]}"; do
      # Expand glob relative to current dir (caller's responsibility to set cwd)
      while IFS= read -r -d '' cfg_file; do
        if [ -f "$cfg_file" ] && grep -qF "$name" "$cfg_file" 2>/dev/null; then
          stale_refs+=("$cfg_file")
          HAS_CONFIG_REF=true
        fi
      done < <(find . -path "./$glob_pattern" -print0 2>/dev/null)
    done
  fi
  ref_count=${#stale_refs[@]}

  # Determine per-entry status
  if $archive_present && $source_absent && [ $ref_count -eq 0 ]; then
    entry_status="OK"
  else
    entry_status="FAIL"
  fi

  # ── Text output ──────────────────────────────────────────────────────────
  if [ "$JSON_MODE" = false ] && [ "$QUIET" = false ]; then
    if [ $ref_count -gt 0 ]; then
      ref_detail="refs: $ref_count (${stale_refs[*]})"
    else
      ref_detail="refs: 0"
    fi
    printf "%-8s %-40s archive: %-8s | source: %-8s | %s\n" \
      "[$entry_status]" "$name" "$archive_status" "$source_status" "$ref_detail"
  fi

  # ── JSON accumulation ────────────────────────────────────────────────────
  if [ "$JSON_MODE" = true ]; then
    # Build refs JSON array
    if [ $ref_count -gt 0 ]; then
      refs_json=""
      for ref in "${stale_refs[@]}"; do
        [ -n "$refs_json" ] && refs_json="$refs_json,"
        refs_json="$refs_json\"$ref\""
      done
      refs_json="[$refs_json]"
    else
      refs_json="[]"
    fi

    item="{\"name\":\"$name\",\"archive_present\":$archive_present,\"source_absent\":$source_absent,\"config_refs\":$refs_json}"
    [ -n "$JSON_RESULTS" ] && JSON_RESULTS="$JSON_RESULTS,"
    JSON_RESULTS="$JSON_RESULTS$item"
  fi
done

# ── Determine overall result and exit code ────────────────────────────────────
if $HAS_SOURCE_PRESENT || $HAS_ARCHIVE_MISSING || $HAS_CONFIG_REF; then
  overall_verified=false
else
  overall_verified=true
fi

# ── JSON output (printed after all entries processed) ────────────────────────
if [ "$JSON_MODE" = true ]; then
  printf '{\n  "verified": %s,\n  "results": [%s]\n}\n' \
    "$overall_verified" "$JSON_RESULTS"
fi

# ── Exit with most-specific code ─────────────────────────────────────────────
# Priority: source-present (1) wins over archive-missing (2) wins over config-ref (3)
if $HAS_SOURCE_PRESENT; then
  exit 1
elif $HAS_ARCHIVE_MISSING; then
  exit 2
elif $HAS_CONFIG_REF; then
  exit 3
fi
exit 0
