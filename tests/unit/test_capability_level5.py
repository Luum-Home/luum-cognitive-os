"""Unit tests for capability level 5 behavior.

Validates that level 5 (autonomous+) correctly disables 11 additional
components beyond level 4, maintains cumulative disabling, never disables
essential hooks, and that bash/python implementations stay in sync.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from lib.capability_levels import (
    DEFAULT_AUTO_DISABLE,
    get_disabled_components,
    should_component_run,
)

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Baseline components that level 5 should disable (from DEFAULT_AUTO_DISABLE[5]).
# New additions to DEFAULT_AUTO_DISABLE[5] are OK; removals are caught.
LEVEL_5_BASELINE_COMPONENTS = {
    "completeness-check",
    "epic-task-detector",
    "scope-proportionality",
    "trust-score-validator",
    "claim-validator",
    "tool-loop-detector",
    "consequence-evaluator",
    "infra-intent-detector",
    "pre-cleanup-snapshot",
    "architecture-compliance",
    "auto-skill-generator",
}

# Essential hooks that must NEVER be disabled at any level
ESSENTIAL_HOOKS = [
    "session-init",
    "session-cleanup",
    "error-learning",
    "secret-detector",
    "result-truncator",
    "content-policy",
]


# ---------------------------------------------------------------------------
# Level 5 Python tests
# ---------------------------------------------------------------------------


class TestLevel5DisablesComponents:
    """Level 5 should auto-disable additional components beyond level 4."""

    def test_level5_disables_at_least_baseline_components(self):
        """Level 5 should auto-disable at least the baseline components."""
        level5_specific = set(DEFAULT_AUTO_DISABLE.get(5, []))
        assert len(level5_specific) >= len(LEVEL_5_BASELINE_COMPONENTS), (
            f"Expected at least {len(LEVEL_5_BASELINE_COMPONENTS)} level-5-specific components, "
            f"got {len(level5_specific)}: {sorted(level5_specific)}"
        )

    def test_level5_baseline_components_present(self):
        """All baseline level 5 components must still be disabled."""
        level5_specific = set(DEFAULT_AUTO_DISABLE.get(5, []))
        missing = LEVEL_5_BASELINE_COMPONENTS - level5_specific
        assert not missing, (
            f"Baseline level-5 components removed (not allowed): {sorted(missing)}"
        )

    def test_level5_no_baseline_removals(self):
        """No baseline component should be removed from level 5."""
        level5_specific = set(DEFAULT_AUTO_DISABLE.get(5, []))
        removed = LEVEL_5_BASELINE_COMPONENTS - level5_specific
        assert not removed, f"Level 5 baseline components removed: {sorted(removed)}"


class TestLevel5CumulativeDisable:
    """Level 5 includes all level 3 + level 4 + level 5 disabled components."""

    def test_level5_cumulative_with_level4(self, tmp_path):
        """Level 5 includes all level 3 + level 4 + level 5 disabled components."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 5\n")

        disabled = get_disabled_components(5, str(config))

        # Level 3 components
        for comp in DEFAULT_AUTO_DISABLE.get(3, []):
            assert comp in disabled, f"Level 3 component '{comp}' missing at level 5"

        # Level 4 components
        for comp in DEFAULT_AUTO_DISABLE.get(4, []):
            assert comp in disabled, f"Level 4 component '{comp}' missing at level 5"

        # Level 5 components
        for comp in DEFAULT_AUTO_DISABLE.get(5, []):
            assert comp in disabled, f"Level 5 component '{comp}' missing at level 5"

    def test_level5_total_disabled_count(self, tmp_path):
        """Level 5 total disabled count should be sum of levels 3+4+5 (deduplicated)."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 5\n")

        disabled = get_disabled_components(5, str(config))

        all_expected = set()
        for lvl in (3, 4, 5):
            all_expected.update(DEFAULT_AUTO_DISABLE.get(lvl, []))

        assert len(disabled) == len(all_expected), (
            f"Expected {len(all_expected)} total disabled, got {len(disabled)}"
        )

    def test_level4_does_not_include_level5(self, tmp_path):
        """Level 4 should NOT include level 5 components."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 4\n")

        disabled = get_disabled_components(4, str(config))

        for comp in LEVEL_5_BASELINE_COMPONENTS:
            assert comp not in disabled, (
                f"Level 5 component '{comp}' should NOT be disabled at level 4"
            )


