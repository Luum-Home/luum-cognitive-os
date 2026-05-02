# SCOPE: both
"""Portability probes for hooks/symlink-mutation-guard.sh — ADR-111 consumer projection.

Verifies that the symlink-mutation-guard fires equivalently under simulated
Codex invocation (PreToolUse[Bash] matcher, COGNITIVE_OS_HARNESS=codex).

Projection type: bash-projectable (native Codex PreToolUse bash matcher).

Paired with: hooks/symlink-mutation-guard.sh  (# SCOPE: both)
ADR reference: ADR-111 §Gate-1
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks" / "symlink-mutation-guard.sh"

SCRUB_VARS = (
    "CI",
    "PYTEST_CURRENT_TEST",
    "COS_ALLOW_SYMLINK_MUTATION",
    "DISABLE_HOOK_SYMLINK_MUTATION_GUARD",
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
            "CLAUDE_PROJECT_DIR": str(project),
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


def _make_symlink_dir(base: Path) -> Path:
    """Create a real directory and a symlink to it, replicating the 2026-05-02 topology."""
    real = base / "real_lib"
    real.mkdir(parents=True)
    link = base / "lib"
    link.symlink_to(real)
    return link


# ---------------------------------------------------------------------------
# Portability: hook fires under simulated Codex environment
# ---------------------------------------------------------------------------


def test_non_symlink_path_allowed_under_codex(tmp_path: Path) -> None:
    """Normal ln -s with non-symlink parent is allowed under Codex harness."""
    result = _run(f"ln -s /some/absolute/target {tmp_path}/newlink", tmp_path)
    assert result.returncode == 0, (
        f"portability: clean ln -s should be allowed; got {result.returncode}\n"
        f"{result.stderr}"
    )


def test_ln_relative_into_symlink_parent_blocked_under_codex(tmp_path: Path) -> None:
    """ln -s with relative target into directory-symlink parent is blocked under Codex harness."""
    link_dir = _make_symlink_dir(tmp_path)
    # Relative target — will not resolve correctly through symlink ancestor
    command = f"ln -s ../../other.py {link_dir}/codex.py"
    result = _run(command, tmp_path)
    assert result.returncode == 2, (
        f"portability: Codex harness must block ln -s with relative target under symlink ancestor; "
        f"got {result.returncode}\n{result.stderr}"
    )
    assert "SYMLINK-MUTATION-GUARD" in result.stderr


def test_rm_under_symlink_parent_warns_under_codex(tmp_path: Path) -> None:
    """rm on path under directory-symlink ancestor emits warning under Codex harness."""
    link_dir = _make_symlink_dir(tmp_path)
    target_file = tmp_path / "real_lib" / "some_file.py"
    target_file.write_text("# placeholder\n")
    command = f"rm {link_dir}/some_file.py"
    result = _run(command, tmp_path)
    # Soft warn — must not block (exit 0)
    assert result.returncode == 0, (
        f"portability: rm under symlink-parent should warn (exit 0), not block; "
        f"got {result.returncode}\n{result.stderr}"
    )
    assert "symlink-mutation-guard" in result.stderr.lower() or "WARN" in result.stderr


def test_bypass_env_var_accepted_under_codex(tmp_path: Path) -> None:
    """COS_ALLOW_SYMLINK_MUTATION=1 bypass is accepted under Codex harness."""
    link_dir = _make_symlink_dir(tmp_path)
    command = f"ln -s ../relative/path {link_dir}/link.py"
    result = _run(command, tmp_path, extra_env={"COS_ALLOW_SYMLINK_MUTATION": "1"})
    assert result.returncode == 0, (
        f"portability: bypass env var must allow exit 0 under Codex; got {result.returncode}\n"
        f"{result.stderr}"
    )


def test_non_bash_tool_passthrough_under_codex(tmp_path: Path) -> None:
    """Non-Bash tool_name is ignored (exit 0) under Codex harness."""
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(tmp_path / "x.py"), "new_string": "x"}}
    env = os.environ.copy()
    for var in SCRUB_VARS:
        env.pop(var, None)
    env.update(
        {
            "COGNITIVE_OS_HARNESS": "codex",
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        }
    )
    result = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"portability: Edit tool_name must be ignored (exit 0) by Bash-only hook under Codex; "
        f"got {result.returncode}"
    )


# ---------------------------------------------------------------------------
# Falsification: bypass must NOT silence the guard without the env var
# ---------------------------------------------------------------------------


def test_falsification_guard_not_bypassed_without_env_var(tmp_path: Path) -> None:
    """Without COS_ALLOW_SYMLINK_MUTATION the guard must block, not allow."""
    link_dir = _make_symlink_dir(tmp_path)
    command = f"ln -s ../../other.py {link_dir}/codex.py"
    result = _run(command, tmp_path)
    assert result.returncode != 0, (
        "falsification: symlink-mutation-guard must NOT allow relative ln -s "
        "into symlink parent without bypass env var"
    )
