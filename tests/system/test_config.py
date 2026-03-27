"""System tests for configuration validation.

Verifies cognitive-os.yaml, squad YAMLs, and customization YAMLs parse correctly.
Migrated from tests/infra/test-config.sh.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

try:
    import yaml as _yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def _load_yaml(filepath: Path):
    """Load and validate a YAML file, returning None on error."""
    if not HAS_YAML:
        pytest.skip("PyYAML not installed")
    with open(filepath) as f:
        return _yaml.safe_load(f)


def _get_yaml_field(data, dotpath: str):
    """Traverse a dict by dot-separated key path."""
    keys = dotpath.split(".")
    val = data
    for key in keys:
        if val is None or not isinstance(val, dict):
            return None
        val = val.get(key)
    return val


@pytest.fixture(scope="module")
def project_root():
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module")
def aos_dir(project_root):
    return project_root / ".cognitive-os"


@pytest.fixture(scope="module")
def config_data(project_root):
    config = project_root / "cognitive-os.yaml"
    if not config.exists():
        pytest.skip("cognitive-os.yaml not found")
    return _load_yaml(config)


@pytest.mark.system
class TestCognitiveOsConfig:
    """Tests for the main cognitive-os.yaml configuration."""

    def test_config_is_valid_yaml(self, project_root):
        config = project_root / "cognitive-os.yaml"
        if not config.exists():
            pytest.fail("cognitive-os.yaml not found")
        data = _load_yaml(config)
        assert data is not None, "cognitive-os.yaml should be valid YAML"

    def test_project_phase_exists(self, config_data):
        val = _get_yaml_field(config_data, "project.phase")
        assert val is not None, "project.phase should exist"

    def test_budget_exists(self, config_data):
        val = _get_yaml_field(config_data, "resources.budget.monthly_limit_usd")
        assert val is not None, "resources.budget.monthly_limit_usd should exist"

    def test_skills_loading_exists(self, config_data):
        val = _get_yaml_field(config_data, "skills.loading.strategy")
        assert val is not None, "skills.loading.strategy should exist"

    def test_project_name_exists(self, config_data):
        val = _get_yaml_field(config_data, "project.name")
        # This is a warning-level check -- just log if missing
        if val is None:
            pytest.skip("project.name is optional")

    def test_memory_provider_exists(self, config_data):
        val = _get_yaml_field(config_data, "memory.provider")
        if val is None:
            pytest.skip("memory.provider is optional")


@pytest.mark.system
class TestSquadYamls:
    """Tests that squad YAML files parse correctly."""

    def test_squad_yamls_valid(self, aos_dir):
        squads_dir = aos_dir / "squads"
        if not squads_dir.is_dir():
            pytest.skip("No squads directory found")

        files = list(squads_dir.glob("*.yaml")) + list(squads_dir.glob("*.yml"))
        if not files:
            pytest.skip("No squad YAML files found")

        for squad_file in files:
            data = _load_yaml(squad_file)
            assert data is not None, f"Squad {squad_file.name} should be valid YAML"


@pytest.mark.system
class TestCustomizationYamls:
    """Tests that customization YAML files parse correctly."""

    def test_customization_yamls_valid(self, aos_dir):
        custom_dir = aos_dir / "customizations"
        if not custom_dir.is_dir():
            pytest.skip("No customizations directory found")

        files = list(custom_dir.glob("*.yaml")) + list(custom_dir.glob("*.yml"))
        if not files:
            pytest.skip("No customization YAML files found")

        for custom_file in files:
            data = _load_yaml(custom_file)
            assert data is not None, f"Customization {custom_file.name} should be valid YAML"


@pytest.mark.system
class TestSessionConcurrency:
    """Tests for session directory and active-sessions.json."""

    def test_sessions_directory(self, aos_dir):
        sessions_dir = aos_dir / "sessions"
        if not sessions_dir.is_dir():
            pytest.skip("sessions/ not yet created (will be on first session)")

    def test_active_sessions_valid_json(self, aos_dir):
        active = aos_dir / "sessions" / "active-sessions.json"
        if not active.exists():
            pytest.skip("active-sessions.json not yet created")
        data = json.loads(active.read_text())
        assert isinstance(data, dict), "active-sessions.json should be a JSON object"

    def test_no_stale_locks(self, aos_dir):
        locks_dir = aos_dir / "sessions" / "locks"
        if not locks_dir.is_dir():
            pytest.skip("locks directory not found")

        stale = 0
        for lf in locks_dir.glob("*.lock"):
            try:
                data = json.loads(lf.read_text())
                pid = data.get("pid", 0)
                if pid > 0:
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        stale += 1
            except Exception:
                continue
        assert stale == 0, f"{stale} stale lock(s) found"

    def test_sessions_concurrency_configured(self, config_data):
        if config_data is None:
            pytest.skip("config not loaded")
        val = _get_yaml_field(config_data, "sessions.concurrency")
        if val is None:
            pytest.skip("sessions.concurrency not configured")
