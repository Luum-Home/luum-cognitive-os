"""
Unit tests for hooks/error-pattern-detector.sh

Covers:
  - Corrupt JSONL lines must not crash the hook (hook exits 0 and produces no warnings)
  - Hook always exits 0 regardless of tool_name (no tool filtering at hook level)
  - Fewer than 3 errors of the same type/service must produce no warning
  - Errors older than 24h must be filtered out (cutoff epoch)
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"
HOOK_PATH = HOOKS_DIR / "error-pattern-detector.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(
    project_dir: str,
    stdin_json: dict | None = None,
    timeout: int = 15,
) -> subprocess.CompletedProcess:
    """Run the error-pattern-detector.sh hook with the given project dir."""
    if not HOOK_PATH.exists():
        pytest.skip(f"Hook not found: {HOOK_PATH}")

    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = project_dir
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"

    stdin_str = json.dumps(stdin_json) if stdin_json is not None else ""

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=stdin_str,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _write_metrics(metrics_dir: Path, entries: list[dict]) -> Path:
    """Write a list of error-learning JSONL entries to the metrics file."""
    metrics_file = metrics_dir / "error-learning.jsonl"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(json.dumps(e) for e in entries)
    metrics_file.write_text(lines + "\n")
    return metrics_file


def _entry(
    service: str,
    error_type: str,
    *,
    age_hours: float = 1.0,
    context: str = "",
    framework: str = "",
    error: str = "test error",
) -> dict:
    """Build a synthetic error-learning JSONL entry."""
    epoch = int(time.time() - age_hours * 3600)
    return {
        "type": error_type,
        "service": service,
        "timestamp_epoch": epoch,
        "context": context,
        "framework": framework,
        "error": error,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCorruptJsonlNocrash:
    """Corrupt JSONL lines in the metrics file must not crash the hook."""

    def test_corrupt_jsonl_line_no_crash(self, tmp_path):
        """A metrics file with a corrupt JSONL line must not cause the hook to fail.

        The hook uses jq to parse entries; a corrupt line should be skipped
        (jq silently ignores non-parseable input by default) and the hook
        must exit 0 without printing a warning for the corrupt entry.
        """
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        metrics_file = metrics_dir / "error-learning.jsonl"

        # Mix valid + corrupt lines — but only 2 valid entries (below threshold)
        valid_entry = _entry("svc-a", "TEST_FAILURE", age_hours=1)
        corrupt_line = "{this is not valid json at all"
        metrics_file.write_text(
            json.dumps(valid_entry) + "\n"
            + corrupt_line + "\n"
            + json.dumps(valid_entry) + "\n"
        )

        result = _run_hook(
            project_dir=str(tmp_path),
            stdin_json={"tool_name": "Agent", "tool_input": {"prompt": "do something"}},
        )

        assert result.returncode == 0, (
            f"Hook must exit 0 even with corrupt JSONL — got {result.returncode}\n"
            f"stderr: {result.stderr}"
        )
        # Fewer than 3 valid entries → no warning output expected
        assert "ERROR PATTERN WARNINGS" not in result.stdout, (
            "Corrupt-line mix with only 2 valid entries should produce no warning"
        )


class TestWarningOnlyForAgentTool:
    """The hook does not filter by tool_name — it always runs for any input."""

    def test_warning_only_for_agent_tool(self, tmp_path):
        """With 3+ errors, the hook outputs a warning regardless of tool_name.

        The hook has no tool-name filtering; the PreToolUse registration in
        settings.json restricts which calls trigger it, but the hook script
        itself always runs when invoked.
        """
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        _write_metrics(
            metrics_dir,
            [_entry("trigger-svc", "BUILD_ERROR", age_hours=1) for _ in range(3)],
        )

        # Invoke with an Agent tool_name — should warn because 3+ errors present
        result = _run_hook(
            project_dir=str(tmp_path),
            stdin_json={"tool_name": "Agent", "tool_input": {"prompt": "build something"}},
        )

        assert result.returncode == 0, (
            f"Hook must exit 0 — got {result.returncode}\nstderr: {result.stderr}"
        )
        assert "ERROR PATTERN WARNINGS" in result.stdout, (
            "Expected warning output for 3 BUILD_ERROR entries with tool_name=Agent\n"
            f"stdout: {result.stdout!r}"
        )


class TestFewerThanThreeErrorsNoWarning:
    """Fewer than 3 errors of the same type+service must produce no warning output."""

    def test_fewer_than_3_errors_no_warning(self, tmp_path):
        """2 errors of the same type+service must produce no warning."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        _write_metrics(
            metrics_dir,
            [_entry("quiet-svc", "LINT_ERROR", age_hours=1) for _ in range(2)],
        )

        result = _run_hook(
            project_dir=str(tmp_path),
            stdin_json={"tool_name": "Agent", "tool_input": {"prompt": "lint check"}},
        )

        assert result.returncode == 0
        assert "ERROR PATTERN WARNINGS" not in result.stdout, (
            "2 errors should be below the threshold (need >= 3) — no warning expected\n"
            f"stdout: {result.stdout!r}"
        )


class TestCutoff24hFiltersOldErrors:
    """Errors older than 24h must be excluded from pattern detection."""

    def test_cutoff_24h_filters_old_errors(self, tmp_path):
        """3 errors recorded 25h ago should NOT produce a warning (outside the 24h window).

        The hook uses `date -v-24H` (macOS) or `date -d '24 hours ago'` (Linux) to
        compute the epoch cutoff. Entries with timestamp_epoch <= cutoff are excluded.
        """
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        # Write 3 entries at 25h ago (outside the 24h window)
        _write_metrics(
            metrics_dir,
            [_entry("old-svc", "TEST_FAILURE", age_hours=25) for _ in range(3)],
        )

        result = _run_hook(
            project_dir=str(tmp_path),
            stdin_json={"tool_name": "Agent", "tool_input": {"prompt": "run tests"}},
        )

        assert result.returncode == 0, (
            f"Hook must exit 0 — got {result.returncode}\nstderr: {result.stderr}"
        )
        assert "ERROR PATTERN WARNINGS" not in result.stdout, (
            "Errors older than 24h should be filtered by the cutoff — no warning expected\n"
            f"stdout: {result.stdout!r}"
        )
