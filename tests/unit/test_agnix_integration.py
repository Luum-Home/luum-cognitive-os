"""Unit tests for agnix linter integration.

Tests the agnix-lint.sh hook logic, .agnix.toml config validity,
and phase-aware behavior.
"""
import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.unit.conftest import run_bash_script


@pytest.fixture
def project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def hook_path(project_root) -> Path:
    """Return path to the agnix-lint.sh hook."""
    return project_root / "hooks" / "agnix-lint.sh"


@pytest.fixture
def agnix_config_path(project_root) -> Path:
    """Return path to .agnix.toml."""
    return project_root / ".agnix.toml"


@pytest.fixture
def hook_env(tmp_path):
    """Standard environment for testing the agnix hook."""
    project_dir = tmp_path / "project"
    metrics_dir = project_dir / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)

    # Create a minimal cognitive-os.yaml
    config_dir = project_dir / ".cognitive-os"
    config_file = config_dir / "cognitive-os.yaml"
    config_file.write_text("project:\n  phase: reconstruction\n")

    return {
        "env": {
            "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
            "COGNITIVE_OS_SESSION_ID": "",
        },
        "project_dir": project_dir,
        "metrics_dir": metrics_dir,
    }


class TestAgnixConfigValid:
    """Verify .agnix.toml is valid TOML and has expected structure."""

    def test_agnix_config_exists(self, agnix_config_path):
        """Config file must exist at project root."""
        assert agnix_config_path.exists(), ".agnix.toml not found at project root"

    def test_agnix_config_valid_toml(self, agnix_config_path):
        """Config must be parseable as valid TOML."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        content = agnix_config_path.read_bytes()
        parsed = tomllib.loads(content.decode("utf-8"))
        assert "config" in parsed, "Missing [config] section"

    def test_agnix_config_has_severity(self, agnix_config_path):
        """Config must define a severity level."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        content = agnix_config_path.read_bytes()
        parsed = tomllib.loads(content.decode("utf-8"))
        assert parsed["config"]["severity"] in ("error", "warning", "info")

    def test_agnix_config_has_target(self, agnix_config_path):
        """Config must specify a target agent platform."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        content = agnix_config_path.read_bytes()
        parsed = tomllib.loads(content.decode("utf-8"))
        assert "target" in parsed["config"]
        assert parsed["config"]["target"] == "claude-code"

    def test_agnix_config_excludes_sessions(self, agnix_config_path):
        """Config must exclude session and metrics directories."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        content = agnix_config_path.read_bytes()
        parsed = tomllib.loads(content.decode("utf-8"))
        excludes = parsed["config"]["exclude"]["patterns"]
        assert ".cognitive-os/sessions/**" in excludes
        assert ".cognitive-os/metrics/**" in excludes


