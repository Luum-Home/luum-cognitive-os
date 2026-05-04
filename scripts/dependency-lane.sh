#!/usr/bin/env bash
# SCOPE: project
# @manual-trigger: manage optional heavy dependency lanes after ADR-145
# dependency-lane.sh — list, inspect, and install optional heavy dependency lanes
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LANE_DIR="$ROOT/requirements/dependency-lanes"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/dependency-lane.sh list
  bash scripts/dependency-lane.sh path <lane>
  bash scripts/dependency-lane.sh show <lane>
  bash scripts/dependency-lane.sh install <lane>

Optional heavy dependency lanes live outside pyproject.toml extras so they do
not block the core maintainer lock. Install only the lane you are validating.
EOF
}

require_lane_dir() {
  if [ ! -d "$LANE_DIR" ]; then
    echo "dependency-lane: missing lane directory: $LANE_DIR" >&2
    exit 1
  fi
}

lane_path() {
  local lane="$1"
  case "$lane" in
    ""|*/*|*..*)
      echo "dependency-lane: invalid lane name: $lane" >&2
      exit 1
      ;;
  esac
  local path="$LANE_DIR/$lane.txt"
  if [ ! -f "$path" ]; then
    echo "dependency-lane: unknown lane: $lane" >&2
    echo "Available lanes:" >&2
    list_lanes >&2
    exit 1
  fi
  printf '%s\n' "$path"
}

list_lanes() {
  require_lane_dir
  find "$LANE_DIR" -maxdepth 1 -type f -name '*.txt' -print \
    | sed 's|.*/||; s|\.txt$||' \
    | sort
}

cmd="${1:-}"
case "$cmd" in
  list)
    list_lanes
    ;;
  path)
    [ $# -eq 2 ] || { usage >&2; exit 1; }
    lane_path "$2"
    ;;
  show)
    [ $# -eq 2 ] || { usage >&2; exit 1; }
    cat "$(lane_path "$2")"
    ;;
  install)
    [ $# -eq 2 ] || { usage >&2; exit 1; }
    req="$(lane_path "$2")"
    if ! command -v uv >/dev/null 2>&1; then
      echo "dependency-lane: uv not found in PATH" >&2
      exit 1
    fi
    echo "Installing dependency lane '$2' from $req"
    uv pip install -r "$req"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
