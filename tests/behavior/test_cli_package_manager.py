"""Behavior tests for the CLI package manager subcommands.

Tests the 6 new CLI subcommands: sources, search, install, uninstall, list, update.
Also covers version and help output for completeness.

Related script: bin/cognitive-os.sh
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLI_PATH = PROJECT_ROOT / "bin" / "cognitive-os.sh"


def _run_cli(
    *args: str,
    cwd: Optional[str] = None,
    timeout: int = 10,
    env_overrides: Optional[Dict[str, str]] = None,
    input_text: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """Run the cognitive-os CLI with given arguments."""
    run_env = os.environ.copy()
    if env_overrides:
        run_env.update(env_overrides)
    return subprocess.run(
        ["bash", str(CLI_PATH), *args],
        capture_output=True,
        text=True,
        input=input_text,
        cwd=cwd or str(PROJECT_ROOT),
        timeout=timeout,
        env=run_env,
    )


def _setup_minimal_project(tmp_path: Path) -> Path:
    """Create a minimal project directory with cognitive-os.yaml and .cognitive-os/."""
    project = tmp_path / "project"
    project.mkdir()

    # Copy cognitive-os.yaml from the real project
    shutil.copy(PROJECT_ROOT / "cognitive-os.yaml", project / "cognitive-os.yaml")

    # Create .cognitive-os structure with some components
    cos_dir = project / ".cognitive-os"
    cos_dir.mkdir()

    # Rules
    rules_dir = cos_dir / "rules"
    rules_dir.mkdir()
    (rules_dir / "test-rule.md").write_text("# Test Rule\n")
    (rules_dir / "another-rule.md").write_text("# Another Rule\n")
    canonical_rules_dir = rules_dir / "cos"
    canonical_rules_dir.mkdir()
    (canonical_rules_dir / "test-rule.md").write_text("# Test Rule Canonical\n")
    (canonical_rules_dir / "another-rule.md").write_text("# Another Rule Canonical\n")

    # Skills
    skill_dir = cos_dir / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Test Skill\n")
    canonical_skill_dir = cos_dir / "skills" / "cos" / "test-skill"
    canonical_skill_dir.mkdir(parents=True)
    (canonical_skill_dir / "SKILL.md").write_text("# Test Skill Canonical\n")

    # Hooks
    hooks_dir = cos_dir / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "test-hook.sh").write_text("#!/usr/bin/env bash\nexit 0\n")

    # .claude directories for install targets
    claude_dir = project / ".claude"
    claude_dir.mkdir()
    (claude_dir / "rules").mkdir()
    (claude_dir / "skills").mkdir()

    # Presets directory
    presets_dir = project / "presets"
    presets_dir.mkdir()
    (presets_dir / "lean.yaml").write_text(
        'name: lean\ndescription: "Minimal preset"\nefficiency_profile: lean\ncapability_level: 4\n'
    )
    (presets_dir / "standard.yaml").write_text(
        'name: standard\ndescription: "Standard preset"\nefficiency_profile: standard\ncapability_level: 3\n'
    )
    (presets_dir / "fintech.yaml").write_text(
        'name: fintech\ndescription: "Fintech preset with extra compliance"\nefficiency_profile: fintech\ncapability_level: 2\n'
    )

    # Init git repo so hooks that rely on git work
    subprocess.run(["git", "init", "-q"], cwd=str(project), capture_output=True)

    return project


# ── Sources ───────────────────────────────────────────────────────────


class TestCLISources:
    """Tests for 'cos sources' subcommand."""

    def test_sources_lists_registries(self):
        """'cos sources' should list all configured registries."""
        result = _run_cli("sources")
        assert result.returncode == 0
        assert "cos-builtin" in result.stdout
        assert "skills-sh" in result.stdout
        assert "mcp-registry" in result.stdout

    def test_sources_shows_disabled(self):
        """Disabled sources should be marked as disabled."""
        result = _run_cli("sources")
        assert result.returncode == 0
        # skillsmp is disabled in the default config
        assert "skillsmp" in result.stdout
        assert "disabled" in result.stdout

    def test_sources_shows_header(self):
        """'cos sources' should show a header."""
        result = _run_cli("sources")
        assert result.returncode == 0
        assert "Configured Package Sources" in result.stdout

    def test_sources_requires_config(self, tmp_path):
        """'cos sources' should fail if cognitive-os.yaml is missing."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = _run_cli("sources", cwd=str(empty_dir))
        assert result.returncode != 0
        assert "cognitive-os.yaml" in result.stderr

    def test_sources_add_missing_args(self):
        """'cos sources add' without arguments should fail."""
        result = _run_cli("sources", "add")
        assert result.returncode != 0
        assert "Usage" in result.stderr


