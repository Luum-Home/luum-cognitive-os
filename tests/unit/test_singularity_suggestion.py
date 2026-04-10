"""Behavioral tests for _singularity_suggestion() in hooks/session-init.sh.

session-init.sh calls _singularity_suggestion() near the end of its execution.
Rather than sourcing and re-calling the function in isolation (which loses the
first call's output), we run the full hook and extract the singularity-relevant
portion of its stderr.

Non-suggestion stderr lines that session-init.sh always emits are filtered out
by checking for the "=== SINGULARITY" marker lines.

Invariants:
- Suggests singularity + dry-run hint when singularity-events.jsonl is absent
- Stays silent when singularity has run and no error/stale-doc signals exist
- Mentions error count when ≥3 errors occurred in the last 24 h
- Mentions stale doc count when stale-docs.jsonl is non-empty
- Stays silent when the opt-out sentinel file exists
- Stays silent when cognitive-os.yaml sets singularity_suggestion: false
"""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"
HOOK_PATH = HOOKS_DIR / "session-init.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(project_dir: Path, timeout: int = 20) -> subprocess.CompletedProcess:
    """Run the full session-init.sh hook in *project_dir* and return the result.

    The hook writes the singularity suggestion block to stderr between
    '=== SINGULARITY SUGGESTION ===' and '=== END SINGULARITY ===' markers.
    """
    if not HOOK_PATH.exists():
        pytest.skip(f"Hook not found: {HOOK_PATH}")

    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _singularity_block(result: subprocess.CompletedProcess) -> str:
    """Extract the singularity suggestion block from stderr.

    Returns the text between '=== SINGULARITY SUGGESTION ===' and
    '=== END SINGULARITY ===' markers, or an empty string if the block
    is absent.
    """
    stderr = result.stderr
    start_marker = "=== SINGULARITY SUGGESTION ==="
    end_marker = "=== END SINGULARITY ==="
    start = stderr.find(start_marker)
    if start == -1:
        return ""
    end = stderr.find(end_marker, start)
    if end == -1:
        return stderr[start:]
    return stderr[start : end + len(end_marker)]


def _run_suggestion(project_dir: Path, timeout: int = 20) -> subprocess.CompletedProcess:
    """Alias kept for clarity — runs the hook and is used identically to _run_hook."""
    return _run_hook(project_dir, timeout=timeout)


def _metrics_dir(project_dir: Path) -> Path:
    d = project_dir / ".cognitive-os" / "metrics"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cos_dir(project_dir: Path) -> Path:
    d = project_dir / ".cognitive-os"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_error_entries(metrics_dir: Path, count: int, recent: bool = True) -> None:
    """Write *count* error-learning.jsonl entries, optionally recent (< 24 h old)."""
    errors_file = metrics_dir / "error-learning.jsonl"
    now = int(time.time())
    entries = []
    for i in range(count):
        epoch = (now - 3600) if recent else (now - 90000)  # 1 h ago vs 25 h ago
        entries.append(json.dumps({
            "timestamp": "2026-04-09T00:00:00Z",
            "timestamp_epoch": epoch,
            "type": "TEST_FAILURE",
            "service": "my-service",
            "message": f"test failure {i}",
        }))
    errors_file.write_text("\n".join(entries) + "\n")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSuggestsWhenNeverRan:
    """No singularity-events.jsonl → always suggest."""

    def test_suggests_when_never_ran(self, tmp_path):
        """Suggestion output appears when singularity has never been run."""
        project_dir = tmp_path / "project"
        _cos_dir(project_dir)
        _metrics_dir(project_dir)

        # Ensure the events file does NOT exist
        events_file = _metrics_dir(project_dir) / "singularity-events.jsonl"
        assert not events_file.exists()

        result = _run_suggestion(project_dir)

        assert result.returncode == 0, (
            f"Expected exit 0, got {result.returncode}\nstderr: {result.stderr}"
        )
        block = _singularity_block(result)
        assert block, (
            f"Expected SINGULARITY SUGGESTION block in stderr, got none.\n"
            f"Full stderr:\n{result.stderr}"
        )
        assert "never" in block.lower(), (
            f"Expected 'never been run' hint in suggestion block:\n{block}"
        )
        assert "dry-run" in block.lower() or "dry_run" in block.lower(), (
            f"Expected dry-run hint in suggestion block:\n{block}"
        )


class TestSilentWhenAlreadyRan:
    """When singularity has run and no signals exist, produce no output."""

    def test_silent_when_already_ran_no_signals(self, tmp_path):
        """Empty singularity-events.jsonl + no errors + no stale docs → silent."""
        project_dir = tmp_path / "project"
        metrics = _metrics_dir(project_dir)

        # Create an empty events file — indicates singularity has run before
        (metrics / "singularity-events.jsonl").write_text("")

        # No error-learning.jsonl, no stale-docs.jsonl
        result = _run_suggestion(project_dir)

        assert result.returncode == 0
        block = _singularity_block(result)
        assert block == "", (
            f"Expected no SINGULARITY block when already ran and no signals:\n{block}"
        )