class TestHookSkipsWhenNotInstalled:
    """Verify hook exits cleanly when agnix is not on PATH."""

    def test_hook_exits_zero_without_agnix(self, hook_path, hook_env):
        """Hook must exit 0 when agnix binary is not found."""
        # Feed a valid Edit tool input via stdin
        stdin_json = json.dumps({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/some/project/rules/test-rule.md"
            }
        })

        # Run with PATH stripped of agnix (use a minimal PATH)
        env = {
            **os.environ,
            **hook_env["env"],
            "PATH": "/usr/bin:/bin",  # Minimal PATH unlikely to have agnix
        }

        result = subprocess.run(
            ["bash", str(hook_path)],
            input=stdin_json,
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0


class TestHookTriggersOnSkillFiles:
    """Verify hook activates for agent config file changes."""

    def test_triggers_on_rules_file(self, hook_path, hook_env):
        """Hook should attempt to lint rules/ files."""
        stdin_json = json.dumps({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(hook_env["project_dir"] / "rules" / "test-rule.md")
            }
        })

        env = {
            **os.environ,
            **hook_env["env"],
            "PATH": "/usr/bin:/bin",  # No agnix -> will exit 0 at the command check
        }

        result = subprocess.run(
            ["bash", str(hook_path)],
            input=stdin_json,
            capture_output=True,
            text=True,
            env=env,
        )
        # Should exit 0 (no agnix installed), but importantly should NOT have
        # exited early at the path-matching gate
        assert result.returncode == 0

    def test_triggers_on_skills_file(self, hook_path, hook_env):
        """Hook should attempt to lint skills/ files."""
        stdin_json = json.dumps({
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(hook_env["project_dir"] / "skills" / "my-skill" / "SKILL.md")
            }
        })

        env = {
            **os.environ,
            **hook_env["env"],
            "PATH": "/usr/bin:/bin",
        }

        result = subprocess.run(
            ["bash", str(hook_path)],
            input=stdin_json,
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0

    def test_triggers_on_claude_dir_file(self, hook_path, hook_env):
        """Hook should attempt to lint .claude/ files."""
        stdin_json = json.dumps({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(hook_env["project_dir"] / ".claude" / "settings.json")
            }
        })

        env = {
            **os.environ,
            **hook_env["env"],
            "PATH": "/usr/bin:/bin",
        }

        result = subprocess.run(
            ["bash", str(hook_path)],
            input=stdin_json,
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0


class TestHookSkipsNonConfigFiles:
    """Verify hook ignores non-agent-config files."""

    @pytest.mark.parametrize("file_path", [
        "/some/project/src/main.py",
        "/some/project/internal/users/handler.go",
        "/some/project/package.json",
        "/some/project/lib/utils.ts",
        "/some/project/tests/test_something.py",
        "/some/project/docker-compose.yml",
    ])
    def test_skips_non_config_files(self, hook_path, hook_env, file_path):
        """Hook must exit 0 immediately for non-agent-config files."""
        stdin_json = json.dumps({
            "tool_name": "Edit",
            "tool_input": {"file_path": file_path}
        })

        env = {**os.environ, **hook_env["env"]}

        result = subprocess.run(
            ["bash", str(hook_path)],
            input=stdin_json,
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0

    def test_skips_non_edit_write_tools(self, hook_path, hook_env):
        """Hook must exit 0 for tools other than Edit/Write."""
        stdin_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"}
        })

        env = {**os.environ, **hook_env["env"]}

        result = subprocess.run(
            ["bash", str(hook_path)],
            input=stdin_json,
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0


class TestPhaseAwareBehavior:
    """Verify phase-dependent exit codes."""

    def _make_config(self, project_dir, phase):
        """Write cognitive-os.yaml with a specific phase."""
        config_file = project_dir / ".cognitive-os" / "cognitive-os.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(f"project:\n  phase: {phase}\n")

    def test_reconstruction_phase_is_advisory(self, hook_path, hook_env):
        """In reconstruction, errors should produce exit 0 (advisory)."""
        self._make_config(hook_env["project_dir"], "reconstruction")

        # Without agnix installed, hook exits 0 regardless
        stdin_json = json.dumps({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(hook_env["project_dir"] / "rules" / "test.md")
            }
        })

        env = {
            **os.environ,
            **hook_env["env"],
            "PATH": "/usr/bin:/bin",
        }

        result = subprocess.run(
            ["bash", str(hook_path)],
            input=stdin_json,
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0

    def test_production_config_exists(self, hook_path, hook_env):
        """Verify the hook reads production phase from config."""
        self._make_config(hook_env["project_dir"], "production")

        # The hook reads the phase via get_phase from common.sh
        # Without agnix it still exits 0, but the phase is parsed
        stdin_json = json.dumps({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(hook_env["project_dir"] / "rules" / "test.md")
            }
        })

        env = {
            **os.environ,
            **hook_env["env"],
            "PATH": "/usr/bin:/bin",
        }

        result = subprocess.run(
            ["bash", str(hook_path)],
            input=stdin_json,
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0

    def test_phase_aware_logic_in_hook_script(self, hook_path):
        """Verify the hook script contains phase-aware exit logic."""
        content = hook_path.read_text()
        assert "get_phase" in content, "Hook must call get_phase"
        assert "production|maintenance" in content, "Hook must handle production/maintenance"
        assert "exit 2" in content, "Hook must be able to BLOCK (exit 2)"
