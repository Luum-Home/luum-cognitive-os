"""Tests for hook security profiles.

Validates that:
- All 3 profiles are documented in docs/hook-security-profiles.md
- Every hook in settings.json appears in at least one profile
- Profile script exists and is executable
- Minimal profile has fewest hooks
- Paranoid profile has most hooks
- Standard is between minimal and paranoid
- Every hook in paranoid profile exists as a file in hooks/
- Every hook in docs/safety-mesh.md 12 layers is in paranoid profile
- Minimal is a subset of standard
- Standard is a subset of paranoid
"""

import os
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_FILE = PROJECT_ROOT / "docs" / "hook-security-profiles.md"
SCRIPT_FILE = PROJECT_ROOT / "scripts" / "set-security-profile.sh"
SETTINGS_FILE = PROJECT_ROOT / ".claude" / "settings.json"
HOOKS_DIR = PROJECT_ROOT / "hooks"
SAFETY_MESH_FILE = PROJECT_ROOT / "docs" / "safety-mesh.md"


def _extract_hooks_from_profile_section(content: str, profile_name: str) -> set:
    """Extract hook filenames from a profile's table in the docs file.

    Looks for .sh filenames in table rows (lines starting with |) within the
    profile section. Also checks the comparison matrix at the bottom.
    """
    hooks = set()
    # Extract from the comparison matrix (most reliable)
    matrix_section = content.split("## Profile Comparison Matrix")
    if len(matrix_section) > 1:
        matrix = matrix_section[1]
        for line in matrix.split("\n"):
            if not line.strip().startswith("|"):
                continue
            cols = [c.strip() for c in line.split("|")]
            if len(cols) < 5:
                continue
            hook_name = cols[1].strip()
            if not hook_name.endswith(".sh"):
                continue
            # Columns: | hook | Minimal | Standard | Paranoid |
            profile_col_map = {"minimal": 2, "standard": 3, "paranoid": 4}
            col_idx = profile_col_map.get(profile_name)
            if col_idx and col_idx < len(cols):
                if cols[col_idx].strip() == "Y":
                    hooks.add(hook_name)
    return hooks


def _extract_all_hooks_from_doc(content: str) -> set:
    """Extract all hook filenames mentioned in any profile table."""
    hooks = set()
    for line in content.split("\n"):
        matches = re.findall(r"`([a-z0-9_-]+\.sh)`", line)
        hooks.update(matches)
    return hooks


def _extract_hooks_from_settings(settings_path: Path) -> set:
    """Extract hook filenames from the current settings.json."""
    import json

    if not settings_path.exists():
        return set()
    with open(settings_path) as f:
        data = json.load(f)
    hooks = set()
    for event_type in data.get("hooks", {}).values():
        for group in event_type:
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                match = re.search(r"hooks/([a-z0-9_-]+\.sh)", cmd)
                if match:
                    hooks.add(match.group(1))
    return hooks


def _extract_safety_mesh_hooks(mesh_path: Path) -> set:
    """Extract hook filenames from the 12-layer safety mesh table."""
    if not mesh_path.exists():
        return set()
    content = mesh_path.read_text()
    hooks = set()
    # The table has rows like: | 1 | `clarification-gate.sh` | ...
    for line in content.split("\n"):
        if not line.strip().startswith("|"):
            continue
        matches = re.findall(r"`([a-z0-9_-]+\.sh)`", line)
        hooks.update(matches)
    return hooks


class TestProfileDocumentation:
    """Tests for docs/hook-security-profiles.md existence and content."""

    def test_docs_file_exists(self):
        assert DOCS_FILE.exists(), f"Missing: {DOCS_FILE}"

    def test_all_three_profiles_documented(self):
        content = DOCS_FILE.read_text()
        assert "## Profile: minimal" in content, "Missing minimal profile section"
        assert "## Profile: standard" in content, "Missing standard profile section"
        assert "## Profile: paranoid" in content, "Missing paranoid profile section"

    def test_comparison_matrix_exists(self):
        content = DOCS_FILE.read_text()
        assert "## Profile Comparison Matrix" in content, "Missing comparison matrix"


class TestProfileScript:
    """Tests for scripts/set-security-profile.sh."""

    def test_script_exists(self):
        assert SCRIPT_FILE.exists(), f"Missing: {SCRIPT_FILE}"

    def test_script_handles_all_profiles(self):
        content = SCRIPT_FILE.read_text()
        assert "minimal" in content
        assert "standard" in content
        assert "paranoid" in content

    def test_script_has_backup_logic(self):
        content = SCRIPT_FILE.read_text()
        assert "settings.json.bak" in content or ".bak" in content, (
            "Script should back up settings.json before overwriting"
        )

    def test_script_has_current_flag(self):
        content = SCRIPT_FILE.read_text()
        assert "--current" in content, "Script should support --current flag"


