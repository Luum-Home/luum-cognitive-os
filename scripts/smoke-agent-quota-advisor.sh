#!/usr/bin/env bash
# SCOPE: os-only
# Live smoke test for ADR-056 L1 — agent-quota-advisor hook.
#
# Seeds fake llm-dispatch.jsonl + cost-events.jsonl data in a temp project
# dir, invokes the hook against that dir, and greps for the expected
# advisory strings. Exits 0 on success, non-zero on mismatch.
#
# Usage: bash scripts/smoke-agent-quota-advisor.sh
#
# Non-aspirational: reads no real metrics, calls no API, never mutates
# the repo's real .cognitive-os/ state.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK="$ROOT/hooks/agent-quota-advisor.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PROJ="$TMP/proj"
METRICS="$PROJ/.cognitive-os/metrics"
mkdir -p "$METRICS"
ln -s "$ROOT/lib" "$PROJ/lib"

fail() {
  echo "SMOKE FAIL: $1" >&2
  exit 1
}

# ── Check 1: silent when no metrics ────────────────────────────────────────
echo "[1/4] silence-on-empty…"
out=$(printf '%s' '{"tool_name":"Agent","tool_input":{}}' | \
  CLAUDE_PROJECT_DIR="$PROJ" bash "$HOOK" 2>&1 || true)
if echo "$out" | grep -q "QUOTA ADVISORY"; then
  fail "expected silence on empty metrics, got: $out"
fi

# ── Check 2: advisory at medium pressure (2 rate-limit errors) ─────────────
echo "[2/4] advisory-at-0.5…"
NOW=$(date -u +%s)
TS1=$(date -u -r $((NOW - 60)) +%Y-%m-%dT%H:%M:%SZ)
TS2=$(date -u -r $((NOW - 120)) +%Y-%m-%dT%H:%M:%SZ)
cat > "$METRICS/llm-dispatch.jsonl" <<EOF
{"ts":"$TS1","dispatch_id":"a","providers_requested":["claude"],"providers_tried":["claude"],"provider_used":"claude","model":"sonnet","task_type":"general","skill_name":null,"tokens_in":0,"tokens_out":0,"cost_usd":0,"latency_ms":0,"success":false,"error":"out of extra usage"}
{"ts":"$TS2","dispatch_id":"b","providers_requested":["claude"],"providers_tried":["claude"],"provider_used":"claude","model":"sonnet","task_type":"general","skill_name":null,"tokens_in":0,"tokens_out":0,"cost_usd":0,"latency_ms":0,"success":false,"error":"rate limit exceeded"}
EOF

out=$(printf '%s' '{"tool_name":"Agent","tool_input":{}}' | \
  CLAUDE_PROJECT_DIR="$PROJ" bash "$HOOK" 2>&1 || true)
if ! echo "$out" | grep -q "QUOTA ADVISORY"; then
  fail "expected advisory at medium pressure, got: $out"
fi

# ── Check 3: strong warning at saturated pressure ──────────────────────────
echo "[3/4] strong-at-1.0…"
: > "$METRICS/llm-dispatch.jsonl"
for i in 1 2 3 4; do
  TSx=$(date -u -r $((NOW - i * 60)) +%Y-%m-%dT%H:%M:%SZ)
  echo "{\"ts\":\"$TSx\",\"dispatch_id\":\"x$i\",\"providers_requested\":[\"claude\"],\"providers_tried\":[\"claude\"],\"provider_used\":\"claude\",\"model\":\"sonnet\",\"task_type\":\"general\",\"skill_name\":null,\"tokens_in\":0,\"tokens_out\":0,\"cost_usd\":0,\"latency_ms\":0,\"success\":false,\"error\":\"out of extra usage\"}" >> "$METRICS/llm-dispatch.jsonl"
done
TSc=$(date -u -r $((NOW - 60)) +%Y-%m-%dT%H:%M:%SZ)
cat > "$METRICS/cost-events.jsonl" <<EOF
{"event_type":"cost.recorded","payload":{"agent":"test","estimated_cost_usd":20.0,"is_estimate":true,"model":"sonnet","tokens_estimated":1000},"schema_version":1,"severity":"info","source":"record_completion","timestamp":"$TSc"}
EOF

out=$(printf '%s' '{"tool_name":"Agent","tool_input":{}}' | \
  CLAUDE_PROJECT_DIR="$PROJ" bash "$HOOK" 2>&1 || true)
if ! echo "$out" | grep -qi "strong"; then
  fail "expected 'strong' advisory at saturated pressure, got: $out"
fi
if ! echo "$out" | grep -q "COS_AUTO_REDIRECT_AGENT"; then
  fail "expected L2 hint in strong advisory, got: $out"
fi

# ── Check 4: kill-switch silences ──────────────────────────────────────────
echo "[4/4] kill-switch…"
out=$(printf '%s' '{"tool_name":"Agent","tool_input":{}}' | \
  CLAUDE_PROJECT_DIR="$PROJ" COS_DISABLE_AGENT_ADVISOR=1 bash "$HOOK" 2>&1 || true)
if echo "$out" | grep -q "QUOTA ADVISORY"; then
  fail "kill-switch did not silence advisory, got: $out"
fi

echo "SMOKE OK: all 4 checks passed."
exit 0
