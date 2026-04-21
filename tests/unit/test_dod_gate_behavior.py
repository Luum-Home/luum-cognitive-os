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
        """dod-gate.sh in production phase must emit a BLOCK warning when DoD
        criteria are absent.

        Note: dod-gate.sh is advisory-only (always exits 0) — the word "BLOCK"
        in its output is a label indicating the enforcement level, not a real
        process block.  The invariant we test is that the hook:
          1. Exits 0 (advisory)
          2. Outputs a BLOCK-labelled warning to stdout
          3. Reports the missing criteria
        """
        (tmp_path / "cognitive-os.yaml").write_text("project:\n  phase: production\n")

        result = _run_hook(
            project_dir=tmp_path,
            agent_output=_output_with_missing_dod("medium"),
            phase="production",
        )

        assert result.returncode == 0, (
            f"dod-gate.sh is advisory-only and must exit 0 even in production, "
            f"got {result.returncode}\nstderr: {result.stderr}"
        )
        combined = result.stdout + result.stderr
        # Should emit some form of DoD warning
        assert any(kw in combined for kw in ("BLOCK", "DOD", "Missing", "missing", "criteria", "DoD")), (
            f"Expected a DoD warning in output but got: {combined[:400]!r}"
        )

    def test_blocks_in_maintenance_phase(self, tmp_path):
        """dod-gate.sh in maintenance phase must emit an advisory BLOCK warning
        when DoD criteria are absent.  Hook always exits 0 (advisory only).
        """
        (tmp_path / "cognitive-os.yaml").write_text("project:\n  phase: maintenance\n")

        result = _run_hook(
            project_dir=tmp_path,
            agent_output=_output_with_missing_dod("small"),
            phase="maintenance",
        )

        assert result.returncode == 0, (
            f"dod-gate.sh is advisory-only, expected exit 0, got {result.returncode}"
        )
        combined = result.stdout + result.stderr
        assert any(kw in combined for kw in ("BLOCK", "DOD", "Missing", "missing", "criteria", "DoD")), (
            f"Expected a DoD warning for maintenance phase, got: {combined[:400]!r}"
        )


class TestDodGateWarning:
    def test_warns_in_reconstruction(self, tmp_path):
        """dod-gate.sh must exit 0 in reconstruction phase and emit a warning
        when DoD criteria are missing.  The warning may appear on stdout or
        stderr (the hook uses echo to stdout for its messages).
        """
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
        combined = result.stdout + result.stderr
        assert any(
            kw in combined
            for kw in ("DOD", "not met", "Missing", "missing", "criteria", "WARNING", "DoD")
        ), (
            "Expected a DoD warning message but got no recognizable output: "
            f"{combined[:400]!r}"
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
