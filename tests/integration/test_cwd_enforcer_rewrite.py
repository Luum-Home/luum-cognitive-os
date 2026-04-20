"""
tests/integration/test_cwd_enforcer_rewrite.py

Behavioural tests for the upgraded hooks/agent-bash-cwd-enforcer.sh (Layer 3).

Layer 3 upgrades the enforcer from warn-only to command-rewrite mode:
  - Simple git commands issued from a worktree are transparently rewritten to
    prepend `git -C <main>` before execution.
  - Already-scoped commands (git -C <any>) pass through untouched.
  - Non-git commands pass through untouched.
  - Compound commands (&&/;/||) fall back to strong advisory warning.
  - Enforcer always exits 0 (never blocks).

Protocol reference: ADR-023 (updatedInput rewrite protocol, Claude Code 2.x).

Test matrix (9 tests):
  1. git commit from worktree → command rewritten, additionalContext explains rewrite
  2. git push from worktree → command rewritten
  3. git add file.txt from worktree → command rewritten
  4. git merge feature from worktree → command rewritten
  5. git rebase main from worktree → command rewritten
  6. git reset --hard HEAD~1 from worktree → command rewritten
  7. Already-prefixed git -C /path commit from worktree → unchanged (no double-prefix)
  8. Non-git (ls) from worktree → unchanged
  9. Compound command (cd /tmp && git commit) from worktree → strong warning fallback
 10. git commit from main (correct cwd) → no rewrite, no warning
 11. Enforcer always exits 0
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
HOOK_PATH = REPO_ROOT / "hooks" / "agent-bash-cwd-enforcer.sh"


def _bash_payload(command: str) -> str:
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


def _fake_git_shim(tmp_path: Path, main_path: str) -> Path:
    """
    Create a fake git binary that returns a single-worktree porcelain list.
    Delegates real git operations to the system git.
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
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t.com",
        },
    )


def _run_enforcer(
    project_dir: Path,
    command: str,
    *,
    cwd: str | None = None,
    git_shim: Path | None = None,
) -> tuple[int, dict]:
    """
    Run the enforcer hook, return (returncode, parsed_hookSpecificOutput).
    parsed_hookSpecificOutput contains the full hookSpecificOutput dict.
    """
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["SO_KILLSWITCH"] = "0"
    if git_shim is not None:
        env["PATH"] = f"{git_shim}:{env.get('PATH', '')}"
    if cwd is not None:
        env["PWD"] = cwd

    result = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=_bash_payload(command),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        cwd=cwd,
    )

    hook_output: dict = {}
    stdout = result.stdout.strip()
    if stdout:
        try:
            data = json.loads(stdout)
            hook_output = data.get("hookSpecificOutput", {})
        except json.JSONDecodeError:
            hook_output = {"raw": stdout}

    return result.returncode, hook_output


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture()
def repo(tmp_path: Path):
    """Returns (main_path, worktree_path, shim_dir)."""
    main_path = tmp_path / "main"
    main_path.mkdir()
    _init_repo(main_path)
    _make_yaml(main_path)
    worktree_path = tmp_path / "worktree-feature"
    worktree_path.mkdir()
    shim = _fake_git_shim(tmp_path, str(main_path))
    return main_path, worktree_path, shim


# ── Test 1: git commit from worktree → rewritten ─────────────────────────────

def test_git_commit_from_worktree_is_rewritten(repo) -> None:
    """git commit from worktree → updatedInput.command prepends git -C <main>."""
    main_path, worktree_path, shim = repo

    rc, output = _run_enforcer(
        main_path,
        'git commit -m "test commit"',
        cwd=str(worktree_path),
        git_shim=shim,
    )

    assert rc == 0, f"Enforcer must never block (exit 0), got {rc}"
    assert "updatedInput" in output, (
        f"Expected updatedInput in hookSpecificOutput, got: {output}"
    )
    rewritten = output["updatedInput"]["command"]
    assert f"git -C" in rewritten, f"Expected git -C in rewritten command, got: {rewritten!r}"
    assert str(main_path) in rewritten, (
        f"Expected main path {main_path} in rewritten command, got: {rewritten!r}"
    )
    assert 'commit -m "test commit"' in rewritten or "commit" in rewritten, (
        f"Expected original subcommand in rewritten cmd, got: {rewritten!r}"
    )

    # Verify additionalContext explains the rewrite
    ctx = output.get("additionalContext", "")
    assert ctx, "Expected additionalContext explaining the rewrite"
    assert "cwd-enforcer" in ctx or "Auto-prepended" in ctx or "rewrote" in ctx, (
        f"additionalContext should explain the rewrite. Got: {ctx!r}"
    )

    # Verify logging
    metrics_file = main_path / ".cognitive-os" / "metrics" / "cwd-enforcer.jsonl"
    assert metrics_file.exists()
    entries = [json.loads(l) for l in metrics_file.read_text().splitlines() if l.strip()]
    assert any(e.get("event") == "rewritten" for e in entries), (
        f"Expected event=rewritten in log. Got: {entries}"
    )


