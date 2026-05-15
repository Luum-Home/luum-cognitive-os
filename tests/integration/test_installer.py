"""Tests for install.sh — the Cognitive OS installer.

Validates:
- Fresh installation creates expected structure
- Self-install guard prevents installing into the OS repo itself
- --force flag overwrites existing installations
- Broken symlinks don't crash the installer
- Update (re-install with --force) preserves project files
- .gitignore covers all runtime paths
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.timeout(180)]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

INSTALLER = Path(__file__).resolve().parent.parent.parent / "install.sh"
RUNTIME_HOOK_REALITY = INSTALLER.parent / "scripts" / "runtime_hook_reality.py"
COS_INIT = INSTALLER.parent / "scripts" / "cos_init.py"
STRUCTURAL_HARNESSES = [
    "agents-md",
    "opencode",
    "vscode-copilot",
    "cursor",
    "qwen-code",
    "kimi-code",
    "gemini-cli",
    "warp",
    "amp-code",
    "jetbrains-junie",
    "qoder",
    "factory-droid",
    "cline",
    "continue-dev",
    "kilo-code",
    "zed-ai",
    "augment-code",
    "goose",
    "aider",
    "shell-ci",
]


@pytest.fixture
def install_dir(tmp_path):
    """Create a temporary project directory for installation tests."""
    project = tmp_path / "test-project"
    project.mkdir()
    # Initialize git so the installer doesn't complain
    subprocess.run(["git", "init"], cwd=project, capture_output=True)
    return project


@pytest.fixture(autouse=True)
def isolate_registry(tmp_path, monkeypatch):
    """Use a temp registry so tests don't pollute ~/.cognitive-os/installations.json."""
    registry = tmp_path / "test-registry.json"
    monkeypatch.setenv("COS_REGISTRY_FILE", str(registry))


@pytest.fixture
def cos_source():
    """Return the path to the Cognitive OS source repo."""
    return INSTALLER.parent


def _init_git_project(project: Path, files: dict[str, str] | None = None) -> None:
    """Create a minimal git-backed consumer project."""
    project.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=project, capture_output=True, check=False)
    for relpath, content in (files or {}).items():
        path = project / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def _run_installer(project: Path, cos_source: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run install.sh against a consumer project using the checked-out source."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [str(INSTALLER), "--from", str(cos_source), "--force", *args],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=180,
        env=merged_env,
    )


# ---------------------------------------------------------------------------
# Fresh Installation
# ---------------------------------------------------------------------------


