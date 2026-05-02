"""Tests for hooks/stash-budget-warn.sh.

Validates:
- Below threshold: no warning printed
- At/above threshold: warning to stderr + JSONL line written
- Cooldown: second invocation within 5 min does NOT re-warn
- After cooldown expiry: next invocation warns again
- Falsification: rubber-stamp hook (always silent) fails threshold-exceeded scenario
"""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.timeout(60)]

HOOK_PATH = Path(__file__).resolve().parents[2] / "hooks" / "stash-budget-warn.sh"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def git_repo(tmp_path):
    """Temporary git repo with basic config so stash operations work."""
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo, check=True, capture_output=True,
    )

    # Create an initial commit so stash has something to work with
    (repo / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo, check=True, capture_output=True,
    )

    # Ensure runtime + metrics dirs exist
    (repo / ".cognitive-os" / "runtime").mkdir(parents=True)
    (repo / ".cognitive-os" / "metrics").mkdir(parents=True)

    return repo


def _make_auto_stash(repo: Path, tag: str, index: int) -> None:
    """Create one synthetic auto-* stash in the repo."""
    stash_file = repo / f"work-{index}.txt"
    stash_file.write_text(f"work {index}")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "stash", "push", "-m", f"{tag}-{index:04d}"],
        cwd=repo, check=True, capture_output=True,
    )