# ── Test 2: git push from worktree → rewritten ───────────────────────────────

def test_git_push_from_worktree_is_rewritten(repo) -> None:
    """git push from worktree → updatedInput.command uses git -C <main> push."""
    main_path, worktree_path, shim = repo

    rc, output = _run_enforcer(
        main_path,
        "git push origin main",
        cwd=str(worktree_path),
        git_shim=shim,
    )

    assert rc == 0
    assert "updatedInput" in output, f"Expected rewrite, got: {output}"
    rewritten = output["updatedInput"]["command"]
    assert "git -C" in rewritten
    assert "push" in rewritten
    assert str(main_path) in rewritten


# ── Test 3: git add from worktree → rewritten ────────────────────────────────

def test_git_add_from_worktree_is_rewritten(repo) -> None:
    """git add <file> from worktree → updatedInput.command uses git -C <main> add."""
    main_path, worktree_path, shim = repo

    rc, output = _run_enforcer(
        main_path,
        "git add src/main.go",
        cwd=str(worktree_path),
        git_shim=shim,
    )

    assert rc == 0
    assert "updatedInput" in output, f"Expected rewrite, got: {output}"
    rewritten = output["updatedInput"]["command"]
    assert "git -C" in rewritten
    assert "add" in rewritten
    assert str(main_path) in rewritten


# ── Test 4: git merge from worktree → rewritten ──────────────────────────────

def test_git_merge_from_worktree_is_rewritten(repo) -> None:
    main_path, worktree_path, shim = repo

    rc, output = _run_enforcer(
        main_path,
        "git merge feature-branch",
        cwd=str(worktree_path),
        git_shim=shim,
    )

    assert rc == 0
    assert "updatedInput" in output, f"Expected rewrite, got: {output}"
    rewritten = output["updatedInput"]["command"]
    assert "git -C" in rewritten and "merge" in rewritten


# ── Test 5: git rebase from worktree → rewritten ─────────────────────────────

def test_git_rebase_from_worktree_is_rewritten(repo) -> None:
    main_path, worktree_path, shim = repo

    rc, output = _run_enforcer(
        main_path,
        "git rebase main",
        cwd=str(worktree_path),
        git_shim=shim,
    )

    assert rc == 0
    assert "updatedInput" in output, f"Expected rewrite, got: {output}"
    rewritten = output["updatedInput"]["command"]
    assert "git -C" in rewritten and "rebase" in rewritten


# ── Test 6: git reset from worktree → rewritten ──────────────────────────────

def test_git_reset_from_worktree_is_rewritten(repo) -> None:
    main_path, worktree_path, shim = repo

    rc, output = _run_enforcer(
        main_path,
        "git reset --hard HEAD~1",
        cwd=str(worktree_path),
        git_shim=shim,
    )

    assert rc == 0
    assert "updatedInput" in output, f"Expected rewrite, got: {output}"
    rewritten = output["updatedInput"]["command"]
    assert "git -C" in rewritten and "reset" in rewritten


# ── Test 7: already-prefixed git -C → unchanged ──────────────────────────────

def test_already_scoped_git_c_unchanged(repo) -> None:
    """git -C <any-path> commit from worktree → pass through unchanged (no double-prefix)."""
    main_path, worktree_path, shim = repo

    original_cmd = f'git -C {main_path} commit -m "already scoped"'
    rc, output = _run_enforcer(
        main_path,
        original_cmd,
        cwd=str(worktree_path),
        git_shim=shim,
    )

    assert rc == 0
    # No updatedInput — command should pass through unchanged
    assert "updatedInput" not in output, (
        f"Should not rewrite already-scoped command. Got updatedInput: {output.get('updatedInput')}"
    )
    # No additionalContext warning either
    ctx = output.get("additionalContext", "")
    assert not ctx, f"Should not warn for already-scoped command, got: {ctx!r}"


