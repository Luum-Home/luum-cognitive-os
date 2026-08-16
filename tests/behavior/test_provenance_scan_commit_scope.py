"""Behavioural mutation tests for hooks/provenance-scan.sh scan scope.

The hook used to run the CLI with ``--staged`` unconditionally, so it judged the
whole shared index instead of what the pending commit would actually carry.
Under the ``git commit --only -- <my paths>`` idiom that this repo mandates for
concurrent writers, one agent's staged leak blocked every other agent.

These tests run the REAL hook against throwaway git repositories and assert
behaviour in both directions:

* someone else's staged leak must not block my scoped commit or my edit
  (the bug), and
* a leak inside my own pathspec must still block (the guard must survive).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "provenance-scan.sh"
CLI = REPO_ROOT / "scripts" / "provenance-scan"

# Built from fragments so this test file does not itself contain a literal
# host-absolute path (the real policy flags those as path hacks).
LEAK_PREFIX = "/" + "home/" + "leakyfixtureuser"
LEAK_LINE = LEAK_PREFIX + "/workspace/notes.txt"

CONFIG_TEMPLATE = """schema_version: provenance-scan/v1
provenance:
  forbidden_terms: []
  forbidden_paths:
    - "(?i){pattern}"
  forbidden_provenance_language: []
  allowed_absolute_paths:
    - /tmp/
    - /var/folders/
    - /private/var/folders/
  allowed_import_roots:
    go: []
    python: []
    ts: []
  forbidden_import_roots:
    go: []
    python: []
    ts: []
  exclude_globs: []
  scan_imports: false
  scan_path_hacks: false
"""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Throwaway git repo with the scan policy installed."""
    root = tmp_path / "sandbox-repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "fixture")
    (root / "config.yaml").write_text(
        CONFIG_TEMPLATE.format(pattern=LEAK_PREFIX + "/"), encoding="utf-8"
    )
    (root / "seed.md").write_text("seed\n", encoding="utf-8")
    _git(root, "add", "seed.md")
    _git(root, "commit", "-q", "-m", "seed", "--no-verify")
    return root