# ── List ──────────────────────────────────────────────────────────────


class TestCLIList:
    """Tests for 'cos list' subcommand."""

    def test_list_skills(self, tmp_path):
        """'cos list skills' should show installed skills."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("list", "skills", cwd=str(project))
        assert result.returncode == 0
        assert "Installed Skills" in result.stdout

    def test_list_rules(self, tmp_path):
        """'cos list rules' should show installed rules."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("list", "rules", cwd=str(project))
        assert result.returncode == 0
        assert "Installed Rules" in result.stdout

    def test_list_skills_uses_canonical_surface_when_driver_missing(self, tmp_path):
        """'cos list skills' should still work from canonical artifacts without .claude projection."""
        project = _setup_minimal_project(tmp_path)
        shutil.rmtree(project / ".claude" / "skills")

        result = _run_cli("list", "skills", cwd=str(project))

        assert result.returncode == 0
        assert "test-skill" in result.stdout
        assert "(canonical: .cognitive-os/skills/cos/)" in result.stdout

    def test_list_rules_uses_canonical_surface_when_driver_missing(self, tmp_path):
        """'cos list rules' should still work from canonical artifacts without .claude projection."""
        project = _setup_minimal_project(tmp_path)
        shutil.rmtree(project / ".claude" / "rules")

        result = _run_cli("list", "rules", cwd=str(project))

        assert result.returncode == 0
        assert "test-rule" in result.stdout
        assert "(canonical: .cognitive-os/rules/cos/)" in result.stdout

    def test_list_hooks(self, tmp_path):
        """'cos list hooks' should show installed hooks."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("list", "hooks", cwd=str(project))
        assert result.returncode == 0
        assert "Installed Hooks" in result.stdout

    def test_list_presets(self, tmp_path):
        """'cos list presets' should show available presets."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("list", "presets", cwd=str(project))
        assert result.returncode == 0
        assert "Available Presets" in result.stdout
        assert "lean" in result.stdout
        assert "standard" in result.stdout
        assert "fintech" in result.stdout

    def test_list_all(self, tmp_path):
        """'cos list' with no type should show all categories."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("list", cwd=str(project))
        assert result.returncode == 0
        assert "Installed Skills" in result.stdout
        assert "Installed Rules" in result.stdout
        assert "Installed Hooks" in result.stdout
        assert "Available Presets" in result.stdout

    def test_list_unknown_type_fails(self, tmp_path):
        """'cos list badtype' should fail with an error."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("list", "badtype", cwd=str(project))
        assert result.returncode != 0
        assert "Unknown type" in result.stderr

    def test_list_requires_config(self, tmp_path):
        """'cos list' should fail without cognitive-os.yaml."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = _run_cli("list", cwd=str(empty_dir))
        assert result.returncode != 0


# ── Search ────────────────────────────────────────────────────────────


class TestCLISearch:
    """Tests for 'cos search' subcommand."""

    def test_search_shows_header(self, tmp_path):
        """'cos search' should show a search header with the query."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("search", "test-skill", cwd=str(project))
        assert result.returncode == 0
        assert "Searching for" in result.stdout
        assert "test-skill" in result.stdout

    def test_search_finds_local_skill(self, tmp_path):
        """'cos search' should find skills in local sources."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("search", "test-skill", cwd=str(project))
        assert result.returncode == 0
        # Should find the test-skill in cos-builtin local source
        assert "test-skill" in result.stdout

    def test_search_no_results(self, tmp_path):
        """'cos search' with gibberish should not find any matching components."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("search", "xyzzy12345nonexistent", cwd=str(project))
        assert result.returncode == 0
        # Should not contain any "skill:" or "rule:" or "hook:" result lines
        assert "skill:" not in result.stdout
        assert "rule:" not in result.stdout
        assert "hook:" not in result.stdout

    def test_search_missing_query_fails(self):
        """'cos search' without a query should fail."""
        result = _run_cli("search")
        assert result.returncode != 0
        assert "Usage" in result.stderr

    def test_search_requires_config(self, tmp_path):
        """'cos search' should fail without cognitive-os.yaml."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = _run_cli("search", "foo", cwd=str(empty_dir))
        assert result.returncode != 0


# ── Install ───────────────────────────────────────────────────────────


class TestCLIInstall:
    """Tests for 'cos install' subcommand."""

    def test_install_missing_args_fails(self):
        """'cos install' without arguments should fail."""
        result = _run_cli("install")
        assert result.returncode != 0
        assert "Usage" in result.stderr

    def test_install_unknown_type_fails(self, tmp_path):
        """'cos install badtype foo' should fail gracefully."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("install", "badtype", "foo", cwd=str(project))
        assert result.returncode != 0
        assert "Unknown component type" in result.stderr

    def test_install_skill_from_local(self, tmp_path):
        """'cos install skill' should install from .cognitive-os/skills/."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("install", "skill", "test-skill", cwd=str(project))
        assert result.returncode == 0
        assert "Installed skill" in result.stdout
        # Verify the skill was actually copied
        installed = project / ".claude" / "skills" / "test-skill" / "SKILL.md"
        assert installed.exists()

    def test_install_rule_from_local(self, tmp_path):
        """'cos install rule' should install from .cognitive-os/rules/."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("install", "rule", "test-rule", cwd=str(project))
        assert result.returncode == 0
        assert "Installed rule" in result.stdout
        installed = project / ".claude" / "rules" / "test-rule.md"
        assert installed.exists()

    def test_install_skill_reads_canonical_surface_first(self, tmp_path):
        """'cos install skill' should accept the canonical .cognitive-os/skills/cos layout."""
        project = _setup_minimal_project(tmp_path)
        shutil.rmtree(project / ".cognitive-os" / "skills" / "test-skill")
        result = _run_cli("install", "skill", "test-skill", cwd=str(project))
        assert result.returncode == 0
        assert (project / ".claude" / "skills" / "test-skill" / "SKILL.md").exists()

    def test_install_rule_reads_canonical_surface_first(self, tmp_path):
        """'cos install rule' should accept the canonical .cognitive-os/rules/cos layout."""
        project = _setup_minimal_project(tmp_path)
        (project / ".cognitive-os" / "rules" / "test-rule.md").unlink()
        result = _run_cli("install", "rule", "test-rule", cwd=str(project))
        assert result.returncode == 0
        assert (project / ".claude" / "rules" / "test-rule.md").exists()

    def test_install_rule_not_found(self, tmp_path):
        """'cos install rule nonexistent' should fail."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("install", "rule", "nonexistent-rule", cwd=str(project))
        assert result.returncode != 0
        assert "not found" in result.stderr

    def test_install_hook_shows_info(self, tmp_path):
        """'cos install hook' should explain that hooks are registered, not copied."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("install", "hook", "test-hook", cwd=str(project))
        assert result.returncode == 0
        assert "settings.json" in result.stdout

    def test_install_hook_not_found(self, tmp_path):
        """'cos install hook nonexistent' should fail."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("install", "hook", "nonexistent-hook", cwd=str(project))
        assert result.returncode != 0

    def test_install_preset_shows_info(self, tmp_path):
        """'cos install preset' should show preset info and attempt to apply it."""
        project = _setup_minimal_project(tmp_path)
        # Create a preset with all fields populated (efficiency_profile,
        # capability_level) so grep doesn't fail under pipefail.
        # Also provide the apply-efficiency-profile.sh script as a no-op
        # so the preset can complete successfully.
        full_preset = project / "presets" / "testpreset.yaml"
        full_preset.write_text(
            "name: testpreset\n"
            'description: "Test preset"\n'
            "efficiency_profile: lean\n"
            "capability_level: 3\n"
        )
        scripts_dir = project / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        apply_script = scripts_dir / "apply-efficiency-profile.sh"
        apply_script.write_text("#!/usr/bin/env bash\necho \"Applied profile: $1\"\n")
        apply_script.chmod(0o755)

        result = _run_cli("install", "preset", "testpreset", cwd=str(project))
        assert result.returncode == 0
        assert "Installing preset: testpreset" in result.stdout
        assert "Preset 'testpreset' applied" in result.stdout

    def test_install_preset_not_found(self, tmp_path):
        """'cos install preset nonexistent' should fail."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("install", "preset", "nonexistent", cwd=str(project))
        assert result.returncode != 0
        assert "not found" in result.stderr

    def test_install_mcp_server_stub(self, tmp_path):
        """'cos install mcp-server' should search the MCP registry."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("install", "mcp-server", "some-server", cwd=str(project))
        # The command searches the MCP registry; if not found, exits 1
        combined = result.stdout + result.stderr
        assert "MCP" in combined or "Searching" in combined or "registry" in combined.lower()


# ── Uninstall ─────────────────────────────────────────────────────────


class TestCLIUninstall:
    """Tests for 'cos uninstall' subcommand."""

    def test_uninstall_missing_args_fails(self):
        """'cos uninstall' without arguments should fail."""
        result = _run_cli("uninstall")
        assert result.returncode != 0
        assert "Usage" in result.stderr

    def test_uninstall_unknown_type_fails(self, tmp_path):
        """'cos uninstall badtype foo' should fail."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("uninstall", "badtype", "foo", cwd=str(project))
        assert result.returncode != 0

    def test_uninstall_skill_not_installed(self, tmp_path):
        """'cos uninstall skill nonexistent' should report not installed."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("uninstall", "skill", "nonexistent", cwd=str(project))
        assert result.returncode != 0
        assert "not installed" in result.stderr

    def test_uninstall_rule_not_installed(self, tmp_path):
        """'cos uninstall rule nonexistent' should report not installed."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("uninstall", "rule", "nonexistent", cwd=str(project))
        assert result.returncode != 0
        assert "not installed" in result.stderr

    def test_uninstall_hook_not_supported(self, tmp_path):
        """'cos uninstall hook' should explain hooks are managed via settings.json."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("uninstall", "hook", "some-hook", cwd=str(project))
        assert result.returncode != 0
        assert "settings.json" in result.stderr

    def test_uninstall_preset_not_supported(self, tmp_path):
        """'cos uninstall preset' should explain presets cannot be uninstalled."""
        project = _setup_minimal_project(tmp_path)
        result = _run_cli("uninstall", "preset", "lean", cwd=str(project))
        assert result.returncode != 0
        assert "cannot be" in result.stderr

    def test_uninstall_skill_removes_canonical_and_driver_surfaces(self, tmp_path):
        project = _setup_minimal_project(tmp_path)
        driver_skill = project / ".claude" / "skills" / "test-skill"
        driver_skill.mkdir(parents=True)
        (driver_skill / "SKILL.md").write_text("# Driver Skill\n")

        result = _run_cli(
            "uninstall",
            "skill",
            "test-skill",
            cwd=str(project),
            input_text="y\n",
        )
        assert result.returncode == 0
        assert not (project / ".cognitive-os" / "skills" / "cos" / "test-skill").exists()
        assert not driver_skill.exists()

    def test_uninstall_rule_removes_canonical_and_driver_surfaces(self, tmp_path):
        project = _setup_minimal_project(tmp_path)
        driver_rule = project / ".claude" / "rules" / "test-rule.md"
        driver_rule.write_text("# Driver Rule\n")

        result = _run_cli(
            "uninstall",
            "rule",
            "test-rule",
            cwd=str(project),
            input_text="y\n",
        )
        assert result.returncode == 0
        assert not (project / ".cognitive-os" / "rules" / "cos" / "test-rule.md").exists()
        assert not driver_rule.exists()


# ── Update ────────────────────────────────────────────────────────────


class TestCLIUpdate:
    """Tests for 'cos update' subcommand."""

    def test_update_runs_cleanly(self):
        """'cos update' should complete without errors."""
        result = _run_cli("update")
        assert result.returncode == 0
        assert "Updating Source Indexes" in result.stdout
        assert "Done" in result.stdout

    def test_update_lists_sources(self):
        """'cos update' should mention each source."""
        result = _run_cli("update")
        assert result.returncode == 0
        assert "cos-builtin" in result.stdout

    def test_update_skips_disabled(self):
        """'cos update' should skip disabled sources."""
        result = _run_cli("update")
        assert result.returncode == 0
        assert "skipped" in result.stdout.lower() or "disabled" in result.stdout.lower()

    def test_update_requires_config(self, tmp_path):
        """'cos update' should fail without cognitive-os.yaml."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = _run_cli("update", cwd=str(empty_dir))
        assert result.returncode != 0


