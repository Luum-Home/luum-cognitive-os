"""Behavior tests for the resource governor.

Tests resource-check.sh with mock cost data at various budget levels.
Migrated from test-resource-governor.sh.
"""

import json
import os
import subprocess
import time

import pytest

MOCK_AGENT = json.dumps({"tool_name": "Agent", "tool_input": {"prompt": "do work"}})


@pytest.fixture
def resource_hook(project_root):
    hook = project_root / "hooks" / "resource-check.sh"
    if not hook.exists() or not os.access(hook, os.X_OK):
        pytest.skip("resource-check.sh not found or not executable")
    return hook


@pytest.fixture
def cost_file(project_root):
    """Return the cost events file path with backup/restore."""
    path = project_root / ".cognitive-os" / "metrics" / "cost-events.jsonl"
    backup = path.read_text() if path.exists() else None

    yield path

    # Restore
    if backup is not None:
        path.write_text(backup)
    else:
        path.write_text("")


def _run_check(resource_hook, project_root, mock_input=MOCK_AGENT):
    return subprocess.run(
        ["bash", str(resource_hook)],
        input=mock_input,
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project_root)},
        timeout=10,
    )


@pytest.mark.behavior
class TestResourceGovernor:
    """Tests for the resource/budget governor hook."""

    def test_empty_cost_file_allows(self, resource_hook, cost_file, project_root):
        cost_file.write_text("")
        result = _run_check(resource_hook, project_root)
        assert result.returncode == 0, "should allow with empty cost file"

    def test_low_spend_allows(self, resource_hook, cost_file, project_root):
        today = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        lines = [
            json.dumps({"timestamp": today, "estimated_cost_usd": 0.50, "model": "sonnet", "operation": "agent"}),
            json.dumps({"timestamp": today, "estimated_cost_usd": 0.30, "model": "sonnet", "operation": "agent"}),
        ]
        cost_file.write_text("\n".join(lines) + "\n")
        result = _run_check(resource_hook, project_root)
        assert result.returncode == 0, "should allow with low spend"

    def test_high_spend_triggers_warning(self, resource_hook, cost_file, project_root):
        today = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        entries = "\n".join(
            json.dumps({"timestamp": today, "estimated_cost_usd": 10.0, "model": "opus", "operation": "agent"})
            for _ in range(17)
        )
        cost_file.write_text(entries + "\n")
        result = _run_check(resource_hook, project_root)
        output = (result.stdout + result.stderr).upper()
        assert any(w in output for w in ["BUDGET", "DOWNGRADE", "SONNET", "PRESSURE"]), (
            "should trigger budget warning at >80% spend"
        )

    def test_over_budget_blocks(self, resource_hook, cost_file, project_root):
        today = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        entries = "\n".join(
            json.dumps({"timestamp": today, "estimated_cost_usd": 10.0, "model": "opus", "operation": "agent"})
            for _ in range(25)
        )
        cost_file.write_text(entries + "\n")
        result = _run_check(resource_hook, project_root)
        output = (result.stdout + result.stderr).upper()
        assert any(w in output for w in ["BLOCKED", "EXCEEDED", "DENY"]), (
            "should block agent launch when over monthly budget"
        )

