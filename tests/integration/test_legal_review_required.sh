#!/usr/bin/env bash
# Integration test for hooks/legal-review-required-on-runtime-import.sh (ADR-270 #8).
# Verifies:
#   1. Hook is syntactically valid.
#   2. Hook short-circuits on non-`git commit` commands.
#   3. Hook short-circuits on bypass env var.
#   4. Hook is registered in .claude/settings.json.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

HOOK="hooks/legal-review-required-on-runtime-import.sh"

# 1. Syntax
bash -n "$HOOK"

# 2. Non git-commit short-circuit: hook should exit 0 on `git status`.
echo '{"tool_name":"Bash","tool_input":{"command":"git status"}}' | bash "$HOOK"

# 3. Bypass env var skips even on git commit.
echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}' | \
  COS_ALLOW_PRE_LEGAL_REVIEW_IMPORT=1 bash "$HOOK"

# 4. Registered in settings.json
if ! grep -q "legal-review-required-on-runtime-import" .claude/settings.json; then
  echo "FAIL: hook not registered in .claude/settings.json" >&2
  exit 1
fi

# 5. Classification entry exists
if ! grep -q "legal-review-required-on-runtime-import.sh" manifests/hook-registration-classification.yaml; then
  echo "FAIL: hook not classified in hook-registration-classification.yaml" >&2
  exit 1
fi

echo "PASS: legal-review-required hook integration smoke"
