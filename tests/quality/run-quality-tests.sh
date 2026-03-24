#!/usr/bin/env bash
# Layer 3: Quality Tests Runner
# Runs promptfoo evaluations for LLM-level quality checks.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/promptfoo-config.yaml"

echo "=== QUALITY TESTS (LLM-evaluated, Promptfoo) ==="
echo ""

# Check if promptfoo is available
if command -v promptfoo &>/dev/null; then
  PROMPTFOO="promptfoo"
elif command -v npx &>/dev/null; then
  # Check if promptfoo is installed locally
  if npx promptfoo --version &>/dev/null 2>&1; then
    PROMPTFOO="npx promptfoo"
  else
    echo "  SKIP: promptfoo not installed"
    echo ""
    echo "  To install: npm install -g promptfoo"
    echo "  Then run: promptfoo eval -c $CONFIG"
    echo ""
    echo "=== QUALITY SUMMARY ==="
    echo "  SKIP: promptfoo not available"
    exit 0
  fi
else
  echo "  SKIP: Neither promptfoo nor npx found"
  echo ""
  echo "  To install: npm install -g promptfoo"
  echo ""
  echo "=== QUALITY SUMMARY ==="
  echo "  SKIP: promptfoo not available"
  exit 0
fi

# Check config exists
if [ ! -f "$CONFIG" ]; then
  echo "  FAIL: promptfoo-config.yaml not found at $CONFIG"
  exit 1
fi

# Check for ANTHROPIC_API_KEY
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "  SKIP: ANTHROPIC_API_KEY not set"
  echo "  Set it via: export ANTHROPIC_API_KEY=sk-ant-..."
  echo ""
  echo "=== QUALITY SUMMARY ==="
  echo "  SKIP: API key not configured"
  exit 0
fi

echo "  Running promptfoo eval..."
echo "  Config: $CONFIG"
echo ""

# Run promptfoo eval
$PROMPTFOO eval -c "$CONFIG" --no-cache 2>&1
EXIT_CODE=$?

echo ""
if [ "$EXIT_CODE" -eq 0 ]; then
  echo "=== QUALITY SUMMARY ==="
  echo "  All quality tests passed"
else
  echo "=== QUALITY SUMMARY ==="
  echo "  Some quality tests failed (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
