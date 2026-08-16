"""Behavior tests for the --amend verdict of hooks/git-commit-scope-guard.sh.

These tests EXECUTE the hook against real throwaway git repositories and assert
on its exit code. They deliberately do not assert that any string appears in the
hook source: a test that greps for "--amend" only proves someone typed it.

Context: commit 3506e1481 (2026-08-15) absorbed files belonging to three other
agents because a bare `git commit --amend` rewrites the tip using the ENTIRE
index, while `--amend -- <path>` honours the pathspec.

Exit-code contract: 0 = allow, 2 = block.
"""

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "git-commit-scope-guard.sh"

ALLOW, BLOCK = 0, 2


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


@pytest.fixture()
def shared_checkout(tmp_path: Path) -> Path:
    """A repo where agent A has a commit and agent B has a file staged."""
    repo = tmp_path / "shared"
    repo.mkdir()
    _git(repo, "init", "-q", ".")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "mine.md").write_text("base\n")
    (repo / "theirs.md").write_text("base\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")

    (repo / "mine.md").write_text("A1\n")
    _git(repo, "add", "mine.md")
    _git(repo, "commit", "-q", "--only", "-m", "A: my commit", "--", "mine.md")
    # concurrent agent B stages its work into the SAME index
    (repo / "theirs.md").write_text("B1\n")
    _git(repo, "add", "theirs.md")
    return repo


def run_guard(command: str, project_dir: Path) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run(
        ["bash", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin",
             "HOME": str(project_dir),
             "COGNITIVE_OS_PROJECT_DIR": str(project_dir)},
    )


# -- the accident ------------------------------------------------------------

def test_bare_amend_blocked_when_another_agent_has_staged_work(shared_checkout):
    """The exact shape that produced 3506e1481."""
    result = run_guard("git commit --amend -m 'fixed message'", shared_checkout)
    assert result.returncode == BLOCK
    assert "--amend" in result.stderr
    # the message must name what would be swallowed, not just say "blocked"
    assert "theirs.md" in result.stderr


def test_bare_amend_would_indeed_swallow_the_other_agents_file(shared_checkout):
    """Proves the guard protects against real git behavior, not a myth."""
    _git(shared_checkout, "commit", "-q", "--amend", "--no-edit")
    committed = subprocess.run(
        ["git", "-C", str(shared_checkout), "show", "--stat", "--format=", "HEAD"],
        capture_output=True, text=True).stdout
    assert "theirs.md" in committed, "bare --amend absorbed the whole index"


# -- the two safe forms that must stay allowed -------------------------------

def test_amend_with_pathspec_allowed(shared_checkout):
    """`--amend -- <path>` honours the pathspec; blocking it would be wrong."""
    result = run_guard("git commit --amend -m 'fixed' -- mine.md", shared_checkout)
    assert result.returncode == ALLOW


def test_amend_with_pathspec_does_not_touch_the_other_agents_file(shared_checkout):
    _git(shared_checkout, "commit", "-q", "--amend", "-m", "fixed", "--", "mine.md")
    committed = subprocess.run(
        ["git", "-C", str(shared_checkout), "show", "--stat", "--format=", "HEAD"],
        capture_output=True, text=True).stdout
    assert "theirs.md" not in committed
    staged = subprocess.run(
        ["git", "-C", str(shared_checkout), "diff", "--cached", "--name-only"],
        capture_output=True, text=True).stdout
    assert "theirs.md" in staged, "the other agent's staging survived"


def test_bare_amend_allowed_once_index_is_clean(shared_checkout):
    """The escape: with nothing staged, an amend cannot co-opt anyone."""
    _git(shared_checkout, "restore", "--staged", "theirs.md")
    result = run_guard("git commit --amend -m 'fixed message'", shared_checkout)
    assert result.returncode == ALLOW


# -- the two evasions found on 2026-08-15 ------------------------------------

def test_scoped_commit_does_not_launder_a_later_amend(shared_checkout):
    """A scoped first commit used to whitelist everything after `&&`."""
    result = run_guard(
        "git commit --only -m 'x' -- mine.md && git commit --amend --no-edit",
        shared_checkout)
    assert result.returncode == BLOCK


def test_git_dash_c_form_is_not_invisible(shared_checkout):
    """`git -C <dir> commit` skipped the literal-adjacency trigger regex."""
    result = run_guard(
        f"git -C {shared_checkout} commit --amend --no-edit", shared_checkout)
    assert result.returncode == BLOCK


# -- no false positives on legitimate commits --------------------------------

@pytest.mark.parametrize("command", [
    "git commit --only -m 'msg' -- docs/report.md",
    "git commit -a -m 'all modified'",
    "git commit -- docs/report.md -m 'msg'",
    # a message that merely talks about the dangerous command must not trip it
    "git commit --only -m 'fix: git commit --amend swallows the index' -- a.md",
    "git commit --only -m 'a; b && c' -- a.md",
    "git status && git log",
])
def test_legitimate_forms_still_allowed(command, shared_checkout):
    assert run_guard(command, shared_checkout).returncode == ALLOW
