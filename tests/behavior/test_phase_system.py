"""Behavior tests for the phase system.

Verifies that inject-phase-context.sh outputs correct rules per phase.
Migrated from test-phase-system.sh.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

MOCK_INPUT = json.dumps({"tool_name": "Agent", "tool_input": {"prompt": "test"}})


@pytest.fixture
def phase_hook(project_root):
    """Return the path to inject-phase-context.sh and skip if not executable."""
    hook = project_root / "hooks" / "inject-phase-context.sh"
    if not hook.exists() or not os.access(hook, os.X_OK):
        pytest.skip("inject-phase-context.sh not found or not executable")
    return hook


@pytest.fixture
def config_path(project_root):
    """Return the config path and skip if not found."""
    config = project_root / ".cognitive-os" / "cognitive-os.yaml"
    if not config.exists():
        pytest.skip("cognitive-os.yaml not found")
    return config


@pytest.fixture
def phase_context(phase_hook, config_path, project_root, tmp_path):
    """Provide a helper that sets the phase in config and runs the hook.

    Returns a context manager / callable that temporarily sets a phase,
    runs the hook, and restores the original config after the test.
    """
    backup = config_path.read_text()

    def _run(phase: str) -> str:
        text = config_path.read_text()
        text = re.sub(r"phase:.*", f"phase: {phase}", text)
        config_path.write_text(text)

        result = subprocess.run(
            ["bash", str(phase_hook)],
            input=MOCK_INPUT,
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(project_root)},
            timeout=10,
        )
        return result.stdout + result.stderr

    yield _run

    # Restore original config
    config_path.write_text(backup)


@pytest.mark.behavior
class TestPhaseSystem:
    """Tests for phase-specific context injection."""

    def test_reconstruction_includes_rewrite_rules(self, phase_context):
        output = phase_context("reconstruction")
        assert re.search(r"rewrite", output, re.IGNORECASE), (
            "reconstruction phase should include rewrite rules"
        )

    def test_production_includes_stability_rules(self, phase_context):
        output = phase_context("production")
        assert re.search(r"feature flag|break existing|Do NOT break", output, re.IGNORECASE), (
            "production phase should include stability/feature-flag rules"
        )

    def test_maintenance_restricts_to_bug_fixes(self, phase_context):
        output = phase_context("maintenance")
        assert re.search(r"bug fix|security patch|minimal", output, re.IGNORECASE), (
            "maintenance phase should restrict to bug fixes/security"
        )

    def test_stabilization_outputs_relevant_rules(self, phase_context):
        output = phase_context("stabilization")
        assert re.search(r"stabilization|fix|standard", output, re.IGNORECASE), (
            "stabilization phase should output relevant rules"
        )

    @pytest.mark.parametrize(
        "phase",
        ["reconstruction", "stabilization", "production", "maintenance"],
    )
    def test_phase_includes_constitutional_gates(self, phase_context, phase):
        output = phase_context(phase)
        assert re.search(r"CONSTITUTIONAL GATES", output, re.IGNORECASE), (
            f"{phase} phase should include constitutional gates"
        )
