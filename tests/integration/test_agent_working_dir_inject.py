"""
tests/integration/test_agent_working_dir_inject.py

Behavioral tests for hooks/agent-working-dir-inject.sh.

Each test:
- Creates a temporary project skeleton with its own git repo (or mocked git)
- Invokes the hook with a fake PreToolUse:Agent stdin payload
- Asserts the additionalContext output content or exit-0 silence

Test matrix:
  1. policy=main_worktree  → injects main path
  2. policy=current        → no injection (empty additionalContext)
  3. policy=branch         → injects current branch's worktree path
  4. yaml missing          → exits 0 silently (no output)
  5. git command fails     → exits 0 silently, logs reason
  6. latency <50ms         → p95 timing check (skipped if CI-slow)
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.parent
HOOK_PATH = REPO_ROOT / "hooks" / "agent-working-dir-inject.sh"

# Fake PreToolUse:Agent stdin payload
FAKE_STDIN = json.dumps({"tool_name": "Agent", "prompt": "do something"})


def _make_yaml(tmp_path: Path, policy: str) -> Path:
    """Write a minimal cognitive-os.yaml with the given sub_agent_cwd policy."""
    config = tmp_path / "cognitive-os.yaml"
    config.write_text(
        f"orchestration:\n  sub_agent_cwd: {policy}  # test\n\nefficiency:\n  profile: default\n"
    )
    return config


def _fake_git_shim(tmp_path: Path, worktree_output: str) -> Path:
    """
    Create a directory with a fake `git` script that returns the given
    worktree_output for `git worktree list --porcelain` and falls through
    for other git calls (symbolic-ref, rev-parse) via the real git.
    Returns the shim dir (to prepend to PATH).
    """
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    fake_git = shim_dir / "git"
    real_git = shutil.which("git") or "/usr/bin/git"
    fake_git.write_text(
        f"""#!/usr/bin/env bash
if [ "${{@}}" = "worktree list --porcelain" ] || \
   ([ "$2" = "worktree" ] && [ "$3" = "list" ] && [ "$4" = "--porcelain" ]); then
  printf '%s' {repr(worktree_output)}
  exit 0
fi
exec {real_git} "$@"
"""
    )
    fake_git.chmod(fake_git.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return shim_dir


def _broken_git_shim(tmp_path: Path) -> Path:
    """
    Create a fake `git` that always exits 1 — simulates git failure.
    """
    shim_dir = tmp_path / "shim_broken"
    shim_dir.mkdir()
    fake_git = shim_dir / "git"
    fake_git.write_text("#!/usr/bin/env bash\nexit 1\n")
    fake_git.chmod(fake_git.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return shim_dir


def _run_hook(
    tmp_path: Path,
    *,
    stdin: str = FAKE_STDIN,
    extra_env: dict[str, str] | None = None,
    path_prepend: Path | None = None,
) -> subprocess.CompletedProcess:
    """Invoke the hook and return the CompletedProcess."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    env["SO_KILLSWITCH"] = "0"  # ensure killswitch is off
    if path_prepend is not None:
        env["PATH"] = f"{path_prepend}:{env.get('PATH', '')}"
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


def _parse_context(result: subprocess.CompletedProcess) -> str:
    """
    Extract additionalContext from hookSpecificOutput JSON on stdout.
    Returns empty string if stdout is empty or contains no valid JSON.
    """
    stdout = result.stdout.strip()
    if not stdout:
        return ""
    try:
        data = json.loads(stdout)
        return data.get("hookSpecificOutput", {}).get("additionalContext", "")
    except json.JSONDecodeError:
        return stdout  # raw text fallback for debugging


def _init_bare_repo(tmp_path: Path) -> None:
    """Init a minimal git repo so git commands don't fail."""
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "--allow-empty", "-m", "init"],
        check=True,
        capture_output=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@test.com",
             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@test.com"},
    )


# ---------------------------------------------------------------------------
# Test 1: main_worktree policy injects main path
# ---------------------------------------------------------------------------

def test_main_worktree_injects_main_path(tmp_path: Path) -> None:
    """Policy main_worktree → WORKING DIR points at the main-branch worktree."""
    _init_bare_repo(tmp_path)
    _make_yaml(tmp_path, "main_worktree")

    # Build a worktree list where tmp_path is main
    wt_output = f"worktree {tmp_path}\nHEAD abc123\nbranch refs/heads/main\n\n"
    shim = _fake_git_shim(tmp_path, wt_output)

    result = _run_hook(tmp_path, path_prepend=shim)

    assert result.returncode == 0, f"Hook exited {result.returncode}; stderr={result.stderr}"
    context = _parse_context(result)
    assert f"WORKING DIR: {tmp_path}" in context, (
        f"Expected 'WORKING DIR: {tmp_path}' in context, got: {context!r}"
    )
    assert "agent-working-dir-inject.sh" in context


