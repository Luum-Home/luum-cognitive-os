"""Behavior tests specifically for compaction protection scenarios.

Validates that the system's defenses against context-compaction-induced data loss
are in place, correctly configured, and contain the expected logic.

A compaction event destroys everything in working memory. These tests verify
the layers that ensure important state is saved BEFORE compaction occurs and
that the next session can recover from where the last one left off.
"""

import json
import re
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

    def test_context_management_rule_exists(self):
        """rules/context-management.md must exist."""
        assert CONTEXT_MGMT_RULE.exists(), (
            f"rules/context-management.md not found at {CONTEXT_MGMT_RULE}. "
            "This rule defines the 50/70/85% thresholds for proactive state-saving."
        )

    def test_fifty_percent_threshold_documented(self):
        """Context-management rule must document the 50% efficiency-mode threshold."""
        if not CONTEXT_MGMT_RULE.exists():
            pytest.skip("rules/context-management.md not found")
        content = CONTEXT_MGMT_RULE.read_text()
        assert "50%" in content or "50 %" in content, (
            "rules/context-management.md must document the 50% threshold "
            "(efficiency mode: be concise, start saving important decisions)."
        )

    def test_seventy_percent_threshold_documented(self):
        """Context-management rule must document the 70% save-and-summarize threshold."""
        if not CONTEXT_MGMT_RULE.exists():
            pytest.skip("rules/context-management.md not found")
        content = CONTEXT_MGMT_RULE.read_text()
        assert "70%" in content or "70 %" in content, (
            "rules/context-management.md must document the 70% threshold "
            "(CRITICAL save point: mandatory Engram save before proceeding)."
        )

    def test_eighty_five_percent_threshold_documented(self):
        """Context-management rule must document the 85% stop-and-handoff threshold."""
        if not CONTEXT_MGMT_RULE.exists():
            pytest.skip("rules/context-management.md not found")
        content = CONTEXT_MGMT_RULE.read_text()
        assert "85%" in content or "85 %" in content, (
            "rules/context-management.md must document the 85% threshold "
            "(URGENT: stop new work, complete current task, call mem_session_summary)."
        )

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

    def test_context_management_rule_mandates_session_summary(self):
        """Context-management rule must mandate mem_session_summary at 85%."""
        if not CONTEXT_MGMT_RULE.exists():
            pytest.skip("rules/context-management.md not found")
        content = CONTEXT_MGMT_RULE.read_text()
        assert "mem_session_summary" in content, (
            "rules/context-management.md must mandate calling mem_session_summary "
            "at the 85% threshold so the next session can resume intelligently."
        )


# ===========================================================================
# Pre-Compaction Flush Hook Tests
# ===========================================================================


class TestPreCompactionFlushHook:
    """Verify the pre-compaction-flush.sh hook is correct and registered."""

    def test_flush_hook_exists(self):
        """pre-compaction-flush.sh must exist in the hooks directory."""
        assert FLUSH_HOOK.exists(), (
            f"pre-compaction-flush.sh not found at {FLUSH_HOOK}. "
            "This is the last-resort safety net before context compaction."
        )

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

    def test_flush_hook_contains_session_summary_instruction(self):
        """pre-compaction-flush.sh must instruct the agent to call mem_session_summary."""
        if not FLUSH_HOOK.exists():
            pytest.skip("pre-compaction-flush.sh not found")
        content = FLUSH_HOOK.read_text().lower()
        assert "mem_session_summary" in content, (
            "pre-compaction-flush.sh must instruct the agent to call "
            "mem_session_summary. Without a session summary, the next session "
            "has no structured record of what was accomplished."
        )

    def test_flush_hook_contains_mem_save_instruction(self):
        """pre-compaction-flush.sh must instruct the agent to call mem_save."""
        if not FLUSH_HOOK.exists():
            pytest.skip("pre-compaction-flush.sh not found")
        content = FLUSH_HOOK.read_text().lower()
        assert "mem_save" in content, (
            "pre-compaction-flush.sh must instruct the agent to call mem_save "
            "for unsaved decisions, bug fixes, or discoveries."
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

    def test_session_init_creates_session_id_directory(self):
        """session-init.sh must create a unique session ID directory."""
        session_init = HOOKS_DIR / "session-init.sh"
        if not session_init.exists():
            pytest.skip("session-init.sh not found")
        content = session_init.read_text()
        # Verify it creates SESSION_DIR
        assert "SESSION_DIR" in content or "session_dir" in content.lower(), (
            "session-init.sh must create a per-session directory (SESSION_DIR) "
            "for session isolation."
        )

    def test_session_init_creates_meta_json(self):
        """session-init.sh must create meta.json with session metadata."""
        session_init = HOOKS_DIR / "session-init.sh"
        if not session_init.exists():
            pytest.skip("session-init.sh not found")
        content = session_init.read_text()
        assert "meta.json" in content, (
            "session-init.sh must create meta.json containing session_id, pid, "
            "and start_time for crash recovery identification."
        )

    def test_session_init_creates_tasks_json(self):
        """session-init.sh must create an empty tasks.json for session-scoped tracking."""
        session_init = HOOKS_DIR / "session-init.sh"
        if not session_init.exists():
            pytest.skip("session-init.sh not found")
        content = session_init.read_text()
        assert "tasks.json" in content, (
            "session-init.sh must create a session-scoped tasks.json. "
            "This enables per-session task isolation."
        )

    def test_session_init_creates_metrics_directory(self):
        """session-init.sh must create a metrics/ subdirectory for session metrics."""
        session_init = HOOKS_DIR / "session-init.sh"
        if not session_init.exists():
            pytest.skip("session-init.sh not found")
        content = session_init.read_text()
        assert "metrics" in content, (
            "session-init.sh must create a metrics/ directory within the session "
            "directory for session-scoped metric isolation."
        )

    def test_session_init_runs_at_session_start(self):
        """session-init.sh must be registered as a SessionStart hook."""
        cmds = _load_settings_commands()
        is_registered = any("session-init" in cmd for cmd in cmds)
        assert is_registered, (
            "session-init.sh must be registered in .claude/settings.json as a "
            "SessionStart hook. Without registration, sessions are not isolated."
        )
