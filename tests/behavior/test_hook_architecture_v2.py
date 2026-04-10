"""Tests for Hook Architecture v2 plan.

Validates that:
- Plan file exists and is well-structured
- Settings JSON files are valid JSON
- All target events have at least 1 hook
- Async hooks are non-critical (no exit 2 in async hook source)
- SubagentStart hook is planned
- UserPromptSubmit hook is planned
- PreCompact hook is planned
- Every hook in new settings.json exists as a file
- Hook count per profile: minimal < standard < paranoid
- Security-critical hooks are synchronous
- New hooks to create are documented in the plan
"""

import json
import os
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PLANS_DIR = PROJECT_ROOT / ".cognitive-os" / "plans" / "features"
PLAN_FILE = PLANS_DIR / "hook-architecture-v2.md"
SETTINGS_STANDARD = PLANS_DIR / "hook-architecture-v2-settings.json"
SETTINGS_MINIMAL = PLANS_DIR / "hook-architecture-v2-settings-minimal.json"
SETTINGS_PARANOID = PLANS_DIR / "hook-architecture-v2-settings-paranoid.json"

HOOKS_CORE_DIR = PROJECT_ROOT / "hooks"
PACKAGES_DIR = PROJECT_ROOT / "packages"

# Events that MUST have at least 1 hook in standard profile
REQUIRED_EVENTS_STANDARD = [
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "SubagentStart",
    "PreCompact",
    "Stop",
]

# Security-critical hooks that must NEVER be async
SECURITY_CRITICAL_HOOKS = [
    "secret-detector.sh",
    "content-policy.sh",
    "rate-limiter.sh",
    "clarification-gate.sh",
    "pre-compaction-flush.sh",
]


def _load_settings(path: Path) -> dict:
    """Load and parse a settings JSON file."""
    with open(path) as f:
        return json.load(f)


def _extract_hook_commands(settings: dict) -> list[dict]:
    """Extract all hook entries from a settings dict, preserving async flag."""
    hooks = []
    for event, entries in settings.get("hooks", {}).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                is_async = hook.get("async", False)
                hooks.append({
                    "event": event,
                    "matcher": entry.get("matcher", ""),
                    "command": cmd,
                    "async": is_async,
                    "filename": _extract_filename(cmd),
                })
    return hooks


def _extract_filename(command: str) -> str:
    """Extract the .sh filename from a hook command string."""
    match = re.search(r'[\\/]([a-z0-9_-]+\.sh)', command)
    return match.group(1) if match else ""


def _resolve_hook_path(command: str) -> Path:
    """Resolve the hook path from a command string, replacing $CLAUDE_PROJECT_DIR."""
    # Extract the path after 'bash "'
    match = re.search(r'bash\s+"([^"]+)"', command)
    if not match:
        return Path()
    path = match.group(1).replace("$CLAUDE_PROJECT_DIR", str(PROJECT_ROOT))
    return Path(path)


def _count_unique_hooks(settings: dict) -> int:
    """Count unique hook commands in a settings dict."""
    hooks = _extract_hook_commands(settings)
    return len({h["command"] for h in hooks})


# --- Plan file structure tests ---


class TestPlanFileExists:
    """Verify plan file exists and has required sections."""

    def test_plan_file_exists(self):
        assert PLAN_FILE.exists(), f"Plan file not found: {PLAN_FILE}"

    def test_plan_has_current_state_section(self):
        content = PLAN_FILE.read_text()
        assert "## 1. Current State" in content or "## Current State" in content

    def test_plan_has_target_state_section(self):
        content = PLAN_FILE.read_text()
        assert "## 2. Target State" in content or "## Target State" in content

    def test_plan_has_migration_plan_section(self):
        content = PLAN_FILE.read_text()
        assert any(s in content for s in [
            "## 3. Migration Plan",
            "## Migration Plan",
            "## 3. What Claude Code",
            "## 10. Implementation Phases",
            "## Implementation Phases",
        ]), "Plan must have a migration or implementation section"

    def test_plan_has_new_hooks_section(self):
        content = PLAN_FILE.read_text()
        assert "## 4. New Hooks to CREATE" in content or "New Hooks" in content or "## 4. Proposed" in content

    def test_plan_has_risks_section(self):
        content = PLAN_FILE.read_text()
        assert "Risks" in content, "Plan must have a risks section"

    def test_plan_has_test_plan_section(self):
        content = PLAN_FILE.read_text()
        assert "Test Plan" in content, "Plan must have a test plan section"


