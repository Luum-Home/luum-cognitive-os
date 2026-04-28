"""Behavior tests for Engram access reinforcement hook."""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "engram-reinforce-on-access.sh"


def _run_hook(project_dir: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
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
