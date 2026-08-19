# SCOPE: both
"""Behavioural test for the symlink mutation guard.

The hook is the only one of the three PreToolUse/PostToolUse primitives audited
on 2026-08-19 that can actually *deny*: it exits 2 and writes to stderr. Nothing
here greps the hook source — every case builds a real directory-symlink topology
(the 2026-05-02 `lib/harness_adapter` incident, reproduced), feeds a real
PreToolUse payload to the real script and asserts on exit code and stderr.

Both directions are covered on purpose:
  * the `ln -s <relative> <path-under-a-dir-symlink>` shape MUST be blocked;
  * an absolute target, a path with no symlink ancestor, a non-Bash tool call
    and the documented bypass MUST all pass — a guard that blocks everything is
    as broken as one that blocks nothing;
  * `rm` under a directory symlink MUST warn on stderr and still exit 0, because
    detector 2 is a soft detector and silently promoting it to a block would
    stop legitimate work.

Falsification run (see the report of 2026-08-19): point
``COS_TEST_HOOK_SOURCE_DIR`` at a copy of the hook whose ``exit 2`` was removed
and the blocking cases go red while the permissive cases stay green.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_REL = "hooks/symlink-mutation-guard.sh"
HOOK_BASENAME = "symlink-mutation-guard.sh"
BLOCK_BANNER = "SYMLINK-MUTATION-GUARD: BLOCKED"
WARN_PREFIX = "[symlink-mutation-guard] WARN:"

# Real target of the hook's detector 1: a package directory exposed through a
# directory symlink, exactly like lib/harness_adapter in this repo.
REAL_DIR = "packages/agent-lifecycle/lib/harness_adapter"
LINK_DIR = "lib/harness_adapter"


def _hook_source() -> Path:
    """Where to copy the hook from — overridable only for the falsification run."""
    override = os.environ.get("COS_TEST_HOOK_SOURCE_DIR")
    base = Path(override) if override else REPO_ROOT
    return base / HOOK_REL


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    # resolve() matters: on macOS /var is itself a symlink, and an unresolved
    # tmp path would make every case look like it lives under a symlink.
    repo = (tmp_path / "repo").resolve()
    (repo / REAL_DIR).mkdir(parents=True)
    (repo / REAL_DIR / "codex.py").write_text("# real file\n", encoding="utf-8")
    (repo / "lib").mkdir(parents=True)
    (repo / LINK_DIR).symlink_to(repo / REAL_DIR)
    (repo / "scripts" / "plain").mkdir(parents=True)
    (repo / "scripts" / "plain" / "a.py").write_text("# plain\n", encoding="utf-8")
    (repo / "hooks").mkdir(parents=True)
    shutil.copy(_hook_source(), repo / HOOK_REL)
    (repo / HOOK_REL).chmod(0o755)
    return repo


def run_hook(repo: Path, command: str, tool: str = "Bash", **env_extra: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": tool, "tool_input": {"command": command}})
    env = dict(os.environ)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env.pop("COS_ALLOW_SYMLINK_MUTATION", None)
    env.pop("DISABLE_HOOK_SYMLINK_MUTATION_GUARD", None)
    env.update(env_extra)
    # /bin/bash is 3.2 on macOS: the guard must run there, not only under
    # whichever bash the PATH happens to expose.
    return subprocess.run(
        ["/bin/bash", str(repo / HOOK_REL)],
        input=payload,
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo),
        timeout=30,
    )


# --- must deny ---------------------------------------------------------------


def test_blocks_relative_symlink_under_symlinked_parent(repo: Path) -> None:
    """The 2026-05-02 incident shape. This is the whole reason the hook exists."""
    result = run_hook(repo, f"ln -s ../../{REAL_DIR}/codex.py {LINK_DIR}/codex.py")
    assert result.returncode == 2, f"guard did not deny: {result.stdout}{result.stderr}"
    assert BLOCK_BANNER in result.stderr
    assert LINK_DIR in result.stderr


def test_blocks_regardless_of_flag_spelling(repo: Path) -> None:
    """`ln -sfn` is the spelling agents actually type when relinking."""
    result = run_hook(repo, f"ln -sfn ../{REAL_DIR}/codex.py {LINK_DIR}/other.py")
    assert result.returncode == 2, f"guard did not deny: {result.stdout}{result.stderr}"
    assert BLOCK_BANNER in result.stderr


def test_blocks_when_the_link_sits_deeper_under_the_symlink(repo: Path) -> None:
    (repo / REAL_DIR / "sub").mkdir()
    result = run_hook(repo, f"ln -s ../codex.py {LINK_DIR}/sub/codex.py")
    assert result.returncode == 2, f"guard did not deny: {result.stdout}{result.stderr}"


# --- must NOT deny -----------------------------------------------------------


def test_absolute_target_is_allowed(repo: Path) -> None:
    """Absolute targets resolve unambiguously — blocking them would be noise."""
    result = run_hook(repo, f"ln -s {repo}/{REAL_DIR}/codex.py {LINK_DIR}/codex.py")
    assert result.returncode == 0, result.stderr
    assert BLOCK_BANNER not in result.stderr


def test_relative_link_without_symlink_ancestor_is_allowed(repo: Path) -> None:
    result = run_hook(repo, "ln -s ../plain/a.py scripts/plain/b.py")
    assert result.returncode == 0, result.stderr
    assert result.stderr.strip() == ""


def test_non_bash_tool_is_ignored(repo: Path) -> None:
    payload_cmd = f"ln -s ../../{REAL_DIR}/codex.py {LINK_DIR}/codex.py"
    result = run_hook(repo, payload_cmd, tool="Edit")
    assert result.returncode == 0, result.stderr
    assert result.stderr.strip() == ""


def test_documented_bypass_lets_the_blocked_shape_through(repo: Path) -> None:
    result = run_hook(
        repo,
        f"ln -s ../../{REAL_DIR}/codex.py {LINK_DIR}/codex.py",
        COS_ALLOW_SYMLINK_MUTATION="1",
    )
    assert result.returncode == 0, result.stderr
    assert BLOCK_BANNER not in result.stderr


def test_killswitch_disables_the_guard(repo: Path) -> None:
    result = run_hook(
        repo,
        f"ln -s ../../{REAL_DIR}/codex.py {LINK_DIR}/codex.py",
        DISABLE_HOOK_SYMLINK_MUTATION_GUARD="true",
    )
    assert result.returncode == 0, result.stderr


# --- soft detector: warns, never denies --------------------------------------


def test_rm_under_directory_symlink_warns_without_blocking(repo: Path) -> None:
    result = run_hook(repo, f"rm {LINK_DIR}/codex.py")
    assert result.returncode == 0, f"detector 2 must not block: {result.stderr}"
    assert WARN_PREFIX in result.stderr
    assert LINK_DIR in result.stderr


def test_rm_outside_symlink_topology_is_silent(repo: Path) -> None:
    result = run_hook(repo, "rm scripts/plain/a.py")
    assert result.returncode == 0, result.stderr
    assert WARN_PREFIX not in result.stderr


def test_empty_stdin_is_survivable(repo: Path) -> None:
    env = dict(os.environ)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    result = subprocess.run(
        ["/bin/bash", str(repo / HOOK_REL)],
        input="",
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo),
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
