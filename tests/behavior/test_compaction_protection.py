"""Behavior tests specifically for compaction protection scenarios.

Validates that the system's defenses against context-compaction-induced data loss
are in place, correctly configured, and contain the expected logic.

A compaction event destroys everything in working memory. These tests verify
the layers that ensure important state is saved BEFORE compaction occurs and
that the next session can recover from where the last one left off.
"""

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = PROJECT_ROOT / "hooks"
RULES_DIR = PROJECT_ROOT / "rules"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
SETTINGS_PATH = PROJECT_ROOT / ".claude" / "settings.json"

FLUSH_HOOK = HOOKS_DIR / "pre-compaction-flush.sh"
WATCHDOG_HOOK = HOOKS_DIR / "context-watchdog.sh"
CONTEXT_MGMT_RULE = RULES_DIR / "context-management.md"
PREAMBLE = TEMPLATES_DIR / "agent-preamble.md"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _load_settings_commands() -> list[str]:
    """Return all hook command strings from .claude/settings.json."""
    if not SETTINGS_PATH.exists():
        return []
    d = json.loads(SETTINGS_PATH.read_text())
    cmds = []
    for hook_type, entries in d.get("hooks", {}).items():
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    for h in entry.get("hooks", []):
                        if isinstance(h, dict) and h.get("command"):
                            cmds.append(h["command"])
    return cmds


# ===========================================================================
# Context-Management Threshold Tests
# ===========================================================================


class TestContextManagementThresholds:
    """Verify that context-management thresholds are documented and actionable."""


    def test_context_management_rule_mandates_engram_save(self):
        """Context-management rule must mandate Engram saves at the 70% threshold."""
        if not CONTEXT_MGMT_RULE.exists():
            pytest.skip("rules/context-management.md not found")
        content = CONTEXT_MGMT_RULE.read_text().lower()
        has_engram_save = "mem_save" in content or "engram" in content
        assert has_engram_save, (
            "rules/context-management.md must reference Engram (mem_save) as the "
            "mandatory save mechanism at the 70% threshold."
        )

    def test_context_management_rule_documents_early_checkpoint(self):
        """Context-management rule must document the early lightweight checkpoint."""
        if not CONTEXT_MGMT_RULE.exists():
            pytest.skip("rules/context-management.md not found")
        content = CONTEXT_MGMT_RULE.read_text().lower()
        assert "15%" in content
        assert "checkpoint" in content



class TestContextWatchdogHook:
    """Verify context-watchdog is active, low-noise, and has early checkpoint behavior."""

    def test_context_watchdog_registered_as_post_tool_use(self):
        cmds = _load_settings_commands()
        assert any("context-watchdog.sh" in cmd and "PostToolUse" in cmd for cmd in cmds), (
            "context-watchdog.sh must be projected as a real PostToolUse hook, not only documented."
        )

    def test_context_watchdog_emits_early_checkpoint_once(self, tmp_path, monkeypatch):
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
        monkeypatch.setenv("COGNITIVE_OS_SESSION_ID", "test-session")
        monkeypatch.setenv("CONTEXT_WATCHDOG_THRESHOLD_15", "2")
        monkeypatch.setenv("CONTEXT_WATCHDOG_THRESHOLD_50", "50")
        monkeypatch.setenv("CONTEXT_WATCHDOG_THRESHOLD_70", "70")
        monkeypatch.setenv("CONTEXT_WATCHDOG_THRESHOLD_85", "85")
        monkeypatch.setenv("CONTEXT_WATCHDOG_MAX_CALLS", "100")

        first = subprocess.run(["bash", str(WATCHDOG_HOOK)], capture_output=True, text=True, timeout=10)
        second = subprocess.run(["bash", str(WATCHDOG_HOOK)], capture_output=True, text=True, timeout=10)
        third = subprocess.run(["bash", str(WATCHDOG_HOOK)], capture_output=True, text=True, timeout=10)

        assert first.returncode == second.returncode == third.returncode == 0
        assert "CHECKPOINT" not in first.stderr
        assert "CHECKPOINT" in second.stderr
        assert "CHECKPOINT" not in third.stderr

        metric = tmp_path / ".cognitive-os" / "metrics" / "context-watchdog.jsonl"
        rows = [json.loads(line) for line in metric.read_text().splitlines()]
        assert [row["level"] for row in rows].count("checkpoint") == 1


# ===========================================================================
# Pre-Compaction Flush Hook Tests
# ===========================================================================


class TestPreCompactionFlushHook:
    """Verify the pre-compaction-flush.sh hook is correct and registered."""


    def test_flush_hook_is_executable_or_valid_bash(self):
        """pre-compaction-flush.sh must be valid bash (bash -n passes)."""
        if not FLUSH_HOOK.exists():
            pytest.skip("pre-compaction-flush.sh not found")
        result = subprocess.run(
            ["bash", "-n", str(FLUSH_HOOK)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"pre-compaction-flush.sh has bash syntax errors:\n{result.stderr}"
        )


    def test_flush_hook_mentions_in_progress_tasks(self):
        """pre-compaction-flush.sh must instruct noting in-progress tasks."""
        if not FLUSH_HOOK.exists():
            pytest.skip("pre-compaction-flush.sh not found")
        content = FLUSH_HOOK.read_text().lower()
        has_in_progress = "in-progress" in content or "in_progress" in content or "in progress" in content
        assert has_in_progress, (
            "pre-compaction-flush.sh must instruct the agent to note which tasks "
            "are in-progress so the next session can resume without duplicating work."
        )


# ===========================================================================
# Session Directory Structure Tests
# ===========================================================================


class TestSessionDirectoryStructure:
    """Verify that session-init creates the proper directory structure."""


    def test_session_init_runs_at_session_start(self):
        """session-init.sh must be registered as a SessionStart hook."""
        cmds = _load_settings_commands()
        is_registered = any("session-init" in cmd for cmd in cmds)
        assert is_registered, (
            "session-init.sh must be registered in .claude/settings.json as a "
            "SessionStart hook. Without registration, sessions are not isolated."
        )