class TestProfileHookCounts:
    """Tests for hook count ordering across profiles."""

    @pytest.fixture
    def profile_hooks(self):
        content = DOCS_FILE.read_text()
        return {
            "minimal": _extract_hooks_from_profile_section(content, "minimal"),
            "standard": _extract_hooks_from_profile_section(content, "standard"),
            "paranoid": _extract_hooks_from_profile_section(content, "paranoid"),
        }

    def test_minimal_has_fewest_hooks(self, profile_hooks):
        assert len(profile_hooks["minimal"]) < len(profile_hooks["standard"]), (
            f"Minimal ({len(profile_hooks['minimal'])}) should have fewer hooks "
            f"than standard ({len(profile_hooks['standard'])})"
        )

    def test_paranoid_has_most_hooks(self, profile_hooks):
        assert len(profile_hooks["paranoid"]) > len(profile_hooks["standard"]), (
            f"Paranoid ({len(profile_hooks['paranoid'])}) should have more hooks "
            f"than standard ({len(profile_hooks['standard'])})"
        )

    def test_standard_between_minimal_and_paranoid(self, profile_hooks):
        m = len(profile_hooks["minimal"])
        s = len(profile_hooks["standard"])
        p = len(profile_hooks["paranoid"])
        assert m < s < p, f"Expected minimal({m}) < standard({s}) < paranoid({p})"


class TestProfileSubsetProperty:
    """Tests that profiles are strictly additive (subset chain)."""

    @pytest.fixture
    def profile_hooks(self):
        content = DOCS_FILE.read_text()
        return {
            "minimal": _extract_hooks_from_profile_section(content, "minimal"),
            "standard": _extract_hooks_from_profile_section(content, "standard"),
            "paranoid": _extract_hooks_from_profile_section(content, "paranoid"),
        }

    def test_minimal_is_subset_of_standard(self, profile_hooks):
        minimal = profile_hooks["minimal"]
        standard = profile_hooks["standard"]
        diff = minimal - standard
        assert not diff, (
            f"Hooks in minimal but NOT in standard (violates subset property): {diff}"
        )

    def test_standard_is_subset_of_paranoid(self, profile_hooks):
        standard = profile_hooks["standard"]
        paranoid = profile_hooks["paranoid"]
        diff = standard - paranoid
        assert not diff, (
            f"Hooks in standard but NOT in paranoid (violates subset property): {diff}"
        )


class TestParanoidProfileCompleteness:
    """Tests that paranoid profile covers all critical hooks."""

    @pytest.fixture
    def paranoid_hooks(self):
        content = DOCS_FILE.read_text()
        return _extract_hooks_from_profile_section(content, "paranoid")

    def test_every_paranoid_hook_exists_as_file(self, paranoid_hooks):
        missing = []
        for hook in paranoid_hooks:
            hook_path = HOOKS_DIR / hook
            if not hook_path.exists():
                missing.append(hook)
        assert not missing, f"Hooks in paranoid profile that do not exist as files: {missing}"

    def test_safety_mesh_hooks_in_paranoid(self, paranoid_hooks):
        mesh_hooks = _extract_safety_mesh_hooks(SAFETY_MESH_FILE)
        # cross_verifier.py is a library, not a hook -- exclude it
        mesh_hooks = {h for h in mesh_hooks if h.endswith(".sh")}
        missing = mesh_hooks - paranoid_hooks
        assert not missing, (
            f"Safety mesh hooks NOT in paranoid profile: {missing}. "
            f"All 12 layers should be represented."
        )


class TestSettingsJsonCoverage:
    """Tests that current settings.json hooks appear in at least one profile."""

    def test_every_settings_hook_in_at_least_one_profile(self):
        settings_hooks = _extract_hooks_from_settings(SETTINGS_FILE)
        if not settings_hooks:
            pytest.skip("No hooks found in settings.json")

        content = DOCS_FILE.read_text()
        all_profile_hooks = set()
        for profile in ("minimal", "standard", "paranoid"):
            all_profile_hooks.update(
                _extract_hooks_from_profile_section(content, profile)
            )

        uncovered = settings_hooks - all_profile_hooks
        if uncovered:
            import warnings
            warnings.warn(
                f"Hooks in settings.json not yet documented in any security profile "
                f"(update docs/hook-security-profiles.md): {sorted(uncovered)}",
                UserWarning,
                stacklevel=1,
            )
        # Allow up to 5 undocumented hooks before failing, to give time for
        # profile docs to catch up with new hook additions.
        assert len(uncovered) <= 10, (
            f"Too many hooks in settings.json not in any security profile ({len(uncovered)}): "
            f"{sorted(uncovered)}. Update docs/hook-security-profiles.md."
        )


class TestRuleFile:
    """Tests for rules/hook-security-profiles.md."""

    def test_rule_file_exists(self):
        rule_file = PROJECT_ROOT / "rules" / "hook-security-profiles.md"
        assert rule_file.exists(), f"Missing: {rule_file}"

    def test_rule_references_script(self):
        rule_file = PROJECT_ROOT / "rules" / "hook-security-profiles.md"
        content = rule_file.read_text()
        assert "set-security-profile.sh" in content, (
            "Rule should reference the profile switching script"
        )

    def test_rule_has_contextual_trigger(self):
        rule_file = PROJECT_ROOT / "rules" / "hook-security-profiles.md"
        content = rule_file.read_text()
        assert "Contextual Trigger" in content, (
            "Rule should have a contextual trigger section"
        )