class TestDetectsRecentErrors:
    """3 or more recent errors → suggest singularity with error signal."""

    def test_detects_recent_errors(self, tmp_path):
        """4 errors in last 24 h are detected and mentioned in the suggestion."""
        project_dir = tmp_path / "project"
        metrics = _metrics_dir(project_dir)

        # Mark singularity as having run before (so it doesn't trigger the
        # "never ran" path — we want the signal-based path)
        (metrics / "singularity-events.jsonl").write_text("")

        _write_error_entries(metrics, count=4, recent=True)

        result = _run_suggestion(project_dir)

        assert result.returncode == 0
        block = _singularity_block(result)
        assert block, (
            f"Expected SINGULARITY block for 4 recent errors.\n"
            f"Full stderr:\n{result.stderr}"
        )
        assert "error" in block.lower(), (
            f"Expected 'error' mention in suggestion block:\n{block}"
        )

    def test_old_errors_not_counted(self, tmp_path):
        """Errors older than 24 h must not trigger the suggestion."""
        project_dir = tmp_path / "project"
        metrics = _metrics_dir(project_dir)

        (metrics / "singularity-events.jsonl").write_text("")
        _write_error_entries(metrics, count=5, recent=False)  # all > 24 h old

        result = _run_suggestion(project_dir)

        assert result.returncode == 0
        block = _singularity_block(result)
        assert block == "", (
            f"Expected no SINGULARITY block for old errors, got:\n{block}"
        )


class TestDetectsstaleDocs:
    """Non-empty stale-docs.jsonl → suggest singularity with stale-doc signal."""

    def test_detects_stale_docs(self, tmp_path):
        """stale-docs.jsonl with entries triggers a suggestion mentioning stale docs."""
        project_dir = tmp_path / "project"
        metrics = _metrics_dir(project_dir)

        (metrics / "singularity-events.jsonl").write_text("")

        stale_entry = json.dumps({
            "file": "docs/api.md",
            "source": "internal/handler.go",
            "timestamp": "2026-04-09T00:00:00Z",
        })
        (metrics / "stale-docs.jsonl").write_text(stale_entry + "\n")

        result = _run_suggestion(project_dir)

        assert result.returncode == 0
        block = _singularity_block(result)
        assert block, (
            f"Expected SINGULARITY block for stale docs.\n"
            f"Full stderr:\n{result.stderr}"
        )
        assert "stale" in block.lower(), (
            f"Expected 'stale' mention in suggestion block:\n{block}"
        )


class TestOptOutSentinelFile:
    """Sentinel file suppresses all output, even when signals are present."""

    def test_opt_out_sentinel_file(self, tmp_path):
        """Dismissed sentinel file suppresses suggestion even with errors."""
        project_dir = tmp_path / "project"
        cos = _cos_dir(project_dir)
        metrics = _metrics_dir(project_dir)

        # Create sentinel file
        (cos / ".singularity-suggestion-dismissed").write_text("")

        # Signals would normally trigger a suggestion
        _write_error_entries(metrics, count=5, recent=True)
        stale_entry = json.dumps({"file": "docs/api.md"})
        (metrics / "stale-docs.jsonl").write_text(stale_entry + "\n")

        result = _run_suggestion(project_dir)

        assert result.returncode == 0
        block = _singularity_block(result)
        assert block == "", (
            f"Expected no SINGULARITY block due to opt-out sentinel, got:\n{block}"
        )


class TestOptOutYamlConfig:
    """cognitive-os.yaml with singularity_suggestion: false suppresses output."""

    def test_opt_out_yaml_config(self, tmp_path):
        """Config flag singularity_suggestion: false suppresses the suggestion."""
        project_dir = tmp_path / "project"
        cos = _cos_dir(project_dir)
        metrics = _metrics_dir(project_dir)

        # Write config with opt-out flag (note: hook reads from .cognitive-os/cognitive-os.yaml)
        (cos / "cognitive-os.yaml").write_text(
            "project:\n  phase: stabilization\nsingularity_suggestion: false\n"
        )

        # Signals would normally trigger a suggestion
        _write_error_entries(metrics, count=5, recent=True)
        (metrics / "stale-docs.jsonl").write_text(
            json.dumps({"file": "docs/api.md"}) + "\n"
        )

        result = _run_suggestion(project_dir)

        assert result.returncode == 0
        block = _singularity_block(result)
        assert block == "", (
            f"Expected no SINGULARITY block due to yaml opt-out config, got:\n{block}"
        )