# ── Version ───────────────────────────────────────────────────────────


class TestCLIVersion:
    """Tests for 'cos version' subcommand."""

    def test_version_output(self):
        """'cos version' should show version number."""
        result = _run_cli("version")
        assert result.returncode == 0
        assert "cognitive-os v" in result.stdout
        # Should contain a semver-like pattern
        assert "0." in result.stdout or "1." in result.stdout


# ── Help ──────────────────────────────────────────────────────────────


class TestCLIHelp:
    """Tests for 'cos help' subcommand."""

    def test_help_shows_all_commands(self):
        """'cos help' should list all subcommands including new ones."""
        result = _run_cli("help")
        assert result.returncode == 0
        assert "sources" in result.stdout
        assert "search" in result.stdout
        assert "install" in result.stdout
        assert "uninstall" in result.stdout
        assert "list" in result.stdout
        assert "update" in result.stdout

    def test_help_shows_types(self):
        """'cos help' should mention the valid component types."""
        result = _run_cli("help")
        assert result.returncode == 0
        assert "skill" in result.stdout
        assert "rule" in result.stdout
        assert "hook" in result.stdout
        assert "preset" in result.stdout
        assert "mcp-server" in result.stdout

    def test_default_command_is_help(self):
        """Running 'cos' with no arguments should show help."""
        result = _run_cli()
        assert result.returncode == 0
        assert "cognitive-os v" in result.stdout

    def test_unknown_command_fails(self):
        """'cos nonexistent' should fail and show usage."""
        result = _run_cli("nonexistent")
        assert result.returncode != 0
        assert "Unknown command" in result.stdout