def _run_hook(repo: Path, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
    """Invoke stash-budget-warn.sh against the given repo and return the result."""
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    # Feed empty JSON on stdin (UserPromptSubmit hook signature)
    if env_overrides:
        env.update(env_overrides)

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input="{}",
        text=True,
        capture_output=True,
        env=env,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Test 1: Below threshold — no warning
# ---------------------------------------------------------------------------

def test_below_threshold_no_warning(git_repo):
    """With 2 matching stashes and default threshold=3, hook stays silent."""
    for i in range(2):
        _make_auto_stash(git_repo, "auto-pre-agent", i)

    result = _run_hook(git_repo)

    assert result.returncode == 0
    assert "stash-budget-warn" not in result.stderr
    assert "BUDGET EXCEEDED" not in result.stderr

    # No JSONL line should be written
    metrics = git_repo / ".cognitive-os" / "metrics" / "stash-budget.jsonl"
    assert not metrics.exists() or metrics.read_text().strip() == ""


# ---------------------------------------------------------------------------
# Test 2: At/above threshold — warning + JSONL
# ---------------------------------------------------------------------------

def test_above_threshold_warns_and_writes_jsonl(git_repo):
    """With 4 matching stashes and default threshold=3, hook warns and writes JSONL."""
    for i in range(4):
        _make_auto_stash(git_repo, "auto-pre-agent", i)

    result = _run_hook(git_repo)

    assert result.returncode == 0
    assert "BUDGET EXCEEDED" in result.stderr
    assert "Stash count" in result.stderr
    assert "git stash list" in result.stderr

    # JSONL line must exist
    metrics = git_repo / ".cognitive-os" / "metrics" / "stash-budget.jsonl"
    assert metrics.exists(), "stash-budget.jsonl was not created"
    lines = [l for l in metrics.read_text().splitlines() if l.strip()]
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry["count"] == 4
    assert entry["threshold"] == 3
    assert entry["decision"] == "warned"


# ---------------------------------------------------------------------------
# Test 3: Cooldown — second call within 5 min stays silent
# ---------------------------------------------------------------------------

def test_cooldown_suppresses_second_warning(git_repo):
    """A second invocation within the 5-min cooldown must not re-warn."""
    for i in range(4):
        _make_auto_stash(git_repo, "auto-checkpoint", i)

    # First call: should warn
    result1 = _run_hook(git_repo)
    assert "BUDGET EXCEEDED" in result1.stderr

    # Second call immediately after: cooldown active, should be silent
    result2 = _run_hook(git_repo)
    assert result2.returncode == 0
    assert "BUDGET EXCEEDED" not in result2.stderr

    # Exactly one JSONL entry (from first call)
    metrics = git_repo / ".cognitive-os" / "metrics" / "stash-budget.jsonl"
    lines = [l for l in metrics.read_text().splitlines() if l.strip()]
    assert len(lines) == 1


# ---------------------------------------------------------------------------
# Test 4: After cooldown expiry — warns again
# ---------------------------------------------------------------------------

def test_after_cooldown_warns_again(git_repo):
    """After manually expiring the cooldown, next invocation warns again."""
    for i in range(4):
        _make_auto_stash(git_repo, "auto-pre-agent", i)

    # First call: warn
    result1 = _run_hook(git_repo)
    assert "BUDGET EXCEEDED" in result1.stderr

    # Expire the cooldown by backdating the file
    cooldown_file = git_repo / ".cognitive-os" / "runtime" / "stash-budget-last-warn.txt"
    old_timestamp = str(int(time.time()) - 400)  # 400s ago > 300s cooldown
    cooldown_file.write_text(old_timestamp)

    # Second call after expiry: should warn again
    result2 = _run_hook(git_repo)
    assert result2.returncode == 0
    assert "BUDGET EXCEEDED" in result2.stderr

    # Two JSONL entries now
    metrics = git_repo / ".cognitive-os" / "metrics" / "stash-budget.jsonl"
    lines = [l for l in metrics.read_text().splitlines() if l.strip()]
    assert len(lines) == 2


# ---------------------------------------------------------------------------
# Test 5: Falsification — rubber-stamp hook never warns, real hook does
# ---------------------------------------------------------------------------

def test_falsification_rubber_stamp_does_not_match_real_hook(git_repo, tmp_path):
    """A rubber-stamp hook (always exits 0 silently) must NOT produce the warning
    that the real hook produces on a threshold-exceeded scenario."""
    for i in range(4):
        _make_auto_stash(git_repo, "auto-pre-agent", i)

    # Create a rubber-stamp hook (always silent)
    rubber_stamp = tmp_path / "rubber-stamp.sh"
    rubber_stamp.write_text("#!/usr/bin/env bash\nexit 0\n")
    rubber_stamp.chmod(0o755)

    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(git_repo)

    # Real hook: must warn
    real_result = _run_hook(git_repo)
    assert "BUDGET EXCEEDED" in real_result.stderr, (
        "Real hook should warn when stash count exceeds threshold"
    )

    # Rubber-stamp: must NOT warn
    stamp_result = subprocess.run(
        ["bash", str(rubber_stamp)],
        input="{}",
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )
    assert stamp_result.returncode == 0
    assert "BUDGET EXCEEDED" not in stamp_result.stderr, (
        "Rubber-stamp hook must not produce the stash budget warning"
    )

    # The two hooks produce different stderr output on the same scenario
    assert real_result.stderr != stamp_result.stderr, (
        "Real hook and rubber-stamp should differ in output on threshold-exceeded scenario"
    )


# ---------------------------------------------------------------------------
# Test 6: Custom threshold via env var
# ---------------------------------------------------------------------------

def test_custom_threshold_env_var(git_repo):
    """COS_STASH_BUDGET_WARN_THRESHOLD=1 triggers warning with just 2 stashes."""
    for i in range(2):
        _make_auto_stash(git_repo, "auto-pre-agent", i)

    result = _run_hook(git_repo, {"COS_STASH_BUDGET_WARN_THRESHOLD": "1"})

    assert result.returncode == 0
    assert "BUDGET EXCEEDED" in result.stderr

    metrics = git_repo / ".cognitive-os" / "metrics" / "stash-budget.jsonl"
    lines = [l for l in metrics.read_text().splitlines() if l.strip()]
    entry = json.loads(lines[-1])
    assert entry["threshold"] == 1


# ---------------------------------------------------------------------------
# Test 7: Killswitch disables hook entirely
# ---------------------------------------------------------------------------

def test_killswitch_disables_hook(git_repo):
    """DISABLE_HOOK_STASH_BUDGET_WARN=true makes hook completely silent."""
    for i in range(5):
        _make_auto_stash(git_repo, "auto-pre-agent", i)

    result = _run_hook(git_repo, {"DISABLE_HOOK_STASH_BUDGET_WARN": "true"})

    assert result.returncode == 0
    assert "BUDGET EXCEEDED" not in result.stderr
    metrics = git_repo / ".cognitive-os" / "metrics" / "stash-budget.jsonl"
    assert not metrics.exists() or metrics.read_text().strip() == ""