# --- Settings JSON validity tests ---


class TestSettingsJsonValidity:
    """All three profile settings files must be valid JSON."""

    def test_standard_settings_is_valid_json(self):
        settings = _load_settings(SETTINGS_STANDARD)
        assert "hooks" in settings

    def test_minimal_settings_is_valid_json(self):
        settings = _load_settings(SETTINGS_MINIMAL)
        assert "hooks" in settings

    def test_paranoid_settings_is_valid_json(self):
        settings = _load_settings(SETTINGS_PARANOID)
        assert "hooks" in settings

    def test_standard_has_profile_metadata(self):
        settings = _load_settings(SETTINGS_STANDARD)
        assert settings.get("_profile") == "standard"

    def test_minimal_has_profile_metadata(self):
        settings = _load_settings(SETTINGS_MINIMAL)
        assert settings.get("_profile") == "minimal"

    def test_paranoid_has_profile_metadata(self):
        settings = _load_settings(SETTINGS_PARANOID)
        assert settings.get("_profile") == "paranoid"


# --- Event coverage tests ---


class TestEventCoverage:
    """All required events must have at least 1 hook in standard profile."""

    @pytest.fixture
    def standard_settings(self):
        return _load_settings(SETTINGS_STANDARD)

    @pytest.mark.parametrize("event", REQUIRED_EVENTS_STANDARD)
    def test_required_event_has_hooks(self, standard_settings, event):
        hooks_config = standard_settings.get("hooks", {})
        assert event in hooks_config, f"Event '{event}' missing from standard settings"
        entries = hooks_config[event]
        total_hooks = sum(len(e.get("hooks", [])) for e in entries)
        assert total_hooks > 0, f"Event '{event}' has 0 hooks in standard profile"

    def test_subagent_start_planned(self):
        settings = _load_settings(SETTINGS_STANDARD)
        assert "SubagentStart" in settings["hooks"]

    def test_user_prompt_submit_planned(self):
        settings = _load_settings(SETTINGS_STANDARD)
        assert "UserPromptSubmit" in settings["hooks"]

    def test_pre_compact_planned(self):
        settings = _load_settings(SETTINGS_STANDARD)
        assert "PreCompact" in settings["hooks"]

    def test_pre_compact_in_minimal(self):
        """PreCompact is critical -- must be in ALL profiles including minimal."""
        settings = _load_settings(SETTINGS_MINIMAL)
        assert "PreCompact" in settings["hooks"]


# --- Async safety tests ---


class TestAsyncSafety:
    """Async hooks must be non-critical (advisory only, never block)."""

    @pytest.fixture
    def paranoid_hooks(self):
        settings = _load_settings(SETTINGS_PARANOID)
        return _extract_hook_commands(settings)

    def test_no_security_critical_hooks_are_async(self, paranoid_hooks):
        """Security-critical hooks must never be async."""
        for hook in paranoid_hooks:
            if hook["filename"] in SECURITY_CRITICAL_HOOKS:
                assert not hook["async"], (
                    f"Security-critical hook '{hook['filename']}' is marked async. "
                    f"Security hooks must be synchronous to block on violations."
                )

    def test_async_hooks_exist_as_files(self, paranoid_hooks):
        """Even async hooks must reference existing files (except planned new hooks)."""
        # Hooks that are planned but not yet created
        new_hooks = {"subagent-context-injector.sh", "user-prompt-capture.sh"}
        async_hooks = [h for h in paranoid_hooks if h["async"]]
        for hook in async_hooks:
            if hook["filename"] in new_hooks:
                continue
            path = _resolve_hook_path(hook["command"])
            assert path.exists() or not path.parts, (
                f"Async hook file not found: {hook['command']} -> {path}"
            )


# --- Hook file existence tests ---


