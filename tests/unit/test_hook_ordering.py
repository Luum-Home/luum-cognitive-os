"""Tests verifying hook registration order in .claude/settings.json.

These tests confirm that safety-critical hooks appear in the right sequence
and that mandatory hooks are registered at all.  They parse settings.json
directly so they will catch accidental re-orderings without needing to run
a live Claude session.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SETTINGS_FILE = REPO_ROOT / ".claude" / "settings.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        pytest.skip(f"settings.json not found: {SETTINGS_FILE}")
    return json.loads(SETTINGS_FILE.read_text())


def _pre_tool_use_hooks(settings: dict) -> list[dict]:
    """Return the flat list of hook entries for PreToolUse matchers."""
    return settings.get("hooks", {}).get("PreToolUse", [])


def _post_tool_use_hooks(settings: dict) -> list[dict]:
    return settings.get("hooks", {}).get("PostToolUse", [])


def _all_commands_for_event(event_hooks: list[dict]) -> list[str]:
    """Flatten all command strings from a list of hook group entries."""
    commands: list[str] = []
    for group in event_hooks:
        for h in group.get("hooks", []):
            cmd = h.get("command", "")
            if cmd:
                commands.append(cmd)
    return commands


def _commands_for_matcher(event_hooks: list[dict], matcher: str) -> list[str]:
    """Return commands from groups whose matcher contains the given string."""
    commands: list[str] = []
    for group in event_hooks:
        if matcher in group.get("matcher", ""):
            for h in group.get("hooks", []):
                cmd = h.get("command", "")
                if cmd:
                    commands.append(cmd)
    return commands


# ---------------------------------------------------------------------------
# Tests: PreToolUse ordering
# ---------------------------------------------------------------------------


class TestPreToolUseOrdering:
    def test_rate_limiter_before_blast_radius_in_pretooluse(self):
        """rate-limiter.sh must appear before blast-radius.sh in PreToolUse.

        The rate limiter should block runaway launches before the blast-radius
        hook evaluates scope, preserving the budget safety net.
        """
        settings = _load_settings()
        all_pre = _all_commands_for_event(_pre_tool_use_hooks(settings))

        rate_limiter_idx = next(
            (i for i, c in enumerate(all_pre) if "rate-limiter.sh" in c), None
        )
        blast_radius_idx = next(
            (i for i, c in enumerate(all_pre) if "blast-radius.sh" in c), None
        )

        assert rate_limiter_idx is not None, (
            "rate-limiter.sh not found in PreToolUse hooks"
        )
        assert blast_radius_idx is not None, (
            "blast-radius.sh not found in PreToolUse hooks"
        )
        assert rate_limiter_idx < blast_radius_idx, (
            f"rate-limiter.sh (pos {rate_limiter_idx}) must come before "
            f"blast-radius.sh (pos {blast_radius_idx}) in PreToolUse"
        )


# ---------------------------------------------------------------------------
# Tests: PostToolUse registrations
# ---------------------------------------------------------------------------


class TestPostToolUseRegistrations:
    def test_claim_validator_in_posttooluse_agent(self):
        """claim-validator.sh must be registered in PostToolUse for Agent."""
        settings = _load_settings()
        agent_cmds = _commands_for_matcher(_post_tool_use_hooks(settings), "Agent")

        assert any("claim-validator.sh" in c for c in agent_cmds), (
            "claim-validator.sh not found in PostToolUse Agent hooks.\n"
            f"Agent commands: {agent_cmds}"
        )

    def test_secret_detector_in_posttooluse_edit_write(self):
        """secret-detector.sh must be registered in PostToolUse for Edit|Write."""
        settings = _load_settings()
        # Look in the PostToolUse groups whose matcher covers Edit or Write
        post_hooks = _post_tool_use_hooks(settings)
        edit_write_cmds: list[str] = []
        for group in post_hooks:
            m = group.get("matcher", "")
            if "Edit" in m or "Write" in m:
                for h in group.get("hooks", []):
                    cmd = h.get("command", "")
                    if cmd:
                        edit_write_cmds.append(cmd)

        assert any("secret-detector.sh" in c for c in edit_write_cmds), (
            "secret-detector.sh not found in PostToolUse Edit|Write hooks.\n"
            f"Edit|Write commands: {edit_write_cmds}"
        )

    def test_agent_verifier_registered(self):
        """agent-output-verifier.sh must be registered for PostToolUse Agent."""
        settings = _load_settings()
        agent_cmds = _commands_for_matcher(_post_tool_use_hooks(settings), "Agent")

        assert any("agent-output-verifier.sh" in c for c in agent_cmds), (
            "agent-output-verifier.sh not found in PostToolUse Agent hooks.\n"
            f"Agent commands: {agent_cmds}"
        )
