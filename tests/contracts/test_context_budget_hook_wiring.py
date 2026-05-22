from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
REQUIRED_ACCOUNTED_HOOKS = [
    "hooks/skill-router-prompt-suggest.sh",
    "hooks/rule-router-prompt-suggest.sh",
    "hooks/adr-relevance-suggest.sh",
    "hooks/cross-session-peer-context.sh",
    "hooks/agent-message-inbox-context.sh",
]


def test_required_additional_context_hooks_call_accountant() -> None:
    for rel in REQUIRED_ACCOUNTED_HOOKS:
        text = (REPO / rel).read_text(encoding="utf-8")
        assert "context_budget_lib.sh" in text, rel
        assert "context_budget_filter_json" in text, rel


def test_context_budget_meter_registered_last_in_user_prompt_submit() -> None:
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    groups = settings["hooks"]["UserPromptSubmit"]
    commands = [hook["command"] for group in groups for hook in group.get("hooks", [])]
    assert any("context-budget-meter.sh" in command for command in commands)
    assert "context-budget-meter.sh" in commands[-1]

    for profile in (REPO / "templates" / "security-profiles").glob("*.json"):
        data = json.loads(profile.read_text(encoding="utf-8"))
        profile_commands = [hook["command"] for group in data["hooks"]["UserPromptSubmit"] for hook in group.get("hooks", [])]
        assert "context-budget-meter.sh" in profile_commands[-1], profile.name


def test_subagent_context_injector_is_accounted() -> None:
    text = (REPO / "hooks" / "subagent-context-injector.sh").read_text(encoding="utf-8")
    assert "context_budget_lib.sh" in text
    assert "context_budget_filter_json" in text


def test_context_watchdog_registered_in_post_tool_use() -> None:
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    groups = settings["hooks"]["PostToolUse"]
    commands = [hook["command"] for group in groups for hook in group.get("hooks", [])]
    assert any("context-watchdog.sh" in command for command in commands)


def test_document_ingest_guard_registered_before_large_file_advisor() -> None:
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    read_groups = [group for group in settings["hooks"]["PreToolUse"] if group.get("matcher") == "Read"]
    assert read_groups, "Read PreToolUse group missing"
    commands = [hook["command"] for hook in read_groups[0].get("hooks", [])]
    joined = "\n".join(commands)
    assert "document-ingest-guard.sh" in joined
    assert "large-file-advisor.sh" in joined
    assert joined.index("document-ingest-guard.sh") < joined.index("large-file-advisor.sh")


def test_context_diet_registered_for_agent_pretooluse() -> None:
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    agent_groups = [group for group in settings["hooks"]["PreToolUse"] if group.get("matcher") == "Agent"]
    assert agent_groups, "Agent PreToolUse group missing"
    commands = [hook["command"] for hook in agent_groups[0].get("hooks", [])]
    joined = "\n".join(commands)
    assert "query-tailored-context-inject.sh" in joined
    assert "context-diet.sh" in joined
    assert joined.index("query-tailored-context-inject.sh") < joined.index("context-diet.sh")
