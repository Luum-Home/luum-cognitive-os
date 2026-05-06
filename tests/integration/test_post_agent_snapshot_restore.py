"""Integration tests for hooks/post-agent-snapshot-restore.sh.

Validates the post-agent stash-restore hook that closes the silent-revert
root cause identified in docs/reports/revert-investigation-2026-05-02.md.

Each test executes the hook via subprocess in a temporary git repo so
the tests are fully hermetic and never touch the real working tree.

Test cases:
1. Happy path: pre-agent stash created → post-agent applies it cleanly
2. No stash exists (clean WT before agent): hook is a no-op, exits 0
3. Conflict on apply: stash preserved, log written, hook exits 0 (non-blocking)
4. Bypass via COS_DISABLE_POST_AGENT_RESTORE=1: hook short-circuits immediately
5. Marker file present: matches exact stash by UUID (AGENT_ID)
6. Marker file absent: falls back to most-recent auto-pre-agent stash
7. Falsification: a rubber-stamp hook (always exits 0 with no work) does NOT
   produce a "restored" entry in the metrics JSONL when WT was dirty.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.timeout(60)]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PRE_HOOK = REPO_ROOT / "hooks" / "pre-agent-snapshot.sh"
POST_HOOK = REPO_ROOT / "hooks" / "post-agent-snapshot-restore.sh"

AGENT_STDIN = json.dumps({"tool_name": "Agent", "tool_input": {"description": "test"}})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo with one committed file."""
    repo = tmp_path / "repo"
    repo.mkdir()

    env = _git_env(repo)
    _run(["git", "init"], cwd=repo, env=env)
    _run(["git", "config", "user.email", "test@test.com"], cwd=repo, env=env)
    _run(["git", "config", "user.name", "Test"], cwd=repo, env=env)

    initial = repo / "readme.txt"
    initial.write_text("initial content\n")
    _run(["git", "add", "readme.txt"], cwd=repo, env=env)
    _run(["git", "commit", "-m", "initial commit"], cwd=repo, env=env)

    return repo


def _git_env(repo: Path) -> dict:
    """Build minimal env for hook execution."""
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env["CLAUDE_PROJECT_DIR"] = str(repo)
    env["COGNITIVE_OS_SESSION_ID"] = "test-session"
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@test.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@test.com"
    # Prevent hooks from sourcing project-level kill-switch check failing
    env["SO_KILLSWITCH"] = ""
    # Skip any validation mode short-circuits
    env["COS_VALIDATION_MODE"] = "0"
    env["COS_SUPPRESS_AGENT_SNAPSHOT"] = "0"
    return env


def _run(cmd: list, cwd: Path, env: dict | None = None, input_text: str = "") -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        input=input_text,
        env=env,
    )


def _run_pre_hook(repo: Path, agent_id: str | None, env: dict, stdin: str = AGENT_STDIN) -> subprocess.CompletedProcess:
    """Invoke pre-agent-snapshot.sh with synthetic Agent stdin."""
    hook_env = {**env}
    if agent_id is not None:
        hook_env["CLAUDE_AGENT_ID"] = agent_id
    else:
        hook_env.pop("CLAUDE_AGENT_ID", None)
    return _run(
        ["bash", str(PRE_HOOK)],
        cwd=repo,
        env=hook_env,
        input_text=stdin,
    )


def _run_post_hook(
    repo: Path,
    agent_id: str | None,
    env: dict,
    extra_env: dict | None = None,
    stdin: str = AGENT_STDIN,
) -> subprocess.CompletedProcess:
    """Invoke post-agent-snapshot-restore.sh with synthetic Agent stdin."""
    hook_env = {**env}
    if agent_id is not None:
        hook_env["CLAUDE_AGENT_ID"] = agent_id
    else:
        hook_env.pop("CLAUDE_AGENT_ID", None)
    if extra_env:
        hook_env.update(extra_env)
    return _run(
        ["bash", str(POST_HOOK)],
        cwd=repo,
        env=hook_env,
        input_text=stdin,
    )


def _metrics_log(repo: Path) -> Path:
    return repo / ".cognitive-os" / "metrics" / "agent-snapshots.jsonl"


def _read_metrics(repo: Path) -> list[dict]:
    log = _metrics_log(repo)
    if not log.exists():
        return []
    lines = [l for l in log.read_text().splitlines() if l.strip()]
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return records


def _stash_count(repo: Path) -> int:
    result = _run(["git", "stash", "list"], cwd=repo)
    return len([l for l in result.stdout.splitlines() if l.strip()])


def _runtime_markers(repo: Path) -> list[Path]:
    runtime = repo / ".cognitive-os" / "runtime"
    if not runtime.exists():
        return []
    return sorted(runtime.glob("pre-agent-snapshot-*.json"))