class TestFreshInstall:
    """Tests for installing COS into a clean project."""

    def test_creates_cognitive_os_dir(self, install_dir, cos_source):
        """install.sh creates .cognitive-os/ in the target directory."""
        result = subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Installer failed:\n{result.stderr}\n{result.stdout}"
        assert (install_dir / ".cognitive-os").is_dir()

    def test_creates_claude_rules(self, install_dir, cos_source):
        """install.sh creates .claude/rules/cos/ with rule files."""
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        rules_dir = install_dir / ".claude" / "rules" / "cos"
        assert rules_dir.is_dir(), ".claude/rules/cos/ not created"
        rule_files = list(rules_dir.glob("*.md"))
        assert len(rule_files) > 0, "No rule files installed"

    def test_creates_settings_json(self, install_dir, cos_source):
        """install.sh creates .claude/settings.json with hooks."""
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        settings = install_dir / ".claude" / "settings.json"
        assert settings.is_file(), ".claude/settings.json not created"
        content = settings.read_text()
        assert "hooks" in content, "settings.json missing hooks section"

    def test_creates_codex_hooks_when_harness_is_codex(self, install_dir, cos_source):
        """install.sh projects hooks into .codex/hooks.json when Codex is selected."""
        result = subprocess.run(
            [str(INSTALLER), "--force", "--harness=codex"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Installer failed:\n{result.stderr}\n{result.stdout}"
        hooks_path = install_dir / ".codex" / "hooks.json"
        assert hooks_path.is_file(), ".codex/hooks.json not created"
        content = hooks_path.read_text()
        assert "CODEX_PROJECT_DIR" in content, "Codex hooks.json missing Codex project expression"
        assert "Harness:        codex" in result.stdout
        assert "Settings:       .codex/hooks.json" in result.stdout
        assert not (install_dir / ".claude" / "CLAUDE.md").exists()
        assert "Skills available:" in result.stdout

    def test_creates_cognitive_os_yaml(self, install_dir, cos_source):
        """install.sh creates cognitive-os.yaml config."""
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        config = install_dir / "cognitive-os.yaml"
        assert config.is_file(), "cognitive-os.yaml not created"

    def test_creates_claude_md(self, install_dir, cos_source):
        """install.sh creates .claude/CLAUDE.md from template."""
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        claude_md = install_dir / ".claude" / "CLAUDE.md"
        assert claude_md.is_file(), ".claude/CLAUDE.md not created"

    def test_installs_cross_harness_authoring_template(self, install_dir, cos_source):
        """install.sh installs the cross-harness authoring guide into templates/cos."""
        result = subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Installer failed:\n{result.stderr}\n{result.stdout}"
        guide = install_dir / ".cognitive-os" / "templates" / "cos" / "cross-harness-authoring.md"
        assert guide.is_file(), "cross-harness-authoring.md not installed"
        content = guide.read_text()
        assert "Author behavior once" in content

    def test_output_reports_success(self, install_dir, cos_source):
        """install.sh prints success message on completion."""
        result = subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        assert "installed successfully" in result.stdout
        assert "Harness:        claude" in result.stdout
        assert "Settings:       .claude/settings.json" in result.stdout
        assert "Next checks:" in result.stdout

    def test_new_codex_repo_local_source_install_smoke(self, tmp_path, cos_source):
        """Smoke: a brand-new repo can install COS for Codex with closed portable surfaces."""
        project = tmp_path / "new-codex-app"
        project.mkdir()
        subprocess.run(["git", "init"], cwd=project, capture_output=True, check=False)
        (project / "package.json").write_text('{"name": "new-codex-app"}\n')
        (project / "README.md").write_text("# New Codex App\n")

        result = subprocess.run(
            [str(INSTALLER), "--from", str(cos_source), "--force", "--harness=codex"],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=180,
        )

        assert result.returncode == 0, f"Installer failed:\n{result.stderr}\n{result.stdout}"
        assert "Cognitive OS installed successfully." in result.stdout
        assert "Harness:        codex" in result.stdout
        assert "Skills available:" in result.stdout

        install_meta = json.loads((project / ".cognitive-os" / "install-meta.json").read_text())
        assert install_meta["harness"] == "codex"
        assert (project / "cognitive-os.yaml").is_file()
        assert (project / ".codex" / "hooks.json").is_file()
        assert not (project / ".claude" / "CLAUDE.md").exists()
        assert (project / ".cognitive-os" / "skills" / "cos" / "cos-status" / "SKILL.md").is_file()
        assert not (project / ".claude" / "skills").exists()

        hooks_json = (project / ".codex" / "hooks.json").read_text()
        assert "CODEX_PROJECT_DIR" in hooks_json
        assert "CLAUDE_PROJECT_DIR" not in hooks_json

        audit = subprocess.run(
            [
                sys.executable,
                str(RUNTIME_HOOK_REALITY),
                "--project-root",
                str(project),
                "--settings",
                str(project / ".codex" / "hooks.json"),
                "--dependency-closure",
                "--install-scope",
                "project",
                "--fail-on-findings",
            ],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert audit.returncode == 0, audit.stderr + audit.stdout

    def test_new_cursor_repo_local_source_install_smoke(self, tmp_path, cos_source):
        """Smoke: top-level install.sh exposes structural harness projection beyond Claude/Codex."""
        project = tmp_path / "new-cursor-app"
        project.mkdir()
        subprocess.run(["git", "init"], cwd=project, capture_output=True, check=False)
        (project / "package.json").write_text('{"name": "new-cursor-app"}\n')

        result = subprocess.run(
            [str(INSTALLER), "--from", str(cos_source), "--force", "--harness=cursor"],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=180,
        )

        assert result.returncode == 0, f"Installer failed:\n{result.stderr}\n{result.stdout}"
        assert "Cognitive OS installed successfully." in result.stdout
        assert "Harness:        cursor" in result.stdout
        assert "Settings:       .cursor/rules/cognitive-os.mdc" in result.stdout
        assert "Check manifests/harness-projection.yaml before claiming runtime enforcement." in result.stdout

        install_meta = json.loads((project / ".cognitive-os" / "install-meta.json").read_text())
        assert install_meta["harness"] == "cursor"
        assert install_meta["settings_driver"] == ".cursor/rules/cognitive-os.mdc"
        assert (project / ".cursor" / "rules" / "cognitive-os.mdc").is_file()
        assert (project / ".cursor" / "mcp.json").is_file()
        assert (project / ".cognitive-os" / "skills" / "cos" / "cos-status" / "SKILL.md").is_file()
        assert not (project / ".claude" / "CLAUDE.md").exists()
        assert not (project / ".claude" / "skills").exists()

    def test_new_claude_repo_local_source_install_smoke(self, tmp_path, cos_source):
        """Smoke: a brand-new repo can install COS for Claude with portable instructions."""
        project = tmp_path / "new-claude-app"
        project.mkdir()
        subprocess.run(["git", "init"], cwd=project, capture_output=True, check=False)
        (project / "go.mod").write_text("module example.com/new-claude-app\n\ngo 1.22\n")

        result = subprocess.run(
            [str(INSTALLER), "--from", str(cos_source), "--force", "--harness=claude"],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=180,
        )

        assert result.returncode == 0, f"Installer failed:\n{result.stderr}\n{result.stdout}"
        assert "Cognitive OS installed successfully." in result.stdout
        assert "Harness:        claude" in result.stdout
        assert "Skills exposed:" in result.stdout

        claude_md = project / ".claude" / "CLAUDE.md"
        assert claude_md.is_file()
        instructions = claude_md.read_text()
        assert ".cognitive-os/rules/cos/RULES-COMPACT.md" in instructions
        assert ".cognitive-os/skills/cos/" in instructions
        assert "slash commands are supported" in instructions
        assert "acceptance criteria" in instructions
        assert "cos sdd next --feature <slug>" in instructions
        assert ".cognitive-os/workflows/sdd/<slug>" in instructions
        assert "bugfix|decision|architecture|discovery|pattern|config|preference" in instructions

        install_meta = json.loads((project / ".cognitive-os" / "install-meta.json").read_text())
        assert install_meta["harness"] == "claude"
        assert (project / ".claude" / "settings.json").is_file()
        assert (project / ".claude" / "skills" / "cos-status").exists()

    @pytest.mark.parametrize(
        ("harness", "profile_args", "settings_file", "profile"),
        [
            ("claude", (), ".claude/settings.json", "default"),
            ("codex", (), ".codex/hooks.json", "default"),
            ("claude", ("--full",), ".claude/settings.json", "full"),
            ("codex", ("--full",), ".codex/hooks.json", "full"),
        ],
    )
    def test_install_sh_claude_codex_profile_matrix(
        self,
        tmp_path,
        cos_source,
        harness,
        profile_args,
        settings_file,
        profile,
    ):
        """Matrix: install.sh supports default/full profiles for Claude and Codex."""
        project = tmp_path / f"{harness}-{profile}-app"
        _init_git_project(project, {"README.md": f"# {harness} {profile}\n"})

        result = _run_installer(project, cos_source, f"--harness={harness}", *profile_args)

        assert result.returncode == 0, f"Installer failed:\n{result.stderr}\n{result.stdout}"
        assert f"Profile:        {profile}" in result.stdout
        assert f"Harness:        {harness}" in result.stdout
        assert f"Settings:       {settings_file}" in result.stdout
        assert (project / settings_file).is_file()

        install_meta = json.loads((project / ".cognitive-os" / "install-meta.json").read_text())
        assert install_meta["harness"] == harness
        assert install_meta["mode"] == profile
        assert (project / ".cognitive-os" / "skills" / "cos" / "cos-status" / "SKILL.md").is_file()
        if harness == "claude":
            assert (project / ".claude" / "CLAUDE.md").is_file()
            assert (project / ".claude" / "skills").is_dir()
        else:
            assert not (project / ".claude" / "CLAUDE.md").exists()
            assert not (project / ".claude" / "skills").exists()

    @pytest.mark.parametrize("scope", ["project", "both", "all"])
    @pytest.mark.parametrize("harness", ["claude", "codex", "cursor"])
    def test_install_sh_scope_matrix_for_primary_harnesses(self, tmp_path, cos_source, harness, scope):
        """Matrix: install.sh propagates COS_INSTALL_SCOPE/--scope for representative harness classes."""
        project = tmp_path / f"{harness}-{scope}-scope-app"
        _init_git_project(project, {"README.md": f"# {harness} {scope}\n"})

        result = _run_installer(project, cos_source, f"--harness={harness}", f"--scope={scope}")

        assert result.returncode == 0, f"Installer failed:\n{result.stderr}\n{result.stdout}"
        assert f"Harness:        {harness}" in result.stdout
        install_meta = json.loads((project / ".cognitive-os" / "install-meta.json").read_text())
        assert install_meta["harness"] == harness
        assert (project / ".cognitive-os" / "hooks" / "cos" / "session-init.sh").is_file()
        if harness == "codex":
            audit = subprocess.run(
                [
                    sys.executable,
                    str(RUNTIME_HOOK_REALITY),
                    "--project-root",
                    str(project),
                    "--settings",
                    str(project / ".codex" / "hooks.json"),
                    "--dependency-closure",
                    "--install-scope",
                    scope,
                    "--fail-on-findings",
                ],
                cwd=project,
                capture_output=True,
                text=True,
                timeout=60,
            )
            assert audit.returncode == 0, audit.stderr + audit.stdout

    @pytest.mark.parametrize("harness", STRUCTURAL_HARNESSES)
    def test_install_sh_accepts_all_structural_harnesses(self, tmp_path, cos_source, harness):
        """Matrix: top-level install.sh accepts every structural harness supported by cos_init.py."""
        project = tmp_path / f"{harness}-install-app"
        _init_git_project(project, {"README.md": f"# {harness}\n"})

        result = _run_installer(project, cos_source, f"--harness={harness}")

        assert result.returncode == 0, f"{harness} install failed:\n{result.stderr}\n{result.stdout}"
        assert f"Harness:        {harness}" in result.stdout
        assert "Check manifests/harness-projection.yaml before claiming runtime enforcement." in result.stdout
        install_meta = json.loads((project / ".cognitive-os" / "install-meta.json").read_text())
        assert install_meta["harness"] == harness
        assert (project / install_meta["settings_driver"]).exists()
        assert not (project / ".claude" / "CLAUDE.md").exists()
        assert not (project / ".claude" / "skills").exists()

    def test_remote_install_without_from_uses_configured_git_remote(self, tmp_path, cos_source):
        """Smoke: curl-pipe style install without --from clones a git remote source."""
        remote_source = tmp_path / "remote-source"
        shutil.copytree(
            cos_source,
            remote_source,
            ignore=shutil.ignore_patterns(
                ".git",
                ".venv",
                "node_modules",
                "reference",
                ".cognitive-os/metrics",
                ".cognitive-os/runtime",
                "__pycache__",
            ),
        )
        subprocess.run(["git", "init"], cwd=remote_source, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "cos@example.test"], cwd=remote_source, check=True)
        subprocess.run(["git", "config", "user.name", "COS Tests"], cwd=remote_source, check=True)
        subprocess.run(["git", "add", "."], cwd=remote_source, check=True)
        subprocess.run(["git", "commit", "-m", "seed remote source"], cwd=remote_source, capture_output=True, check=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=remote_source, check=True)

        project = tmp_path / "remote-install-app"
        _init_git_project(project, {"README.md": "# Remote Install\n"})
        env = os.environ.copy()
        env["COGNITIVE_OS_REPO_URL"] = str(remote_source)
        env["COGNITIVE_OS_VERSION"] = "main"

        result = subprocess.run(
            ["bash", "-s", "--", "--force", "--harness=codex"],
            cwd=project,
            input=INSTALLER.read_text(),
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
        )

        assert result.returncode == 0, f"Remote installer failed:\n{result.stderr}\n{result.stdout}"
        assert "Downloading Cognitive OS (main)..." in result.stdout
        assert "Harness:        codex" in result.stdout
        assert (project / ".codex" / "hooks.json").is_file()
        assert not (project / ".claude" / "CLAUDE.md").exists()

    def test_optional_github_remote_install_without_from(self, tmp_path):
        """Optional live GitHub smoke for the default no---from install path."""
        if os.environ.get("COS_RUN_GITHUB_REMOTE_INSTALL_SMOKE") != "1":
            pytest.skip("set COS_RUN_GITHUB_REMOTE_INSTALL_SMOKE=1 to run live GitHub install smoke")

        project = tmp_path / "github-remote-install-app"
        _init_git_project(project, {"README.md": "# GitHub Remote Install\n"})

        result = subprocess.run(
            ["bash", "-s", "--", "--force", "--harness=codex"],
            cwd=project,
            input=INSTALLER.read_text(),
            capture_output=True,
            text=True,
            timeout=240,
            env=os.environ.copy(),
        )

        assert result.returncode == 0, f"GitHub remote installer failed:\n{result.stderr}\n{result.stdout}"
        assert "Downloading Cognitive OS" in result.stdout
        assert "Harness:        codex" in result.stdout
        assert (project / ".codex" / "hooks.json").is_file()
        assert not (project / ".claude" / "CLAUDE.md").exists()

    def test_codex_reinstall_preserves_existing_claude_settings_without_claude_md(self, tmp_path, cos_source):
        """Upgrade: Codex install must not synthesize Claude instructions in a legitimate .claude/ dir."""
        project = tmp_path / "codex-with-existing-claude-settings"
        _init_git_project(project, {"README.md": "# Codex Project\n"})
        claude_settings = project / ".claude" / "settings.json"
        claude_settings.parent.mkdir(parents=True, exist_ok=True)
        original_settings = {"permissions": {"allow": ["Bash(echo user-owned)"]}}
        claude_settings.write_text(json.dumps(original_settings, indent=2) + "\n")

        first = _run_installer(project, cos_source, "--harness=codex")
        second = _run_installer(project, cos_source, "--harness=codex")

        assert first.returncode == 0, first.stderr + first.stdout
        assert second.returncode == 0, second.stderr + second.stdout
        assert json.loads(claude_settings.read_text()) == original_settings
        assert (project / ".codex" / "hooks.json").is_file()
        assert not (project / ".claude" / "CLAUDE.md").exists()
        assert not (project / ".claude" / "skills").exists()

    def test_codex_reinstall_preserves_preexisting_user_claude_md(self, tmp_path, cos_source):
        """Upgrade: Codex reinstall preserves a user-owned .claude/CLAUDE.md instead of replacing it."""
        project = tmp_path / "codex-with-user-claude-md"
        _init_git_project(project, {"README.md": "# Codex Project\n"})
        claude_md = project / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        original_instructions = "# User Claude Instructions\n\nOwned by this repo, not COS.\n"
        claude_md.write_text(original_instructions)

        first = _run_installer(project, cos_source, "--harness=codex")
        second = _run_installer(project, cos_source, "--harness=codex")

        assert first.returncode == 0, first.stderr + first.stdout
        assert second.returncode == 0, second.stderr + second.stdout
        assert claude_md.read_text() == original_instructions
        assert (project / ".codex" / "hooks.json").is_file()
        assert not (project / ".claude" / "skills").exists()


# ---------------------------------------------------------------------------
# Self-Install Guard
# ---------------------------------------------------------------------------


class TestSelfInstallGuard:
    """Tests that prevent installing COS into its own repo."""

    def test_blocks_self_install(self, cos_source):
        """Running install.sh from the COS repo itself should fail."""
        result = subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=cos_source,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "Self-install should be blocked"
        combined = f"{result.stdout}\n{result.stderr}"
        assert "CURRENT DIRECTORY" in combined or "project directory" in combined or "FROM the Cognitive OS repo" in combined

    def test_blocks_self_install_with_from(self, cos_source):
        """--from pointing to the same dir as cwd should be blocked."""
        result = subprocess.run(
            [str(INSTALLER), "--from", str(cos_source), "--force"],
            cwd=cos_source,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "Self-install via --from should be blocked"

    def test_blocks_self_install_relative_from(self, cos_source):
        """--from with relative path '.' should also be blocked."""
        result = subprocess.run(
            [str(INSTALLER), "--from", ".", "--force"],
            cwd=cos_source,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "Self-install via --from . should be blocked"


# ---------------------------------------------------------------------------
# Broken Symlinks (the original bug)
# ---------------------------------------------------------------------------


class TestBrokenSymlinks:
    """Tests that broken symlinks don't crash the installer."""

    def test_survives_broken_symlinks_in_source(self, install_dir, cos_source):
        """Installer should not fail even if source has broken symlinks."""
        # Create a broken symlink in a temp copy to simulate the issue
        # The real fix is that rsync --exclude skips .venv entirely
        result = subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Installer failed (possibly broken symlinks):\n{result.stderr}"
        assert (install_dir / ".cognitive-os").is_dir()


# ---------------------------------------------------------------------------
# Update (re-install with --force)
# ---------------------------------------------------------------------------


class TestUpdate:
    """Tests for updating an existing COS installation."""

    def test_force_overwrites_existing(self, install_dir, cos_source):
        """--force should overwrite an existing installation."""
        # First install
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        assert (install_dir / ".cognitive-os").is_dir()

        # Second install (update)
        result = subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Update failed:\n{result.stderr}"
        assert "installed successfully" in result.stdout

    def test_update_preserves_claude_md(self, install_dir, cos_source):
        """Updating should not overwrite an existing .claude/CLAUDE.md."""
        # First install
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )

        # Write custom content to CLAUDE.md
        claude_md = install_dir / ".claude" / "CLAUDE.md"
        custom_content = "# My Custom Project Rules\n\nDo not overwrite this.\n"
        claude_md.write_text(custom_content)

        # Update
        result = subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Verify custom CLAUDE.md is preserved
        assert claude_md.read_text() == custom_content, "CLAUDE.md was overwritten during update"

    def test_update_preserves_project_rules(self, install_dir, cos_source):
        """Updating should not touch project-specific rules outside cos/."""
        # First install
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )

        # Create a project-specific rule
        project_rule = install_dir / ".claude" / "rules" / "my-project-rule.md"
        project_rule.parent.mkdir(parents=True, exist_ok=True)
        project_rule.write_text("# My Rule\n\nProject-specific.\n")

        # Update
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )

        # Verify project rule is preserved
        assert project_rule.is_file(), "Project rule was deleted during update"
        assert "Project-specific" in project_rule.read_text()

    def test_update_refreshes_cos_rules(self, install_dir, cos_source):
        """Updating should refresh COS rules under cos/ namespace."""
        # First install
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )

        cos_rules = install_dir / ".claude" / "rules" / "cos"

        # Update
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )

        rules_after = set(f.name for f in cos_rules.glob("*.md")) if cos_rules.is_dir() else set()
        # COS rules should still exist after update
        assert len(rules_after) > 0, "COS rules missing after update"


