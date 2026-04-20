"""
tests/integration/test_cwd_enforcement_end_to_end.py

End-to-end: orchestrator in worktree, sub-agent receives injection, extracts
the path, and a git commit run with the recommended `git -C <path>` pattern
actually commits to the main worktree's branch — not the worktree branch.

Uses a real git repo with a real git worktree so we can verify branch-level
commit landing.
"""
from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
INJECT_HOOK = REPO_ROOT / "hooks" / "agent-working-dir-inject.sh"


def _git(*args: str, cwd: str | Path, check: bool = True) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@test.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@test.com",
    }
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
        env=env,
    )


def _run_inject_hook(project_dir: Path) -> str:
    """Run the inject hook and return the additionalContext string."""
    stdin = json.dumps({"tool_name": "Agent", "prompt": "do something"})
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["SO_KILLSWITCH"] = "0"

    result = subprocess.run(
        ["bash", str(INJECT_HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    assert result.returncode == 0, f"Inject hook failed: {result.stderr}"

    stdout = result.stdout.strip()
    if not stdout:
        return ""
    try:
        data = json.loads(stdout)
        return data.get("hookSpecificOutput", {}).get("additionalContext", "")
    except json.JSONDecodeError:
        return stdout


def _extract_working_dir(context: str) -> str | None:
    """Extract the WORKING DIR path from additionalContext."""
    for line in context.splitlines():
        if line.startswith("WORKING DIR:"):
            return line.split("WORKING DIR:", 1)[1].strip()
    return None


# ── Single end-to-end test ────────────────────────────────────────────────────

def test_git_commit_lands_on_main_when_using_recommended_pattern(tmp_path: Path) -> None:
    """
    Full flow:
    1. Create a main repo + worktree branch
    2. Write cognitive-os.yaml pointing sub_agent_cwd=main_worktree
    3. Run inject hook (simulating orchestrator in the worktree)
    4. Extract WORKING DIR from additionalContext
    5. Run `git -C <WORKING DIR> commit` from inside the worktree
    6. Verify the commit landed on main, not the worktree branch
    """
    # ── Step 1: initialise main repo ─────────────────────────────────────────
    main_repo = tmp_path / "main_repo"
    main_repo.mkdir()

    _git("init", "-b", "main", cwd=main_repo)
    (main_repo / "README.md").write_text("# project\n")
    _git("add", "README.md", cwd=main_repo)
    _git("commit", "-m", "initial commit", cwd=main_repo)

    # ── Step 2: create a worktree on a feature branch ─────────────────────────
    worktree_path = tmp_path / "feature-worktree"
    _git("worktree", "add", "-b", "feature/test", str(worktree_path), "main", cwd=main_repo)

    # ── Step 3: write cognitive-os.yaml in main repo ──────────────────────────
    (main_repo / "cognitive-os.yaml").write_text(
        "orchestration:\n  sub_agent_cwd: main_worktree\n\nefficiency:\n  profile: default\n"
    )

    # ── Step 4: run inject hook simulating orchestrator in main_repo ──────────
    context = _run_inject_hook(main_repo)
    assert context, "Inject hook returned empty context — check hook and yaml setup"

    working_dir = _extract_working_dir(context)
    assert working_dir is not None, (
        f"Could not extract WORKING DIR from context:\n{context}"
    )
    assert working_dir == str(main_repo), (
        f"Expected WORKING DIR={main_repo}, got {working_dir!r}"
    )

    # Verify the context contains `git -C <path>` guidance
    assert "git -C" in context, (
        f"Context must contain 'git -C' guidance.\nGot: {context!r}"
    )

    # ── Step 5: simulate sub-agent running git commit with recommended pattern ─
    # Sub-agent is "inside" the worktree (cwd=worktree_path) but uses git -C main_repo
    test_file = main_repo / "agent-output.txt"
    test_file.write_text("output from sub-agent\n")

    _git("add", "agent-output.txt", cwd=main_repo)

    # Run commit using the pattern extracted from the advisory: git -C <working_dir>
    commit_result = subprocess.run(
        ["git", "-C", working_dir, "commit", "-m", "sub-agent commit via recommended pattern"],
        cwd=str(worktree_path),  # sub-agent is in worktree
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@test.com",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@test.com",
        },
    )
    assert commit_result.returncode == 0, (
        f"git commit failed:\nstdout={commit_result.stdout}\nstderr={commit_result.stderr}"
    )

    # ── Step 6: verify commit landed on main, not feature/test ───────────────
    main_log = _git("log", "--oneline", "-3", cwd=main_repo).stdout
    assert "sub-agent commit via recommended pattern" in main_log, (
        f"Expected commit on main branch.\nmain log:\n{main_log}"
    )

    # Verify the feature worktree branch does NOT have this commit
    feature_log = _git("log", "--oneline", "-3", cwd=worktree_path).stdout
    assert "sub-agent commit via recommended pattern" not in feature_log, (
        f"Commit incorrectly landed on feature branch!\nfeature log:\n{feature_log}"
    )