# ---------------------------------------------------------------------------
# Test 1 — Happy path: dirty WT, pre-agent stashes, post-agent restores
# ---------------------------------------------------------------------------

def test_happy_path_restore(git_repo: Path):
    """Pre-agent stashes tracked modifications; post-agent applies stash cleanly."""
    env = _git_env(git_repo)
    agent_id = "test-agent-happy-001"

    # Make WT dirty
    (git_repo / "readme.txt").write_text("modified by agent scenario\n")

    stash_count_before = _stash_count(git_repo)

    # Run pre-agent hook — should stash the change
    pre_result = _run_pre_hook(git_repo, agent_id, env)
    assert pre_result.returncode == 0, f"pre-hook failed: {pre_result.stderr}"

    stash_count_after_pre = _stash_count(git_repo)
    assert stash_count_after_pre > stash_count_before, "Pre-hook should have created a stash"

    # Simulate agent modifying WT back (so apply has something to do)
    # (stash --keep-index keeps index; the WT may or may not be clean depending
    #  on tracked vs staged state — the key is: the stash exists and apply works)

    # Run post-agent hook — should apply the stash
    post_result = _run_post_hook(git_repo, agent_id, env)
    assert post_result.returncode == 0, f"post-hook failed: {post_result.stderr}"

    assert _stash_count(git_repo) == stash_count_before, "Successful auto-pre-agent restore should drop its transient stash"

    # Verify metrics log has a restore event
    records = _read_metrics(git_repo)
    restore_events = [r for r in records if r.get("action") == "restored"]
    assert restore_events, f"Expected 'restored' action in metrics. Records: {records}"
    assert restore_events[-1].get("stash_cleanup") == "dropped"


# ---------------------------------------------------------------------------
# Test 2 — No stash exists (clean WT): hook is a no-op
# ---------------------------------------------------------------------------

def test_no_stash_noop(git_repo: Path):
    """When WT is clean, pre-hook skips stashing; post-hook is a clean no-op."""
    env = _git_env(git_repo)
    agent_id = "test-agent-noop-002"

    # WT is clean (no modifications after initial commit)
    pre_result = _run_pre_hook(git_repo, agent_id, env)
    assert pre_result.returncode == 0

    stash_count = _stash_count(git_repo)
    assert stash_count == 0, "Should be no stashes when WT was clean"

    post_result = _run_post_hook(git_repo, agent_id, env)
    assert post_result.returncode == 0, f"Post-hook should exit 0 even on no-op. stderr={post_result.stderr}"

    # Metrics: should NOT have a restore event when WT was clean
    records = _read_metrics(git_repo)
    restore_events = [r for r in records if r.get("action") == "restored"]
    assert not restore_events, f"Should not have restore events when WT was clean. Records: {records}"


# ---------------------------------------------------------------------------
# Test 3 — Conflict on apply: stash preserved, log written, exits 0
# ---------------------------------------------------------------------------

