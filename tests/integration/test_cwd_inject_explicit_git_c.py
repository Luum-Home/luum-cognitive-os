"""
tests/integration/test_cwd_inject_explicit_git_c.py

Regression shield: agent-working-dir-inject.sh MUST emit explicit `git -C`
and `cd <path> &&` guidance in its additionalContext. These tests fail if the
injected text regresses to the old advisory-only wording.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
HOOK_PATH = REPO_ROOT / "hooks" / "agent-working-dir-inject.sh"
FAKE_STDIN = json.dumps({"tool_name": "Agent", "prompt": "do something"})


def _make_yaml(tmp_path: Path, policy: str) -> None:
    config = tmp_path / "cognitive-os.yaml"
    config.write_text(
        f"orchestration:\n  sub_agent_cwd: {policy}\n\nefficiency:\n  profile: default\n"
    )


def _fake_git_shim(tmp_path: Path, worktree_output: str) -> Path:
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    fake_git = shim_dir / "git"
    real_git = shutil.which("git") or "/usr/bin/git"
    fake_git.write_text(
        f"""#!/usr/bin/env bash
if [ "${{@}}" = "worktree list --porcelain" ] || \\
   ([ "$2" = "worktree" ] && [ "$3" = "list" ] && [ "$4" = "--porcelain" ]); then
  printf '%s' {repr(worktree_output)}
  exit 0
fi
exec {real_git} "$@"
"""
    )
    fake_git.chmod(fake_git.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return shim_dir


def _run_hook(tmp_path: Path, shim: Path) -> str:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    env["SO_KILLSWITCH"] = "0"
    env["PATH"] = f"{shim}:{env.get('PATH', '')}"

    result = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=FAKE_STDIN,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    assert result.returncode == 0, f"Hook exited {result.returncode}; stderr={result.stderr}"

    stdout = result.stdout.strip()
    if not stdout:
        return ""
    try:
        data = json.loads(stdout)
        return data.get("hookSpecificOutput", {}).get("additionalContext", "")
    except json.JSONDecodeError:
        return stdout


def _init_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "--allow-empty", "-m", "init"],
        check=True,
        capture_output=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.com",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.com"},
    )


# ── Test 1: injected text MUST contain `git -C` ──────────────────────────────

def test_injected_text_contains_git_dash_c(tmp_path: Path) -> None:
    """Injected additionalContext must include the literal string 'git -C'."""
    _init_repo(tmp_path)
    _make_yaml(tmp_path, "main_worktree")
    wt_output = f"worktree {tmp_path}\nHEAD abc123\nbranch refs/heads/main\n\n"
    shim = _fake_git_shim(tmp_path, wt_output)

    context = _run_hook(tmp_path, shim)

    # Behavioral: context must be non-empty (hook produced output)
    assert len(context) > 0, f"Expected non-empty context, got empty string"
    # Behavioral: context must contain the path we configured
    assert str(tmp_path) == context.splitlines()[0].split("WORKING DIR: ", 1)[-1], (
        f"First line must be 'WORKING DIR: {tmp_path}'"
    )
    assert "git -C" in context, (
        f"'git -C' not found in injected context.\n"
        f"Got: {context!r}\n"
        f"The advisory MUST include an explicit `git -C <path>` example."
    )


# ── Test 2: injected text MUST contain both `cd <path> &&` and `git -C <path>` ─

def test_injected_text_contains_cd_and_git_c_examples(tmp_path: Path) -> None:
    """Injected text must show both `cd <path> &&` AND `git -C <path>` alternatives."""
    _init_repo(tmp_path)
    _make_yaml(tmp_path, "main_worktree")
    wt_output = f"worktree {tmp_path}\nHEAD abc123\nbranch refs/heads/main\n\n"
    shim = _fake_git_shim(tmp_path, wt_output)

    context = _run_hook(tmp_path, shim)

    # Behavioral: context length should be significant (full advisory, not 1-liner)
    assert len(context) > 100, (
        f"Expected substantial advisory text (>100 chars), got {len(context)} chars: {context!r}"
    )
    # Behavioral: the path referenced in context must match the resolved worktree
    lines_with_path = [l for l in context.splitlines() if str(tmp_path) in l]
    assert len(lines_with_path) >= 2, (
        f"Expected the resolved path to appear in multiple advisory lines, got: {lines_with_path}"
    )
    assert "git -C" in context, (
        f"'git -C' not found in injected context: {context!r}"
    )
    assert "cd " in context and "&&" in context, (
        f"Expected a `cd <path> &&` example in context.\n"
        f"Got: {context!r}\n"
        f"The advisory MUST include both methods to scope git operations."
    )


# ── Test 3: missing explicit guidance = test fails (regression shield) ────────

def test_no_vague_advisory_only(tmp_path: Path) -> None:
    """
    The OLD advisory said 'Commits land on the branch checked out at that path.'
    That's vague. The new advisory MUST NOT rely solely on that phrasing;
    it MUST contain an actionable `git -C` example.

    Behavioral: policy=current must return empty context (no injection),
    while main_worktree must return non-empty context with `git -C`.
    This tests the conditional code path, not just string presence.
    """
    _init_repo(tmp_path)

    # Behavioral: policy=current returns NO context
    _make_yaml(tmp_path, "current")
    wt_output = f"worktree {tmp_path}\nHEAD abc123\nbranch refs/heads/main\n\n"
    shim = _fake_git_shim(tmp_path, wt_output)
    context_current = _run_hook(tmp_path, shim)
    assert len(context_current) == 0, (
        f"policy=current MUST return empty context, got: {context_current!r}"
    )

    # Behavioral: policy=main_worktree returns non-empty context
    _make_yaml(tmp_path, "main_worktree")
    context_main = _run_hook(tmp_path, shim)
    assert len(context_main) > 0, (
        f"policy=main_worktree MUST return non-empty context"
    )

    # Regression shield: context must differ between policies (tests branching logic)
    assert context_main != context_current, (
        "Context for main_worktree must differ from context for current"
    )

    # String guards (secondary, not the primary behavioral test)
    assert "git -C" in context_main, (
        f"REGRESSION: injected context lacks explicit `git -C` guidance.\n"
        f"Got: {context_main!r}\n"
        f"Do not revert to advisory-only text without an actionable example."
    )
    assert "CRITICAL" in context_main or "MUST" in context_main, (
        f"Expected strong language (CRITICAL / MUST) in injected context.\n"
        f"Got: {context_main!r}\n"
        f"The advisory must convey urgency, not just hint."
    )
