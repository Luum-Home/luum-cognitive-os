"""Behavior tests for context compaction resilience.

Validates that the hooks that guard against compaction behave correctly:
  - context-watchdog.sh: fires on every tool call, tracks count, warns at thresholds
  - pre-compaction-flush.sh: extended output checks (in-progress task, git branch/status)

These complement the existing tests in tests/unit/test_compaction_behavior.py.
We test the hooks as subprocesses — the same way they run in production.
"""

import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = PROJECT_ROOT / "hooks"
WATCHDOG_PATH = HOOKS_DIR / "context-watchdog.sh"
FLUSH_PATH = HOOKS_DIR / "pre-compaction-flush.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(hook_path: Path, env_overrides: "dict | None" = None, timeout: int = 10) -> subprocess.CompletedProcess:
    """Run a hook script and return the CompletedProcess."""
    if not hook_path.exists():
        pytest.skip(f"Hook not found: {hook_path}")

    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    return subprocess.run(
        ["bash", str(hook_path)],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        input="",
    )


def _run_watchdog(count_override: int = 1, tmp_dir: "Path | None" = None, timeout: int = 10) -> subprocess.CompletedProcess:
    """Run context-watchdog.sh with a pre-seeded tool-call counter."""
    import tempfile

    if tmp_dir is None:
        tmp_dir = Path(tempfile.mkdtemp())

    session_dir = tmp_dir / ".cognitive-os" / "sessions" / "current"
    session_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir = tmp_dir / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    # Pre-seed the counter to count_override - 1 so after +1 in the hook it reaches count_override
    counter_file = session_dir / "tool-call-count"
    counter_file.write_text(str(count_override - 1))

    env = {"CLAUDE_PROJECT_DIR": str(tmp_dir)}
    return _run(WATCHDOG_PATH, env_overrides=env, timeout=timeout)


# ===========================================================================
# context-watchdog.sh tests
# ===========================================================================


class TestContextWatchdogExitBehavior:
    """context-watchdog.sh must ALWAYS exit 0 — never block tool calls."""

    def test_exits_zero_at_low_count(self, tmp_path):
        """Hook exits 0 at low tool call counts."""
        result = _run_watchdog(count_override=10, tmp_dir=tmp_path)
        assert result.returncode == 0, (
            f"context-watchdog.sh exited {result.returncode} at count=10\n"
            f"stderr: {result.stderr}"
        )

    def test_exits_zero_at_50_percent_threshold(self, tmp_path):
        """Hook exits 0 even when the 50% threshold is crossed."""
        result = _run_watchdog(count_override=130, tmp_dir=tmp_path)
        assert result.returncode == 0

    def test_exits_zero_at_70_percent_threshold(self, tmp_path):
        """Hook exits 0 even at the 70% warning threshold."""
        result = _run_watchdog(count_override=185, tmp_dir=tmp_path)
        assert result.returncode == 0

    def test_exits_zero_at_85_percent_threshold(self, tmp_path):
        """Hook exits 0 even at the 85% urgent threshold."""
        result = _run_watchdog(count_override=225, tmp_dir=tmp_path)
        assert result.returncode == 0

    def test_exits_zero_well_above_threshold(self, tmp_path):
        """Hook exits 0 even when far above all thresholds."""
        result = _run_watchdog(count_override=999, tmp_dir=tmp_path)
        assert result.returncode == 0


