#!/usr/bin/env bash
# SCOPE: both
# PURPOSE: Record, and reinforce, engram observations that a retrieval ACTUALLY returned
# EVENT: PostToolUse
# MATCHER: mcp__plugin_engram_engram__mem_search|mcp__plugin_engram_engram__mem_get_observation
# EXIT_CODES: 0=advisory (never blocks — reinforcement failure is non-critical)
# CONCERNS: observability, harness-contract
#
# WHY THIS FILE WAS REWRITTEN (2026-08-15)
# ----------------------------------------
# It was registered in .claude/settings.json since 3ba41b39a (2026-05-05) and its
# ledger, .cognitive-os/metrics/lifecycle-reinforcement.jsonl, had never existed —
# not live, not in .archive/*.gz. Two independent defects, either one fatal:
#
#   1. PHANTOM FIELD. It read `.tool_result` and `.tool_output`. The harness sends
#      neither. The PostToolUse payload carries the result under `tool_response`
#      (same contract hooks/_lib/tool-outcome.sh documents). `.get("tool_result")
#      or .get("tool_output") or {}` collapsed a missing field into an empty dict,
#      so the hook took the "nothing to reinforce" branch and exited 0, silently.
#
#   2. WRONG SHAPE, even on the right field. The old parser walked the result for
#      dicts carrying an `"id"` key. An MCP tool response carries none. It is an
#      ARRAY of content blocks — [{"type":"text","text":"<json string>"}] — whose
#      inner JSON has keys {project, project_path, project_source, result}, and
#      `result` is PROSE. Observation ids live in that prose as `#<digits>`.
#      Fixing only defect 1 would have moved from one phantom to another.
#
# Both shapes were read off 89 real engram tool results in local transcripts.
# Reproduce the payload shape and this hook's arrival with:
#
#   python3 scripts/check_memory_retrieval_arrival.py -v
#
# WHY classify_tool_outcome() IS NOT USED FOR THE VERDICT
# -------------------------------------------------------
# hooks/_lib/tool-outcome.sh branches on `tool_response` being a STRING or an
# OBJECT. An MCP response is an ARRAY, which falls through its final `else` to
# `absent`. That classifier is correct for the tools it was measured on (Bash,
# Read, Write, Edit, Agent) and simply does not cover the MCP content-block
# shape. Its drift RECORDER is still used here, because a payload we cannot read
# is an alarm about the OS's ability to observe, not a quiet no-op.
#
# WHAT A LEDGER ROW MEANS, AND WHAT IT DELIBERATELY DOES NOT
# -----------------------------------------------------------
# A row is written only when the payload was READ and the retrieval's outcome was
# OBSERVED:
#   outcome=hit   ids[] are the observations the harness actually returned
#   outcome=miss  the server answered "No memories found" — a real, useful
#                 negative: memory was consulted and had nothing
# No row is written for "the tool was called". A ledger counting invocations
# would look like coverage and measure nothing. An unreadable payload goes to
# payload-contract-drift.jsonl instead, never to this ledger.
#
# `project_path` from the payload is deliberately NOT stored: it is an absolute
# path carrying the operator's username. Only the project NAME is kept.
#
# Bash 3.x compatible; kebab-case filename per rules/bash-naming.md.

set -euo pipefail

INPUT="$(cat)"

# FAST PATH: skip if neither tool name appears in the input.
case "$INPUT" in
  *"mem_search"* | *"mem_get_observation"*) ;;
  *) exit 0 ;;
esac

PROJECT_ROOT="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
METRICS_DIR="${PROJECT_ROOT}/.cognitive-os/metrics"

# Drift recorder only — see the note above on why the classifier itself is not
# applicable to MCP content-block payloads.
# shellcheck source=/dev/null
[ -f "${PROJECT_ROOT}/hooks/_lib/tool-outcome.sh" ] &&
  . "${PROJECT_ROOT}/hooks/_lib/tool-outcome.sh" 2>/dev/null || true

