"""Behavior tests for scripts/apply-efficiency-profile.sh.

Validates:
- invalid profiles fail fast
- legacy profiles are remapped to `default`
- default profile regenerates the committed baseline Claude projection
- full profile is non-destructive
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "apply-efficiency-profile.sh"
SETTINGS_FILE = PROJECT_ROOT / ".claude" / "settings.json"

pytestmark = pytest.mark.behavior


def _run_profile(profile: str, project_dir: Path) -> subprocess.CompletedProcess:
    """Run apply-efficiency-profile.sh with the given profile in a project dir."""
    return subprocess.run(
        ["bash", str(SCRIPT), profile],
        capture_output=True,
        text=True,
        cwd=str(project_dir),
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(Path.home())},
        timeout=30,
    )


def _load_settings(path: Path) -> dict:
    """Load a settings.json file as a dictionary."""
    return json.loads(path.read_text())


def _session_start_commands(settings: dict) -> list[str]:
    commands: list[str] = []
    for group in settings.get("hooks", {}).get("SessionStart", []):
        for hook in group.get("hooks", []):
            commands.append(hook.get("command", ""))
    return commands


def _make_profile_workspace(tmp_path: Path) -> Path:
    """Create a minimal project directory where the profile script can run."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    src_yaml = PROJECT_ROOT / "cognitive-os.yaml"
    if src_yaml.exists():
        shutil.copy(src_yaml, workspace / "cognitive-os.yaml")
    (workspace / ".claude").mkdir(exist_ok=True)
    return workspace


class TestScriptExists:
    def test_script_is_valid_bash(self):
        result = subprocess.run(
            ["bash", "-n", str(SCRIPT)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Bash syntax error: {result.stderr}"


class TestInvalidProfile:
    def test_invalid_profile_exits_nonzero(self, tmp_path):
        result = _run_profile("ultramax", tmp_path)
        assert result.returncode != 0, "Invalid profile should exit non-zero"

    def test_invalid_profile_prints_error(self, tmp_path):
        result = _run_profile("badprofile", tmp_path)
        combined = result.stdout + result.stderr
        assert "ERROR" in combined or "Unknown" in combined or "Invalid" in combined


class TestDefaultProfile:
    @pytest.fixture
    def generated_settings(self, tmp_path) -> Path:
        workspace = _make_profile_workspace(tmp_path)
        result = _run_profile("default", workspace)
        assert result.returncode == 0, result.stderr
        settings_path = workspace / ".claude" / "settings.json"
        assert settings_path.exists(), "default profile should create settings.json"
        return settings_path

    def test_default_matches_committed_baseline(self, generated_settings):
        generated = _load_settings(generated_settings)
        assert generated == _load_settings(SETTINGS_FILE)

    def test_default_contains_current_projection_surfaces(self, generated_settings):
        settings = _load_settings(generated_settings)["hooks"]
        assert "SubagentStart" in settings
        assert any(
            hook["command"].endswith("infra-health.sh\"") and hook.get("async") is True
            for hook in settings["SessionStart"][0]["hooks"]
        )
        assert any(
            hook["command"].endswith("skill-usage-tracker.sh\"") and hook.get("async") is True
            for group in settings["PostToolUse"]
            for hook in group["hooks"]
        )


class TestLegacyProfiles:
    @pytest.mark.parametrize("profile", ["lean", "standard", "minimal"])
    def test_legacy_profiles_remap_to_default(self, tmp_path, profile):
        workspace = _make_profile_workspace(tmp_path / profile)
        result = _run_profile(profile, workspace)
        assert result.returncode == 0, result.stderr
        combined = result.stdout + result.stderr
        assert "collapsed" in combined.lower()
        assert _load_settings(workspace / ".claude" / "settings.json") == _load_settings(SETTINGS_FILE)


class TestFullProfile:
    def test_full_exits_zero(self):
        result = _run_profile("full", PROJECT_ROOT)
        assert result.returncode == 0, f"full profile exited {result.returncode}: {result.stderr}"

    def test_full_prints_hook_count(self):
        result = _run_profile("full", PROJECT_ROOT)
        combined = result.stdout + result.stderr
        assert "hook" in combined.lower() or "command" in combined.lower()

    def test_full_does_not_overwrite_settings_in_real_project(self):
        if not SETTINGS_FILE.exists():
            pytest.skip("No settings.json in real project")

        original_content = SETTINGS_FILE.read_text()
        result = _run_profile("full", PROJECT_ROOT)
        assert result.returncode == 0, result.stderr
        assert SETTINGS_FILE.read_text() == original_content

    def test_full_mentions_profile_name(self):
        result = _run_profile("full", PROJECT_ROOT)
        combined = result.stdout + result.stderr
        assert "full" in combined.lower()


class TestCoreProfile:
    def test_core_profile_reduces_session_start_hooks(self, tmp_path):
        workspace = _make_profile_workspace(tmp_path / "core")
        result = _run_profile("core", workspace)
        assert result.returncode == 0, result.stderr
        settings = _load_settings(workspace / ".claude" / "settings.json")
        commands = _session_start_commands(settings)
        assert len(commands) == 4
        assert any("session-init.sh" in command for command in commands)
        assert any("cross-session-event-emit.sh" in command for command in commands)
        assert any("validation-lock-cleanup.sh" in command for command in commands)
        assert any("session-start-stash-reapply.sh" in command for command in commands)
        assert not any("host-tool-doctor.sh" in command for command in commands)

    def test_maintainer_profile_matches_default_baseline(self, tmp_path):
        workspace = _make_profile_workspace(tmp_path / "maintainer")
        result = _run_profile("maintainer", workspace)
        assert result.returncode == 0, result.stderr
        assert _load_settings(workspace / ".claude" / "settings.json") == _load_settings(SETTINGS_FILE)
