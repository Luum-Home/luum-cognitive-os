#!/usr/bin/env bash
# Integration test for cos-adoption-unfreeze (ADR-270 #6).
# Verifies the pre-flight gate FAILS when evidence is missing (no patent report).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# Without USPTO reports for a fake tool, the gate must fail with non-zero exit
# and print a "FAIL" line for the patent-report check.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
EVIDENCE="$TMP/fake-evidence.zip"
printf 'dummy' > "$EVIDENCE"

set +e
OUTPUT="$(python3 scripts/cos-adoption-unfreeze \
  --tool nonexistent-tool-xyz \
  --evidence-bundle "$EVIDENCE" \
  --operator test-operator \
  --reason "integration test" 2>&1)"
RC=$?
set -e

if [ "$RC" -eq 0 ]; then
  echo "FAIL: unfreeze should have been blocked but returned 0" >&2
  echo "$OUTPUT" >&2
  exit 1
fi

if ! printf '%s' "$OUTPUT" | grep -q "patent-report"; then
  echo "FAIL: expected patent-report gate failure in output" >&2
  echo "$OUTPUT" >&2
  exit 1
fi

if ! printf '%s' "$OUTPUT" | grep -q "Unfreeze BLOCKED"; then
  echo "FAIL: expected 'Unfreeze BLOCKED' marker" >&2
  echo "$OUTPUT" >&2
  exit 1
fi

echo "PASS: cos-adoption-unfreeze gate correctly blocks missing evidence"
