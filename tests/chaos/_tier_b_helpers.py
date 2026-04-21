"""Shared helpers for Tier B chaos tests (ADR-041 Wave B).

Extracted to avoid duplication across the ~12 Wave B test files. Each Tier B
test uses:

- `setup_project(tmp_path)`: create minimal `.cognitive-os/` layout.
- `run_hook(hook_path, tmp_path, stdin_payload, env_extra)`: invoke hook with
  isolated env, timeout 10s, stdin piped.
- `write_chaos_run(tmp_path, component, scenario, passed)`: append a standard
  chaos-runs.jsonl row so aspirational-audit can observe the exercise.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path


PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = PROJ_ROOT / "hooks"
CHAOS_RUNS_REL = ".cognitive-os/metrics/chaos-runs.jsonl"


def setup_project(tmp_path: Path) -> None:
    """Create the minimal project skeleton expected by Tier B hooks."""
    (tmp_path / ".cognitive-os" / "runtime").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".cognitive-os" / "sessions").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)


def run_hook(
    hook_path: Path,
    tmp_path: Path,
    stdin_payload: str = "",
    env_extra: dict | None = None,
    timeout: int = 10,
) -> subprocess.CompletedProcess:
    """Run a hook with an isolated environment rooted at tmp_path."""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "VALKEY_DISABLED": "1",
        "AGENT_BUS_ENABLED": "false",
    }
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(hook_path)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=str(tmp_path),
    )


def write_chaos_run(
    tmp_path: Path, component: str, scenario: str, passed: bool
) -> None:
    log = tmp_path / CHAOS_RUNS_REL
    log.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event_type": "component.exercised",
        "component": component,
        "scenario": scenario,
        "passed": passed,
        "tier": "B",
        "source": "chaos-test",
    }
    with log.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
