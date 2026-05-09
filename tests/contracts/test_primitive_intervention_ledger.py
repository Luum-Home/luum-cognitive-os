"""ADR-256 Phase 2 — primitive intervention runtime evidence ledger."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GIT_BLOCKER = PROJECT_ROOT / "hooks" / "destructive-git-blocker.sh"
RM_BLOCKER = PROJECT_ROOT / "hooks" / "destructive-rm-blocker.sh"
REINVENTION_CHECK = PROJECT_ROOT / "hooks" / "reinvention-check.sh"
LARGE_FILE_ADVISOR = PROJECT_ROOT / "hooks" / "large-file-advisor.sh"
SKILL_ROUTER_BASH_GATE = PROJECT_ROOT / "hooks" / "skill-router-bash-gate.sh"

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


def test_reinvention_check_emits_content_free_primitive_intervention(tmp_path: Path) -> None:
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "duplicate_helper.py").write_text("print('existing')\n", encoding="utf-8")
    payload = {
        "tool_name": "Agent",
        "tool_input": {
            "prompt": "Please create a new file duplicate_helper.py under lib/ for this private implementation."
        },
    }

    result = subprocess.run(
        ["bash", str(REINVENTION_CHECK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=_clean_env(tmp_path),
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    row = _ledger_rows(tmp_path)[-1]
    assert row["primitive_id"] == "reinvention-check"
    assert row["primitive_source"] == "hooks/reinvention-check.sh"
    assert row["tool"] == "Agent"
    assert row["action_kind"] == "warn"
    assert row["reason_code"] == "possible_reinvention"
    assert row["target_ref"] == "phase-a-duplicate-candidate"
    assert row["source_metric"] == ".cognitive-os/metrics/reinvention-checks.jsonl"
    assert "private implementation" not in json.dumps(row)


def test_large_file_advisor_emits_content_free_primitive_intervention(tmp_path: Path) -> None:
    large_file = tmp_path / "large-private-file.txt"
    large_file.write_text("x" * 41000, encoding="utf-8")
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(large_file)}}

    result = subprocess.run(
        ["bash", str(LARGE_FILE_ADVISOR)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=_clean_env(tmp_path),
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    row = _ledger_rows(tmp_path)[-1]
    assert row["primitive_id"] == "large-file-advisor"
    assert row["primitive_source"] == "hooks/large-file-advisor.sh"
    assert row["tool"] == "Read"
    assert row["action_kind"] == "advise"
    assert row["reason_code"] == "large_file_read"
    assert row["target_ref"] == "large-file"
    assert row["source_metric"] == ".cognitive-os/metrics/large-file-reads.jsonl"
    assert str(large_file) not in json.dumps(row)
    assert "large-private-file" not in json.dumps(row)


def test_skill_router_bash_gate_emits_content_free_primitive_intervention(tmp_path: Path) -> None:
    payload = {"tool_name": "Bash", "tool_input": {"command": "pip install --upgrade private-package-name"}}

    result = subprocess.run(
        ["bash", str(SKILL_ROUTER_BASH_GATE)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=_clean_env(tmp_path),
        cwd=str(PROJECT_ROOT),
        timeout=10,
    )

    assert result.returncode == 2, result.stderr
    row = _ledger_rows(tmp_path)[-1]
    assert row["primitive_id"] == "skill-router"
    assert row["primitive_source"] == "hooks/skill-router-bash-gate.sh"
    assert row["tool"] == "Bash"
    assert row["action_kind"] == "block"
    assert row["reason_code"] == "dependency_update_bypass"
    assert row["target_ref"] == "dependency-update-command"
    assert row["source_metric"] == ".cognitive-os/metrics/skill-routing.jsonl"
    assert "private-package-name" not in json.dumps(row)
