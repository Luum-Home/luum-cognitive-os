"""
tests/unit/test_cognitive_os_yaml_harness_hooks.py

Schema validation tests for the cognitive-os.yaml > harness.hooks canonical block.

ADR-064 Task 2.1 acceptance criteria:
1. harness.hooks block exists and is populated with every hook from .claude/settings.json.
2. Each entry has required fields (script, event) and optional fields (matcher, async, scope).
3. yamllint cognitive-os.yaml passes (covered separately; this test validates Python-level schema).
4. Canonical event names are the valid CC event names.
5. Every hook in .claude/settings.json has a corresponding entry in harness.hooks.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.parent
COGNITIVE_OS_YAML = REPO_ROOT / "cognitive-os.yaml"
SETTINGS_JSON = REPO_ROOT / ".claude" / "settings.json"

VALID_CC_EVENTS = {
    "SessionStart",
    "UserPromptSubmit",
    "SubagentStart",
    "PreCompact",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "TeammateIdle",
    "TaskCreated",
    "TaskCompleted",
}

VALID_SCOPES = {"os-only", "both"}


@pytest.fixture(scope="module")
def config():
    assert COGNITIVE_OS_YAML.exists(), f"cognitive-os.yaml not found at {COGNITIVE_OS_YAML}"
    with COGNITIVE_OS_YAML.open() as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def harness_hooks(config):
    assert "harness" in config, "cognitive-os.yaml missing top-level 'harness' key"
    assert "hooks" in config["harness"], "cognitive-os.yaml missing 'harness.hooks' block"
    return config["harness"]["hooks"]


@pytest.fixture(scope="module")
def settings_json():
    assert SETTINGS_JSON.exists(), f".claude/settings.json not found at {SETTINGS_JSON}"
    with SETTINGS_JSON.open() as f:
        return json.load(f)


class TestHarnessHooksBlockExists:
    def test_harness_key_present(self, config):
        assert "harness" in config, "Expected 'harness' top-level key in cognitive-os.yaml"

    def test_hooks_key_present(self, config):
        assert "hooks" in config.get("harness", {}), "Expected 'harness.hooks' in cognitive-os.yaml"

    def test_hooks_is_dict(self, harness_hooks):
        assert isinstance(harness_hooks, dict), "harness.hooks must be a YAML mapping"

    def test_hooks_non_empty(self, harness_hooks):
        assert len(harness_hooks) > 0, "harness.hooks must contain at least one entry"


class TestHarnessHooksSchema:
    """Each hook entry must satisfy the schema."""

    def test_all_entries_are_dicts(self, harness_hooks):
        for name, entry in harness_hooks.items():
            assert isinstance(entry, dict), f"Hook '{name}' must be a YAML mapping, got {type(entry)}"

    def test_required_field_script(self, harness_hooks):
        for name, entry in harness_hooks.items():
            assert "script" in entry, f"Hook '{name}' missing required field 'script'"
            assert isinstance(entry["script"], str), f"Hook '{name}'.script must be a string"
            assert entry["script"].startswith("hooks/"), (
                f"Hook '{name}'.script must start with 'hooks/', got '{entry['script']}'"
            )

    def test_required_field_event(self, harness_hooks):
        for name, entry in harness_hooks.items():
            assert "event" in entry, f"Hook '{name}' missing required field 'event'"
            assert entry["event"] in VALID_CC_EVENTS, (
                f"Hook '{name}'.event '{entry['event']}' not in valid CC events: {VALID_CC_EVENTS}"
            )

    def test_optional_field_matcher_is_string(self, harness_hooks):
        for name, entry in harness_hooks.items():
            if "matcher" in entry:
                assert isinstance(entry["matcher"], str), (
                    f"Hook '{name}'.matcher must be a string, got {type(entry['matcher'])}"
                )

    def test_optional_field_async_is_bool(self, harness_hooks):
        for name, entry in harness_hooks.items():
            if "async" in entry:
                assert isinstance(entry["async"], bool), (
                    f"Hook '{name}'.async must be boolean, got {type(entry['async'])}"
                )

    def test_optional_field_scope_valid(self, harness_hooks):
        for name, entry in harness_hooks.items():
            if "scope" in entry:
                assert entry["scope"] in VALID_SCOPES, (
                    f"Hook '{name}'.scope '{entry['scope']}' not in {VALID_SCOPES}"
                )

    def test_script_file_ends_with_sh(self, harness_hooks):
        for name, entry in harness_hooks.items():
            assert entry["script"].endswith(".sh"), (
                f"Hook '{name}'.script '{entry['script']}' must end with '.sh'"
            )

    def test_matcher_only_on_tool_events(self, harness_hooks):
        """Matchers are only meaningful on PreToolUse and PostToolUse."""
        tool_events = {"PreToolUse", "PostToolUse"}
        for name, entry in harness_hooks.items():
            if "matcher" in entry and entry["matcher"] != "":
                assert entry["event"] in tool_events, (
                    f"Hook '{name}' has a non-empty matcher '{entry['matcher']}' "
                    f"but event '{entry['event']}' is not PreToolUse/PostToolUse"
                )


class TestHarnessHooksCompleteness:
    """Every hook script referenced in .claude/settings.json must appear in harness.hooks."""

    def _extract_scripts_from_settings(self, settings_json):
        """Extract all hook script basenames from .claude/settings.json commands."""
        scripts = set()
        hooks_section = settings_json.get("hooks", {})
        for event_groups in hooks_section.values():
            for group in event_groups:
                for hook in group.get("hooks", []):
                    command = hook.get("command", "")
                    match = re.search(r'/hooks/([^"]+\.sh)"', command)
                    if match:
                        scripts.add(match.group(1))
        return scripts

    def test_all_settings_json_scripts_in_harness_hooks(self, harness_hooks, settings_json):
        settings_scripts = self._extract_scripts_from_settings(settings_json)
        registered_scripts = {
            Path(entry["script"]).name for entry in harness_hooks.values()
        }
        missing = settings_scripts - registered_scripts
        assert not missing, (
            f"The following hook scripts appear in .claude/settings.json but are NOT "
            f"registered in cognitive-os.yaml > harness.hooks:\n"
            + "\n".join(f"  - {s}" for s in sorted(missing))
        )

    def test_harness_hooks_count_matches_settings(self, harness_hooks, settings_json):
        settings_scripts = self._extract_scripts_from_settings(settings_json)
        registered_scripts = {
            Path(entry["script"]).name for entry in harness_hooks.values()
        }
        assert len(registered_scripts) >= len(settings_scripts), (
            f"harness.hooks has {len(registered_scripts)} unique scripts, "
            f"but .claude/settings.json has {len(settings_scripts)}. "
            "Expected harness.hooks to be a superset."
        )


class TestHarnessHooksEventCoverage:
    """All CC events must have at least one hook registered."""

    EXPECTED_EVENTS_WITH_HOOKS = {
        "SessionStart",
        "UserPromptSubmit",
        "SubagentStart",
        "PreCompact",
        "PreToolUse",
        "PostToolUse",
        "Stop",
        "TeammateIdle",
        "TaskCreated",
        "TaskCompleted",
    }

    def test_all_expected_events_covered(self, harness_hooks):
        registered_events = {entry["event"] for entry in harness_hooks.values()}
        missing = self.EXPECTED_EVENTS_WITH_HOOKS - registered_events
        assert not missing, (
            f"These CC events have no hook in harness.hooks: {missing}"
        )
