"""
tests/integration/test_cwd_enforcer_warns.py

Behavioural tests for hooks/agent-bash-cwd-enforcer.sh.

Test matrix (5 tests):
  1. git commit from worktree → warning emitted, logged to cwd-enforcer.jsonl
  2. git commit from main path → no warning
  3. git -C /main/path commit from worktree → no warning (already scoped)
  4. Non-git bash (ls) → no warning
  5. Enforcer always exits 0 (never blocks)
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent.parent
HOOK_PATH = REPO_ROOT / "hooks" / "agent-bash-cwd-enforcer.sh"


def _bash_payload(command: str) -> str:
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


def _fake_git_shim(tmp_path: Path, main_path: str) -> Path:
    """
    Create a fake git that returns a single-worktree porcelain list for main_path
    and delegates everything else to real git.
    """
    shim_dir = tmp_path / "git_shim"
    shim_dir.mkdir(exist_ok=True)
    fake_git = shim_dir / "git"
    real_git = shutil.which("git") or "/usr/bin/git"
    wt_output = f"worktree {main_path}\nHEAD abc123\nbranch refs/heads/main\n\n"
    fake_git.write_text(
        f"""#!/usr/bin/env bash
if [ "${{@}}" = "worktree list --porcelain" ] || \\
   ([ "$2" = "worktree" ] && [ "$3" = "list" ] && [ "$4" = "--porcelain" ]); then
  printf '%s' {repr(wt_output)}
  exit 0
fi
exec {real_git} "$@"
"""
    )
    fake_git.chmod(fake_git.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return shim_dir


def _make_yaml(project_dir: Path, policy: str = "main_worktree") -> None:
    config = project_dir / "cognitive-os.yaml"
    config.write_text(
        f"orchestration:\n  sub_agent_cwd: {policy}\n\nefficiency:\n  profile: default\n"
    )


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "--allow-empty", "-m", "init"],
        check=True,
        capture_output=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.com",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.com"},
    )


def _run_enforcer(
    project_dir: Path,
    command: str,
    *,
    cwd: str | None = None,
    git_shim: Path | None = None,
) -> tuple[int, str, str]:
    """Run the enforcer hook, return (returncode, additionalContext, stderr)."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["SO_KILLSWITCH"] = "0"
    if git_shim is not None:
        env["PATH"] = f"{git_shim}:{env.get('PATH', '')}"
    # Override PWD to simulate a different cwd (the hook reads $PWD)
    if cwd is not None:
        env["PWD"] = cwd

    result = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=_bash_payload(command),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        cwd=cwd,  # also set the actual cwd of the subprocess
    )

    stdout = result.stdout.strip()
    context = ""
    if stdout:
        try:
            data = json.loads(stdout)
            context = data.get("hookSpecificOutput", {}).get("additionalContext", "")
        except json.JSONDecodeError:
            context = stdout

    return result.returncode, context, result.stderr


# ── Test 1: git commit from worktree → warning emitted, logged ───────────────

def test_git_commit_from_worktree_emits_warning(tmp_path: Path) -> None:
    """git commit run from a worktree (cwd != main) triggers advisory warning."""
    main_path = tmp_path / "main"
    main_path.mkdir()
    _init_repo(main_path)
    _make_yaml(main_path)

    worktree_path = tmp_path / "worktree-feature"
    worktree_path.mkdir()

    shim = _fake_git_shim(tmp_path, str(main_path))

    rc, context, _ = _run_enforcer(
        main_path,
        'git commit -m "test"',
        cwd=str(worktree_path),
        git_shim=shim,
    )

    assert rc == 0, f"Enforcer must never block (exit 0), got {rc}"
    assert context, "Expected a warning advisory context, got empty"
    assert "git" in context.lower(), f"Warning should mention git. Got: {context!r}"

    # Verify logging
    metrics_file = main_path / ".cognitive-os" / "metrics" / "cwd-enforcer.jsonl"
    assert metrics_file.exists(), "Expected cwd-enforcer.jsonl to be written"
    raw_lines = [l for l in metrics_file.read_text().splitlines() if l.strip()]
    assert raw_lines, "Expected at least one log entry in cwd-enforcer.jsonl"
    last = json.loads(raw_lines[-1])
    # Layer 3 upgrade: event is now "rewritten" (command-rewrite mode) instead
    # of "warned". Accept either to remain backward-compatible with test infra.
    assert last.get("event") in ("warned", "rewritten", "warn_fallback"), (
        f"Expected a cwd-enforcement event, got: {last}"
    )


