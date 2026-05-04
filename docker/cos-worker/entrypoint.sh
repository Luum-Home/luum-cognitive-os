#!/usr/bin/env bash
# SCOPE: project
# ADR-140 container worker entrypoint.
set -euo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-/workspace}"
RUNTIME_DIR="${COGNITIVE_OS_RUNTIME_DIR:-${PROJECT_DIR}/.cognitive-os/runtime}"
AUDIT_TRAIL="${RUNTIME_DIR}/agent-audit-trail.jsonl"

mkdir -p "$RUNTIME_DIR"

json_string() {
  python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"
}

write_audit() {
  local event="$1"
  local detail="$2"
  printf '{"timestamp":"%s","event":%s,"detail":%s,"harness":%s,"project_dir":%s}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "$(json_string "$event")" \
    "$(json_string "$detail")" \
    "$(json_string "${COGNITIVE_OS_HARNESS:-barecli}")" \
    "$(json_string "$PROJECT_DIR")" \
    >> "$AUDIT_TRAIL"
}

run_hook_smoke() {
  local hook="${PROJECT_DIR}/hooks/git-commit-scope-guard.sh"
  if [ ! -x "$hook" ]; then
    write_audit "cos-worker-hook-smoke-skipped" "missing executable hook: hooks/git-commit-scope-guard.sh"
    return 0
  fi

  printf '{"tool_name":"Bash","tool_input":{"command":"echo cos-worker-smoke"}}\n' \
    | COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" \
      COGNITIVE_OS_SESSION_ID="${COGNITIVE_OS_SESSION_ID:-cos-worker}" \
      bash "$hook"
  write_audit "cos-worker-hook-smoke-passed" "git-commit-scope-guard.sh accepted harmless Bash command"
}

case "${1:-}" in
  --self-test)
    run_hook_smoke
    write_audit "cos-worker-self-test-passed" "container worker booted without shell profile assumptions"
    echo "cos-worker self-test passed; audit=${AUDIT_TRAIL}"
    ;;
  --print-env)
    printf 'COGNITIVE_OS_PROJECT_DIR=%s\n' "$PROJECT_DIR"
    printf 'COGNITIVE_OS_RUNTIME_DIR=%s\n' "$RUNTIME_DIR"
    printf 'COGNITIVE_OS_HARNESS=%s\n' "${COGNITIVE_OS_HARNESS:-barecli}"
    ;;
  "")
    run_hook_smoke
    ;;
  *)
    exec "$@"
    ;;
esac
