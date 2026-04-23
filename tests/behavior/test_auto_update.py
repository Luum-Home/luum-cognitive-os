"""Behavior tests for the auto-update mechanism.

Tests that:
- cos-registry.sh correctly manages the installations registry
- auto-update-projects.sh finds and updates registered projects
- setup-git-hooks.sh installs/removes the post-merge hook
- cos-init.sh registers projects in the registry
- uninstall.sh deregisters projects from the registry

Related scripts:
  scripts/cos-registry.sh
  scripts/auto-update-projects.sh
  scripts/setup-git-hooks.sh
  scripts/cos-init.sh (registration integration)
  scripts/uninstall.sh (deregistration integration)
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional

import pytest

pytestmark = pytest.mark.behavior

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
REGISTRY_SCRIPT = SCRIPTS_DIR / "cos-registry.sh"
AUTO_UPDATE_SCRIPT = SCRIPTS_DIR / "auto-update-projects.sh"
SETUP_HOOKS_SCRIPT = SCRIPTS_DIR / "setup-git-hooks.sh"
COS_INIT_SCRIPT = SCRIPTS_DIR / "cos-init.sh"
UNINSTALL_SCRIPT = SCRIPTS_DIR / "uninstall.sh"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run_script(
    script: Path,
    args: list = None,
    env_overrides: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    cmd = ["bash", str(script)] + (args or [])
    return subprocess.run(
        cmd, capture_output=True, text=True, env=env,
        cwd=cwd, timeout=30,
    )


def _create_registry(tmp_path: Path, installations: list = None) -> Path:
    """Create a registry file with optional installations."""
    registry_dir = tmp_path / "cos-home"
    registry_dir.mkdir(parents=True, exist_ok=True)
    registry_file = registry_dir / "installations.json"
    data = {"installations": installations or []}
    registry_file.write_text(json.dumps(data, indent=2))
    return registry_file


def _read_registry(registry_file: Path) -> dict:
    return json.loads(registry_file.read_text())


# ── Registry Management Tests ──────────────────────────────────────


class TestCosRegistry:
    """Tests for scripts/cos-registry.sh."""

    def test_register_new_project(self, tmp_path):
        registry_file = _create_registry(tmp_path)
        result = _run_script(
            REGISTRY_SCRIPT,
            ["register", str(tmp_path), "standard", "0.2.1", "my-project", "/path/to/cos"],
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0
        data = _read_registry(registry_file)
        assert len(data["installations"]) == 1
        entry = data["installations"][0]
        assert entry["path"] == str(tmp_path)
        assert entry["mode"] == "standard"
        assert entry["version"] == "0.2.1"
        assert entry["project_name"] == "my-project"
        assert entry["source"] == "/path/to/cos"

    def test_register_updates_existing(self, tmp_path):
        registry_file = _create_registry(tmp_path, [{
            "path": str(tmp_path),
            "mode": "minimal",
            "version": "0.1.0",
            "project_name": "old-name",
            "source": "/old/path",
            "installed_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }])
        result = _run_script(
            REGISTRY_SCRIPT,
            ["register", str(tmp_path), "full", "0.2.1", "new-name", "/new/path"],
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0
        data = _read_registry(registry_file)
        assert len(data["installations"]) == 1
        entry = data["installations"][0]
        assert entry["mode"] == "full"
        assert entry["version"] == "0.2.1"
        assert entry["project_name"] == "new-name"

    def test_deregister_project(self, tmp_path):
        registry_file = _create_registry(tmp_path, [{
            "path": str(tmp_path),
            "mode": "standard",
            "version": "0.2.1",
            "project_name": "my-project",
            "source": "/path/to/cos",
            "installed_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }])
        result = _run_script(
            REGISTRY_SCRIPT,
            ["deregister", str(tmp_path)],
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0
        data = _read_registry(registry_file)
        assert len(data["installations"]) == 0

    def test_deregister_nonexistent_is_safe(self, tmp_path):
        registry_file = _create_registry(tmp_path)
        result = _run_script(
            REGISTRY_SCRIPT,
            ["deregister", "/nonexistent/path"],
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0

    def test_list_empty_registry(self, tmp_path):
        registry_file = _create_registry(tmp_path)
        result = _run_script(
            REGISTRY_SCRIPT,
            ["list"],
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0
        assert "0" in result.stdout

    def test_list_with_entries(self, tmp_path):
        registry_file = _create_registry(tmp_path, [{
            "path": "/projects/foo",
            "mode": "standard",
            "version": "0.2.1",
            "project_name": "foo",
            "source": "/cos",
            "installed_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }])
        result = _run_script(
            REGISTRY_SCRIPT,
            ["list"],
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0
        assert "foo" in result.stdout
        assert "1" in result.stdout

    def test_cleanup_removes_nonexistent_paths(self, tmp_path):
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        registry_file = _create_registry(tmp_path, [
            {
                "path": str(existing_dir),
                "mode": "standard",
                "version": "0.2.1",
                "project_name": "exists",
                "source": "/cos",
                "installed_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
            {
                "path": "/nonexistent/project",
                "mode": "standard",
                "version": "0.2.1",
                "project_name": "gone",
                "source": "/cos",
                "installed_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
        ])
        result = _run_script(
            REGISTRY_SCRIPT,
            ["cleanup"],
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0
        data = _read_registry(registry_file)
        assert len(data["installations"]) == 1
        assert data["installations"][0]["project_name"] == "exists"

    def test_creates_registry_if_missing(self, tmp_path):
        registry_file = tmp_path / "cos-home" / "installations.json"
        assert not registry_file.exists()
        result = _run_script(
            REGISTRY_SCRIPT,
            ["register", str(tmp_path), "standard", "0.2.1", "my-project", "/cos"],
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0
        assert registry_file.exists()
        data = _read_registry(registry_file)
        assert len(data["installations"]) == 1


# ── Auto-Update Tests ──────────────────────────────────────────────


class TestAutoUpdate:
    """Tests for scripts/auto-update-projects.sh."""

    def test_list_mode(self, tmp_path):
        registry_file = _create_registry(tmp_path, [{
            "path": "/projects/foo",
            "mode": "standard",
            "version": "0.2.0",
            "project_name": "foo-project",
            "source": str(PROJECT_ROOT),
            "installed_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }])
        result = _run_script(
            AUTO_UPDATE_SCRIPT,
            ["--list"],
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0
        assert "foo-project" in result.stdout

    def test_no_registry_exits_gracefully(self, tmp_path):
        registry_file = tmp_path / "nonexistent" / "installations.json"
        result = _run_script(
            AUTO_UPDATE_SCRIPT,
            [],
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0
        assert "No installations registered" in result.stdout

    def test_dry_run_shows_would_update(self, tmp_path):
        """Dry run shows projects that would be updated without changing anything."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        # Create minimal install-meta so cos-init sees it as installed
        cos_dir = project_dir / ".cognitive-os"
        cos_dir.mkdir()

        registry_file = _create_registry(tmp_path, [{
            "path": str(project_dir),
            "mode": "standard",
            "version": "0.1.0",  # older version
            "project_name": "my-project",
            "source": str(PROJECT_ROOT),
            "installed_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }])

        result = _run_script(
            AUTO_UPDATE_SCRIPT,
            ["--dry-run"],
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0
        assert "WOULD UPDATE" in result.stdout

    def test_skips_nonexistent_project(self, tmp_path):
        registry_file = _create_registry(tmp_path, [{
            "path": "/nonexistent/project",
            "mode": "standard",
            "version": "0.1.0",
            "project_name": "gone",
            "source": str(PROJECT_ROOT),
            "installed_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }])
        result = _run_script(
            AUTO_UPDATE_SCRIPT,
            [],
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0
        assert "SKIP" in result.stdout

    def test_skips_projects_from_different_source(self, tmp_path):
        """Only updates projects installed from THIS COS source directory."""
        registry_file = _create_registry(tmp_path, [{
            "path": str(tmp_path),
            "mode": "standard",
            "version": "0.1.0",
            "project_name": "other",
            "source": "/some/other/cos",  # different source
            "installed_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }])
        result = _run_script(
            AUTO_UPDATE_SCRIPT,
            [],
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0
        assert "No projects installed from" in result.stdout


# ── Git Hook Setup Tests ───────────────────────────────────────────


class TestSetupGitHooks:
    """Tests for scripts/setup-git-hooks.sh."""

    def _create_fake_git_repo(self, tmp_path: Path) -> Path:
        """Create a minimal fake git repo structure."""
        git_dir = tmp_path / ".git" / "hooks"
        git_dir.mkdir(parents=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        # Copy the setup script so it can find its own location
        setup_content = SETUP_HOOKS_SCRIPT.read_text()
        (scripts_dir / "setup-git-hooks.sh").write_text(setup_content)
        # Create a dummy auto-update script
        (scripts_dir / "auto-update-projects.sh").write_text("#!/usr/bin/env bash\necho ok\n")
        return tmp_path

    def test_status_not_installed(self, tmp_path):
        repo = self._create_fake_git_repo(tmp_path)
        result = _run_script(
            repo / "scripts" / "setup-git-hooks.sh",
            ["--status"],
        )
        assert result.returncode == 0
        assert "NOT INSTALLED" in result.stdout

    def test_install_creates_post_merge_hook(self, tmp_path):
        repo = self._create_fake_git_repo(tmp_path)
        result = _run_script(
            repo / "scripts" / "setup-git-hooks.sh",
        )
        assert result.returncode == 0
        hook = repo / ".git" / "hooks" / "post-merge"
        assert hook.exists()
        content = hook.read_text()
        assert "COS_AUTO_UPDATE" in content
        assert "auto-update-projects.sh" in content

    def test_status_installed(self, tmp_path):
        repo = self._create_fake_git_repo(tmp_path)
        _run_script(repo / "scripts" / "setup-git-hooks.sh")
        result = _run_script(
            repo / "scripts" / "setup-git-hooks.sh",
            ["--status"],
        )
        assert result.returncode == 0
        assert "INSTALLED" in result.stdout

    def test_idempotent_install(self, tmp_path):
        repo = self._create_fake_git_repo(tmp_path)
        _run_script(repo / "scripts" / "setup-git-hooks.sh")
        _run_script(repo / "scripts" / "setup-git-hooks.sh")
        hook = repo / ".git" / "hooks" / "post-merge"
        content = hook.read_text()
        # Should only appear once
        assert content.count("COS_AUTO_UPDATE BEGIN") == 1


    def test_remove_cleans_hook(self, tmp_path):
        repo = self._create_fake_git_repo(tmp_path)
        _run_script(repo / "scripts" / "setup-git-hooks.sh")
        result = _run_script(
            repo / "scripts" / "setup-git-hooks.sh",
            ["--remove"],
        )
        assert result.returncode == 0
        hook = repo / ".git" / "hooks" / "post-merge"
        # Hook was COS-only, so COS section should be removed
        # (hook file may remain if empty or have non-COS content)
        if hook.exists():
            content = hook.read_text()
            assert "auto-update-projects" not in content


# ── Integration: cos-init.sh registers project ─────────────────────


class TestCosInitRegistration:
    """Tests that cos-init.sh registers the project in the global registry."""

    def test_cos_init_registers_project(self, tmp_path):
        """cos-init.sh should register the project using the canonicalized mode."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "package.json").write_text('{"name": "test-project"}')
        registry_file = _create_registry(tmp_path)

        result = _run_script(
            COS_INIT_SCRIPT,
            ["--minimal"],
            cwd=str(project_dir),
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0, f"cos-init failed: {result.stderr}"

        data = _read_registry(registry_file)
        assert len(data["installations"]) == 1
        entry = data["installations"][0]
        assert entry["project_name"] == "test-project"
        assert entry["mode"] == "default"
        assert entry["source"] == str(PROJECT_ROOT)
        assert "collapsed '--minimal' into '--default'" in result.stderr


# ── Integration: uninstall.sh deregisters project ──────────────────


class TestUninstallDeregistration:
    """Tests that uninstall.sh deregisters the project from the global registry."""

    def test_uninstall_deregisters_project(self, tmp_path):
        """uninstall.sh should remove the project from the registry."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        # First install COS
        registry_file = _create_registry(tmp_path)
        _run_script(
            COS_INIT_SCRIPT,
            ["--minimal"],
            cwd=str(project_dir),
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )

        # Verify it was registered
        data = _read_registry(registry_file)
        assert len(data["installations"]) == 1

        # Ensure install-meta.json has source path for registry script discovery
        meta_dir = project_dir / ".cognitive-os"
        meta_dir.mkdir(exist_ok=True)
        import json
        (meta_dir / "install-meta.json").write_text(json.dumps({
            "source": str(PROJECT_ROOT),
            "mode": "minimal",
        }))

        # Now uninstall
        result = _run_script(
            UNINSTALL_SCRIPT,
            [],
            cwd=str(project_dir),
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0

        # Verify it was deregistered
        data = _read_registry(registry_file)
        assert len(data["installations"]) == 0

    def test_uninstall_deregisters_canonical_only_project(self, tmp_path):
        """uninstall.sh should work even when only canonical COS artifacts exist."""
        project_dir = tmp_path / "canonical-only-project"
        project_dir.mkdir()

        registry_file = _create_registry(
            tmp_path,
            installations=[
                {
                    "path": str(project_dir),
                    "mode": "minimal",
                    "version": "0.2.1",
                    "project_name": "canonical-only-project",
                    "source": str(PROJECT_ROOT),
                    "installed_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ],
        )

        cos_dir = project_dir / ".cognitive-os"
        canonical_skill = cos_dir / "skills" / "cos" / "test-skill"
        canonical_skill.mkdir(parents=True)
        (canonical_skill / "SKILL.md").write_text("# Test Skill Canonical\n")

        canonical_rules = cos_dir / "rules" / "cos"
        canonical_rules.mkdir(parents=True)
        (canonical_rules / "test-rule.md").write_text("# Test Rule Canonical\n")

        (cos_dir / "install-meta.json").write_text(
            json.dumps(
                {
                    "source": str(PROJECT_ROOT),
                    "mode": "minimal",
                }
            )
        )

        result = _run_script(
            UNINSTALL_SCRIPT,
            ["--keep-config"],
            cwd=str(project_dir),
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )
        assert result.returncode == 0, result.stderr
        assert not (project_dir / ".cognitive-os").exists()

        data = _read_registry(registry_file)
        assert len(data["installations"]) == 0

    def test_uninstall_strips_cos_hooks_from_active_codex_driver(self, tmp_path):
        """uninstall.sh should clean the active Codex settings driver, not only Claude."""
        project_dir = tmp_path / "codex-project"
        project_dir.mkdir()

        registry_file = _create_registry(
            tmp_path,
            installations=[
                {
                    "path": str(project_dir),
                    "mode": "default",
                    "version": "0.2.1",
                    "project_name": "codex-project",
                    "source": str(PROJECT_ROOT),
                    "installed_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ],
        )

        codex_dir = project_dir / ".codex"
        codex_dir.mkdir()
        hooks_path = codex_dir / "hooks.json"
        hooks_path.write_text(
            json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {
                                "matcher": "*",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": 'bash "${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$PWD}}/.cognitive-os/hooks/cos/test-stop.sh"',
                                    },
                                    {
                                        "type": "command",
                                        "command": 'bash "${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$PWD}}/.codex/hooks/custom-stop.sh"',
                                    },
                                ],
                            }
                        ]
                    }
                }
            )
        )

        cos_dir = project_dir / ".cognitive-os"
        (cos_dir / "hooks" / "cos").mkdir(parents=True)
        (cos_dir / "hooks" / "cos" / "test-stop.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
        (cos_dir / "install-meta.json").write_text(
            json.dumps(
                {
                    "source": str(PROJECT_ROOT),
                    "mode": "default",
                }
            )
        )

        result = _run_script(
            UNINSTALL_SCRIPT,
            ["--keep-config"],
            cwd=str(project_dir),
            env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
        )

        assert result.returncode == 0, result.stderr
        assert (codex_dir / "hooks.json.cos-backup").exists()

        hooks_data = json.loads(hooks_path.read_text())
        commands = [
            hook["command"]
            for group in hooks_data["hooks"]["Stop"]
            for hook in group["hooks"]
        ]
        assert all(".cognitive-os/hooks/" not in cmd for cmd in commands)
        assert any(".codex/hooks/custom-stop.sh" in cmd for cmd in commands)

        data = _read_registry(registry_file)
        assert len(data["installations"]) == 0
