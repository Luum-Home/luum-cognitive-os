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
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

# NOTE: custom resolution — differs from lib.paths.project_root() (Pattern C).
# See tests/unit/test_project_dir_resolution.py for rationale.
# D2.2 fix (ADR-026a): honour COGNITIVE_OS_PROJECT_DIR as a fallback so that
# both env vars are treated equally.  CLAUDE_PROJECT_DIR still wins when set.
PROJECT_DIR = (
    os.environ.get("CLAUDE_PROJECT_DIR")
    or os.environ.get("COGNITIVE_OS_PROJECT_DIR")
    or "."
)
sys.path.insert(0, PROJECT_DIR)
# Also ensure the OS package root (where lib/ lives) is on sys.path so that
# lib.config_loader and its siblings are importable even when CLAUDE_PROJECT_DIR
# points to a consumer project (not the OS root itself).
_OS_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _OS_ROOT not in sys.path:
    sys.path.append(_OS_ROOT)

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
    from lib.config_loader import load_structured  # type: ignore

    cfg_path = Path(PROJECT_DIR) / "cognitive-os.yaml"
    if not cfg_path.exists():
        cfg_path = Path(PROJECT_DIR) / ".cognitive-os" / "cognitive-os.yaml"
    cfg_path_str = str(cfg_path) if cfg_path.exists() else None
    cfg = load_structured(cfg_path_str)
    result["max_agents"] = (
        cfg.get("resources", {}).get("compute", {}).get("max_parallel_agents", 5)
    )
except Exception as e:
    result["error"] += f"config:{e};"

try:
    env_max_agents = os.environ.get("COGNITIVE_OS_MAX_PARALLEL_AGENTS")
    if env_max_agents is not None and env_max_agents.strip() != "":
        result["max_agents"] = int(env_max_agents)
except Exception as e:
    result["error"] += f"config_env:{e};"

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

        def _age_seconds(task):
            ts = task.get("started_at") or task.get("launchedAt") or task.get("requested_at")
            if not ts:
                return None
            try:
                dt = datetime.fromisoformat(str(ts).rstrip("Z")).replace(tzinfo=timezone.utc)
                return (datetime.now(timezone.utc) - dt).total_seconds()
            except Exception:
                return None

        def _pid_alive(pid):
            try:
                os.kill(int(pid), 0)
                return True
            except Exception:
                return False

        def _is_dispatch_active(task):
            if task.get("status") != "in_progress":
                return False
            pid = task.get("pid")
            if pid is not None:
                return _pid_alive(pid)
            age = _age_seconds(task)
            return age is None or age <= (30 * 60)

        result["active"] = sum(
            1
            for t in tasks_data.get("tasks", [])
            if _is_dispatch_active(t)
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
