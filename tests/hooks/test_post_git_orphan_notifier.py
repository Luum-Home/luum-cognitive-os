# SCOPE: os-only
"""Behavioural test for the post-git orphan notifier (ADR-116 P3.1).

The hook shells out to `scripts/orphan_commit_scan.py` and is supposed to print
a recovery alert on stderr when that scanner exits 1 (orphans found). It never
did: the exit code was captured as

    SCAN_OUTPUT=$(python3 "$SCANNER" ...) || true
    SCAN_EXIT=$?

and `$?` after `|| true` is the exit status of `true`. SCAN_EXIT was 0 on every
one of the 8508 invocations recorded in `hook-timing.jsonl` plus the rotated
archives, so the whole alert block was unreachable code. The JSONL ledger the
scanner writes kept filling, which is why the defect survived: the data was
there, only the operator was never told.

Covered in both directions:
  * a repo that HAS an unreachable commit after `git reset --hard` MUST get the
    alert on stderr, with the orphan's short SHA in it;
  * a clean repo MUST stay silent;
  * a non-trigger command (`git status`) MUST not even run the scanner;
  * every path MUST exit 0 — the hook is advisory and must never block a Bash
    call that already ran.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_REL = "hooks/post-git-orphan-notifier.sh"
SCANNER_REL = "scripts/orphan_commit_scan.py"
LEDGER_REL = ".cognitive-os/metrics/orphan-notifier.jsonl"
ALERT_MARK = "=== POST-GIT-ORPHAN-NOTIFIER ==="


def _hook_source() -> Path:
    """Where to copy the hook from — overridable only for the falsification run."""
    override = os.environ.get("COS_TEST_HOOK_SOURCE_DIR")
    base = Path(override) if override else REPO_ROOT
    return base / HOOK_REL


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    repo = (tmp_path / "repo").resolve()
    (repo / "hooks").mkdir(parents=True)
    (repo / "scripts").mkdir(parents=True)
    shutil.copy(_hook_source(), repo / HOOK_REL)
    (repo / HOOK_REL).chmod(0o755)
    shutil.copytree(REPO_ROOT / "hooks" / "_lib", repo / "hooks" / "_lib")
    shutil.copy(REPO_ROOT / SCANNER_REL, repo / SCANNER_REL)
    (repo / ".cognitive-os" / "metrics").mkdir(parents=True)

    _git(repo, "init", "-q", ".")
    _git(repo, "config", "user.email", "hook-test@example.invalid")
    _git(repo, "config", "user.name", "hook-test")
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-qm", "base")
    return repo


def orphan_a_commit(repo: Path) -> str:
    """Commit, then throw the commit away — leaving it in the reflog only."""
    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-qm", "work-that-must-not-be-lost")
    sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "reset", "--hard", "-q", "HEAD~1")
    return sha


def run_hook(repo: Path, command: str) -> subprocess.CompletedProcess:
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {"stdout": "", "stderr": "", "interrupted": False},
    }
    env = dict(os.environ)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env.pop("CLAUDE_TOOL_INPUT", None)
    env.pop("DISABLE_HOOK_POST_GIT_ORPHAN_NOTIFIER", None)
    return subprocess.run(
        ["/bin/bash", str(repo / HOOK_REL)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo),
        timeout=120,
    )


def ledger_rows(repo: Path) -> list[dict]:
    path = repo / LEDGER_REL
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# --- must alert --------------------------------------------------------------


def test_orphaned_commit_reaches_the_operator(repo: Path) -> None:
    """The whole point of the hook. Unreachable before the SCAN_EXIT fix."""
    sha = orphan_a_commit(repo)

    result = run_hook(repo, "git reset --hard HEAD~1")

    assert result.returncode == 0, result.stderr
    assert ALERT_MARK in result.stderr, (
        "the operator was never told about an orphaned commit — the alert block "
        f"is unreachable. stderr={result.stderr!r}"
    )
    assert sha[:7] in result.stderr, f"the alert did not name the orphan {sha[:7]}"
    assert "reflog" in result.stderr


def test_the_scan_is_recorded_even_though_it_alerts(repo: Path) -> None:
    orphan_a_commit(repo)
    run_hook(repo, "git reset --hard HEAD~1")

    rows = ledger_rows(repo)
    assert rows, "the scanner wrote no ledger row"
    assert rows[-1]["orphan_count"] >= 1
    assert rows[-1]["trigger"] == "post-reset"


# --- must stay silent --------------------------------------------------------


def test_clean_repo_does_not_alert(repo: Path) -> None:
    """A reset that orphaned nothing must not print anything to the operator."""
    result = run_hook(repo, "git reset --hard HEAD")

    assert result.returncode == 0, result.stderr
    assert ALERT_MARK not in result.stderr, (
        f"the notifier cried wolf on a repo with no orphans: {result.stderr!r}"
    )
    rows = ledger_rows(repo)
    assert rows and rows[-1]["orphan_count"] == 0


def test_non_trigger_command_does_not_even_scan(repo: Path) -> None:
    orphan_a_commit(repo)

    result = run_hook(repo, "git status --porcelain")

    assert result.returncode == 0, result.stderr
    assert ALERT_MARK not in result.stderr
    assert ledger_rows(repo) == [], "the scanner ran for a command that displaces nothing"


def test_non_bash_tool_is_ignored(repo: Path) -> None:
    orphan_a_commit(repo)
    payload = {"tool_name": "Agent", "tool_input": {"command": "git reset --hard HEAD~1"}}
    env = dict(os.environ)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env.pop("CLAUDE_TOOL_INPUT", None)
    result = subprocess.run(
        ["/bin/bash", str(repo / HOOK_REL)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo),
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert ALERT_MARK not in result.stderr
    assert ledger_rows(repo) == []


# --- must never block --------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "git reset --hard HEAD~1",
        "git rebase --continue",
        "git pull --rebase origin main",
        "git status",
    ],
)
def test_hook_never_blocks(repo: Path, command: str) -> None:
    orphan_a_commit(repo)
    result = run_hook(repo, command)
    assert result.returncode == 0, (
        f"advisory hook returned {result.returncode} for {command!r}: {result.stderr}"
    )
