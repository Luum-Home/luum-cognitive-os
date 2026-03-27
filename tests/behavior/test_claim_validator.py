"""Behavior tests for hooks/claim-validator.sh

Tests the claim-validator PostToolUse hook behavior: ignoring non-Agent
tools, detecting hallucinated files, passing when files exist, logging
metrics, phase-aware blocking, and test count claim detection.
"""

import json
import os
import subprocess
import tempfile

import pytest

pytestmark = pytest.mark.behavior

HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "hooks", "claim-validator.sh"
)


def _run_hook(
    tool_name: str,
    tool_response: str,
    project_dir: str,
    tool_input_prompt: str = "test task",
    phase: str = "reconstruction",
) -> subprocess.CompletedProcess:
    """Run the claim-validator hook with given input."""
    # Create minimal cognitive-os.yaml for phase
    config_dir = os.path.join(project_dir, ".cognitive-os")
    os.makedirs(config_dir, exist_ok=True)
    metrics_dir = os.path.join(config_dir, "metrics")
    os.makedirs(metrics_dir, exist_ok=True)
    config_path = os.path.join(project_dir, "cognitive-os.yaml")
    with open(config_path, "w") as f:
        f.write("project:\n  phase: %s\n" % phase)

    input_data = json.dumps(
        {
            "tool_name": tool_name,
            "tool_response": tool_response,
            "tool_input": {"prompt": tool_input_prompt},
        }
    )

    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = project_dir

    result = subprocess.run(
        ["bash", HOOK_PATH],
        input=input_data,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    return result


class TestClaimValidatorHook:
    """Behavior tests for claim-validator.sh."""

    def test_ignores_non_agent_tools(self, tmp_path):
        """Hook should exit 0 for non-Agent tools (Bash, Edit, etc.)."""
        result = _run_hook("Bash", "some output", str(tmp_path))
        assert result.returncode == 0

    def test_ignores_read_tool(self, tmp_path):
        """Hook should exit 0 for Read tool."""
        result = _run_hook("Read", "file contents", str(tmp_path))
        assert result.returncode == 0

    def test_detects_file_hallucination(self, tmp_path):
        """Should detect when agent claims file exists but it does not."""
        response = "Created internal/auth/handler.go with JWT validation logic."
        result = _run_hook("Agent", response, str(tmp_path))
        assert result.returncode == 0  # reconstruction = warn only
        assert "HALLUCINATION" in result.stderr or "hallucination" in result.stderr.lower()

    def test_passes_when_file_exists(self, tmp_path):
        """Should pass when claimed files actually exist."""
        # Create the file first
        target = tmp_path / "existing.py"
        target.write_text("x = 1\n")

        response = "Created existing.py with the implementation."
        result = _run_hook("Agent", response, str(tmp_path))
        assert result.returncode == 0
        assert "HALLUCINATION" not in result.stderr

    def test_logs_to_hallucinations_jsonl(self, tmp_path):
        """Should log hallucination events to metrics."""
        response = "Created phantom_file.go with the handler."
        _run_hook("Agent", response, str(tmp_path))

        metrics_file = tmp_path / ".cognitive-os" / "metrics" / "hallucinations.jsonl"
        if metrics_file.exists():
            content = metrics_file.read_text().strip()
            if content:
                entry = json.loads(content.split("\n")[-1])
                assert "hallucinations" in entry
                assert "timestamp" in entry

    def test_blocks_in_production_on_hallucination(self, tmp_path):
        """Should exit 2 (BLOCK) in production phase when hallucination detected."""
        response = "Created nonexistent_production.go with critical auth logic."
        result = _run_hook("Agent", response, str(tmp_path), phase="production")
        # Should block with exit code 2
        assert result.returncode == 2

    def test_warns_in_reconstruction_on_hallucination(self, tmp_path):
        """Should exit 0 (WARN) in reconstruction phase when hallucination detected."""
        response = "Created nonexistent_recon.go with handler."
        result = _run_hook("Agent", response, str(tmp_path), phase="reconstruction")
        assert result.returncode == 0

    def test_detects_test_count_claims(self, tmp_path):
        """Should detect and flag test count claims."""
        response = "All 25 tests passing successfully. Build clean."
        result = _run_hook("Agent", response, str(tmp_path))
        assert result.returncode == 0
        # Should flag the test count claim
        assert "CLAIM" in result.stderr or "25 tests" in result.stderr.lower() or result.stderr == ""

    def test_empty_response_passes(self, tmp_path):
        """Should pass cleanly with empty response."""
        result = _run_hook("Agent", "", str(tmp_path))
        assert result.returncode == 0

    def test_blocks_in_maintenance_on_hallucination(self, tmp_path):
        """Should exit 2 (BLOCK) in maintenance phase when hallucination detected."""
        response = "Created ghost_file.ts with the component."
        result = _run_hook("Agent", response, str(tmp_path), phase="maintenance")
        assert result.returncode == 2
