#!/usr/bin/env bash
# SCOPE: both
# Shared artifact status loaders for governance hooks.
#
# Contract:
# - Caller defines PROJECT_DIR before invoking these functions.
# - Caller initializes TEST_ARTIFACT_* and COVERAGE_ARTIFACT_* globals when it
#   needs to distinguish unset from missing.
# - Functions cache JSON/status/run variables and return success only when the
#   persisted artifact status is not "missing".

_load_test_artifact_status() {
  [ -n "${TEST_ARTIFACT_JSON:-}" ] && return 0
  local helper="$PROJECT_DIR/scripts/cos_test_artifact_status.py"
  [ -f "$helper" ] || return 1
  TEST_ARTIFACT_JSON=$(python3 "$helper" --project-root "$PROJECT_DIR" --json 2>/dev/null || true)
  [ -n "$TEST_ARTIFACT_JSON" ] || return 1
  TEST_ARTIFACT_STATUS=$(echo "$TEST_ARTIFACT_JSON" | jq -r '.status // "missing"' 2>/dev/null)
  TEST_ARTIFACT_RUN=$(echo "$TEST_ARTIFACT_JSON" | jq -r '.run_dir // ""' 2>/dev/null)
  [ "$TEST_ARTIFACT_STATUS" != "missing" ]
}

_load_coverage_artifact_status() {
  [ -n "${COVERAGE_ARTIFACT_JSON:-}" ] && return 0
  local helper="$PROJECT_DIR/scripts/cos_test_artifact_status.py"
  [ -f "$helper" ] || return 1
  COVERAGE_ARTIFACT_JSON=$(python3 "$helper" --project-root "$PROJECT_DIR" --artifact-kind coverage --coverage-threshold 80 --json 2>/dev/null || true)
  [ -n "$COVERAGE_ARTIFACT_JSON" ] || return 1
  COVERAGE_ARTIFACT_STATUS=$(echo "$COVERAGE_ARTIFACT_JSON" | jq -r '.status // "missing"' 2>/dev/null)
  COVERAGE_ARTIFACT_RUN=$(echo "$COVERAGE_ARTIFACT_JSON" | jq -r '.run_dir // ""' 2>/dev/null)
  [ "$COVERAGE_ARTIFACT_STATUS" != "missing" ]
}