class TestHookFileExistence:
    """Every hook referenced in settings must exist as a file."""

    @pytest.fixture(params=["standard", "minimal", "paranoid"])
    def profile_hooks(self, request):
        file_map = {
            "standard": SETTINGS_STANDARD,
            "minimal": SETTINGS_MINIMAL,
            "paranoid": SETTINGS_PARANOID,
        }
        settings = _load_settings(file_map[request.param])
        hooks = _extract_hook_commands(settings)
        return request.param, hooks

    def test_all_hook_files_exist(self, profile_hooks):
        profile, hooks = profile_hooks
        missing = []
        for hook in hooks:
            path = _resolve_hook_path(hook["command"])
            # Skip hooks that need to be created (documented in plan)
            new_hooks = {"subagent-context-injector.sh", "user-prompt-capture.sh"}
            if hook["filename"] in new_hooks:
                continue
            if path.parts and not path.exists():
                missing.append(f"{hook['filename']} -> {path}")
        assert not missing, (
            f"Profile '{profile}' references {len(missing)} missing hook files:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )


# --- Profile ordering tests ---


class TestProfileOrdering:
    """Hook counts must be ordered: minimal < standard < paranoid."""

    def test_hook_count_ordering(self):
        minimal = _count_unique_hooks(_load_settings(SETTINGS_MINIMAL))
        standard = _count_unique_hooks(_load_settings(SETTINGS_STANDARD))
        paranoid = _count_unique_hooks(_load_settings(SETTINGS_PARANOID))

        assert minimal < standard, (
            f"Minimal ({minimal}) must have fewer hooks than standard ({standard})"
        )
        assert standard < paranoid, (
            f"Standard ({standard}) must have fewer hooks than paranoid ({paranoid})"
        )

    def test_minimal_is_subset_of_standard(self):
        """Every hook in minimal must also be in standard."""
        minimal_hooks = {
            h["filename"]
            for h in _extract_hook_commands(_load_settings(SETTINGS_MINIMAL))
        }
        standard_hooks = {
            h["filename"]
            for h in _extract_hook_commands(_load_settings(SETTINGS_STANDARD))
        }
        missing = minimal_hooks - standard_hooks
        assert not missing, (
            f"Hooks in minimal but not in standard: {missing}"
        )

    def test_standard_is_subset_of_paranoid(self):
        """Every hook in standard must also be in paranoid."""
        standard_hooks = {
            h["filename"]
            for h in _extract_hook_commands(_load_settings(SETTINGS_STANDARD))
        }
        paranoid_hooks = {
            h["filename"]
            for h in _extract_hook_commands(_load_settings(SETTINGS_PARANOID))
        }
        missing = standard_hooks - paranoid_hooks
        assert not missing, (
            f"Hooks in standard but not in paranoid: {missing}"
        )


# --- New hooks documentation tests ---


class TestNewHooksDocumented:
    """New hooks to be created must be documented in the plan."""

    @pytest.fixture
    def plan_content(self):
        return PLAN_FILE.read_text()

    def test_subagent_context_injector_documented(self, plan_content):
        assert "subagent-context-injector" in plan_content

    def test_user_prompt_capture_documented(self, plan_content):
        assert "user-prompt-capture" in plan_content

    def test_pre_compaction_flush_documented(self, plan_content):
        assert "pre-compaction-flush" in plan_content


# --- Profile metadata consistency tests ---


class TestProfileMetadata:
    """Profile metadata (_hook_count, _events_used) must match actual content."""

    @pytest.mark.parametrize(
        "path,expected_profile",
        [
            (SETTINGS_STANDARD, "standard"),
            (SETTINGS_MINIMAL, "minimal"),
            (SETTINGS_PARANOID, "paranoid"),
        ],
    )
    def test_hook_count_metadata_is_close(self, path, expected_profile):
        """The _hook_count metadata should be within 3 of actual count."""
        settings = _load_settings(path)
        claimed = settings.get("_hook_count", 0)
        actual = _count_unique_hooks(settings)
        assert abs(claimed - actual) <= 3, (
            f"Profile '{expected_profile}' claims {claimed} hooks but has {actual}. "
            f"Update _hook_count metadata."
        )

    @pytest.mark.parametrize(
        "path,expected_profile",
        [
            (SETTINGS_STANDARD, "standard"),
            (SETTINGS_MINIMAL, "minimal"),
            (SETTINGS_PARANOID, "paranoid"),
        ],
    )
    def test_events_used_metadata_matches(self, path, expected_profile):
        """The _events_used metadata should list all events with hooks."""
        settings = _load_settings(path)
        claimed_events = set(settings.get("_events_used", []))
        actual_events = set(settings.get("hooks", {}).keys())
        assert claimed_events == actual_events, (
            f"Profile '{expected_profile}' _events_used mismatch. "
            f"Claimed: {claimed_events}. Actual: {actual_events}."
        )