def run_hook(repo: Path, payload: dict) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(
        {
            "CLAUDE_PROJECT_DIR": str(repo),
            "COGNITIVE_OS_PROJECT_DIR": str(repo),
            "COS_PROVENANCE_SCAN_CLI": str(CLI),
            "COS_PROVENANCE_SCAN_CONFIG": str(repo / "config.yaml"),
        }
    )
    for noisy in ("COS_DISABLE_ALL_GOVERNANCE", "DISABLE_HOOK_PROVENANCE_SCAN"):
        env.pop(noisy, None)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def bash_payload(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def edit_payload(path: Path) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": str(path)}}


def stage_foreign_leak(repo: Path) -> None:
    """Another agent stages a file carrying a host-local path."""
    foreign = repo / "foreign.md"
    foreign.write_text(f"see {LEAK_LINE} for details\n", encoding="utf-8")
    _git(repo, "add", "foreign.md")


def write_mine(repo: Path, leaky: bool = False) -> Path:
    mine = repo / "mine.md"
    body = f"note about {LEAK_LINE}\n" if leaky else "clean note\n"
    mine.write_text(body, encoding="utf-8")
    return mine


def test_git_only_commits_the_working_tree_copy_of_the_pathspec(repo: Path) -> None:
    """Load-bearing premise of the fix: what travels is the WORKING TREE copy.

    The hook scans the working-tree content of the pathspec rather than the
    index entry. That is only correct if `git commit --only -- <path>` commits
    the working-tree version and leaves everyone else's index untouched.
    """
    (repo / "a.md").write_text("staged version\n", encoding="utf-8")
    _git(repo, "add", "a.md")
    (repo / "a.md").write_text("worktree version\n", encoding="utf-8")
    (repo / "b.md").write_text("foreign\n", encoding="utf-8")
    _git(repo, "add", "b.md")

    _git(repo, "commit", "-q", "-m", "scoped", "--only", "--", "a.md")

    committed = _git(repo, "show", "HEAD:a.md").stdout
    assert committed == "worktree version\n", "--only did not commit the worktree copy"
    files = _git(repo, "show", "--name-only", "--format=", "HEAD").stdout.split()
    assert files == ["a.md"], f"--only carried more than its pathspec: {files}"
    still_staged = _git(repo, "diff", "--cached", "--name-only").stdout.split()
    assert still_staged == ["b.md"], "the foreign file did not survive the commit"


def test_hook_and_cli_are_present() -> None:
    assert HOOK.is_file(), f"missing hook: {HOOK}"
    assert os.access(CLI, os.X_OK), f"scan CLI not executable: {CLI}"


def test_policy_fixture_actually_detects_a_leak(repo: Path) -> None:
    """Guard against a vacuous suite: the fixture policy must fire at all."""
    write_mine(repo, leaky=True)
    result = run_hook(repo, bash_payload('git commit -m "x" --only -- mine.md'))
    assert result.returncode == 2, result.stderr


def test_scoped_commit_ignores_another_agents_staged_leak(repo: Path) -> None:
    """The bug: `--only -- mine.md` must not be judged on foreign.md."""
    stage_foreign_leak(repo)
    write_mine(repo, leaky=False)
    result = run_hook(repo, bash_payload('git commit --only -m "x" -- mine.md'))
    assert result.returncode == 0, (
        "scoped commit blocked by another agent's staged file:\n" + result.stderr
    )


def test_leak_inside_my_own_pathspec_still_blocks(repo: Path) -> None:
    """The direction that decides whether the guard still guards."""
    stage_foreign_leak(repo)
    write_mine(repo, leaky=True)
    result = run_hook(repo, bash_payload('git commit --only -m "x" -- mine.md'))
    assert result.returncode == 2, "leak in my own pathspec was not blocked"
    assert "mine.md" in (result.stderr + result.stdout)


def test_commit_all_scans_every_modification(repo: Path) -> None:
    """`git commit -a` carries everything modified, so everything is scanned."""
    tracked = repo / "tracked.md"
    tracked.write_text("clean\n", encoding="utf-8")
    _git(repo, "add", "tracked.md")
    _git(repo, "commit", "-q", "-m", "add tracked", "--no-verify")
    tracked.write_text(f"now leaks {LEAK_LINE}\n", encoding="utf-8")
    result = run_hook(repo, bash_payload('git commit -a -m "x"'))
    assert result.returncode == 2, "-a did not scan an unstaged tracked leak"


def test_bare_commit_still_scans_the_whole_index(repo: Path) -> None:
    """No pathspec means the whole index enters: previous behaviour preserved."""
    stage_foreign_leak(repo)
    result = run_hook(repo, bash_payload('git commit -m "x"'))
    assert result.returncode == 2, "bare commit stopped scanning the index"


def test_amend_without_pathspec_still_scans_the_whole_index(repo: Path) -> None:
    stage_foreign_leak(repo)
    result = run_hook(repo, bash_payload("git commit --amend --no-edit"))
    assert result.returncode == 2, "bare --amend stopped scanning the index"


def test_unparseable_commit_flag_fails_closed(repo: Path) -> None:
    """An unknown flag may swallow the next token: fall back to the index."""
    stage_foreign_leak(repo)
    write_mine(repo, leaky=False)
    result = run_hook(repo, bash_payload('git commit --brand-new-flag -m "x" mine.md'))
    assert result.returncode == 2, "unknown flag did not fail closed"


def test_edit_is_not_blocked_by_another_agents_staged_leak(repo: Path) -> None:
    """An Edit creates no commit, so a foreign staged file cannot travel."""
    stage_foreign_leak(repo)
    mine = write_mine(repo, leaky=False)
    result = run_hook(repo, edit_payload(mine))
    assert result.returncode == 0, (
        "edit blocked by another agent's staged file:\n" + result.stderr
    )


def test_edit_of_a_file_that_already_leaks_still_blocks(repo: Path) -> None:
    mine = write_mine(repo, leaky=True)
    result = run_hook(repo, edit_payload(mine))
    assert result.returncode == 2, "edit of a leaking file was not blocked"


def test_non_commit_bash_command_scans_the_index(repo: Path) -> None:
    stage_foreign_leak(repo)
    result = run_hook(repo, bash_payload("ls -la"))
    assert result.returncode == 2, "non-commit command stopped scanning the index"


def test_commit_into_another_repo_fails_closed(repo: Path, tmp_path: Path) -> None:
    other = tmp_path / "elsewhere"
    other.mkdir()
    stage_foreign_leak(repo)
    write_mine(repo, leaky=False)
    result = run_hook(
        repo, bash_payload(f'git -C {other} commit --only -m "x" -- mine.md')
    )
    assert result.returncode == 2, "commit into another repo did not fail closed"


def test_missing_cli_is_a_no_op(repo: Path, tmp_path: Path) -> None:
    """Absent scanner must not block; unchanged contract."""
    env = os.environ.copy()
    env.update(
        {
            "CLAUDE_PROJECT_DIR": str(repo),
            "COGNITIVE_OS_PROJECT_DIR": str(repo),
            "COS_PROVENANCE_SCAN_CLI": str(tmp_path / "no-such-cli"),
        }
    )
    stage_foreign_leak(repo)
    result = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(bash_payload('git commit -m "x"')),
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0


def test_hook_is_not_a_stub() -> None:
    """Cheap-green tripwire: no blanket bypass env var may be introduced."""
    text = HOOK.read_text(encoding="utf-8")
    assert "--staged" in text, "the index-wide fallback disappeared entirely"
    banned = ("COS_SKIP_PROVENANCE", "PROVENANCE_SCAN_SKIP", "COS_PROVENANCE_BYPASS")
    for name in banned:
        assert name not in text, f"new bypass switch introduced: {name}"


@pytest.mark.skipif(shutil.which("git") is None, reason="git required")
def test_shellcheck_free_of_syntax_errors() -> None:
    result = subprocess.run(
        ["bash", "-n", str(HOOK)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