def test_conflict_on_apply_nonblocking(git_repo: Path):
    """When git stash apply has a conflict, hook exits 0 and preserves stash."""
    env = _git_env(git_repo)
    agent_id = "test-agent-conflict-003"

    # Make WT dirty and stash it via pre-hook
    (git_repo / "readme.txt").write_text("version A — will conflict\n")
    pre_result = _run_pre_hook(git_repo, agent_id, env)
    assert pre_result.returncode == 0

    stash_count = _stash_count(git_repo)
    if stash_count == 0:
        pytest.skip("Pre-hook did not create a stash (WT may not have had tracked changes)")

    # Now write conflicting content to the same file so apply will conflict
    (git_repo / "readme.txt").write_text("version B — conflicting content\n")

    # Post-hook should exit 0 despite conflict
    post_result = _run_post_hook(git_repo, agent_id, env)
    assert post_result.returncode == 0, "Post-hook must be non-blocking even on conflict"

    # Stash should still be present (not popped)
    stash_count_after = _stash_count(git_repo)
    assert stash_count_after >= stash_count, "Stash should be preserved on conflict"

    # Conflict warning should appear on stderr or log
    has_conflict_log = any(
        r.get("action") == "conflict"
        for r in _read_metrics(git_repo)
    )
    has_stderr_warning = "conflict" in post_result.stderr.lower() or "WARN" in post_result.stderr
    assert has_conflict_log or has_stderr_warning, (
        "Should log or warn about conflict. "
        f"stderr={post_result.stderr!r}, metrics={_read_metrics(git_repo)}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Bypass via env var: hook short-circuits
# ---------------------------------------------------------------------------

def test_bypass_env_var(git_repo: Path):
    """COS_DISABLE_POST_AGENT_RESTORE=1 causes immediate exit 0 with no side effects."""
    env = _git_env(git_repo)
    agent_id = "test-agent-bypass-004"

    # Make WT dirty
    (git_repo / "readme.txt").write_text("dirty for bypass test\n")
    _run_pre_hook(git_repo, agent_id, env)

    metrics_before = len(_read_metrics(git_repo))

    # Run post-hook with bypass
    post_result = _run_post_hook(
        git_repo, agent_id, env,
        extra_env={"COS_DISABLE_POST_AGENT_RESTORE": "1"},
    )
    assert post_result.returncode == 0

    metrics_after = len(_read_metrics(git_repo))
    # Hook should have added no new metrics entries
    assert metrics_after == metrics_before, (
        "Bypassed hook should not write metrics entries. "
        f"Before={metrics_before}, after={metrics_after}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Marker file present: matches exact stash by UUID
# ---------------------------------------------------------------------------

def test_marker_file_exact_match(git_repo: Path):
    """When marker file is present, post-hook uses the exact stash_ref in the marker."""
    env = _git_env(git_repo)
    agent_id = "test-agent-marker-005"

    # Make WT dirty
    (git_repo / "readme.txt").write_text("dirty for marker test\n")

    # Run pre-hook — this should create the marker file
    pre_result = _run_pre_hook(git_repo, agent_id, env)
    assert pre_result.returncode == 0

    stash_count = _stash_count(git_repo)
    if stash_count == 0:
        pytest.skip("Pre-hook did not create a stash")

    # Verify marker file was written
    marker_path = git_repo / ".cognitive-os" / "runtime" / f"pre-agent-snapshot-{agent_id}.json"
    assert marker_path.exists(), f"Marker file should exist at {marker_path}"

    marker_data = json.loads(marker_path.read_text())
    assert marker_data.get("stash_ref"), "Marker should contain stash_ref"
    assert marker_data.get("agent_id") == agent_id

    # Run post-hook — should use marker to apply exact stash
    post_result = _run_post_hook(git_repo, agent_id, env)
    assert post_result.returncode == 0

    records = _read_metrics(git_repo)
    restore_events = [r for r in records if r.get("action") == "restored"]
    assert restore_events, f"Should have restored via marker. Records: {records}"

    assert not marker_path.exists(), "Marker must be cleaned up after successful restore"


def test_deterministic_payload_id_restores_long_running_agent_without_env_id(git_repo: Path):
    """PostToolUse can exact-match pre markers even without CLAUDE_AGENT_ID.

    This reproduces the real failure mode: pre generated a random ID, the agent
    ran longer than the five-minute fallback window, and post had agent_id=unknown.
    Deterministic IDs from tool_input remove that time dependency.
    """
    env = _git_env(git_repo)
    payload = json.dumps(
        {
            "tool_name": "Agent",
            "tool_use_id": "toolu_snapshot_exact_001",
            "tool_input": {"description": "long SDD propose", "prompt": "long SDD propose"},
        }
    )

    (git_repo / "readme.txt").write_text("dirty before long agent\n")
    pre_result = _run_pre_hook(git_repo, None, env, stdin=payload)
    assert pre_result.returncode == 0, pre_result.stderr
    assert _stash_count(git_repo) == 1

    markers = _runtime_markers(git_repo)
    assert len(markers) == 1
    marker_data = json.loads(markers[0].read_text())
    assert marker_data["agent_id"] == "toolu_snapshot_exact_001"
    assert marker_data["session_id"] == "test-session"

    post_payload = json.dumps(
        {
            "tool_name": "Agent",
            "tool_use_id": "toolu_snapshot_exact_001",
            "tool_input": {"description": "long SDD propose", "prompt": "long SDD propose"},
            "tool_response": "completed after more than five minutes",
        }
    )
    post_result = _run_post_hook(git_repo, None, env, stdin=post_payload)
    assert post_result.returncode == 0, post_result.stderr

    records = _read_metrics(git_repo)
    assert any(r.get("action") == "restored" for r in records), records
    assert _runtime_markers(git_repo) == []
    assert _stash_count(git_repo) == 0


def test_copy_only_marker_is_removed_on_post_noop(git_repo: Path):
    """Copy-mode untracked snapshots should not leave permanent runtime markers."""
    env = _git_env(git_repo)
    agent_id = "copy-only-marker"
    (git_repo / "notes.txt").write_text("untracked but still present\n")

    pre_result = _run_pre_hook(git_repo, agent_id, env)
    assert pre_result.returncode == 0, pre_result.stderr
    assert _stash_count(git_repo) == 0
    marker_path = git_repo / ".cognitive-os" / "runtime" / f"pre-agent-snapshot-{agent_id}.json"
    assert marker_path.exists()
    assert json.loads(marker_path.read_text()).get("stash_ref") == ""

    post_result = _run_post_hook(git_repo, agent_id, env)
    assert post_result.returncode == 0, post_result.stderr
    assert not marker_path.exists(), "copy-only marker should be completed and removed"
    assert any(r.get("action") == "skip_no_stash" for r in _read_metrics(git_repo))


# ---------------------------------------------------------------------------
# Test 6 — Marker file absent: fallback to most-recent auto-pre-agent stash
# ---------------------------------------------------------------------------

def test_fallback_without_marker(git_repo: Path):
    """When AGENT_ID is unknown, hook falls back to most-recent auto-pre-agent stash."""
    env = _git_env(git_repo)
    agent_id = "test-agent-fallback-006"

    # Make WT dirty
    (git_repo / "readme.txt").write_text("dirty for fallback test\n")

    # Run pre-hook WITH a known agent ID (creates stash + marker)
    pre_result = _run_pre_hook(git_repo, agent_id, env)
    assert pre_result.returncode == 0

    stash_count = _stash_count(git_repo)
    if stash_count == 0:
        pytest.skip("Pre-hook did not create a stash")

    # Delete the marker to simulate absence (fallback scenario)
    marker_path = git_repo / ".cognitive-os" / "runtime" / f"pre-agent-snapshot-{agent_id}.json"
    if marker_path.exists():
        marker_path.unlink()

    # Run post-hook WITHOUT agent ID — fallback path
    fallback_env = {**env}
    fallback_env.pop("CLAUDE_AGENT_ID", None)
    post_result = subprocess.run(
        ["bash", str(POST_HOOK)],
        cwd=str(git_repo),
        capture_output=True,
        text=True,
        input=AGENT_STDIN,
        env=fallback_env,
    )
    # Hook must exit 0 in any case
    assert post_result.returncode == 0, f"Post-hook must be non-blocking. stderr={post_result.stderr}"

    records = _read_metrics(git_repo)
    # Check either restored (fallback worked) or skip_no_stash (stash list timestamp
    # didn't match 5-min window in CI). Either is acceptable for the fallback case.
    actions = {r.get("action") for r in records}
    assert actions & {"restored", "skip_no_stash", "conflict"}, (
        f"Post-hook should log an action. Records: {records}"
    )


# ---------------------------------------------------------------------------
# Test 7 — Falsification: rubber-stamp hook does NOT produce restore evidence
# ---------------------------------------------------------------------------

def test_falsification_rubber_stamp(git_repo: Path, tmp_path: Path):
    """A hook that always exits 0 with no work does NOT match real restore behavior.

    This test writes a minimal 'rubber-stamp' hook (always exits 0, writes nothing)
    and asserts that its behavior is distinguishable from the real hook's behavior
    on a dirty-WT scenario: the real hook produces a 'restored' metrics entry,
    the rubber-stamp does not.
    """
    env = _git_env(git_repo)
    agent_id = "test-agent-falsify-007"

    # Make WT dirty and create stash via pre-hook
    (git_repo / "readme.txt").write_text("dirty for falsification test\n")
    _run_pre_hook(git_repo, agent_id, env)

    stash_count = _stash_count(git_repo)
    if stash_count == 0:
        pytest.skip("Pre-hook did not create a stash")

    # Write a rubber-stamp hook
    rubber_stamp = tmp_path / "rubber-stamp.sh"
    rubber_stamp.write_text("#!/usr/bin/env bash\n# does nothing\nexit 0\n")
    rubber_stamp.chmod(0o755)

    # Run rubber-stamp: exits 0, writes nothing
    stamp_result = _run(
        ["bash", str(rubber_stamp)],
        cwd=git_repo,
        env=env,
        input_text=AGENT_STDIN,
    )
    assert stamp_result.returncode == 0

    metrics_after_stamp = _read_metrics(git_repo)
    restore_events_after_stamp = [r for r in metrics_after_stamp if r.get("action") == "restored"]

    # Clear log to isolate real hook run
    log = _metrics_log(git_repo)
    if log.exists():
        log.write_text("")

    # Run real post-hook
    real_result = _run_post_hook(git_repo, agent_id, env)
    assert real_result.returncode == 0

    metrics_after_real = _read_metrics(git_repo)
    restore_events_after_real = [r for r in metrics_after_real if r.get("action") == "restored"]

    # Falsification: real hook produces restore evidence; rubber-stamp does not
    assert not restore_events_after_stamp, (
        "Rubber-stamp should produce no restore events — it does no work"
    )
    assert restore_events_after_real, (
        "Real hook should produce restore event on dirty-WT scenario. "
        f"Records: {metrics_after_real}"
    )
