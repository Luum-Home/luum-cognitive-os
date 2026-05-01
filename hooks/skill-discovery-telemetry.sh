#!/usr/bin/env bash
# SCOPE: both
# Skill Discovery Telemetry — PostToolUse hook (Agent tool)
#
# After an Agent tool completes, heuristically checks whether the agent
# described re-implementing something that an existing skill provides —
# indicating the agent failed to discover and invoke the relevant skill.
#
# Detection strategy (heuristic, low-false-positive):
#   Look for phrases in agent output that suggest manual re-implementation:
#   "I'll implement", "let me write a script", "I'll create a function",
#   "building a", "writing a custom" — when combined with topics that match
#   known skill names/descriptions from CATALOG-COMPACT.md.
#
# Appends events to .cognitive-os/runtime/skill-discovery.jsonl:
#   {ts, session_id, agent_id, lazy_catalog_active, prompt_keywords,
#    skills_invoked, suspected_missed_skills}
#
# Non-blocking: exits 0 on any error. Must complete in ≤200ms.

set -uo pipefail

# Only fire on Agent tool
TOOL_NAME="${CLAUDE_TOOL_NAME:-}"
if [ "$TOOL_NAME" != "Agent" ] && [ "$TOOL_NAME" != "Task" ]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
CATALOG_COMPACT="$PROJECT_DIR/skills/CATALOG-COMPACT.md"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
mkdir -p "$RUNTIME_DIR"

SESSION_ID="${COGNITIVE_OS_SESSION_ID:-unknown}"
LAZY_ACTIVE="${COS_LAZY_CATALOG:-1}"

python3 - <<'PYEOF' 2>/dev/null || exit 0
import json, os, re, time, sys
from pathlib import Path

project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
catalog_path = Path(project_dir) / "skills" / "CATALOG-COMPACT.md"
runtime_dir = Path(project_dir) / ".cognitive-os" / "runtime"
runtime_dir.mkdir(parents=True, exist_ok=True)

session_id = os.environ.get("COGNITIVE_OS_SESSION_ID", "unknown")
lazy_active = os.environ.get("COS_LAZY_CATALOG", "1") == "1"

# Extract tool result and input from env vars
tool_result_raw = os.environ.get("CLAUDE_TOOL_RESULT", "")
tool_input_raw = os.environ.get("CLAUDE_TOOL_INPUT", "")

# Parse agent output text
agent_output = ""
try:
    result = json.loads(tool_result_raw)
    if isinstance(result, dict):
        agent_output = result.get("output", result.get("result", ""))
    elif isinstance(result, str):
        agent_output = result
except Exception:
    agent_output = tool_result_raw[:2000]

# Parse agent prompt keywords
prompt_keywords = []
try:
    inp = json.loads(tool_input_raw)
    prompt_text = inp.get("prompt", "")[:500].lower()
    # Extract notable keywords (words >4 chars)
    prompt_keywords = list(set(re.findall(r'\b\w{5,}\b', prompt_text)))[:20]
except Exception:
    pass

# Load skill names from catalog for matching
skill_names = []
if catalog_path.exists():
    try:
        content = catalog_path.read_text()
        # Extract skill names: lines starting with "**skill-name**" or "- skill-name"
        matches = re.findall(r'^\*\*([a-z][a-z0-9-]+)\*\*', content, re.MULTILINE)
        matches += re.findall(r'^- \*\*([a-z][a-z0-9-]+)\*\*', content, re.MULTILINE)
        skill_names = list(set(matches))
    except Exception:
        pass

# Re-implementation signal phrases
reimpl_phrases = [
    r"i.ll implement", r"let me write a script", r"i.ll create a function",
    r"building a.*from scratch", r"writing a custom", r"i.ll build",
    r"creating a new.*script", r"implementing.*myself", r"i.ll write.*code",
    r"let me code", r"i.ll develop", r"i.ll create.*tool",
]

output_lower = agent_output.lower()
reimpl_detected = any(re.search(p, output_lower) for p in reimpl_phrases)

# Match suspected missed skills: skill names mentioned in output context
# but agent chose to re-implement instead of invoking
suspected_missed = []
if reimpl_detected and skill_names:
    for skill in skill_names:
        # Check if skill topic appears in either the prompt or agent output
        topic_words = skill.replace("-", " ")
        if topic_words in output_lower or topic_words in " ".join(prompt_keywords):
            suspected_missed.append(skill)

# Skills that WERE invoked (appear in output as "Invoking skill: X" or similar)
skills_invoked = []
invoked_matches = re.findall(r'(?:invoking|using|running) skill[:\s]+([a-z][a-z0-9-]+)', output_lower)
skills_invoked = list(set(invoked_matches))

record = {
    "ts": time.time(),
    "event": "agent_telemetry",
    "session_id": session_id,
    "agent_id": os.environ.get("CLAUDE_AGENT_ID", "unknown"),
    "lazy_catalog_active": lazy_active,
    "prompt_keywords": prompt_keywords[:10],
    "skills_invoked": skills_invoked,
    "reimpl_detected": reimpl_detected,
    "suspected_missed_skills": suspected_missed,
}

out_path = runtime_dir / "skill-discovery.jsonl"
with open(out_path, "a") as f:
    f.write(json.dumps(record) + "\n")
PYEOF

exit 0
