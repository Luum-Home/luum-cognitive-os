#!/usr/bin/env bash
# SCOPE: os-only
# test-mcp-server.sh -- Quick smoke test for the COS MCP server.
#
# Verifies:
#   1. The server starts without import errors
#   2. fastmcp can list all 8 tools
#   3. fastmcp can call cos_status and get valid JSON
#
# Usage:
#   bash scripts/test-mcp-server.sh
#
# Exit codes:
#   0 - all checks passed
#   1 - one or more checks failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER="$PROJECT_ROOT/mcp-server/cos_mcp.py"

PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); echo "  [PASS] $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  [FAIL] $1"; }

echo "=== COS MCP Server Smoke Test ==="
echo ""

# ---- Check 1: Python can import the server without errors ----
echo "1. Server imports cleanly..."
if python3 -c "
import sys, importlib.util
spec = importlib.util.spec_from_file_location('cos_mcp', '$SERVER')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
" 2>/dev/null; then
    pass "Server imports without errors"
else
    fail "Server import failed"
fi

# ---- Check 2: fastmcp is installed ----
echo "2. fastmcp available..."
if command -v fastmcp &>/dev/null; then
    pass "fastmcp CLI found: $(fastmcp version 2>&1 | head -1)"
else
    fail "fastmcp CLI not found (pip install fastmcp)"
    echo ""
    echo "Results: $PASS passed, $FAIL failed"
    exit 1
fi

# ---- Check 3: fastmcp lists exactly 8 tools ----
echo "3. Tool count..."
TOOL_OUTPUT=$(fastmcp list "$SERVER" 2>/dev/null)
TOOL_COUNT=$(echo "$TOOL_OUTPUT" | grep -c "cos_" || true)
if [ "$TOOL_COUNT" -eq 8 ]; then
    pass "8 tools listed"
else
    fail "Expected 8 tools, found $TOOL_COUNT"
fi

# ---- Check 4: cos_status returns valid JSON ----
echo "4. cos_status returns valid JSON..."
STATUS_OUTPUT=$(fastmcp call "$SERVER" cos_status 2>/dev/null)
if echo "$STATUS_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'result' in d" 2>/dev/null; then
    pass "cos_status returns valid JSON"
else
    fail "cos_status did not return valid JSON"
fi

# ---- Check 5: cos_status reports components ----
echo "5. cos_status reports components..."
RULES_COUNT=$(echo "$STATUS_OUTPUT" | python3 -c "
import sys, json
d = json.loads(json.load(sys.stdin)['result'])
print(d.get('rules', 0))
" 2>/dev/null || echo "0")
if [ "$RULES_COUNT" -gt 0 ]; then
    pass "cos_status reports $RULES_COUNT rules"
else
    fail "cos_status reported 0 rules"
fi

# ---- Check 6: fastmcp inspect shows server metadata ----
echo "6. Server metadata..."
INSPECT_OUTPUT=$(fastmcp inspect "$SERVER" 2>/dev/null)
if echo "$INSPECT_OUTPUT" | grep -q "Cognitive OS"; then
    pass "Server name: Cognitive OS"
else
    fail "Server name not found in inspect output"
fi

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
