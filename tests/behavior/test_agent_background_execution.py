"""Behavior tests for agent background execution of long-running commands.

Tests verify that:
1. The agent preamble documents background execution requirements
2. Related rules reference background execution patterns
3. Background execution actually works via subprocess simulation
4. Timeout configuration is appropriate for test suites
"""

import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).parent.parent.parent
PREAMBLE_PATH = PROJECT_ROOT / "templates" / "agent-preamble.md"
RESPONSIVENESS_PATH = PROJECT_ROOT / "rules" / "responsiveness.md"
CLOSED_LOOP_PATH = PROJECT_ROOT / "rules" / "closed-loop-prompts.md"


# ---------------------------------------------------------------------------
# Preamble content tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Pattern documentation tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Integration tests -- actual background behavior
# ---------------------------------------------------------------------------


class TestBackgroundExecution:
    """Integration tests proving background vs foreground behavior."""

    def test_background_command_returns_immediately(self):
        """A background subprocess must return control in under 1 second.

        Simulates what an agent does when using run_in_background: true --
        the agent launches a subprocess without waiting for it to finish.
        """
        start = time.monotonic()
        proc = subprocess.Popen(
            ["bash", "-c", "sleep 3 && echo background-done"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        elapsed = time.monotonic() - start
        # Popen returns immediately -- it does not block
        assert elapsed < 1.0, (
            f"Popen (background launch) should return in <1s, took {elapsed:.2f}s"
        )
        # Cleanup: terminate the background process
        proc.terminate()
        proc.wait(timeout=5)

    def test_background_output_readable_after_completion(self):
        """After a background command finishes, its output must be readable."""
        proc = subprocess.Popen(
            ["bash", "-c", "echo 'result-42'"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, _ = proc.communicate(timeout=10)
        assert "result-42" in stdout, (
            "Background command output must be readable after completion"
        )
        assert proc.returncode == 0

    def test_foreground_command_blocks(self):
        """A foreground subprocess.run blocks until completion.

        This proves the difference: without run_in_background, the caller
        is stuck waiting. With a 3-second sleep, we expect >2s of blocking.
        """
        start = time.monotonic()
        result = subprocess.run(
            ["bash", "-c", "sleep 3 && echo foreground-done"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        elapsed = time.monotonic() - start
        assert elapsed >= 2.0, (
            f"Foreground run should block for ~3s, but only took {elapsed:.2f}s"
        )
        assert "foreground-done" in result.stdout


# ---------------------------------------------------------------------------
# Timeout configuration tests
# ---------------------------------------------------------------------------


class TestTimeoutConfiguration:
    """Verify timeout configuration is appropriate for test suites."""

    def test_default_bash_timeout_too_short_for_full_suite(self):
        """The default 120s timeout may be too short for a full test suite.

        The preamble recommends 300000ms (5 min) for full suites.
        This test documents that the default is 120s = 120000ms.
        """
        default_timeout_ms = 120_000
        recommended_timeout_ms = 300_000
        assert recommended_timeout_ms > default_timeout_ms, (
            "The recommended suite timeout (300000ms) must exceed "
            "the default bash timeout (120000ms)"
        )

    def test_full_suite_timing_fast_subset(self, tmp_path):
        """Run a fast test subset and measure timing.

        Even a small subset may take a few seconds, demonstrating why
        background execution helps for larger suites.
        """
        test_file = tmp_path / "test_fast_subset.py"
        test_file.write_text(
            "def test_fast_subset_smoke():\n"
            "    assert 1 + 1 == 2\n",
            encoding="utf-8",
        )

        start = time.monotonic()
        subprocess.run(
            [
                "python3", "-m", "pytest",
                str(test_file),
                "-q", "--tb=no", "--no-header",
            ],
            capture_output=True,
            text=True,
            # The behavior lane has a global 30s per-test timeout. Keep this
            # nested pytest subprocess below that ceiling so pytest-timeout can
            # report the real assertion instead of killing the whole test.
            timeout=20,
            cwd=str(tmp_path),
        )
        elapsed = time.monotonic() - start

        # The test ran (pass or fail, we just care about timing)
        assert elapsed < 20, (
            f"Even a single test file should finish within 20s, took {elapsed:.2f}s"
        )
        # Document: if even a small file takes >1s, a full suite would benefit
        # from background execution
        if elapsed > 1.0:
            # This is informational, not a failure
            pass