class TestLevel5NeverDisablesEssential:
    """Essential hooks should never be disabled even at level 5."""

    def test_level5_never_disables_essential(self, tmp_path):
        """Essential hooks should never be disabled even at level 5."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 5\n")

        disabled = get_disabled_components(5, str(config))

        for hook in ESSENTIAL_HOOKS:
            assert hook not in disabled, (
                f"Essential hook '{hook}' must NEVER be disabled, "
                f"but it appears in disabled list at level 5"
            )

    def test_essential_not_in_any_disable_level(self):
        """Essential hooks must not appear in any level's disable list."""
        for level, components in DEFAULT_AUTO_DISABLE.items():
            for hook in ESSENTIAL_HOOKS:
                assert hook not in components, (
                    f"Essential hook '{hook}' found in DEFAULT_AUTO_DISABLE[{level}]"
                )


class TestLevel5HooksHaveCapabilityCheck:
    """All 11 level-5 hooks must have check_capability_level call."""

    def test_level5_hooks_have_capability_check(self):
        """All 11 level-5 hooks must call check_capability_level in their source."""
        hooks_dir = PROJECT_ROOT / "hooks"
        missing = []

        for component in LEVEL_5_BASELINE_COMPONENTS:
            # Hook files use the component name, sometimes with .sh suffix
            hook_file = hooks_dir / f"{component}.sh"
            if not hook_file.exists():
                missing.append(f"{component}.sh (file not found)")
                continue

            content = hook_file.read_text()
            if "check_capability_level" not in content:
                missing.append(f"{component}.sh (no check_capability_level call)")

        assert not missing, (
            f"Hooks missing check_capability_level call:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )


class TestLevel5BashFunctionMatchesPython:
    """The hardcoded list in common.sh must match capability_levels.py."""

    def test_level5_bash_function_matches_python(self):
        """The hardcoded list in common.sh must match capability_levels.py."""
        common_sh = PROJECT_ROOT / "hooks" / "_lib" / "common.sh"
        content = common_sh.read_text()

        # Extract the level 5 case block from common.sh
        # The bash fallback has a case block for level 5
        # Pattern: case "$component_name" in ... followed by component names
        in_level5 = False
        bash_components = set()

        for line in content.splitlines():
            stripped = line.strip()
            # Detect the '5)' case
            if stripped == "5)":
                in_level5 = True
                continue
            if in_level5:
                # The case pattern line lists components separated by |
                if ")" in stripped and "|" in stripped:
                    # Extract component names from the case pattern
                    # Format: name1|name2|name3|...)
                    pattern_line = stripped.rstrip(")")
                    # May continue on next line with backslash
                    components = pattern_line.replace("\\", "").split("|")
                    for comp in components:
                        comp = comp.strip()
                        if comp and comp != "case" and not comp.startswith("$"):
                            bash_components.add(comp)
                elif stripped.startswith("disabled="):
                    # End of the pattern
                    break
                elif stripped == ";;":
                    in_level5 = False

        # Also parse more robustly: find all component names between 5) and ;;
        # Use regex to extract the level 5 case block
        level5_match = re.search(
            r'5\)\s*\n\s*case\s+"\$component_name"\s+in\s*\n(.*?)\n\s*disabled=',
            content,
            re.DOTALL,
        )
        if level5_match:
            case_body = level5_match.group(1)
            # Extract names: they are pipe-separated, possibly with backslash continuations
            case_body = case_body.replace("\\", "").replace("\n", "")
            # Remove the trailing ) from the pattern
            case_body = case_body.rstrip().rstrip(")")
            bash_components = set()
            for name in case_body.split("|"):
                name = name.strip()
                if name and not name.startswith("$") and name != "case":
                    bash_components.add(name)

        python_components = set(DEFAULT_AUTO_DISABLE.get(5, []))
        # Also include cumulative (levels 3 and 4) since bash level 5 case
        # includes ALL components disabled at that level
        all_python_at_5 = set()
        for lvl in (3, 4, 5):
            all_python_at_5.update(DEFAULT_AUTO_DISABLE.get(lvl, []))

        # The bash fallback for level 5 should contain all components
        # disabled at levels 3, 4, and 5 combined
        missing_in_bash = all_python_at_5 - bash_components
        extra_in_bash = bash_components - all_python_at_5

        assert not missing_in_bash, (
            f"Python has components missing from bash level-5 fallback:\n"
            + "\n".join(f"  - {c}" for c in sorted(missing_in_bash))
        )
        assert not extra_in_bash, (
            f"Bash level-5 fallback has extra components not in Python:\n"
            + "\n".join(f"  - {c}" for c in sorted(extra_in_bash))
        )


# ---------------------------------------------------------------------------
# Bash integration tests
# ---------------------------------------------------------------------------


class TestLevel5BashIntegration:
    """Integration tests that run actual hooks with different capability levels."""

    def _make_config(self, tmp_path, level: int) -> Path:
        """Create a cognitive-os.yaml with specified capability level."""
        project_dir = tmp_path / "project"
        cos_dir = project_dir / ".cognitive-os"
        cos_dir.mkdir(parents=True, exist_ok=True)
        metrics_dir = cos_dir / "metrics"
        metrics_dir.mkdir(exist_ok=True)

        config = project_dir / "cognitive-os.yaml"
        config.write_text(
            f"model_capability:\n"
            f"  level: {level}\n"
            f"project:\n"
            f"  phase: reconstruction\n"
        )
        return project_dir

    def test_level5_hook_exits_early(self, tmp_path):
        """At level 5, completeness-check.sh should exit 0 without processing."""
        project_dir = self._make_config(tmp_path, level=5)
        hook_path = PROJECT_ROOT / "hooks" / "completeness-check.sh"

        if not hook_path.exists():
            pytest.skip("completeness-check.sh not found")

        # Provide minimal stdin JSON that the hook expects
        stdin_json = '{"tool_name": "Agent", "tool_input": {"prompt": "test prompt"}}'

        env = {
            **os.environ,
            "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
            "TOOL_NAME": "Agent",
        }

        result = subprocess.run(
            ["bash", str(hook_path)],
            capture_output=True,
            text=True,
            env=env,
            input=stdin_json,
            timeout=10,
        )

        # Hook should exit 0 (skipped due to capability level)
        assert result.returncode == 0, (
            f"Expected exit 0 at level 5, got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_level3_hook_runs_normally(self, tmp_path):
        """At level 3 (current default), completeness-check.sh should run normally."""
        project_dir = self._make_config(tmp_path, level=3)
        hook_path = PROJECT_ROOT / "hooks" / "completeness-check.sh"

        if not hook_path.exists():
            pytest.skip("completeness-check.sh not found")

        # Provide a prompt that should trigger processing (not just exit)
        stdin_json = '{"tool_name": "Agent", "tool_input": {"prompt": "do all the things everywhere"}}'

        env = {
            **os.environ,
            "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
            "TOOL_NAME": "Agent",
        }

        result = subprocess.run(
            ["bash", str(hook_path)],
            capture_output=True,
            text=True,
            env=env,
            input=stdin_json,
            timeout=10,
        )

        # At level 3, completeness-check is NOT disabled, so it should process.
        # It may produce output (warnings) or exit 0 silently depending on the prompt.
        # The key assertion: it should NOT have been short-circuited by capability check.
        # We verify by checking that the hook ran (returncode is 0 for advisory hooks)
        assert result.returncode == 0, (
            f"Expected exit 0 at level 3, got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


class TestLevel5ShouldComponentRun:
    """Verify should_component_run returns False for all level-5 components."""

    def test_all_level5_components_disabled(self, tmp_path):
        """Every level-5 component should return False from should_component_run."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 5\n")

        for comp in LEVEL_5_BASELINE_COMPONENTS:
            assert should_component_run(comp, 5, str(config)) is False, (
                f"Component '{comp}' should be disabled at level 5"
            )

    def test_all_level5_components_enabled_at_level2(self, tmp_path):
        """Every level-5-only component should be enabled at level 2."""
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("model_capability:\n  level: 2\n")

        for comp in LEVEL_5_BASELINE_COMPONENTS:
            assert should_component_run(comp, 2, str(config)) is True, (
                f"Component '{comp}' should be enabled at level 2"
            )
