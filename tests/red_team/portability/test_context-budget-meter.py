# SCOPE: os-only
"""Portability proof for hooks/context-budget-meter.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "hooks" / "context-budget-meter.sh"


def _run_hook(project: Path, payload: dict, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update({"CLAUDE_PROJECT_DIR": str(project), "COGNITIVE_OS_SESSION_ID": "portability-session"})
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(project),
        timeout=10,
    )


def test_records_metric_in_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: metric path must follow CLAUDE_PROJECT_DIR, not repo cwd."""
    (tmp_path / "cognitive-os.yaml").write_text("context_budget:\n  user_max_tokens: 12000\n", encoding="utf-8")
    result = _run_hook(tmp_path, {"prompt": "portable prompt"})
    assert result.returncode == 0, result.stderr
    metric = tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl"
    row = json.loads(metric.read_text(encoding="utf-8").splitlines()[-1])
    assert row["source"] == "context-budget-meter"
    assert row["session_id"] == "portability-session"
    assert row["allowed"] is True


def test_disable_env_writes_no_metric(tmp_path: Path) -> None:
    """Falsification probe: disabled hook must not create consumer-local state."""
    result = _run_hook(tmp_path, {"prompt": "portable prompt"}, {"DISABLE_HOOK_CONTEXT_BUDGET_METER": "1"})
    assert result.returncode == 0
    assert not (tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl").exists()