# One Python process does everything: parse, extract, reinforce, append. The old
# version spent three. Exit status distinguishes the drift path for bash.
#   0 = ledger row written   3 = payload unreadable (drift)   other = give up
set +e
COS_HOOK_INPUT="$INPUT" COS_METRICS_DIR="$METRICS_DIR" COS_PROJECT_ROOT="$PROJECT_ROOT" \
  python3 - <<'PYEOF'
import json, os, re, sys, datetime

payload_raw = os.environ.get("COS_HOOK_INPUT", "")
metrics_dir = os.environ.get("COS_METRICS_DIR", "")
project_root = os.environ.get("COS_PROJECT_ROOT", "")

try:
    data = json.loads(payload_raw)
except Exception:
    sys.exit(3)
if not isinstance(data, dict):
    sys.exit(3)

tool_name = str(data.get("tool_name") or "")
if "mem_get_observation" in tool_name:
    tool = "mem_get_observation"
elif "mem_search" in tool_name:
    tool = "mem_search"
else:
    # Matcher fired but tool_name is unreadable: fall back to payload sniffing
    # rather than mislabel the row.
    tool = "mem_get_observation" if "mem_get_observation" in payload_raw else "mem_search"

# THE field. Absence is drift, never "nothing to do".
if "tool_response" not in data or data.get("tool_response") is None:
    sys.exit(3)
resp = data["tool_response"]

# MCP content blocks -> the text they carry.
if isinstance(resp, list):
    text = "".join(
        b.get("text", "") for b in resp if isinstance(b, dict) and isinstance(b.get("text"), str)
    )
elif isinstance(resp, str):
    text = resp
elif isinstance(resp, dict):
    text = resp.get("text") or resp.get("result") or ""
    if not isinstance(text, str):
        text = ""
else:
    sys.exit(3)

if not text.strip():
    sys.exit(3)

project = ""
result = text
try:
    inner = json.loads(text)
    if isinstance(inner, dict):
        # project_path is intentionally dropped — it embeds the operator's home.
        project = str(inner.get("project") or "")
        if isinstance(inner.get("result"), str):
            result = inner["result"]
except Exception:
    pass

# Anchored id extraction. A bare r"#(\d+)" over the prose would also match issue
# and PR numbers quoted inside an observation's own body, inflating the ledger
# with ids that were never retrieved.
#   mem_search        "[1] #29943 (manual) — Title"
#   mem_get_observation  "#29943 [manual] Title"
ids = []
for line in result.splitlines():
    m = re.match(r"\s*\[\d+\]\s+#(\d+)\b", line) or re.match(r"\s*#(\d+)\s+[\[(]", line)
    if m and m.group(1) not in ids:
        ids.append(m.group(1))

if ids:
    outcome = "hit"
elif re.search(r"No memories found|Found 0 memories", result):
    outcome = "miss"
else:
    # Read the payload fine, but recognised neither a hit nor a stated miss:
    # the server's response format moved. That is drift, not an empty result.
    sys.exit(3)

# Reinforce only what was actually returned. Advisory: never raises.
if ids:
    try:
        if project_root and project_root not in sys.path:
            sys.path.insert(0, project_root)
        from cos_lib.engram_lifecycle import EngramLifecycle

        lc = EngramLifecycle()
        for obs_id in ids:
            try:
                lc.reinforce(obs_id)
            except Exception:
                pass
    except Exception:
        pass

row = {
    "timestamp": datetime.datetime.now(datetime.timezone.utc)
    .strftime("%Y-%m-%dT%H:%M:%SZ"),
    "tool": tool,
    "outcome": outcome,
    "observation_ids": ids,
    "n": len(ids),
    "project": project,
}
try:
    os.makedirs(metrics_dir, exist_ok=True)
    with open(os.path.join(metrics_dir, "lifecycle-reinforcement.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
except Exception:
    sys.exit(3)

sys.exit(0)
PYEOF
rc=$?
set -e

if [ "$rc" = "3" ]; then
  if type record_payload_contract_drift >/dev/null 2>&1; then
    record_payload_contract_drift "$METRICS_DIR" "engram-reinforce-on-access.sh" \
      "tool_response absent, or MCP content shape not recognised — no retrieval could be observed"
  fi
fi

exit 0