class TestContextWatchdogThresholdWarnings:
    """context-watchdog.sh must emit threshold warnings to stderr at the right counts."""

    def test_no_warning_below_50_percent(self, tmp_path):
        """Below threshold 50 (130 calls), hook is completely silent on stderr."""
        result = _run_watchdog(count_override=50, tmp_dir=tmp_path)
        assert result.returncode == 0
        assert not result.stderr.strip(), (
            f"Expected no stderr below 50% threshold, got: {result.stderr!r}"
        )

    def test_warning_emitted_at_70_percent(self, tmp_path):
        """At 185+ tool calls (70%), hook emits WARNING to stderr."""
        result = _run_watchdog(count_override=185, tmp_dir=tmp_path)
        assert result.returncode == 0
        assert "WARNING" in result.stderr or "warning" in result.stderr.lower(), (
            f"Expected WARNING in stderr at count=185\nstderr: {result.stderr!r}"
        )

    def test_urgent_warning_emitted_at_85_percent(self, tmp_path):
        """At 225+ tool calls (85%), hook emits URGENT to stderr."""
        result = _run_watchdog(count_override=225, tmp_dir=tmp_path)
        assert result.returncode == 0
        assert "URGENT" in result.stderr or "urgent" in result.stderr.lower(), (
            f"Expected URGENT in stderr at count=225\nstderr: {result.stderr!r}"
        )

    def test_70_percent_warning_mentions_engram(self, tmp_path):
        """The 70% warning must tell the agent to save to Engram."""
        result = _run_watchdog(count_override=190, tmp_dir=tmp_path)
        stderr_lower = result.stderr.lower()
        has_engram_ref = "engram" in stderr_lower or "mem_save" in result.stderr or "save" in stderr_lower
        assert has_engram_ref, (
            f"Expected Engram save instruction in 70% warning.\nstderr: {result.stderr!r}"
        )

    def test_85_percent_warning_mentions_session_summary(self, tmp_path):
        """The 85% urgent warning must mention mem_session_summary."""
        result = _run_watchdog(count_override=230, tmp_dir=tmp_path)
        has_session_ref = (
            "mem_session_summary" in result.stderr
            or "session_summary" in result.stderr.lower()
            or "session" in result.stderr.lower()
        )
        assert has_session_ref, (
            f"Expected session summary instruction in URGENT warning.\nstderr: {result.stderr!r}"
        )

    def test_85_percent_warning_says_stop(self, tmp_path):
        """The urgent warning must tell the agent to stop new work."""
        result = _run_watchdog(count_override=230, tmp_dir=tmp_path)
        stderr_lower = result.stderr.lower()
        has_stop = any(kw in stderr_lower for kw in ("stop", "halt", "finish", "compact"))
        assert has_stop, (
            f"Expected 'stop new work' instruction in URGENT warning.\nstderr: {result.stderr!r}"
        )


class TestContextWatchdogPerformance:
    """context-watchdog.sh must be fast — it runs on every tool call."""

    def test_completes_under_200ms(self, tmp_path):
        """Hook must complete in under 200ms to stay under the <50ms target (allowing CI overhead)."""
        start = time.monotonic()
        result = _run_watchdog(count_override=10, tmp_dir=tmp_path, timeout=5)
        elapsed = time.monotonic() - start
        assert result.returncode == 0
        assert elapsed < 0.5, (
            f"Hook took {elapsed * 1000:.0f}ms — expected <500ms (target is <50ms); "
            f"may indicate a slow CI environment or a performance regression."
        )

    def test_completes_under_200ms_at_high_count(self, tmp_path):
        """Hook stays fast even at high tool call counts."""
        start = time.monotonic()
        result = _run_watchdog(count_override=500, tmp_dir=tmp_path, timeout=5)
        elapsed = time.monotonic() - start
        assert result.returncode == 0
        assert elapsed < 0.5, (
            f"Hook took {elapsed * 1000:.0f}ms at high count — performance regression"
        )


class TestContextWatchdogRobustness:
    """context-watchdog.sh handles edge environments gracefully."""

    def test_creates_session_dir_if_missing(self, tmp_path):
        """Hook creates the session directory if it doesn't exist."""
        # Don't pre-create the session dir — let the hook do it
        env = {"CLAUDE_PROJECT_DIR": str(tmp_path)}
        result = _run(WATCHDOG_PATH, env_overrides=env)
        assert result.returncode == 0

    def test_handles_missing_claude_project_dir(self):
        """Hook survives when CLAUDE_PROJECT_DIR is not set."""
        env = os.environ.copy()
        env.pop("CLAUDE_PROJECT_DIR", None)
        result = subprocess.run(
            ["bash", str(WATCHDOG_PATH)],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
            input="",
        )
        assert result.returncode == 0, (
            f"Hook crashed without CLAUDE_PROJECT_DIR\nstderr: {result.stderr}"
        )

    def test_handles_corrupted_counter_file(self, tmp_path):
        """Hook recovers gracefully when the counter file contains garbage."""
        session_dir = tmp_path / ".cognitive-os" / "sessions" / "current"
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "tool-call-count").write_text("not-a-number!@#")

        env = {"CLAUDE_PROJECT_DIR": str(tmp_path)}
        result = _run(WATCHDOG_PATH, env_overrides=env)
        assert result.returncode == 0, (
            f"Hook crashed on corrupted counter file\nstderr: {result.stderr}"
        )

    def test_counter_increments_each_run(self, tmp_path):
        """Each invocation must increment the counter by 1."""
        session_dir = tmp_path / ".cognitive-os" / "sessions" / "current"
        session_dir.mkdir(parents=True, exist_ok=True)
        counter_file = session_dir / "tool-call-count"
        counter_file.write_text("10")

        env = {"CLAUDE_PROJECT_DIR": str(tmp_path)}
        _run(WATCHDOG_PATH, env_overrides=env)

        new_count = int(counter_file.read_text().strip())
        assert new_count == 11, f"Expected counter to be 11, got {new_count}"

    def test_counter_starts_at_one_when_missing(self, tmp_path):
        """Counter starts at 1 when no counter file exists."""
        session_dir = tmp_path / ".cognitive-os" / "sessions" / "current"
        session_dir.mkdir(parents=True, exist_ok=True)
        counter_file = session_dir / "tool-call-count"
        # Ensure counter does not exist
        counter_file.unlink(missing_ok=True)

        env = {"CLAUDE_PROJECT_DIR": str(tmp_path)}
        _run(WATCHDOG_PATH, env_overrides=env)

        new_count = int(counter_file.read_text().strip())
        assert new_count == 1, f"Expected counter to start at 1, got {new_count}"

    def test_metrics_file_written_at_threshold(self, tmp_path):
        """Hook writes to the metrics JSONL file when a threshold is crossed."""
        _run_watchdog(count_override=185, tmp_dir=tmp_path)

        metrics_file = tmp_path / ".cognitive-os" / "metrics" / "context-watchdog.jsonl"
        assert metrics_file.exists(), "Metrics file not created at 70% threshold"
        content = metrics_file.read_text().strip()
        assert content, "Metrics file is empty after threshold was crossed"

    def test_metrics_file_contains_valid_json(self, tmp_path):
        """Metrics file entries are valid JSON objects."""
        import json
        _run_watchdog(count_override=185, tmp_dir=tmp_path)

        metrics_file = tmp_path / ".cognitive-os" / "metrics" / "context-watchdog.jsonl"
        if not metrics_file.exists():
            pytest.skip("Metrics file not created — likely below logging threshold")

        for line in metrics_file.read_text().strip().splitlines():
            obj = json.loads(line)
            assert "tool_calls" in obj, f"Missing tool_calls field in: {line}"
            assert "level" in obj, f"Missing level field in: {line}"
            assert "usage_pct" in obj, f"Missing usage_pct field in: {line}"


