"""Behavior tests for the Simulation Arena scenarios and skill.

Validates that scenario files exist, are valid YAML, have required fields,
and that the simulation-arena skill is properly defined.

Author: luum
"""

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

# Project root — tests run from the repo root.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCENARIOS_DIR = _PROJECT_ROOT / "tests" / "arena" / "scenarios"
_SKILL_DIR = _PROJECT_ROOT / "skills" / "simulation-arena"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    """Load a YAML file, skipping if PyYAML is not installed."""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _scenario_files() -> list:
    """List all YAML scenario files in the scenarios directory."""
    if not _SCENARIOS_DIR.exists():
        return []
    return sorted(_SCENARIOS_DIR.glob("*.yaml"))


# ---------------------------------------------------------------------------
# Test: scenario files exist
# ---------------------------------------------------------------------------

class TestScenarioFilesExist:

    def test_scenarios_dir_exists(self):
        """The tests/arena/scenarios/ directory exists."""
        assert _SCENARIOS_DIR.exists(), f"Missing directory: {_SCENARIOS_DIR}"

    def test_at_least_three_scenarios(self):
        """At least 3 scenario files exist."""
        files = _scenario_files()
        assert len(files) >= 3, (
            f"Expected at least 3 scenario files, found {len(files)}: "
            f"{[f.name for f in files]}"
        )

    def test_scenario_1_feature_exists(self):
        """scenario-1-feature.yaml exists."""
        path = _SCENARIOS_DIR / "scenario-1-feature.yaml"
        assert path.exists(), f"Missing: {path}"

    def test_scenario_2_bugfix_exists(self):
        """scenario-2-bugfix.yaml exists."""
        path = _SCENARIOS_DIR / "scenario-2-bugfix.yaml"
        assert path.exists(), f"Missing: {path}"

    def test_scenario_3_evolution_exists(self):
        """scenario-3-evolution.yaml exists."""
        path = _SCENARIOS_DIR / "scenario-3-evolution.yaml"
        assert path.exists(), f"Missing: {path}"


# ---------------------------------------------------------------------------
# Test: scenario files are valid YAML with required fields
# ---------------------------------------------------------------------------

class TestScenarioValidation:

    @pytest.mark.parametrize(
        "filename",
        ["scenario-1-feature.yaml", "scenario-2-bugfix.yaml", "scenario-3-evolution.yaml"],
    )
    def test_scenario_is_valid_yaml(self, filename):
        """Each scenario file is valid YAML."""
        path = _SCENARIOS_DIR / filename
        if not path.exists():
            pytest.skip(f"File not found: {path}")
        data = _load_yaml(path)
        assert isinstance(data, dict), f"{filename} did not parse as a dict"

    @pytest.mark.parametrize(
        "filename",
        ["scenario-1-feature.yaml", "scenario-2-bugfix.yaml", "scenario-3-evolution.yaml"],
    )
    def test_scenario_has_required_fields(self, filename):
        """Each scenario has name, turns, and expected_total_cost."""
        path = _SCENARIOS_DIR / filename
        if not path.exists():
            pytest.skip(f"File not found: {path}")
        data = _load_yaml(path)

        assert "name" in data, f"{filename} missing 'name'"
        assert "turns" in data, f"{filename} missing 'turns'"
        assert "expected_total_cost" in data, f"{filename} missing 'expected_total_cost'"
        assert isinstance(data["turns"], list), f"{filename} 'turns' is not a list"
        assert len(data["turns"]) > 0, f"{filename} has no turns"

    @pytest.mark.parametrize(
        "filename",
        ["scenario-1-feature.yaml", "scenario-2-bugfix.yaml", "scenario-3-evolution.yaml"],
    )
    def test_scenario_turns_have_type_and_content(self, filename):
        """Every turn in each scenario has 'type' and 'content' fields."""
        path = _SCENARIOS_DIR / filename
        if not path.exists():
            pytest.skip(f"File not found: {path}")
        data = _load_yaml(path)

        valid_types = {"user", "expect", "checkpoint", "delay"}
        for i, turn in enumerate(data["turns"]):
            assert "type" in turn, f"{filename} turn {i} missing 'type'"
            assert "content" in turn, f"{filename} turn {i} missing 'content'"
            assert turn["type"] in valid_types, (
                f"{filename} turn {i} has invalid type '{turn['type']}'"
            )


# ---------------------------------------------------------------------------
# Test: simulation-arena skill exists
# ---------------------------------------------------------------------------

class TestSkillExists:

    def test_skill_directory_exists(self):
        """skills/simulation-arena/ directory exists."""
        assert _SKILL_DIR.exists(), f"Missing: {_SKILL_DIR}"

    def test_skill_md_exists(self):
        """skills/simulation-arena/SKILL.md exists."""
        skill_md = _SKILL_DIR / "SKILL.md"
        assert skill_md.exists(), f"Missing: {skill_md}"

    def test_skill_md_has_frontmatter(self):
        """SKILL.md has YAML frontmatter with name field."""
        skill_md = _SKILL_DIR / "SKILL.md"
        if not skill_md.exists():
            pytest.skip("SKILL.md not found")

        content = skill_md.read_text(encoding="utf-8")
        assert content.startswith("---"), "SKILL.md does not start with YAML frontmatter"
        assert "name: simulation-arena" in content, "Frontmatter missing 'name: simulation-arena'"

    def test_skill_md_has_invoke_section(self):
        """SKILL.md documents the /simulate invocation."""
        skill_md = _SKILL_DIR / "SKILL.md"
        if not skill_md.exists():
            pytest.skip("SKILL.md not found")

        content = skill_md.read_text(encoding="utf-8")
        assert "/simulate" in content, "SKILL.md does not document /simulate invocation"


# ---------------------------------------------------------------------------
# Test: lib module importable
# ---------------------------------------------------------------------------

class TestLibImport:

    def test_simulation_arena_importable(self):
        """lib/simulation_arena.py is importable."""
        from lib.simulation_arena import SimulationArena, Scenario, Turn, TurnType
        assert SimulationArena is not None
        assert Scenario is not None
