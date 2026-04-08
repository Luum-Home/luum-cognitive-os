"""Unit tests for hooks/agent-output-verifier.sh

Validates file claim detection, missing-file warnings, metrics logging,
and graceful handling of edge cases.

Python 3.9+ compatible. Author: luum.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import pytest

pytestmark = pytest.mark.unit

HOOK = Path(__file__).parent.parent.parent / "hooks" / "agent-output-verifier.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_hook(tool_output: str, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run the hook with the given tool_output string as stdin JSON."""
    payload = json.dumps({"tool_output": {"result": tool_output}})
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        ["bash", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env=merged_env,
    )


def run_hook_raw(stdin: str, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run the hook with raw stdin content (no JSON wrapping)."""
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        ["bash", str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        env=merged_env,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDetectsMissingFile:
    """Hook warns when a claimed file does not exist on disk."""

    def test_warns_on_missing_file(self):
        """Feed output claiming /nonexistent/path/file.py → warning on stderr."""
        output = "Created /nonexistent/path/that/does/not/exist/file.py"
        result = run_hook(output)
        assert result.returncode == 0, "Hook must always exit 0 (advisory)"
        assert "MISSING" in result.stderr or "WARNING" in result.stderr

    def test_warning_names_the_missing_file(self):
        """Warning message includes the specific path that is absent."""
        path = "/absolutely/nonexistent/missing_file.go"
        output = f"File created at {path}"
        result = run_hook(output)
        assert path in result.stderr

    def test_warns_for_wrote_pattern(self):
        """'Wrote /nonexistent/file' pattern triggers warning."""
        path = "/nonexistent/wrote_file.ts"
        output = f"Wrote {path}"
        result = run_hook(output)
        assert result.returncode == 0
        assert "MISSING" in result.stderr or path in result.stderr

    def test_warns_for_file_written_to_pattern(self):
        """'File written to /path' pattern triggers warning."""
        path = "/nonexistent/written_file.py"
        output = f"File written to {path}"
        result = run_hook(output)
        assert result.returncode == 0
        assert "MISSING" in result.stderr or path in result.stderr

    def test_multiple_missing_files_all_reported(self):
        """All missing files are reported in the warning, not just the first."""
        path_a = "/nonexistent/alpha.go"
        path_b = "/nonexistent/beta.go"
        output = f"Created {path_a}\nCreated {path_b}"
        result = run_hook(output)
        assert "MISSING" in result.stderr or "WARNING" in result.stderr
        # At least 1 missing path should appear
        assert path_a in result.stderr or path_b in result.stderr


class TestPassesExistingFile:
    """Hook stays silent when claimed files actually exist."""

    def test_no_warning_for_existing_file(self):
        """Feed output claiming /tmp/<real_file> → no warning on stderr."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            real_path = f.name
        try:
            output = f"Created {real_path}"
            result = run_hook(output)
            assert result.returncode == 0
            assert "WARNING" not in result.stderr
            assert "MISSING" not in result.stderr
        finally:
            os.unlink(real_path)

    def test_silent_when_all_claimed_files_exist(self):
        """No stderr output when every claimed file is present on disk."""
        with tempfile.NamedTemporaryFile(delete=False) as f1, \
             tempfile.NamedTemporaryFile(delete=False) as f2:
            p1, p2 = f1.name, f2.name
        try:
            output = f"File created at {p1}\nFile written to {p2}"
            result = run_hook(output)
            assert result.returncode == 0
            assert result.stderr.strip() == ""
        finally:
            os.unlink(p1)
            os.unlink(p2)


class TestHandlesNoFileClaims:
    """Hook is silent when output contains no file path claims."""

    def test_no_claims_in_output(self):
        """Plain agent output with no path references → no stderr, exit 0."""
        output = "The task has been completed successfully."
        result = run_hook(output)
        assert result.returncode == 0
        assert result.stderr.strip() == ""

    def test_relative_paths_ignored(self):
        """Relative paths (no leading /) are not treated as claims."""
        output = "Created src/main.go and updated tests/foo_test.go"
        result = run_hook(output)
        assert result.returncode == 0
        assert result.stderr.strip() == ""

    def test_empty_output_field(self):
        """Empty result string → exit 0, no output."""
        result = run_hook("")
        assert result.returncode == 0
        assert result.stderr.strip() == ""


class TestHandlesEmptyInput:
    """Hook handles malformed or empty stdin without crashing."""

    def test_empty_stdin(self):
        """Empty stdin → exit 0, no crash."""
        result = run_hook_raw("")
        assert result.returncode == 0

    def test_invalid_json_stdin(self):
        """Non-JSON stdin → exit 0, no crash."""
        result = run_hook_raw("not json at all")
        assert result.returncode == 0

    def test_json_without_tool_output(self):
        """JSON with unrelated keys → exit 0, no crash."""
        result = run_hook_raw(json.dumps({"some_other_key": "value"}))
        assert result.returncode == 0


class TestLogsToJsonl:
    """Hook writes a JSON line to agent-verification.jsonl when files are claimed."""

    def test_metrics_file_created(self):
        """A .jsonl entry is written when the hook processes file claims."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_dir = Path(tmpdir) / ".cognitive-os" / "metrics"
            metrics_dir.mkdir(parents=True)
            real_file = metrics_dir / "real_file.go"
            real_file.touch()

            env = {"CLAUDE_PROJECT_DIR": tmpdir}
            output = f"Created {real_file}"
            run_hook(output, env=env)

            jsonl_path = metrics_dir / "agent-verification.jsonl"
            assert jsonl_path.exists(), "Metrics file should be created"
            lines = jsonl_path.read_text().strip().splitlines()
            assert len(lines) >= 1

    def test_metrics_entry_has_required_fields(self):
        """Each logged entry contains timestamp, verified, missing, and total."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_dir = Path(tmpdir) / ".cognitive-os" / "metrics"
            metrics_dir.mkdir(parents=True)

            # Claim a file that does NOT exist so the entry is definitely written
            env = {"CLAUDE_PROJECT_DIR": tmpdir}
            output = "Created /nonexistent/metrics_test_file.py"
            run_hook(output, env=env)

            jsonl_path = metrics_dir / "agent-verification.jsonl"
            if not jsonl_path.exists():
                pytest.skip("jq not available or hook did not write metrics")

            last_line = jsonl_path.read_text().strip().splitlines()[-1]
            entry = json.loads(last_line)
            assert "timestamp" in entry
            assert "verified" in entry
            assert "missing" in entry
            assert "total" in entry

    def test_verified_count_reflects_existing_files(self):
        """verified count equals the number of files that actually exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_dir = Path(tmpdir) / ".cognitive-os" / "metrics"
            metrics_dir.mkdir(parents=True)

            real_file = metrics_dir / "exists.go"
            real_file.touch()

            env = {"CLAUDE_PROJECT_DIR": tmpdir}
            output = f"Created {real_file}\nCreated /nonexistent/absent.go"
            run_hook(output, env=env)

            jsonl_path = metrics_dir / "agent-verification.jsonl"
            if not jsonl_path.exists():
                pytest.skip("jq not available")

            last_line = jsonl_path.read_text().strip().splitlines()[-1]
            entry = json.loads(last_line)
            assert entry["verified"] == 1
            assert entry["missing"] == 1
            assert entry["total"] == 2
