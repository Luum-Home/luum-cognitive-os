# SCOPE: os-only
"""Portability proof for hooks/subagent-context-injector.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "hooks" / "subagent-context-injector.sh"


def _run(project: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    (project / "templates").mkdir(parents=True, exist_ok=True)
    (project / "templates" / "agent-preamble.md").write_text("Preamble {{phase}}", encoding="utf-8")
    (project / "templates" / "agent-mandatory-rules.md").write_text("Rules", encoding="utf-8")
    (project / "cognitive-os.yaml").write_text("project:\n  phase: portability\n", encoding="utf-8")
    env = os.environ.copy()
    env.update({"CLAUDE_PROJECT_DIR": str(project), "COGNITIVE_OS_PROJECT_DIR": str(project)})
    if extra_env:
        env.update(extra_env)
    payload = {"prompt": "Identity: portable-agent", "agent_id": "agent-1", "agent_type": "worker"}
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(project),
        timeout=10,
    )


def test_injects_context_from_arbitrary_project_templates(tmp_path: Path) -> None:
    """Falsification probe: context must come from consumer project, not OS repo."""
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    ctx = data["hookSpecificOutput"]["additionalContext"]
    assert "Rules" in ctx
    assert "Preamble portability" in ctx


def test_sidecar_lookup_is_opt_in_by_default(tmp_path: Path) -> None:
    """Falsification probe: default cold-start path must not call optional sidecar lookup."""
    result = _run(tmp_path, {"PYTHONPATH": "/nonexistent"})
    assert result.returncode == 0, result.stderr
    assert "Sidecar Context" not in result.stdout
