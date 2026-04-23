"""Integration tests for generate-project-settings.sh and cos-init.sh settings generation.

Tests that external projects get correct hook paths, self-hosting hooks are
excluded, mode filtering works, and no paths resolve to the COS source.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = PROJECT_ROOT / "scripts" / "generate-project-settings.sh"
COS_INIT = PROJECT_ROOT / "scripts" / "cos-init.sh"
COS_SETTINGS = PROJECT_ROOT / ".claude" / "settings.json"


def run_generator(mode="--standard", harness="claude", env_extra=None):
    """Run generate-project-settings.sh and return parsed JSON."""
    env = os.environ.copy()
    env["COS_SOURCE_DIR"] = str(PROJECT_ROOT)
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        ["bash", str(GENERATOR), mode, f"--harness={harness}"],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, f"Generator failed: {result.stderr}"
    return json.loads(result.stdout)


def extract_hook_commands(settings_json):
    """Extract all hook command strings from a settings dict."""
    commands = []
    for event_name, groups in settings_json.get("hooks", {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                commands.append(hook.get("command", ""))
    return commands


def extract_hook_filenames(settings_json):
    """Extract hook filenames (without path) from settings dict."""
    filenames = []
    for cmd in extract_hook_commands(settings_json):
        # Command format: bash "$CLAUDE_PROJECT_DIR/.../hookname.sh"
        parts = cmd.split("/")
        if parts:
            fname = parts[-1].rstrip('"').rstrip("\\")
            filenames.append(fname)
    return filenames


class TestGenerateProjectSettings:
    """Tests for scripts/generate-project-settings.sh."""

    def test_generator_exists(self):
        assert GENERATOR.exists()

    def test_output_is_valid_json(self):
        settings = run_generator("--standard")
        assert "hooks" in settings

    def test_all_cos_paths_use_cognitive_os_namespace(self):
        """No hook should reference $CLAUDE_PROJECT_DIR/hooks/ (COS source layout)."""
        settings = run_generator("--full")
        for cmd in extract_hook_commands(settings):
            if "CLAUDE_PROJECT_DIR" in cmd:
                assert ".cognitive-os/hooks/cos/" in cmd or ".claude/hooks/" in cmd, (
                    f"Hook uses COS source path: {cmd}"
                )

    def test_codex_projection_uses_codex_runtime_expression(self):
        settings = run_generator("--full", harness="codex")
        commands = extract_hook_commands(settings)
        assert commands, "Expected hook commands for codex projection"
        assert any("CODEX_PROJECT_DIR" in cmd for cmd in commands), commands
        assert all("$CLAUDE_PROJECT_DIR/hooks/" not in cmd for cmd in commands), commands

    def test_self_install_excluded(self):
        """self-install.sh is self-hosting only — must not appear in project settings."""
        for mode in ["--minimal", "--standard", "--full"]:
            filenames = extract_hook_filenames(run_generator(mode))
            assert "self-install.sh" not in filenames, (
                f"self-install.sh found in {mode} mode"
            )

    def test_release_guard_excluded(self):
        """release-guard.sh is self-hosting only — must not appear in project settings."""
        for mode in ["--minimal", "--standard", "--full"]:
            filenames = extract_hook_filenames(run_generator(mode))
            assert "release-guard.sh" not in filenames, (
                f"release-guard.sh found in {mode} mode"
            )

    def test_minimal_mode_is_remapped_to_default(self):
        minimal = set(extract_hook_filenames(run_generator("--minimal")))
        default = set(extract_hook_filenames(run_generator("--default")))
        assert minimal == default, f"Legacy --minimal should match --default: {minimal ^ default}"

    def test_minimal_includes_session_init(self):
        filenames = extract_hook_filenames(run_generator("--minimal"))
        assert "session-init.sh" in filenames

    def test_minimal_includes_session_cleanup(self):
        filenames = extract_hook_filenames(run_generator("--minimal"))
        assert "session-cleanup.sh" in filenames

    def test_standard_includes_quality_gates(self):
        filenames = extract_hook_filenames(run_generator("--standard"))
        for expected in ["clarification-gate.sh", "blast-radius.sh", "error-pattern-detector.sh"]:
            assert expected in filenames, f"{expected} missing from standard mode"

    def test_standard_is_subset_of_full(self):
        standard = set(extract_hook_filenames(run_generator("--standard")))
        full = set(extract_hook_filenames(run_generator("--full")))
        assert standard.issubset(full), f"Standard hooks not in full: {standard - full}"

    def test_minimal_is_same_as_standard_legacy_alias(self):
        minimal = set(extract_hook_filenames(run_generator("--minimal")))
        standard = set(extract_hook_filenames(run_generator("--standard")))
        assert minimal == standard, f"Legacy aliases should resolve to the same curated tier: {minimal ^ standard}"

    def test_full_mode_has_all_source_hooks_except_self_hosting(self):
        """Full mode should include all hooks from source except self-hosting-only."""
        source_settings = json.loads(COS_SETTINGS.read_text())
        source_hooks = set(extract_hook_filenames(source_settings))
        full_hooks = set(extract_hook_filenames(run_generator("--full")))
        self_hosting = {"self-install.sh", "release-guard.sh"}
        expected = source_hooks - self_hosting
        assert expected == full_hooks, (
            f"Missing: {expected - full_hooks}, Extra: {full_hooks - expected}"
        )


class TestCosInitSettingsGeneration:
    """Tests that cos-init.sh generates correct settings.json in projects."""

    def _run_cos_init(self, project_dir, mode="--standard", harness=None):
        """Run cos-init.sh in a directory and return the generated settings."""
        env = os.environ.copy()
        env["COS_SOURCE_DIR"] = str(PROJECT_ROOT)
        # Isolate registry to prevent polluting ~/.cognitive-os/installations.json
        env["COS_REGISTRY_FILE"] = str(project_dir / ".cos-test-registry.json")
        cmd = ["bash", str(COS_INIT), mode]
        if harness:
            cmd.append(f"--harness={harness}")
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, cwd=str(project_dir), env=env,
        )
        settings_path = project_dir / ".claude" / "settings.json"
        if harness == "codex":
            settings_path = project_dir / ".codex" / "hooks.json"
        if settings_path.exists():
            return json.loads(settings_path.read_text()), result
        return None, result

    def test_fresh_project_gets_correct_paths(self, tmp_path):
        """A brand new project (no .claude/) should get settings with COS namespace paths."""
        settings, result = self._run_cos_init(tmp_path, "--standard")
        assert settings is not None, f"No settings generated: {result.stderr}"
        for cmd in extract_hook_commands(settings):
            if "CLAUDE_PROJECT_DIR" in cmd:
                assert ".cognitive-os/hooks/cos/" in cmd or ".claude/hooks/" in cmd, (
                    f"Wrong path in fresh project: {cmd}"
                )

    def test_fresh_project_excludes_self_install(self, tmp_path):
        settings, _ = self._run_cos_init(tmp_path, "--standard")
        filenames = extract_hook_filenames(settings)
        assert "self-install.sh" not in filenames

    def test_existing_project_preserves_custom_hooks(self, tmp_path):
        """Project with existing settings.json should keep its custom hooks."""
        # Create a project with custom settings
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        custom_settings = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {
                                "type": "command",
                                "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/my-custom.sh"'
                            }
                        ]
                    }
                ]
            }
        }
        (claude_dir / "settings.json").write_text(json.dumps(custom_settings))

        settings, _ = self._run_cos_init(tmp_path, "--standard")
        commands = extract_hook_commands(settings)
        custom_found = any("my-custom.sh" in cmd for cmd in commands)
        assert custom_found, f"Custom hook lost after cos-init: {commands}"

    def test_cos_init_does_not_copy_docker_compose(self, tmp_path):
        """cos-init must NOT create docker-compose.cognitive-os.yml in the project."""
        self._run_cos_init(tmp_path, "--standard")
        assert not (tmp_path / "docker-compose.cognitive-os.yml").exists()
        assert not (tmp_path / "docker-compose.yml").exists()

    def test_hook_paths_do_not_resolve_to_cos_source(self, tmp_path):
        """After cos-init, no .cognitive-os path should resolve to COS source via realpath."""
        self._run_cos_init(tmp_path, "--standard")
        cos_dir = tmp_path / ".cognitive-os"
        if cos_dir.exists():
            real = os.path.realpath(str(cos_dir))
            assert str(PROJECT_ROOT) not in real, (
                f".cognitive-os resolves to COS source: {real}"
            )

    def test_settings_is_valid_json_after_init(self, tmp_path):
        settings, _ = self._run_cos_init(tmp_path, "--full")
        assert settings is not None
        # Verify it's re-parseable
        settings_path = tmp_path / ".claude" / "settings.json"
        json.loads(settings_path.read_text())

    def test_codex_harness_writes_hooks_json(self, tmp_path):
        settings, result = self._run_cos_init(tmp_path, "--standard", harness="codex")
        assert settings is not None, f"No codex hooks generated: {result.stderr}"
        hooks_path = tmp_path / ".codex" / "hooks.json"
        assert hooks_path.exists(), "Expected .codex/hooks.json to be created"
        commands = extract_hook_commands(settings)
        assert any("CODEX_PROJECT_DIR" in cmd for cmd in commands), commands

    def test_codex_harness_preserves_existing_codex_hooks(self, tmp_path):
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir()
        custom_settings = {
            "hooks": {
                "Stop": [
                    {
                        "matcher": "shutdown",
                        "hooks": [
                            {
                                "type": "command",
                                "command": 'bash "${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$PWD}}/.codex/hooks/custom-stop.sh"',
                            }
                        ],
                    }
                ]
            }
        }
        (codex_dir / "hooks.json").write_text(json.dumps(custom_settings))

        settings, _ = self._run_cos_init(tmp_path, "--standard", harness="codex")
        commands = extract_hook_commands(settings)
        assert any("custom-stop.sh" in cmd for cmd in commands), commands


class TestSettingsNoLegacyPaths:
    """Tests that generated settings have no legacy or broken paths."""

    def test_no_agent_os_paths(self):
        """No .agent-os paths (legacy pre-rename) should appear."""
        settings = run_generator("--full")
        for cmd in extract_hook_commands(settings):
            assert ".agent-os" not in cmd, f"Legacy .agent-os path: {cmd}"

    def test_no_bare_hooks_path(self):
        """No bare $CLAUDE_PROJECT_DIR/hooks/ path (COS source layout)."""
        settings = run_generator("--standard")
        for cmd in extract_hook_commands(settings):
            if "$CLAUDE_PROJECT_DIR/hooks/" in cmd and ".cognitive-os/hooks/" not in cmd:
                pytest.fail(f"Bare hooks/ path (COS layout): {cmd}")

    def test_all_paths_have_consistent_format(self):
        """All COS hook paths should follow the pattern .cognitive-os/hooks/cos/X.sh."""
        settings = run_generator("--full")
        import re
        cos_pattern = re.compile(r'\.cognitive-os/hooks/cos/[\w-]+\.sh')
        project_pattern = re.compile(r'\.claude/hooks/[\w-]+\.sh')
        for cmd in extract_hook_commands(settings):
            if "CLAUDE_PROJECT_DIR" in cmd:
                assert cos_pattern.search(cmd) or project_pattern.search(cmd), (
                    f"Unexpected path format: {cmd}"
                )
