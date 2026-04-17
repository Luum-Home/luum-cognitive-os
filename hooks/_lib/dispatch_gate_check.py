#!/usr/bin/env python3
# SCOPE: both
"""Single-pass dispatch gate check — consolidates all python3 invocations from dispatch-gate.sh.

Reads stdin JSON once, performs all checks, and emits a single JSON result.

Exit codes: always 0 (caller interprets the JSON fields).
Output: JSON to stdout, errors to stderr.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

# NOTE: custom resolution — differs from lib.paths.project_root() (Pattern C).
# See tests/unit/test_project_dir_resolution.py for rationale.
PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", ".")
sys.path.insert(0, PROJECT_DIR)

# Read stdin once
try:
    stdin_raw = sys.stdin.read()
    d = json.loads(stdin_raw) if stdin_raw.strip() else {}
except Exception:
    d = {}

tool_input = d.get("tool_input", {})
task_desc = tool_input.get("description", "") or tool_input.get("prompt", "")

result: dict = {
    "max_agents": 5,
    "active": 0,
    "skill_name": "",
    "disabled": False,
    "model_override": "",
    "cb_blocked": False,
    "cb_task_type": "",
    "model_directive": "",
    "model_advice": "",
    "log_desc": "",
    "error": "",
}

# ---------------------------------------------------------------------------
# 1. Read config (cognitive-os.yaml)
# ---------------------------------------------------------------------------
try:
    import yaml  # type: ignore

    cfg_path = Path(PROJECT_DIR) / "cognitive-os.yaml"
    if not cfg_path.exists():
        cfg_path = Path(PROJECT_DIR) / ".cognitive-os" / "cognitive-os.yaml"
    if cfg_path.exists():
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f) or {}
        result["max_agents"] = (
            cfg.get("resources", {}).get("compute", {}).get("max_parallel_agents", 5)
        )
except Exception as e:
    result["error"] += f"config:{e};"

# ---------------------------------------------------------------------------
# 2. Count active tasks (active-tasks.json)
# ---------------------------------------------------------------------------
try:
    tasks_path = (
        Path(PROJECT_DIR) / ".cognitive-os" / "tasks" / "active-tasks.json"
    )
    if tasks_path.exists():
        with open(tasks_path) as f:
            tasks_data = json.load(f)
        result["active"] = sum(
            1
            for t in tasks_data.get("tasks", [])
            if t.get("status") == "in_progress"
        )
except Exception as e:
    result["error"] += f"tasks:{e};"

# ---------------------------------------------------------------------------
# 3. Extract skill name from description
# ---------------------------------------------------------------------------
try:
    desc = task_desc.strip()
    m = re.match(r"[/]?([a-zA-Z0-9_-]+)", desc)
    result["skill_name"] = m.group(1).lower() if m else ""
except Exception:
    pass

# ---------------------------------------------------------------------------
# 4. Log description (first 100 chars, JSON-safe)
# ---------------------------------------------------------------------------
try:
    prompt = (
        tool_input.get("prompt", "") or tool_input.get("description", "")
    )
    result["log_desc"] = prompt[:100].replace('"', '\\"')
except Exception:
    pass

# ---------------------------------------------------------------------------
# 5 & 6. Consequence engine: DISABLE + model override
# ---------------------------------------------------------------------------
skill_name = result["skill_name"]
if skill_name:
    try:
        from lib.consequence_engine import ConsequenceEngine  # type: ignore

        ce = ConsequenceEngine()
        result["disabled"] = ce.is_skill_disabled(skill_name)
        override = ce.get_model_override(skill_name)
        result["model_override"] = override if override else ""
    except Exception as e:
        result["error"] += f"consequence:{e};"

# ---------------------------------------------------------------------------
# 7. Circuit breaker check
# ---------------------------------------------------------------------------
try:
    from lib.circuit_breaker import CircuitBreaker  # type: ignore
    from lib.record_completion import classify_task_type  # type: ignore

    task_type = classify_task_type(task_desc or "general")
    cb = CircuitBreaker()
    if not cb.can_launch(task_type):
        result["cb_blocked"] = True
        result["cb_task_type"] = task_type
except Exception as e:
    result["error"] += f"circuit_breaker:{e};"

# ---------------------------------------------------------------------------
# 8. Model routing (only on allow path — but we compute it always so bash
#    can decide; it's cheap compared to the cold starts we're saving)
# ---------------------------------------------------------------------------
try:
    from lib.dispatch_model_advisor import (  # type: ignore
        recommend_model,
        format_model_directive,
        format_model_advice,
    )

    skill_match = re.search(r"skill[:\s]+([a-zA-Z0-9_-]+)", task_desc[:300])
    skill_hint = skill_match.group(1) if skill_match else None
    rec = recommend_model(task_desc, skill_name=skill_hint)
    result["model_directive"] = format_model_directive(rec)
    result["model_advice"] = format_model_advice(rec)
except Exception as e:
    result["model_directive"] = "MODEL_ADVICE: sonnet"
    result["model_advice"] = f"Model: sonnet (default, error: {str(e)[:60]})"
    result["error"] += f"model_routing:{e};"

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
print(json.dumps(result))
