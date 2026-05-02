# SCOPE: both
"""Portability proofs for hooks/orchestrator-claim-gate.sh.

These tests invoke the hook against a minimal, non-SO repository to prove that
the claim-gate logic does not depend on luum-agent-os project-local runtime
state, environment variables, or installed tooling specific to this project.

Three proofs:
  1. Non-git commands are ignored (exit 0) in a foreign repo.
  2. A commit command with no high-stakes claim passes in a foreign repo.
  3. Falsification: hook without jq or python3 must exit 0 (fail-open), not 2.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks" / "orchestrator-claim-gate.sh"

SCRUB_VARS = (
    "CI",
    "PYTEST_CURRENT_TEST",
    "COS_ORCHESTRATOR_CLAIM_GATE_MODE",
    "COS_PUSH_COLLISION_MODE",
    "COGNITIVE_OS_SESSION_ID",
    "ORCHESTRATOR_MODE",
)


def _run(
    command: str,
    project: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    env = os.environ.copy()
    for var in SCRUB_VARS:
        env.pop(var, None)
    env.update(
        {
            "CLAUDE_PROJECT_DIR": str(project),
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
    )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial commit"],
        cwd=path,
        check=True,
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# Proof 1: Non-git command is transparently ignored
# ---------------------------------------------------------------------------


def test_non_git_command_exits_0_in_foreign_repo(tmp_path: Path) -> None:
    """Non-git commands must be passed through (exit 0) in a foreign repo."""
    _init_repo(tmp_path)
    result = _run("echo hello", tmp_path)
    assert result.returncode == 0, (
        f"portability: non-git command must exit 0; got {result.returncode}\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Proof 2: Commit with no high-stakes claim passes
# ---------------------------------------------------------------------------


def test_simple_commit_no_claim_exits_0(tmp_path: Path) -> None:
    """A mundane git commit message with no high-stakes claims must pass."""
    _init_repo(tmp_path)
    result = _run('git commit -m "fix: minor typo in README"', tmp_path)
    assert result.returncode == 0, (
        f"portability: plain commit must pass in foreign repo; got {result.returncode}\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Proof 3 (Falsification): When scripts are missing the hook must fail open
# ---------------------------------------------------------------------------


def test_missing_python_script_fails_open(tmp_path: Path) -> None:
    """Portability falsification: if the gate Python script is absent, hook exits 0.

    The gate must never block when its own infrastructure is unavailable —
    it should fail open rather than creating a hard dependency on a specific
    project layout.
    """
    # Use an empty directory that has no orchestrator_claim_gate.py
    empty_project = tmp_path / "empty_project"
    empty_project.mkdir()
    _init_repo(empty_project)
    result = _run('git commit -m "feat: something"', empty_project)
    # With no scripts/orchestrator_claim_gate.py the hook must exit 0 (fail open)
    assert result.returncode == 0, (
        f"falsification: hook must fail open when Python script absent; "
        f"got {result.returncode}\nstderr: {result.stderr}"
    )