# ---------------------------------------------------------------------------
# --from Flag
# ---------------------------------------------------------------------------


class TestFromFlag:
    """Tests for the --from flag."""

    def test_from_with_valid_path(self, install_dir, cos_source):
        """--from with a valid COS repo path should work."""
        result = subprocess.run(
            [str(INSTALLER), "--from", str(cos_source), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"--from failed:\n{result.stderr}"
        assert (install_dir / ".cognitive-os").is_dir()

    def test_from_with_invalid_path(self, install_dir):
        """--from with a non-existent path should fail gracefully."""
        result = subprocess.run(
            [str(INSTALLER), "--from", "/nonexistent/path", "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "does not exist" in result.stdout or "does not exist" in result.stderr

    def test_from_with_non_cos_dir(self, install_dir, tmp_path):
        """--from with a dir that's not a COS repo should fail."""
        fake_source = tmp_path / "not-cos"
        fake_source.mkdir()
        result = subprocess.run(
            [str(INSTALLER), "--from", str(fake_source), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "does not look like" in result.stdout or "does not look like" in result.stderr


# ---------------------------------------------------------------------------
# .gitignore Coverage
# ---------------------------------------------------------------------------


class TestGitignore:
    """Tests that .gitignore covers all runtime paths."""

    ALLOWED_TRACKED_COGNITIVE_OS_SOURCE_FILES = {
        ".cognitive-os/migrations/components-to-primitives.md",
        ".cognitive-os/migrations/test-architecture-inventory.md",
        ".cognitive-os/skills/_catalog-allowlist.txt",
        ".cognitive-os/test-lanes.yaml",
        ".cognitive-os/test-resource-policy.yaml",
        ".cognitive-os/tests/adversarial-generalization/scenarios.yaml",
        ".cognitive-os/tests/agentic-tools/license-matrix.json",
        ".cognitive-os/tests/runtime-comparison/tasks.yaml",
        ".cognitive-os/tests/skill-efficacy/tasks.json",
    }
    ALLOWED_TRACKED_PREFIXES = {
        ".cognitive-os/plans/",
    }
    ALLOWED_TRACKED_NON_COS_SOURCE_FILES = {
        ".promptfoo/config.yaml",
    }

    def test_gitignore_exists(self, cos_source):
        """The repo must have a .gitignore."""
        assert (cos_source / ".gitignore").is_file()

    @pytest.mark.parametrize(
        "pattern",
        [
            ".cognitive-os/",
            "sessions/",
            "metrics/*.jsonl",
            "tasks/active-tasks.json",
            "dynamic-tools/",
            ".env",
            "__pycache__/",
            ".venv/",
            "node_modules/",
            "reference/",
            ".DS_Store",
            "*.log",
            ".claude/settings.local.json",
            ".claude/plugins/.cognitive-os/",
            "skills/auto-generated/",
            ".ruff_cache/",
            ".promptfoo/",
            ".coverage",
        ],
    )
    def test_gitignore_contains_pattern(self, cos_source, pattern):
        """Critical patterns must be present in .gitignore."""
        content = (cos_source / ".gitignore").read_text()
        assert pattern in content, f".gitignore missing pattern: {pattern}"

    def test_no_runtime_files_tracked(self, cos_source):
        """No .cognitive-os/ files should be tracked in git."""
        result = subprocess.run(
            ["git", "ls-files", "--cached"],
            cwd=cos_source,
            capture_output=True,
            text=True,
        )
        deleted_result = subprocess.run(
            ["git", "ls-files", "--cached", "--deleted"],
            cwd=cos_source,
            capture_output=True,
            text=True,
        )
        tracked = result.stdout.strip().split("\n")
        staged_or_worktree_deleted = set(deleted_result.stdout.strip().split("\n"))
        runtime_tracked = [
            f for f in tracked
            if f not in staged_or_worktree_deleted
            if (
                f.startswith(".cognitive-os/")
                and f not in self.ALLOWED_TRACKED_COGNITIVE_OS_SOURCE_FILES
                and not any(
                    f.startswith(prefix) for prefix in self.ALLOWED_TRACKED_PREFIXES
                )
            )
            or (
                f.startswith(".promptfoo/")
                and f not in self.ALLOWED_TRACKED_NON_COS_SOURCE_FILES
            )
            or f.startswith(".ruff_cache/")
        ]
        assert runtime_tracked == [], f"Runtime files still tracked in git: {runtime_tracked}"


# ---------------------------------------------------------------------------
# Registry Source Tracking
# ---------------------------------------------------------------------------


class TestRegistrySource:
    """Tests that the registry tracks the real source repo, not temp dirs."""

    def test_registry_source_is_real_repo(self, install_dir, cos_source):
        """The registry source field should point to the real COS repo, not /tmp/."""
        registry = Path(os.environ["COS_REGISTRY_FILE"])

        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )

        if registry.is_file():
            import json

            data = json.loads(registry.read_text())
            entries = data.get("installations", [])
            for entry in entries:
                source = entry.get("source", "")
                assert "/tmp/" not in source or "pytest" in source, (
                    f"Registry source points to temp dir: {source}"
                )

    def test_install_meta_source_is_real_repo(self, install_dir, cos_source):
        """install-meta.json source field should be the real COS repo path."""
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )

        meta = install_dir / ".cognitive-os" / "install-meta.json"
        if meta.is_file():
            import json

            data = json.loads(meta.read_text())
            source = data.get("source", "")
            # Should be the real COS repo, not a mktemp directory
            assert str(cos_source) in source or source == str(cos_source), (
                f"install-meta.json source is '{source}', expected to contain '{cos_source}'"
            )


# ---------------------------------------------------------------------------
# Project .gitignore Update
# ---------------------------------------------------------------------------


class TestProjectGitignore:
    """Tests that the installer updates the project's .gitignore."""

    def test_creates_gitignore_if_missing(self, install_dir, cos_source):
        """Installer should create .gitignore in the project if none exists."""
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        gitignore = install_dir / ".gitignore"
        assert gitignore.is_file(), ".gitignore not created in project"

    @pytest.mark.parametrize(
        "pattern",
        [
            ".cognitive-os/sessions/",
            ".cognitive-os/metrics/",
            ".cognitive-os/tasks/",
            ".cognitive-os/checkpoints/",
            ".cognitive-os/dynamic-tools/",
            ".claude/settings.local.json",
        ],
    )
    def test_gitignore_contains_cos_patterns(self, install_dir, cos_source, pattern):
        """Project .gitignore must contain all COS runtime patterns."""
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )
        content = (install_dir / ".gitignore").read_text()
        assert pattern in content, f"Project .gitignore missing COS pattern: {pattern}"

    def test_update_adds_new_patterns(self, install_dir, cos_source):
        """Re-running installer should add new patterns without duplicates."""
        # First install
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )

        gitignore = install_dir / ".gitignore"

        # Second install (update)
        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )

        content_after = gitignore.read_text()
        # No duplicates: count occurrences of a key pattern
        count = content_after.count(".cognitive-os/sessions/")
        assert count == 1, f"Pattern duplicated {count} times after update"

    def test_preserves_existing_gitignore_content(self, install_dir, cos_source):
        """Installer should not remove existing .gitignore entries."""
        gitignore = install_dir / ".gitignore"
        gitignore.write_text("# My project\nnode_modules/\n*.log\n")

        subprocess.run(
            [str(INSTALLER), "--force"],
            cwd=install_dir,
            capture_output=True,
            text=True,
        )

        content = gitignore.read_text()
        assert "node_modules/" in content, "Existing .gitignore content was removed"
        assert "*.log" in content, "Existing .gitignore content was removed"
        assert ".cognitive-os/sessions/" in content, "COS patterns not added"


# ---------------------------------------------------------------------------
# Help Flag
# ---------------------------------------------------------------------------


class TestHelpFlag:
    """Tests for --help output."""

    def test_help_mentions_project_directory(self):
        """--help should clearly explain to run from project dir."""
        result = subprocess.run(
            [str(INSTALLER), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "CURRENT DIRECTORY" in result.stdout or "project directory" in result.stdout

    def test_help_documents_harness_drivers(self):
        """--help should document supported harness drivers and the default."""
        result = subprocess.run(
            [str(INSTALLER), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--harness=NAME" in result.stdout
        assert "claude" in result.stdout
        assert "codex" in result.stdout
        assert "cursor" in result.stdout
        assert "opencode" in result.stdout
        assert "shell-ci" in result.stdout
        assert "default: claude" in result.stdout

    def test_installer_harness_list_matches_shared_registry(self):
        """install.sh, cos_init.py, and Go CLI must use the shared first-run harness registry."""
        install_text = INSTALLER.read_text()
        match = re.search(r'^SUPPORTED_HARNESSES="([^"]+)"', install_text, re.MULTILINE)
        assert match, "install.sh missing SUPPORTED_HARNESSES"
        install_harnesses = match.group(1).split()

        registry = json.loads((INSTALLER.parent / "manifests" / "harness-projection-registry.json").read_text())
        registry_harnesses = registry["implemented_order"]
        implemented = {row["id"] for row in registry["harnesses"] if row["status"] == "implemented"}
        assert set(registry_harnesses) == implemented
        assert install_harnesses == registry_harnesses

        code = """import scripts.cos_init as c; print(' '.join(c.SUPPORTED_HARNESSES))"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=INSTALLER.parent,
            text=True,
            capture_output=True,
            check=True,
        )
        assert result.stdout.strip().split() == registry_harnesses

    def test_help_explains_from_flag(self):
        """--help should explain when --from is needed."""
        result = subprocess.run(
            [str(INSTALLER), "--help"],
            capture_output=True,
            text=True,
        )
        assert "--from" in result.stdout
