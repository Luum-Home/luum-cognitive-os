"""Behavior tests for Engram access reinforcement hook."""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "engram-reinforce-on-access.sh"


def _run_hook(
    project_dir: Path,
    payload: dict,
    *,
    env_var: str = "COGNITIVE_OS_PROJECT_DIR",
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env[env_var] = str(project_dir)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=10,
    )


def test_reinforce_hook_logs_every_observation_id(tmp_path: Path) -> None:
    result = _run_hook(
        tmp_path,
        {
            "tool_name": "mcp__plugin_engram_engram__mem_search",
            "tool_result": {"observations": [{"id": 123}, {"id": "456"}]},
        },
    )

    assert result.returncode == 0, result.stderr
    metrics = tmp_path / ".cognitive-os" / "metrics" / "lifecycle-reinforcement.jsonl"
    lines = [json.loads(line) for line in metrics.read_text().splitlines()]
    assert [line["observation_id"] for line in lines] == ["123", "456"]
    assert {line["tool"] for line in lines} == {"mem_search"}


def test_reinforce_hook_ignores_unrelated_tool_events(tmp_path: Path) -> None:
    result = _run_hook(
        tmp_path,
        {
            "tool_name": "mcp__plugin_engram_engram__mem_save",
            "tool_result": {"id": 123},
        },
    )

    assert result.returncode == 0, result.stderr
    metrics = tmp_path / ".cognitive-os" / "metrics" / "lifecycle-reinforcement.jsonl"
    assert not metrics.exists()


def test_reinforce_hook_writes_under_codex_project_dir(tmp_path: Path) -> None:
    result = _run_hook(
        tmp_path,
        {
            "tool_name": "mcp__plugin_engram_engram__mem_get_observation",
            "tool_result": {"id": 789},
        },
        env_var="CODEX_PROJECT_DIR",
    )

    assert result.returncode == 0, result.stderr
    metrics = tmp_path / ".cognitive-os" / "metrics" / "lifecycle-reinforcement.jsonl"
    line = json.loads(metrics.read_text().splitlines()[-1])
    assert line["observation_id"] == "789"
    assert line["tool"] == "mem_get_observation"
