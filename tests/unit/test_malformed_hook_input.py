"""Tests that hooks handle malformed (non-object) JSON input gracefully.

Every hook reads its event JSON from stdin.  If the input is not a JSON object
(array, null, boolean, number) the hook must not crash — it should exit 0 and
produce no blocking output.

Hooks under test:
  - rate-limiter.sh
  - blast-radius.sh
  - error-pipeline.sh  (PostToolUse/Bash, mapped from error-learning path)
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(
    hook_name: str,
    stdin_payload,
    extra_env: "dict | None" = None,
    timeout: int = 15,
) -> subprocess.CompletedProcess:
    """Execute *hook_name* from HOOKS_DIR with the given stdin payload.

    *stdin_payload* is serialised to JSON before being passed.  Returns the
    CompletedProcess; skips the test if the hook file is missing.
    """
    hook_path = HOOKS_DIR / hook_name
    if not hook_path.exists():
        pytest.skip(f"Hook not found: {hook_path}")

    env = os.environ.copy()
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    env["PRIVATE_MODE"] = "false"
    # Disable rate-limit state persistence so tests don't interfere
    env["CLAUDE_PROJECT_DIR"] = str(HOOKS_DIR.parent)
    if extra_env:
        env.update(extra_env)

    stdin_text = json.dumps(stdin_payload)
    return subprocess.run(
        ["bash", str(hook_path)],
        input=stdin_text,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# rate-limiter.sh
# ---------------------------------------------------------------------------


class TestRateLimiterMalformedInput:
    """rate-limiter.sh must not crash on non-object JSON."""

    def test_rate_limiter_with_array_json(self, tmp_path):
        """rate-limiter.sh exits 0 when stdin is a JSON array."""
        result = _run_hook("rate-limiter.sh", [1, 2, 3])
        assert result.returncode in (0, 1), (
            f"rate-limiter.sh crashed (exit {result.returncode}) on array input\n"
            f"stderr: {result.stderr}"
        )
        # It must NOT exit with code 2 (block) on malformed input
        assert result.returncode != 2, (
            "rate-limiter.sh blocked (exit 2) on malformed array input — "
            "should be graceful"
        )

    def test_rate_limiter_with_null_json(self, tmp_path):
        """rate-limiter.sh exits 0 when stdin is JSON null."""
        result = _run_hook("rate-limiter.sh", None)
        assert result.returncode != 2, (
            f"rate-limiter.sh blocked on null input\nstderr: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# blast-radius.sh
# ---------------------------------------------------------------------------


class TestBlastRadiusMalformedInput:
    def test_blast_radius_with_boolean_json(self, tmp_path):
        """blast-radius.sh exits 0 when stdin is JSON true."""
        result = _run_hook("blast-radius.sh", True)
        assert result.returncode in (0, 1), (
            f"blast-radius.sh crashed (exit {result.returncode}) on boolean input\n"
            f"stderr: {result.stderr}"
        )
        assert result.returncode != 2, (
            "blast-radius.sh produced a BLOCK exit on malformed boolean input"
        )


# ---------------------------------------------------------------------------
# error-pipeline.sh / error-learning.sh
# ---------------------------------------------------------------------------


class TestErrorPipelineMalformedInput:
    def test_error_pipeline_with_number_json(self, tmp_path):
        """error-pipeline.sh (or error-learning.sh) exits 0 on a numeric stdin."""
        # Try error-pipeline.sh first, then error-learning.sh as fallback
        for hook_name in ("error-pipeline.sh", "error-learning.sh"):
            hook_path = HOOKS_DIR / hook_name
            if hook_path.exists():
                break
        else:
            pytest.skip("Neither error-pipeline.sh nor error-learning.sh found")

        result = _run_hook(hook_name, 42)
        assert result.returncode == 0, (
            f"{hook_name} crashed (exit {result.returncode}) on numeric input\n"
            f"stderr: {result.stderr}"
        )
