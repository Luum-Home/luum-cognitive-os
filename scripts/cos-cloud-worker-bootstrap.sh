#!/usr/bin/env bash
# SCOPE: project
# @manual-trigger: launch the ADR-140 COS worker Compose surface
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$ROOT/docker/cos-worker/docker-compose.yml"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/cos-cloud-worker-bootstrap.sh config
  bash scripts/cos-cloud-worker-bootstrap.sh self-test
  bash scripts/cos-cloud-worker-bootstrap.sh up
  bash scripts/cos-cloud-worker-bootstrap.sh down
  bash scripts/cos-cloud-worker-bootstrap.sh path

Environment:
  COS_WORKSPACE              Workspace bind mount. Defaults to repo root.
  COGNITIVE_OS_SESSION_ID    Session id exposed inside the worker.
  LLM_PRIMARY_API_KEY        Optional BYOK primary provider key.
  LLM_FALLBACK_API_KEY       Optional BYOK fallback provider key.

This wrapper is intentionally thin: ADR-140 keeps the container worker surface
as Docker Compose configuration instead of shell-profile bootstrap magic.
EOF
}

compose() {
  COS_WORKSPACE="${COS_WORKSPACE:-$ROOT}" docker compose -f "$COMPOSE_FILE" "$@"
}

case "${1:-}" in
  config)
    compose config
    ;;
  self-test)
    compose build cos-worker
    compose run --rm cos-worker --self-test
    ;;
  up)
    compose up --build cos-worker
    ;;
  down)
    compose down
    ;;
  path)
    printf '%s\n' "$COMPOSE_FILE"
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    echo "unknown command: $1" >&2
    usage >&2
    exit 2
    ;;
esac
