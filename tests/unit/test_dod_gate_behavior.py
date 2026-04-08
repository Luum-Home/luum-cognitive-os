"""Behavioral tests for hooks/dod-gate.sh.

Verifies:
- Hook blocks (exit 2) in production phase when DoD criteria are missing
- Hook warns (exit 0) in reconstruction phase for the same missing criteria
- Hook passes (exit 0) when the required DoD markers are present in the output
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"
HOOK_PATH = HOOKS_DIR / "dod-gate.sh"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stdin(agent_output: str) -> str:
    """Build the PostToolUse event JSON for an Agent tool completion."""
    payload = {
        "tool_name": "Agent",
        "tool_input": {"prompt": "implement feature"},
        "tool_response": {
            "content": agent_output,
        },
    }
    return json.dumps(payload)


def _run_hook(
    project_dir: Path,
    agent_output: str,
    phase: str = "reconstruction",
    extra_env: "dict | None" = None,
    timeout: int = 15,
) -> subprocess.CompletedProcess:
    if not HOOK_PATH.exists():
        pytest.skip(f"Hook not found: {HOOK_PATH}")

    # Build a minimal cognitive-os.yaml so get_phase() can read it
    config_file = project_dir / "cognitive-os.yaml"
    if not config_file.exists():
        config_file.write_text(f"project:\n  phase: {phase}\n")

    env = os.environ.copy()
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    env["PRIVATE_MODE"] = "false"
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=_make_stdin(agent_output),
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _output_with_missing_dod(complexity: str = "medium") -> str:
    """Agent output that declares a complexity but omits all DoD markers."""
    return f"Complexity: {complexity}\nDone implementing the feature."


def _output_with_met_dod(complexity: str = "medium") -> str:
    """Agent output that declares complexity AND satisfies the DoD markers."""
    return (
        f"Complexity: {complexity}\n"
        "Added unit_tests_added: test_handler_test.go created.\n"
        "coverage: 85% — lint clean.\n"
        "Tests: all pass."
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDodGateBlocking:
    def test_blocks_when_no_criteria_in_production(self, tmp_path):
        """dod-gate.sh must exit 2 in production phase when DoD markers are absent."""
        # Write cognitive-os.yaml with production phase
        (tmp_path / "cognitive-os.yaml").write_text("project:\n  phase: production\n")

        result = _run_hook(
            project_dir=tmp_path,
            agent_output=_output_with_missing_dod("medium"),
            phase="production",
        )

        assert result.returncode == 2, (
            f"Expected exit 2 (BLOCK) in production with missing DoD, "
            f"got {result.returncode}\nstderr: {result.stderr}"
        )

    def test_blocks_in_maintenance_phase(self, tmp_path):
        """dod-gate.sh must block (exit 2) in maintenance phase too."""
        (tmp_path / "cognitive-os.yaml").write_text("project:\n  phase: maintenance\n")

        result = _run_hook(
            project_dir=tmp_path,
            agent_output=_output_with_missing_dod("small"),
            phase="maintenance",
        )

        assert result.returncode == 2, (
            f"Expected exit 2 in maintenance, got {result.returncode}"
        )


class TestDodGateWarning:
    def test_warns_in_reconstruction(self, tmp_path):
        """dod-gate.sh must exit 0 (warn, not block) in reconstruction phase."""
        (tmp_path / "cognitive-os.yaml").write_text(
            "project:\n  phase: reconstruction\n"
        )

        result = _run_hook(
            project_dir=tmp_path,
            agent_output=_output_with_missing_dod("medium"),
            phase="reconstruction",
        )

        assert result.returncode == 0, (
            f"Expected exit 0 (warn only) in reconstruction, "
            f"got {result.returncode}\nstderr: {result.stderr}"
        )
        # Should mention DoD not met in stderr
        assert "DOD" in result.stderr or "not met" in result.stderr.lower() or \
               "Missing" in result.stderr, (
            "Expected a DoD warning message in stderr but got: "
            f"{result.stderr!r}"
        )

    def test_warns_in_stabilization(self, tmp_path):
        """dod-gate.sh must exit 0 in stabilization phase when DoD missing."""
        (tmp_path / "cognitive-os.yaml").write_text(
            "project:\n  phase: stabilization\n"
        )

        result = _run_hook(
            project_dir=tmp_path,
            agent_output=_output_with_missing_dod("large"),
            phase="stabilization",
        )

        assert result.returncode == 0, (
            f"Expected exit 0 in stabilization, got {result.returncode}"
        )


class TestDodGatePass:
    def test_passes_when_criteria_present(self, tmp_path):
        """dod-gate.sh must exit 0 when all required DoD markers are present."""
        (tmp_path / "cognitive-os.yaml").write_text("project:\n  phase: production\n")

        result = _run_hook(
            project_dir=tmp_path,
            agent_output=_output_with_met_dod("medium"),
            phase="production",
        )

        assert result.returncode == 0, (
            f"Expected exit 0 when DoD criteria present, "
            f"got {result.returncode}\nstderr: {result.stderr}"
        )

    def test_passes_when_no_complexity_declared(self, tmp_path):
        """dod-gate.sh must exit 0 (skip) if no Complexity line is found."""
        (tmp_path / "cognitive-os.yaml").write_text("project:\n  phase: production\n")

        result = _run_hook(
            project_dir=tmp_path,
            agent_output="No complexity declared. Just prose output.",
            phase="production",
        )

        assert result.returncode == 0, (
            f"Expected exit 0 when no Complexity line present, "
            f"got {result.returncode}"
        )
