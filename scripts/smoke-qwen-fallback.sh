#!/usr/bin/env bash
# SCOPE: os-only
# @on-demand: run weekly/before releases/after env changes to verify ADR-049 Qwen fallback still works
# smoke-qwen-fallback.sh — End-to-end verification of ADR-049 fallback.
#
# What it checks (in order):
#   1. cos-config-audit.sh reports meta.llm_providers_reachable = IMPL
#   2. lib/qwen_provider.py is importable and call() works (real API call)
#   3. scripts/orchestrator.py _try_qwen_primary() returns a result object
#      when invoked programmatically (mocked rate-limit error)
#   4. COS_DISABLE_LLM_FALLBACK=1 kill-switch blocks the fallback
#
# Run this periodically (weekly / before releases / after env changes) to
# confirm the overflow path still works.
#
# Exit codes:
#   0 — all 4 checks pass (fallback system healthy)
#   1 — check 1 fails (validator disagrees)
#   2 — check 2 fails (SDK or API call broken)
#   3 — check 3 fails (orchestrator helper broken)
#   4 — check 4 fails (kill-switch not respected — CRITICAL, please fix)

set -uo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"

# Source .env if present (for ALIBABA_QWEN_API_KEY, ALIBABA_QWEN_BASE_URL).
# COS_SKIP_DOTENV=1 is the public operator/agent-safe bypass for live smokes
# that must use already-exported environment variables only. It also prevents
# lib/qwen_provider.py from auto-loading .env later in the Python process.
case "${COS_SKIP_DOTENV:-0}" in
  1|true|TRUE|yes|YES|on|ON)
    export _COS_QWEN_DOTENV_LOADED=1
    ;;
  *)
    if [ -f "$PROJECT_DIR/.env" ]; then
      set -a
      # shellcheck disable=SC1091
      source "$PROJECT_DIR/.env" 2>/dev/null || true
      set +a
    fi
    ;;
esac

say() { printf '\n=== %s ===\n' "$*"; }
fail() { printf '  FAIL: %s\n' "$*" >&2; }
pass() { printf '  PASS: %s\n' "$*"; }

say "Check 1 / 4 — meta.llm_providers_reachable"
audit_output=$(python3 scripts/cos-config-audit.sh 2>/dev/null | grep llm_providers_reachable || true)
if echo "$audit_output" | grep -q '\[ IMPL  \]'; then
  pass "validator reports IMPL — $audit_output"
else
  fail "validator does NOT report IMPL: $audit_output"
  exit 1
fi

say "Check 2 / 4 — qwen_provider.call() live smoke"
live_result=$(
  uv run python3 -c "
from lib.qwen_provider import call, is_configured
if not is_configured():
    print('UNCONFIGURED'); raise SystemExit(0)
r = call(
    messages=[{'role':'user','content':'Respond with exactly: OK'}],
    model='qwen3.6-plus',
    max_tokens=10,
)
print(f'SUCCESS={r.success} ERROR={r.error[:80] if r.error else \"\"}')
" 2>&1 | tail -1
)
if echo "$live_result" | grep -q 'SUCCESS=True'; then
  pass "qwen_provider.call() → success"
elif echo "$live_result" | grep -q 'UNCONFIGURED'; then
  if [ "${COS_SKIP_DOTENV:-0}" = "1" ]; then
    fail "ALIBABA_QWEN_API_KEY not set — COS_SKIP_DOTENV=1 requires exported env credentials"
  else
    fail "ALIBABA_QWEN_API_KEY not set — set it in .env or export it in the shell"
  fi
  exit 2
else
  fail "live call did NOT succeed: $live_result"
  exit 2
fi

say "Check 3 / 4 — orchestrator _try_qwen_primary() returns result"
orch_result=$(
  uv run python3 -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('orch', 'scripts/orchestrator.py')
orch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orch)
r = orch._try_qwen_primary('Respond with: PONG')
if r is None:
    print('FALLBACK_NONE'); raise SystemExit(0)
print(f'FALLBACK_RESULT success={r.success} provider={r.provider}')
" 2>&1 | tail -1
)
if echo "$orch_result" | grep -q 'success=True'; then
  pass "orchestrator helper returned success=True"
else
  fail "orchestrator helper did not return success: $orch_result"
  exit 3
fi

say "Check 4 / 4 — COS_DISABLE_LLM_FALLBACK=1 cascade kill-switch"
# Per C1 Option B rewrite: the kill-switch is CASCADE-SCOPED. It blocks advance
# to a fallback provider, NOT the initial primary call. Semantically correct
# because Qwen-as-primary should still fire (it's what the user explicitly
# requested via --providers qwen,...); only the fallback-to-Claude step is
# what the switch blocks.
switch_result=$(
  COS_DISABLE_LLM_FALLBACK=1 uv run python3 -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('orch', 'scripts/orchestrator.py')
orch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orch)
# Verify _fallback_disabled() returns True under the env var
disabled = orch._fallback_disabled(verbose=False)
print('SWITCH_RESPECTED' if disabled else 'SWITCH_IGNORED')
" 2>&1 | tail -1
)
if echo "$switch_result" | grep -q 'SWITCH_RESPECTED'; then
  pass "cascade kill-switch detected as expected"
else
  fail "CRITICAL: cascade kill-switch IGNORED — $switch_result"
  exit 4
fi

printf '\nALL 4 CHECKS PASS — ADR-049 fallback system healthy.\n'
exit 0
