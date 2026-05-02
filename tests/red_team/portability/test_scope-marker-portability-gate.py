# SCOPE: both
"""Portability probes for hooks/scope-marker-portability-gate.sh — ADR-111 consumer projection.

Verifies that the scope-marker-portability-gate fires equivalently under
simulated Codex invocation (PreToolUse[Bash] matcher, COGNITIVE_OS_HARNESS=codex).

Projection type: bash-projectable (native Codex PreToolUse bash matcher).

Paired with: hooks/scope-marker-portability-gate.sh  (# SCOPE: both)
ADR reference: ADR-111 §Gate-2
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks" / "scope-marker-portability-gate.sh"

SCRUB_VARS = (
    "CI",
    "PYTEST_CURRENT_TEST",
    "COS_ALLOW_UNPROVEN_SCOPE_BOTH",
    "COGNITIVE_OS_SESSION_ID",
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
            "COGNITIVE_OS_HARNESS": "codex",
            "COGNITIVE_OS_PROJECT_DIR": str(project),
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
        timeout=20,
    )


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=path, check=True, capture_output=True)


def _stage_scope_both_hook(path: Path, stem: str) -> Path:
    """Stage a hook file with SCOPE: both and no portability test."""
    hooks_dir = path / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_file = hooks_dir / f"{stem}.sh"
    hook_file.write_text(f"#!/usr/bin/env bash\n# SCOPE: both\necho hello\n")
    subprocess.run(["git", "add", str(hook_file)], cwd=path, check=True, capture_output=True)
    return hook_file


def _add_portability_test(path: Path, stem: str) -> Path:
    """Add a portability test file and stage it."""
    tests_dir = path / "tests" / "red_team" / "portability"
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_file = tests_dir / f"{stem}.bats"
    test_file.write_text(f"# portability test for {stem}\n@test 'fires' {{ true; }}\n")
    subprocess.run(["git", "add", str(test_file)], cwd=path, check=True, capture_output=True)
    return test_file


# ---------------------------------------------------------------------------
# Portability: hook fires under simulated Codex environment
# ---------------------------------------------------------------------------


def test_non_commit_command_passthrough_under_codex(tmp_path: Path) -> None:
    """Non-git-commit commands are allowed without inspection under Codex harness."""
    _init_repo(tmp_path)
    result = _run("echo hello world", tmp_path)
    assert result.returncode == 0, (
        f"portability: non-commit command must pass through; got {result.returncode}\n"
        f"{result.stderr}"
    )


def test_commit_with_scope_both_no_test_blocked_under_codex(tmp_path: Path) -> None:
    """git commit blocked when staged SCOPE: both file has no portability test under Codex harness."""
    _init_repo(tmp_path)
    _stage_scope_both_hook(tmp_path, "my-new-gate")
    result = _run("git commit -m 'add my-new-gate'", tmp_path)
    assert result.returncode == 2, (
        f"portability: Codex harness must block commit for SCOPE: both without portability test; "
        f"got {result.returncode}\n{result.stderr}"
    )
    assert "scope-marker-portability-gate" in result.stderr


def test_commit_with_scope_both_and_test_allowed_under_codex(tmp_path: Path) -> None:
    """git commit allowed when staged SCOPE: both file has paired portability test under Codex harness."""
    _init_repo(tmp_path)
    _stage_scope_both_hook(tmp_path, "my-proven-gate")
    _add_portability_test(tmp_path, "my-proven-gate")
    result = _run("git commit -m 'add my-proven-gate with test'", tmp_path)
    assert result.returncode == 0, (
        f"portability: Codex harness must allow commit when portability test exists; "
        f"got {result.returncode}\n{result.stderr}"
    )


def test_bypass_env_accepted_under_codex(tmp_path: Path) -> None:
    """COS_ALLOW_UNPROVEN_SCOPE_BOTH=1 bypass is accepted under Codex harness."""
    _init_repo(tmp_path)
    _stage_scope_both_hook(tmp_path, "emergency-gate")
    result = _run(
        "git commit -m 'emergency'",
        tmp_path,
        extra_env={"COS_ALLOW_UNPROVEN_SCOPE_BOTH": "1"},
    )
    assert result.returncode == 0, (
        f"portability: bypass env var must allow exit 0 under Codex; got {result.returncode}\n"
        f"{result.stderr}"
    )


def test_portability_test_files_self_exempt(tmp_path: Path) -> None:
    """Files under tests/red_team/portability/ are exempt from the gate under Codex harness."""
    _init_repo(tmp_path)
    tests_dir = tmp_path / "tests" / "red_team" / "portability"
    tests_dir.mkdir(parents=True, exist_ok=True)
    portability_file = tests_dir / "my-gate.bats"
    portability_file.write_text("# SCOPE: both\n@test 'fires' {{ true; }}\n")
    subprocess.run(["git", "add", str(portability_file)], cwd=tmp_path, check=True, capture_output=True)
    result = _run("git commit -m 'add portability test'", tmp_path)
    assert result.returncode == 0, (
        f"portability: files under tests/red_team/portability/ must be self-exempt; "
        f"got {result.returncode}\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# Falsification: bypass must NOT silence the gate without env var
# ---------------------------------------------------------------------------


def test_falsification_gate_not_bypassed_without_env_var(tmp_path: Path) -> None:
    """Without COS_ALLOW_UNPROVEN_SCOPE_BOTH the gate must block, not allow."""
    _init_repo(tmp_path)
    _stage_scope_both_hook(tmp_path, "unpaired-gate")
    result = _run("git commit -m 'add unpaired'", tmp_path)
    assert result.returncode != 0, (
        "falsification: scope-marker-portability-gate must NOT allow commit "
        "without paired portability test and without bypass env var"
    )