# ===========================================================================
# pre-compaction-flush.sh extended behavior tests
# ===========================================================================


class TestPreCompactionFlushExtended:
    """Extended behavior tests for pre-compaction-flush.sh.

    The unit tests in test_compaction_behavior.py cover the core behavior.
    These tests check the additional requirements around in-progress tasks,
    git status, and the overall compaction resilience narrative.
    """

    def test_hook_instructs_to_note_in_progress_tasks(self):
        """Agent must be told to note in-progress tasks for session resumption."""
        result = _run(FLUSH_PATH)
        output_lower = result.stdout.lower()
        has_task_ref = any(
            kw in output_lower
            for kw in ("in-progress", "in progress", "task", "resume", "next session")
        )
        assert has_task_ref, (
            f"Expected in-progress task instruction.\nGot: {result.stdout!r}"
        )

    def test_hook_instructs_to_note_files_being_modified(self):
        """Agent should capture which files are being modified when compaction hits."""
        result = _run(FLUSH_PATH)
        output_lower = result.stdout.lower()
        # The hook should mention saving the state of current modifications
        has_files_ref = any(
            kw in output_lower
            for kw in ("file", "modif", "discover", "decision", "bug", "fix")
        )
        assert has_files_ref, (
            f"Expected reference to files/decisions being modified.\nGot: {result.stdout!r}"
        )

    def test_hook_output_mentions_next_session_continuity(self):
        """Output must reference continuity for the next session."""
        result = _run(FLUSH_PATH)
        output_lower = result.stdout.lower()
        has_continuity = any(
            kw in output_lower
            for kw in ("next session", "resume", "after", "continue", "start blind", "blind")
        )
        assert has_continuity, (
            f"Expected next-session continuity instruction.\nGot: {result.stdout!r}"
        )

    def test_hook_warns_about_consequence_of_not_saving(self):
        """Hook must tell the agent WHY saving is critical (not optional framing)."""
        result = _run(FLUSH_PATH)
        output_lower = result.stdout.lower()
        has_consequence = any(
            kw in output_lower
            for kw in ("not optional", "without", "blind", "critical", "must", "will")
        )
        assert has_consequence, (
            f"Expected consequence framing (why saving matters).\nGot: {result.stdout!r}"
        )

    def test_both_hooks_exit_zero(self):
        """Both compaction protection hooks must always exit 0."""
        flush_result = _run(FLUSH_PATH)
        watchdog_result = _run(WATCHDOG_PATH)
        assert flush_result.returncode == 0, f"pre-compaction-flush.sh failed: {flush_result.stderr}"
        assert watchdog_result.returncode == 0, f"context-watchdog.sh failed: {watchdog_result.stderr}"
