# SCOPE: os-only
"""Behavioural test for the auto-stash budget warning.

The count was computed as

    STASH_COUNT=$(git stash list | grep -c -E '...' || echo "0")

but `grep -c` already prints "0" and exits 1 when nothing matches, so the
`|| echo "0"` appended a SECOND zero. STASH_COUNT became the two-line string
"0\\n0", `[ "0\\n0" -le 3 ]` failed with "integer expression expected", and the
under-threshold guard fell THROUGH to the warning: the hook announced
"AUTO-STASH BUDGET EXCEEDED" on a repo with zero stashes, then died inside
`printf %d` via its own `trap 'exit 0' ERR` — before the cooldown file and
before the metrics row. That is why 335 recorded invocations left
`.cognitive-os/metrics/stash-budget.jsonl` non-existent.

This is the case that shows why one direction is not enough: the bug made the
hook fire when it must NOT, and a test that only checked "does it warn over
budget" would have passed on the broken hook.

Covered in both directions:
  * zero stashes MUST be silent, with no cooldown file and no metrics row;
  * over-budget MUST warn AND leave the cooldown file AND one metrics row;
  * exactly-at-threshold MUST be silent (the guard is `-le`);
  * a second prompt inside the cooldown window MUST stay silent;
  * every path MUST exit 0 — this hook runs on UserPromptSubmit and blocking
    it would eat the operator's prompt.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_REL = "hooks/stash-budget-warn.sh"
METRICS_REL = ".cognitive-os/metrics/stash-budget.jsonl"
COOLDOWN_REL = ".cognitive-os/runtime/stash-budget-last-warn.txt"
WARNING_MARK = "AUTO-STASH BUDGET EXCEEDED"


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
    shutil.copy(_hook_source(), repo / HOOK_REL)
    (repo / HOOK_REL).chmod(0o755)

    _git(repo, "init", "-q", ".")
    _git(repo, "config", "user.email", "hook-test@example.invalid")
    _git(repo, "config", "user.name", "hook-test")
    (repo / "a.txt").write_text("0\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-qm", "base")
    return repo


def make_stashes(repo: Path, n: int) -> None:
    for i in range(n):
        (repo / "a.txt").write_text(f"change {i}\n", encoding="utf-8")
        _git(repo, "stash", "push", "-m", f"auto-pre-agent-{i}")


def run_hook(repo: Path, threshold: str | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env.pop("DISABLE_HOOK_STASH_BUDGET_WARN", None)
    if threshold is not None:
        env["COS_STASH_BUDGET_WARN_THRESHOLD"] = threshold
    else:
        env.pop("COS_STASH_BUDGET_WARN_THRESHOLD", None)
    payload = {"hook_event_name": "UserPromptSubmit", "prompt": "seguimos con el informe"}
    return subprocess.run(
        ["/bin/bash", str(repo / HOOK_REL)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo),
        timeout=60,
    )


def metrics_rows(repo: Path) -> list[dict]:
    path = repo / METRICS_REL
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# --- must stay silent --------------------------------------------------------


def test_zero_stashes_is_silent(repo: Path) -> None:
    """The defect: the hook shouted BUDGET EXCEEDED with nothing stashed."""
    result = run_hook(repo)

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK not in result.stderr, (
        f"warned about an exceeded budget with zero stashes: {result.stderr!r}"
    )
    assert metrics_rows(repo) == []
    assert not (repo / COOLDOWN_REL).exists()


def test_exactly_at_threshold_is_silent(repo: Path) -> None:
    """The guard is `-le`: 3 stashes with threshold 3 is inside budget."""
    make_stashes(repo, 3)

    result = run_hook(repo, threshold="3")

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK not in result.stderr
    assert metrics_rows(repo) == []


def test_unrelated_stashes_do_not_count(repo: Path) -> None:
    for i in range(5):
        (repo / "a.txt").write_text(f"manual {i}\n", encoding="utf-8")
        _git(repo, "stash", "push", "-m", f"wip-manual-{i}")

    result = run_hook(repo)

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK not in result.stderr, "manual stashes were counted against the auto budget"
    assert metrics_rows(repo) == []


def test_second_prompt_inside_cooldown_is_silent(repo: Path) -> None:
    make_stashes(repo, 5)
    first = run_hook(repo)
    assert WARNING_MARK in first.stderr

    second = run_hook(repo)

    assert second.returncode == 0, second.stderr
    assert WARNING_MARK not in second.stderr, "re-warned inside the 5-minute cooldown"
    assert len(metrics_rows(repo)) == 1


def test_killswitch_silences_the_hook(repo: Path) -> None:
    make_stashes(repo, 5)
    env = dict(os.environ)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env["DISABLE_HOOK_STASH_BUDGET_WARN"] = "true"
    result = subprocess.run(
        ["/bin/bash", str(repo / HOOK_REL)],
        input="{}",
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo),
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK not in result.stderr
    assert metrics_rows(repo) == []


# --- must warn ---------------------------------------------------------------


def test_over_budget_warns_and_records(repo: Path) -> None:
    """The warning is only half of it — the cooldown and the ledger are the
    part that 335 invocations never reached."""
    make_stashes(repo, 5)

    result = run_hook(repo)

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK in result.stderr, f"stayed silent over budget: {result.stderr!r}"
    assert "Stash count : 5" in result.stderr, (
        f"the count never made it into the message: {result.stderr!r}"
    )

    rows = metrics_rows(repo)
    assert len(rows) == 1, f"the hook died before writing the metrics row: {rows!r}"
    assert rows[0]["count"] == 5
    assert rows[0]["threshold"] == 3
    assert rows[0]["decision"] == "warned"

    cooldown = repo / COOLDOWN_REL
    assert cooldown.exists(), "no cooldown stamp — the next prompt would re-warn immediately"
    assert abs(int(cooldown.read_text().strip()) - int(time.time())) < 120


# --- must never block --------------------------------------------------------


@pytest.mark.parametrize("count", [0, 3, 5])
def test_hook_never_blocks(repo: Path, count: int) -> None:
    make_stashes(repo, count)
    result = run_hook(repo)
    assert result.returncode == 0, (
        f"UserPromptSubmit hook returned {result.returncode} — it would eat the prompt"
    )