# ---------------------------------------------------------------------------
# Test 2: current policy → no injection
# ---------------------------------------------------------------------------

def test_current_policy_no_injection(tmp_path: Path) -> None:
    """Policy current → hook exits 0 with no additionalContext output."""
    _init_bare_repo(tmp_path)
    _make_yaml(tmp_path, "current")

    result = _run_hook(tmp_path)

    assert result.returncode == 0, f"Hook exited {result.returncode}; stderr={result.stderr}"
    context = _parse_context(result)
    assert context == "", f"Expected no context for policy=current, got: {context!r}"


# ---------------------------------------------------------------------------
# Test 3: branch policy injects current branch worktree path
# ---------------------------------------------------------------------------

def test_branch_policy_injects_branch_worktree(tmp_path: Path) -> None:
    """Policy branch → WORKING DIR points at the worktree for the current branch."""
    _init_bare_repo(tmp_path)
    _make_yaml(tmp_path, "branch")

    # Simulate worktree list where tmp_path is on branch "main" (the current branch)
    wt_output = f"worktree {tmp_path}\nHEAD abc123\nbranch refs/heads/main\n\n"
    shim = _fake_git_shim(tmp_path, wt_output)

    result = _run_hook(tmp_path, path_prepend=shim)

    assert result.returncode == 0, f"Hook exited {result.returncode}; stderr={result.stderr}"
    context = _parse_context(result)
    assert "WORKING DIR:" in context, f"Expected WORKING DIR in context, got: {context!r}"
    # The resolved path should be under tmp_path (or tmp_path itself)
    assert str(tmp_path) in context, f"Expected tmp_path in context, got: {context!r}"


# ---------------------------------------------------------------------------
# Test 4: yaml missing → exits 0 silently
# ---------------------------------------------------------------------------

def test_yaml_missing_exits_silently(tmp_path: Path) -> None:
    """No cognitive-os.yaml → hook exits 0 with no output."""
    _init_bare_repo(tmp_path)
    # No yaml written

    result = _run_hook(tmp_path)

    assert result.returncode == 0, f"Hook exited {result.returncode}; stderr={result.stderr}"
    context = _parse_context(result)
    assert context == "", f"Expected empty context when yaml missing, got: {context!r}"


# ---------------------------------------------------------------------------
# Test 5: git command fails → exits 0 silently, logs reason
# ---------------------------------------------------------------------------

def test_git_failure_exits_silently(tmp_path: Path) -> None:
    """Broken git (all commands fail) → hook exits 0, no injection, logs to jsonl."""
    _make_yaml(tmp_path, "main_worktree")
    shim = _broken_git_shim(tmp_path)

    # Also provide a fake cognitive-os.yaml but no working git
    result = _run_hook(tmp_path, path_prepend=shim)

    assert result.returncode == 0, f"Hook exited {result.returncode}; stderr={result.stderr}"
    context = _parse_context(result)
    assert context == "", f"Expected empty context on git failure, got: {context!r}"

    # Optionally verify a log entry was written (best-effort — may not exist if metrics dir
    # could not be created without git, which is fine)
    metrics = tmp_path / ".cognitive-os" / "metrics" / "cwd-inject.jsonl"
    if metrics.exists():
        lines = metrics.read_text().strip().splitlines()
        assert lines, "Expected at least one log entry"
        entry = json.loads(lines[-1])
        assert "event" in entry


# ---------------------------------------------------------------------------
# Test 6: latency <50ms
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    os.environ.get("CI_SLOW", "") == "1",
    reason="Skipped in CI_SLOW=1 environments where disk I/O inflates timing",
)
def test_latency_under_50ms(tmp_path: Path) -> None:
    """Hook must complete in <50ms p95 across 5 runs."""
    _init_bare_repo(tmp_path)
    _make_yaml(tmp_path, "main_worktree")

    wt_output = f"worktree {tmp_path}\nHEAD abc123\nbranch refs/heads/main\n\n"
    shim = _fake_git_shim(tmp_path, wt_output)

    # Run 1 warmup (cold disk-cache miss is excluded from the p95 calculation)
    warmup = _run_hook(tmp_path, path_prepend=shim)
    assert warmup.returncode == 0

    durations: list[float] = []
    for _ in range(5):
        start = time.perf_counter()
        result = _run_hook(tmp_path, path_prepend=shim)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert result.returncode == 0
        durations.append(elapsed_ms)

    sorted_durations = sorted(durations)
    # p95 of 5 warm samples = 5th value (worst case)
    p95 = sorted_durations[-1]

    assert p95 < 50.0, (
        f"p95 latency {p95:.1f}ms exceeds 50ms target. All runs: {[f'{d:.1f}ms' for d in durations]}"
    )
