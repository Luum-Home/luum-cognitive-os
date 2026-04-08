"""Behavioral tests for context compaction.

Verifies the pre-compaction-flush hook produces the expected instructions
and behaves gracefully under edge conditions (missing session, empty env, etc.).

The hook is a PreCompact hook that outputs save-to-Engram instructions.
We test it as a subprocess, the same way it runs in production.
"""

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"
HOOK_PATH = HOOKS_DIR / "pre-compaction-flush.sh"


def _run_hook(env_overrides: "dict | None" = None, timeout: int = 10) -> subprocess.CompletedProcess:
    """Execute pre-compaction-flush.sh and return the result.

    Args:
        env_overrides: Optional dict merged into the subprocess environment.
        timeout: Seconds before the subprocess is killed.

    Returns:
        CompletedProcess with stdout, stderr, and returncode.
    """
    if not HOOK_PATH.exists():
        pytest.skip(f"Hook not found: {HOOK_PATH}")

    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        input="",  # no stdin needed
    )


# ---------------------------------------------------------------------------
# Core behavior: hook outputs save instructions
# ---------------------------------------------------------------------------


class TestPreCompactionFlushOutputs:
    """pre-compaction-flush.sh must emit actionable save instructions."""

    def test_hook_exits_zero(self):
        """Hook should always exit 0 — it never blocks compaction."""
        result = _run_hook()
        assert result.returncode == 0, (
            f"pre-compaction-flush.sh exited {result.returncode} — expected 0\n"
            f"stderr: {result.stderr}"
        )

    def test_hook_produces_output(self):
        """Hook must produce non-empty stdout (the save instructions)."""
        result = _run_hook()
        assert result.stdout.strip(), (
            "pre-compaction-flush.sh produced no output — instructions missing"
        )

    def test_hook_mentions_session_summary(self):
        """Output must instruct the agent to call mem_session_summary."""
        result = _run_hook()
        output = result.stdout.lower()
        assert "mem_session_summary" in result.stdout or "session_summary" in output, (
            f"Expected mem_session_summary instruction in output.\nGot: {result.stdout!r}"
        )

    def test_hook_mentions_saving_to_engram(self):
        """Output must instruct the agent to save decisions/discoveries to Engram."""
        result = _run_hook()
        output_lower = result.stdout.lower()
        # Check for engram save instructions or mem_save
        has_save_instruction = (
            "mem_save" in result.stdout
            or "engram" in output_lower
            or "save" in output_lower
        )
        assert has_save_instruction, (
            f"Expected save-to-Engram instruction in output.\nGot: {result.stdout!r}"
        )

    def test_hook_output_contains_numbered_steps(self):
        """Output should provide ordered steps (1. ... 2. ... 3. ...) for clarity."""
        result = _run_hook()
        # The hook outputs "1.", "2.", "3." — structured instructions
        assert "1." in result.stdout or "2." in result.stdout, (
            f"Expected numbered steps in output.\nGot: {result.stdout!r}"
        )

    def test_hook_mentions_compaction_context(self):
        """Output should reference compaction or context window pressure."""
        result = _run_hook()
        output_lower = result.stdout.lower()
        has_context_ref = (
            "compact" in output_lower
            or "context" in output_lower
            or "session" in output_lower
        )
        assert has_context_ref, (
            f"Expected compaction/context reference in output.\nGot: {result.stdout!r}"
        )

    def test_hook_output_is_actionable(self):
        """Output must contain imperative verbs: MUST, call, save, note."""
        result = _run_hook()
        output_lower = result.stdout.lower()
        has_imperative = any(
            kw in output_lower
            for kw in ("must", "call", "save", "note", "before")
        )
        assert has_imperative, (
            f"Expected actionable imperative language in output.\nGot: {result.stdout!r}"
        )


# ---------------------------------------------------------------------------
# Robustness: missing session, empty env, custom session ID
# ---------------------------------------------------------------------------


class TestPreCompactionFlushRobustness:
    """Hook must handle edge environments gracefully."""

    def test_hook_succeeds_without_session_id(self):
        """Hook must not crash when COGNITIVE_OS_SESSION_ID is empty."""
        result = _run_hook(env_overrides={"COGNITIVE_OS_SESSION_ID": ""})
        assert result.returncode == 0, (
            f"Hook crashed with empty session ID (exit {result.returncode})\n"
            f"stderr: {result.stderr}"
        )

    def test_hook_succeeds_without_project_dir(self):
        """Hook must work even when CLAUDE_PROJECT_DIR is unset."""
        env = os.environ.copy()
        env.pop("CLAUDE_PROJECT_DIR", None)
        env.pop("COGNITIVE_OS_PROJECT_DIR", None)

        result = subprocess.run(
            ["bash", str(HOOK_PATH)],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
            input="",
        )
        assert result.returncode == 0, (
            f"Hook crashed without project dir (exit {result.returncode})\n"
            f"stderr: {result.stderr}"
        )

    def test_hook_is_idempotent(self):
        """Running the hook multiple times produces the same output."""
        result1 = _run_hook()
        result2 = _run_hook()
        assert result1.stdout == result2.stdout, (
            "pre-compaction-flush.sh is not idempotent — output varies between runs"
        )
        assert result1.returncode == result2.returncode == 0

    def test_hook_output_stable_across_environments(self):
        """Hook output should be the same regardless of session ID value."""
        result_a = _run_hook(env_overrides={"COGNITIVE_OS_SESSION_ID": "session-abc-123"})
        result_b = _run_hook(env_overrides={"COGNITIVE_OS_SESSION_ID": "session-xyz-999"})
        # Both should succeed and produce identical instructions
        assert result_a.returncode == 0
        assert result_b.returncode == 0
        # The static message should be the same
        assert result_a.stdout == result_b.stdout, (
            "Hook output changed with different session IDs — should output static instructions"
        )

    def test_hook_does_not_write_to_stderr_normally(self):
        """Under normal conditions, hook should not write to stderr."""
        result = _run_hook()
        # Stderr should be empty (or contain only debug info, not errors)
        assert result.returncode == 0
        # If there's stderr output, it must not contain "error" or "failed"
        if result.stderr.strip():
            stderr_lower = result.stderr.lower()
            assert "error" not in stderr_lower and "failed" not in stderr_lower, (
                f"Hook wrote error to stderr: {result.stderr!r}"
            )

    def test_hook_completes_quickly(self):
        """Hook must complete in under 5 seconds — it's in the compaction critical path."""
        import time

        start = time.monotonic()
        result = _run_hook(timeout=5)
        elapsed = time.monotonic() - start
        assert result.returncode == 0
        assert elapsed < 5.0, (
            f"Hook took {elapsed:.2f}s — must complete under 5s"
        )

    def test_hook_output_contains_in_progress_task_reference(self):
        """Agent should be told to note in-progress tasks for session continuity."""
        result = _run_hook()
        output_lower = result.stdout.lower()
        has_task_ref = any(
            kw in output_lower
            for kw in ("in-progress", "in progress", "task", "resume", "next session")
        )
        assert has_task_ref, (
            f"Expected in-progress task instruction.\nGot: {result.stdout!r}"
        )
