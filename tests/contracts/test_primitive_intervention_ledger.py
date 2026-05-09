"""ADR-256 Phase 2 — primitive intervention runtime evidence ledger."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GIT_BLOCKER = PROJECT_ROOT / "hooks" / "destructive-git-blocker.sh"
RM_BLOCKER = PROJECT_ROOT / "hooks" / "destructive-rm-blocker.sh"

LEDGER = Path(".cognitive-os/metrics/primitive-interventions.jsonl")


def _clean_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "CI",
        "PYTEST_CURRENT_TEST",
        "COS_GIT_BYPASS",
        "COS_ALLOW_DESTRUCTIVE_GIT",
        "CLAUDE_AGENT_ID",
        "COGNITIVE_OS_SESSION_ID",
        "ORCHESTRATOR_MODE",
        "CLAUDE_TOOL_INPUT",
    ):
        env.pop(key, None)
    env.update(
        {
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
            "COGNITIVE_OS_HARNESS": "codex",
        }
    )
    return env


def _ledger_rows(tmp_path: Path) -> list[dict[str, object]]:
    path = tmp_path / LEDGER
    assert path.exists(), f"primitive intervention ledger missing: {path}"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_destructive_git_block_emits_content_free_primitive_intervention(tmp_path: Path) -> None:
    payload = {"tool_name": "Bash", "tool_input": {"command": "git reset --hard private-target-branch"}}
    result = subprocess.run(
        ["bash", str(GIT_BLOCKER)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=_clean_env(tmp_path),
        timeout=10,
    )

    assert result.returncode == 2, result.stderr
    row = _ledger_rows(tmp_path)[-1]
    assert row["schema_version"] == "primitive-intervention.v1"
    assert row["primitive_id"] == "destructive-git-blocker"
    assert row["primitive_family"] == "hook"
    assert row["primitive_source"] == "hooks/destructive-git-blocker.sh"
    assert row["harness"] == "codex"
    assert row["tool"] == "Bash"
    assert row["action_kind"] == "block"
    assert row["reason_code"] == "destructive_git_op"
    assert row["target_ref"] == "git-reset"
    assert row["source_metric"] == ".cognitive-os/metrics/git-op-blocks.jsonl"
    assert "command" not in row
    assert "private-target-branch" not in json.dumps(row)


def test_destructive_rm_block_emits_content_free_primitive_intervention(tmp_path: Path) -> None:
    env = _clean_env(tmp_path)
    env.update(
        {
            "CLAUDE_AGENT_ID": "agent-ledger-test",
            "CLAUDE_TOOL_INPUT": f"rm -rf {tmp_path}/private-target-dir",
        }
    )
    result = subprocess.run(
        ["bash", str(RM_BLOCKER)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(PROJECT_ROOT),
        timeout=10,
    )

    assert result.returncode == 2, result.stderr
    row = _ledger_rows(tmp_path)[-1]
    assert row["schema_version"] == "primitive-intervention.v1"
    assert row["primitive_id"] == "destructive-rm-blocker"
    assert row["primitive_family"] == "hook"
    assert row["primitive_source"] == "hooks/destructive-rm-blocker.sh"
    assert row["harness"] == "codex"
    assert row["tool"] == "Bash"
    assert row["action_kind"] == "block"
    assert row["reason_code"] == "destructive_file_op"
    assert row["target_ref"] == "rm-recursive"
    assert row["source_metric"] == ".cognitive-os/metrics/rm-op-blocks.jsonl"
    assert "command" not in row
    assert "private-target-dir" not in json.dumps(row)
