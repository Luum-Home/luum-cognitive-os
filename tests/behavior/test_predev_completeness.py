"""Behavior tests for hooks/predev-completeness-check.sh.

Validates that the hook correctly:
- Blocks implementation agents in production when artifacts are missing
- Passes non-implementation prompts unconditionally
- Warns (but passes) in reconstruction phase even without artifacts
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior


class TestPredevCompletenessCheck:
    """Tests for hooks/predev-completeness-check.sh."""

    # ------------------------------------------------------------------
    # F3: production phase + no artifacts + impl prompt → BLOCK
    # ------------------------------------------------------------------

    def test_blocks_implementation_without_artifacts_in_production(
        self, run_hook, cognitive_os_env
    ):
        """Hook must exit 2 in production phase when required artifacts are missing."""
        project_dir: Path = cognitive_os_env["project_dir"]

        # Create cognitive-os.yaml with production phase
        yaml_file = project_dir / "cognitive-os.yaml"
        yaml_file.write_text("project:\n  phase: production\n")

        # Do NOT create any docs/ directories (no artifacts present)

        stdin_payload = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "sdd-apply implement the auth module"},
        })

        result = run_hook(
            "predev-completeness-check.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_payload,
        )
        assert result.returncode == 2, (
            f"Expected exit 2 (BLOCK) in production without artifacts but got "
            f"{result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    # ------------------------------------------------------------------
    # F4: non-implementation prompt → SKIP (always pass)
    # ------------------------------------------------------------------

    def test_skips_non_implementation_prompts(self, run_hook, cognitive_os_env):
        """Hook must silently pass for prompts that are not implementation-related."""
        project_dir: Path = cognitive_os_env["project_dir"]

        yaml_file = project_dir / "cognitive-os.yaml"
        yaml_file.write_text("project:\n  phase: production\n")

        stdin_payload = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "research caching strategies"},
        })

        result = run_hook(
            "predev-completeness-check.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_payload,
        )
        assert result.returncode == 0, (
            f"Expected exit 0 (non-impl prompt skipped) but got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    # ------------------------------------------------------------------
    # F5: reconstruction phase + no artifacts + impl prompt → WARN, pass
    # ------------------------------------------------------------------

    def test_warns_but_passes_in_reconstruction(self, run_hook, cognitive_os_env):
        """Hook must warn but exit 0 in reconstruction phase when artifacts are missing."""
        project_dir: Path = cognitive_os_env["project_dir"]

        yaml_file = project_dir / "cognitive-os.yaml"
        yaml_file.write_text("project:\n  phase: reconstruction\n")

        # No artifacts present
        stdin_payload = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "implement the user registration feature"},
        })

        result = run_hook(
            "predev-completeness-check.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_payload,
        )
        assert result.returncode == 0, (
            f"Expected exit 0 (warn only in reconstruction) but got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        # Should still emit a warning
        combined = result.stdout + result.stderr
        assert "WARNING" in combined or "warn" in combined.lower() or "WARN" in combined, (
            "Expected a warning message in reconstruction phase output"
        )

    # ------------------------------------------------------------------
    # Extra: non-Agent tool → SKIP
    # ------------------------------------------------------------------

    def test_skips_non_agent_tools(self, run_hook, cognitive_os_env):
        """Hook must silently pass for tools other than Agent."""
        stdin_payload = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "sdd-apply implement the service"},
        })

        result = run_hook(
            "predev-completeness-check.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_payload,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    # ------------------------------------------------------------------
    # Extra: maintenance phase + no artifacts → BLOCK
    # ------------------------------------------------------------------

    def test_blocks_in_maintenance_phase(self, run_hook, cognitive_os_env):
        """Hook must block in maintenance phase when artifacts are missing."""
        project_dir: Path = cognitive_os_env["project_dir"]

        yaml_file = project_dir / "cognitive-os.yaml"
        yaml_file.write_text("project:\n  phase: maintenance\n")

        stdin_payload = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "implement the new caching layer"},
        })

        result = run_hook(
            "predev-completeness-check.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_payload,
        )
        assert result.returncode == 2, (
            f"Expected exit 2 (BLOCK) in maintenance without artifacts but got "
            f"{result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