# ── Test 8: non-git command → unchanged ──────────────────────────────────────

def test_non_git_command_unchanged(repo) -> None:
    """ls, echo, pytest — no rewrite, no warning."""
    main_path, worktree_path, shim = repo

    for cmd in ["ls -la", "echo hello", "pytest tests/", "yarn build"]:
        rc, output = _run_enforcer(
            main_path,
            cmd,
            cwd=str(worktree_path),
            git_shim=shim,
        )
        assert rc == 0, f"Enforcer must exit 0 for '{cmd}'"
        assert "updatedInput" not in output, (
            f"Should not rewrite non-git command '{cmd}'. Got: {output}"
        )
        assert not output.get("additionalContext"), (
            f"Should not warn for non-git command '{cmd}'"
        )


# ── Test 9: compound command → strong warning fallback ───────────────────────

def test_compound_git_command_emits_strong_warning(repo) -> None:
    """cd /tmp && git commit — too complex to rewrite, strong advisory warning."""
    main_path, worktree_path, shim = repo

    rc, output = _run_enforcer(
        main_path,
        'cd /tmp && git commit -m "compound"',
        cwd=str(worktree_path),
        git_shim=shim,
    )

    assert rc == 0, "Enforcer must never block"
    # Should NOT rewrite compound commands
    assert "updatedInput" not in output, (
        f"Should NOT rewrite compound commands, got updatedInput: {output.get('updatedInput')}"
    )
    # Should emit a strong warning
    ctx = output.get("additionalContext", "")
    assert ctx, "Expected strong advisory warning for compound command"
    # Warning should be prominent — indicate the problem
    assert any(
        keyword in ctx for keyword in ["BLOCKER", "WRONG", "manually", "must", "prefix", "fix"]
    ), f"Expected strong warning keywords in context. Got: {ctx!r}"

    # Verify fallback logged
    metrics_file = main_path / ".cognitive-os" / "metrics" / "cwd-enforcer.jsonl"
    if metrics_file.exists():
        entries = [json.loads(l) for l in metrics_file.read_text().splitlines() if l.strip()]
        assert any(e.get("event") in ("warn_fallback", "warned") for e in entries), (
            f"Expected warn_fallback event in log. Got: {entries}"
        )


# ── Test 10: git commit from correct cwd → no output ─────────────────────────

def test_git_commit_from_main_path_no_output(repo) -> None:
    """git commit run from the main worktree itself → silent (no rewrite, no warning)."""
    main_path, _worktree_path, shim = repo

    rc, output = _run_enforcer(
        main_path,
        'git commit -m "from main"',
        cwd=str(main_path),
        git_shim=shim,
    )

    assert rc == 0
    assert "updatedInput" not in output, (
        f"Should not rewrite when already in correct cwd. Got: {output}"
    )
    assert not output.get("additionalContext"), (
        f"Should not warn when already in correct cwd. Got: {output.get('additionalContext')!r}"
    )


# ── Test 11: enforcer always exits 0 ─────────────────────────────────────────

def test_enforcer_always_exits_zero(repo) -> None:
    """Under all scenarios the enforcer must exit 0 — never blocks."""
    main_path, worktree_path, shim = repo

    scenarios = [
        ('git commit -m "test"', str(worktree_path)),
        (f"git -C {main_path} commit -m 'test'", str(worktree_path)),
        ("git push origin main", str(worktree_path)),
        ("git add .", str(worktree_path)),
        ("git merge feature", str(worktree_path)),
        ("git rebase main", str(worktree_path)),
        ("git reset --hard HEAD~1", str(worktree_path)),
        ("cd /tmp && git commit -m 'compound'", str(worktree_path)),
        ("ls -la", str(worktree_path)),
        ("", str(worktree_path)),  # empty command
        ('git commit -m "from main"', str(main_path)),
    ]

    for cmd, cwd in scenarios:
        rc, _ = _run_enforcer(
            main_path,
            cmd,
            cwd=cwd,
            git_shim=shim,
        )
        assert rc == 0, (
            f"Enforcer MUST always exit 0. Got exit {rc} for command: {cmd!r}"
        )