# ── Test 2: git commit from main path → no warning ───────────────────────────

def test_git_commit_from_main_path_no_warning(tmp_path: Path) -> None:
    """git commit run from the main worktree itself → no advisory needed."""
    main_path = tmp_path / "main"
    main_path.mkdir()
    _init_repo(main_path)
    _make_yaml(main_path)

    shim = _fake_git_shim(tmp_path, str(main_path))

    rc, context, _ = _run_enforcer(
        main_path,
        'git commit -m "test"',
        cwd=str(main_path),
        git_shim=shim,
    )

    assert rc == 0, f"Enforcer must never block (exit 0), got {rc}"
    assert context == "", f"Expected no warning when cwd == target, got: {context!r}"


# ── Test 3: git -C /main/path commit from worktree → no warning ──────────────

def test_git_c_scoped_commit_no_warning(tmp_path: Path) -> None:
    """git -C <main> commit already scopes to target — no warning should fire."""
    main_path = tmp_path / "main"
    main_path.mkdir()
    _init_repo(main_path)
    _make_yaml(main_path)

    worktree_path = tmp_path / "worktree-feature"
    worktree_path.mkdir()

    shim = _fake_git_shim(tmp_path, str(main_path))

    rc, context, _ = _run_enforcer(
        main_path,
        f'git -C {main_path} commit -m "test"',
        cwd=str(worktree_path),
        git_shim=shim,
    )

    assert rc == 0, f"Enforcer must never block (exit 0), got {rc}"
    assert context == "", (
        f"Expected no warning when command uses `git -C {main_path}`, "
        f"got: {context!r}"
    )


# ── Test 4: Non-git bash (ls) → no warning ───────────────────────────────────

def test_non_git_command_no_warning(tmp_path: Path) -> None:
    """ls or any non-git command must produce no advisory."""
    main_path = tmp_path / "main"
    main_path.mkdir()
    _init_repo(main_path)
    _make_yaml(main_path)

    worktree_path = tmp_path / "worktree-feature"
    worktree_path.mkdir()

    shim = _fake_git_shim(tmp_path, str(main_path))

    for cmd in ["ls -la", "echo hello", "pytest tests/", "yarn build"]:
        rc, context, _ = _run_enforcer(
            main_path,
            cmd,
            cwd=str(worktree_path),
            git_shim=shim,
        )
        assert rc == 0, f"Enforcer must exit 0 for '{cmd}', got {rc}"
        assert context == "", f"Expected no warning for '{cmd}', got: {context!r}"


# ── Test 5: Enforcer always exits 0 (never blocks) ───────────────────────────

def test_enforcer_always_exits_zero(tmp_path: Path) -> None:
    """Under all scenarios the enforcer must exit 0 — it is advisory only."""
    main_path = tmp_path / "main"
    main_path.mkdir()
    _init_repo(main_path)
    _make_yaml(main_path)

    worktree_path = tmp_path / "worktree-feature"
    worktree_path.mkdir()

    shim = _fake_git_shim(tmp_path, str(main_path))

    scenarios = [
        ('git commit -m "test"', str(worktree_path)),
        (f'git -C {main_path} commit -m "test"', str(worktree_path)),
        ('git push origin main', str(worktree_path)),
        ('git merge feature', str(worktree_path)),
        ('git rebase main', str(worktree_path)),
        ('git reset --hard HEAD~1', str(worktree_path)),
        ('ls -la', str(worktree_path)),
        ('', str(worktree_path)),  # empty command
    ]

    for cmd, cwd in scenarios:
        rc, _, _ = _run_enforcer(
            main_path,
            cmd,
            cwd=cwd,
            git_shim=shim,
        )
        assert rc == 0, (
            f"Enforcer MUST always exit 0 (advisory only). "
            f"Got exit {rc} for command: {cmd!r}"
        )
