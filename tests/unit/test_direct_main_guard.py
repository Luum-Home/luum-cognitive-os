"""Tests for ADR-116 direct-main local guard."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK = PROJECT_ROOT / "hooks" / "direct-main-guard.sh"

pytestmark = pytest.mark.unit


def init_repo(path: Path, branch: str = "main") -> None:
    subprocess.run(["git", "init", "-b", branch], cwd=path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "README.md").write_text("# test\n")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def run_hook(repo: Path, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update(env or {})
    merged_env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    merged_env.setdefault("CLAUDE_TOOL_INPUT", "git commit -m test -- README.md")
    return subprocess.run(["bash", str(HOOK)], cwd=repo, env=merged_env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def test_agent_commit_to_main_blocks(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    proc = run_hook(tmp_path, env={"COS_ACTOR": "agent"})
    assert proc.returncode == 2
    assert "BLOCK" in proc.stderr


def test_operator_commit_to_main_warns_by_default(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    proc = run_hook(tmp_path, env={"COS_ACTOR": "operator"})
    assert proc.returncode == 0
    assert "WARN" in proc.stderr


def test_operator_policy_block_blocks(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    proc = run_hook(tmp_path, env={"COS_ACTOR": "operator", "COS_OPERATOR_MAIN_POLICY": "block"})
    assert proc.returncode == 2
    assert "operator direct commit" in proc.stderr


def test_feature_branch_allows_agent(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    subprocess.run(["git", "switch", "-c", "session/test"], cwd=tmp_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc = run_hook(tmp_path, env={"COS_ACTOR": "agent"})
    assert proc.returncode == 0
    assert proc.stderr == ""


def test_allow_bypass_allows_agent_on_main(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    proc = run_hook(
        tmp_path,
        env={
            "COS_ACTOR": "agent",
            "COS_ALLOW_DIRECT_MAIN": "1",
            "COS_DIRECT_MAIN_BYPASS_REASON": "unit-test emergency commit",
        },
    )
    assert proc.returncode == 0
    assert proc.stderr == ""
    audit = tmp_path / ".cognitive-os" / "metrics" / "direct-main-bypass.jsonl"
    records = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
    assert records[-1]["action"] == "commit"
    assert records[-1]["reason"] == "unit-test emergency commit"


def test_direct_main_commit_bypass_requires_reason(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    proc = run_hook(tmp_path, env={"COS_ACTOR": "agent", "COS_ALLOW_DIRECT_MAIN": "1"})
    assert proc.returncode == 2
    assert "requires COS_DIRECT_MAIN_BYPASS_REASON" in proc.stderr


def test_operator_policy_allow_suppresses_warning(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    proc = run_hook(tmp_path, env={"COS_ACTOR": "operator", "COS_OPERATOR_MAIN_POLICY": "allow"})
    assert proc.returncode == 0
    assert proc.stderr == ""


def test_claude_agent_id_auto_detects_agent(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    proc = run_hook(tmp_path, env={"CLAUDE_AGENT_ID": "agent-123"})
    assert proc.returncode == 2
    assert "autonomous/session agents" in proc.stderr


def test_master_branch_is_guarded_like_main(tmp_path: Path) -> None:
    init_repo(tmp_path, "master")
    proc = run_hook(tmp_path, env={"COS_ACTOR": "agent"})
    assert proc.returncode == 2
    assert "master" in proc.stderr


def test_non_commit_bash_command_is_ignored(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    merged_env = os.environ.copy()
    merged_env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    merged_env["CLAUDE_TOOL_INPUT"] = "git status --short"
    proc = subprocess.run(["bash", str(HOOK)], cwd=tmp_path, env=merged_env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    assert proc.returncode == 0
    assert proc.stderr == ""


def test_non_bash_tool_input_is_ignored(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    payload = '{"tool_name":"Read","tool_input":{"command":"git commit -m test"}}'
    proc = subprocess.run(["bash", str(HOOK)], cwd=tmp_path, input=payload, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    assert proc.returncode == 0
    assert proc.stderr == ""


def test_direct_push_to_main_blocks(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    proc = run_hook(tmp_path, env={"COS_GIT_COMMAND": "git push", "CLAUDE_TOOL_INPUT": ""})
    assert proc.returncode == 2
    assert "direct push" in proc.stderr


def test_merge_queue_push_to_main_allows(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    proc = run_hook(
        tmp_path,
        env={"COS_GIT_COMMAND": "git push", "CLAUDE_TOOL_INPUT": "", "COS_MERGE_QUEUE_WORKER": "1"},
    )
    assert proc.returncode == 0
    assert proc.stderr == ""


def test_direct_push_bypass_requires_reason(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    proc = run_hook(
        tmp_path,
        env={"COS_GIT_COMMAND": "git push origin main", "CLAUDE_TOOL_INPUT": "", "COS_ALLOW_DIRECT_PUSH": "1"},
    )
    assert proc.returncode == 2
    assert "requires COS_DIRECT_MAIN_BYPASS_REASON" in proc.stderr


def test_direct_push_bypass_with_reason_is_audited(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    proc = run_hook(
        tmp_path,
        env={
            "COS_GIT_COMMAND": "git push origin main",
            "CLAUDE_TOOL_INPUT": "",
            "COS_ALLOW_DIRECT_PUSH": "1",
            "COS_BYPASS_REASON": "unit-test emergency push",
        },
    )
    assert proc.returncode == 0
    assert proc.stderr == ""
    audit = tmp_path / ".cognitive-os" / "metrics" / "direct-main-bypass.jsonl"
    records = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
    assert records[-1]["action"] == "push"
    assert records[-1]["reason"] == "unit-test emergency push"


def test_pre_push_refs_non_main_allows(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    refs = "refs/heads/session/x abc refs/heads/session/x def"
    proc = run_hook(
        tmp_path,
        env={"COS_GIT_COMMAND": "git push", "CLAUDE_TOOL_INPUT": "", "COS_PRE_PUSH_REFS": refs},
    )
    assert proc.returncode == 0
    assert proc.stderr == ""


def test_direct_push_delete_non_main_branch_from_main_allows(tmp_path: Path) -> None:
    """Deleting a non-protected remote branch from local main is not a direct-main push."""
    init_repo(tmp_path, "main")
    proc = run_hook(
        tmp_path,
        env={"COS_GIT_COMMAND": "git push origin --delete codex/old-branch", "CLAUDE_TOOL_INPUT": ""},
    )
    assert proc.returncode == 0
    assert proc.stderr == ""


def test_direct_push_explicit_main_ref_blocks(tmp_path: Path) -> None:
    init_repo(tmp_path, "main")
    proc = run_hook(
        tmp_path,
        env={"COS_GIT_COMMAND": "git push origin main", "CLAUDE_TOOL_INPUT": ""},
    )
    assert proc.returncode == 2
    assert "direct push" in proc.stderr


def test_push_block_message_lists_both_bypass_vars(tmp_path: Path) -> None:
    """Contract: the BLOCK message must mention BOTH env vars required for bypass.

    Operators following the hint should not have to fail twice (once for the
    intent flag, again for the missing reason). Both env vars must appear in
    one shot. See `_require_bypass_reason()` in the hook for the second-line
    defense; this test pins the first-line UX.
    """
    init_repo(tmp_path, "main")
    proc = run_hook(tmp_path, env={"COS_GIT_COMMAND": "git push origin main", "CLAUDE_TOOL_INPUT": ""})
    assert proc.returncode == 2
    assert "COS_ALLOW_DIRECT_PUSH=1" in proc.stderr
    assert "COS_DIRECT_MAIN_BYPASS_REASON" in proc.stderr


def test_agent_commit_block_message_lists_both_bypass_vars(tmp_path: Path) -> None:
    """Same contract for agent commit-to-main BLOCK: both env vars in one hint."""
    init_repo(tmp_path, "main")
    proc = run_hook(tmp_path, env={"CLAUDE_AGENT_ID": "agent-test"})
    assert proc.returncode == 2
    assert "COS_ALLOW_DIRECT_MAIN=1" in proc.stderr
    assert "COS_DIRECT_MAIN_BYPASS_REASON" in proc.stderr
