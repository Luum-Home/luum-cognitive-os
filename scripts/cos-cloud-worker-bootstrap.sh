#!/usr/bin/env bash
# SCOPE: os-only
# @manual-trigger: launch the ADR-140 COS worker Compose surface
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$ROOT/docker/cos-worker/docker-compose.yml"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/cos-cloud-worker-bootstrap.sh config       validate compose file
  bash scripts/cos-cloud-worker-bootstrap.sh self-test    build + smoke test
  bash scripts/cos-cloud-worker-bootstrap.sh up           start cos-worker only
  bash scripts/cos-cloud-worker-bootstrap.sh up-full      start full stack (incl. engram-cloud)
  bash scripts/cos-cloud-worker-bootstrap.sh down         stop everything
  bash scripts/cos-cloud-worker-bootstrap.sh path         print compose file path

Environment:
  COS_WORKSPACE              Workspace bind mount. Defaults to repo root.
  COGNITIVE_OS_SESSION_ID    Session id exposed inside the worker.
  LLM_PRIMARY_API_KEY        Optional BYOK primary provider key.
  LLM_FALLBACK_API_KEY       Optional BYOK fallback provider key.

Operator runbook: docs/05-Methodology/runbooks/run-cos-in-docker.md

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
  up-full)
    # Full stack including engram-cloud profile (ADR-141 replication surface).
    # See docs/05-Methodology/runbooks/run-cos-in-docker.md for the operator walkthrough.
    COS_WORKSPACE="${COS_WORKSPACE:-$ROOT}" \
      docker compose -f "$COMPOSE_FILE" --profile engram-cloud up --build -d
    ;;
  down)
    # Stop both default-profile and engram-cloud-profile services so callers do
    # not have to know which subset of services was started by which subcommand.
    COS_WORKSPACE="${COS_WORKSPACE:-$ROOT}" \
      docker compose -f "$COMPOSE_FILE" --profile engram-cloud down
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
