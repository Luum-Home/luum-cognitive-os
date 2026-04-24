"""Behavior tests for the self-install auto-sync hook.

Tests that hooks/self-install.sh correctly detects self-hosting and syncs
ALL framework components via the SYNC_DIRS registry: rules, skills, squads,
templates, agents, customizations, docs, and runtime dirs.

Related hook: hooks/self-install.sh
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Optional

import pytest

pytestmark = pytest.mark.behavior

HOOK_PATH = Path(__file__).resolve().parents[2] / "hooks" / "self-install.sh"


def _run_hook(
    project_dir: str,
    env_overrides: Optional[Dict[str, str]] = None,
    project_env_var: str = "CLAUDE_PROJECT_DIR",
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env[project_env_var] = project_dir
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        capture_output=True, text=True, env=env, timeout=5,
    )


def _setup_full_project(tmp_path: Path) -> Path:
    """Create a complete self-hosted luum-agent-os structure."""
    # Marker
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "self-install.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
    (hooks_dir / "session-init.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
    (hooks_dir / "health.sh").write_text("#!/usr/bin/env bash\nexit 0\n")

    # Rules — in self-hosting/full mode, ALL rules are synced to cos/.
    # alpha.md and beta.md are included to verify that non-CORE_RULES files
    # are also synced in self-hosting mode.
    # RULES-COMPACT.md and adaptive-bypass.md ARE in CORE_RULES.
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "alpha.md").write_text("# Alpha\n")
    (rules_dir / "beta.md").write_text("# Beta\n")
    (rules_dir / "RULES-COMPACT.md").write_text("# Compact\n")
    (rules_dir / "adaptive-bypass.md").write_text("# Adaptive Bypass\n")

    # Skills (subdirs with SKILL.md)
    for name in ["repo-scout", "contract-drift", "sdd-apply"]:
        skill = tmp_path / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"# {name}\n")
    (tmp_path / "skills" / "CATALOG.md").write_text("# Catalog\n")

    # Squads
    squads_dir = tmp_path / "squads"
    squads_dir.mkdir()
    (squads_dir / "infra-team.yaml").write_text("name: infra\n")
    (squads_dir / "platform-team.yaml").write_text("name: platform\n")

    # Templates
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "agent-preamble.md").write_text("# Preamble\n")

    # Agents
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "stack-validator.md").write_text("# Stack Validator\n")
    (agents_dir / "test-coverage.md").write_text("# Test Coverage\n")

    # Customizations
    cust_dir = tmp_path / "customizations"
    cust_dir.mkdir()
    (cust_dir / "example.yaml").write_text("model: sonnet\n")

    # Docs (tree with subdirs)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "README.md").write_text("# Docs\n")
    (docs_dir / "architecture.md").write_text("# Architecture\n")
    assets_dir = docs_dir / "assets"
    assets_dir.mkdir()
    (assets_dir / "diagram.png").write_text("fake-png\n")

    # Infrastructure
    (tmp_path / ".claude").mkdir(parents=True)
    (tmp_path / ".claude" / "settings.json").write_text('{"hooks": {}}\n')
    (tmp_path / "cognitive-os.yaml").write_text("version: 1\n")

    # Infrastructure checks in self-install.sh (checks 3, 4, 5):
    # Create .githooks/pre-commit so check 3 passes.
    githooks_dir = tmp_path / ".githooks"
    githooks_dir.mkdir()
    pre_commit = githooks_dir / "pre-commit"
    pre_commit.write_text("#!/usr/bin/env bash\nexit 0\n")
    pre_commit.chmod(0o755)
    # Initialize a git repo so check 4 (core.hooksPath) persists across runs.
    import subprocess as _sp
    _sp.run(["git", "init", str(tmp_path)], capture_output=True, check=False)
    _sp.run(["git", "-C", str(tmp_path), "config", "core.hooksPath", ".githooks"],
            capture_output=True, check=False)
    # Create .cognitive-os/workflows/ so check 5 passes.
    (tmp_path / ".cognitive-os" / "workflows").mkdir(parents=True, exist_ok=True)

    return tmp_path


class TestDetection:
    def test_detects_self_hosting(self, tmp_path):
        project = _setup_full_project(tmp_path)
        result = _run_hook(str(project))
        assert result.returncode == 0
        assert "Self-hosting:" in result.stdout

    def test_detects_self_hosting_via_codex_project_dir(self, tmp_path):
        project = _setup_full_project(tmp_path)
        result = _run_hook(str(project), project_env_var="CODEX_PROJECT_DIR")
        assert result.returncode == 0
        assert "Self-hosting:" in result.stdout

    def test_cognitive_os_project_dir_takes_precedence(self, tmp_path):
        project = _setup_full_project(tmp_path)
        other = tmp_path / "other"
        other.mkdir()
        result = _run_hook(
            str(other),
            env_overrides={"COGNITIVE_OS_PROJECT_DIR": str(project)},
            project_env_var="CLAUDE_PROJECT_DIR",
        )
        assert result.returncode == 0
        assert "Self-hosting:" in result.stdout

    def test_codex_settings_target_is_accepted(self, tmp_path):
        project = _setup_full_project(tmp_path)
        (project / ".claude" / "settings.json").unlink()
        codex_dir = project / ".codex"
        codex_dir.mkdir()
        (codex_dir / "hooks.json").write_text('{"hooks": {}}\n')

        result = _run_hook(str(project), project_env_var="CODEX_PROJECT_DIR")
        assert result.returncode == 0
        assert ".codex/hooks.json missing" not in result.stdout

    def test_skips_non_self_hosted(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        result = _run_hook(str(tmp_path))
        assert result.returncode == 0
        assert result.stdout.strip() == ""


class TestAgentsSync:
    """Tests for agents/ directory auto-sync."""


    def test_no_agents_dir_is_ok(self, tmp_path):
        project = _setup_full_project(tmp_path)
        import shutil
        shutil.rmtree(project / "agents")
        result = _run_hook(str(project))
        assert result.returncode == 0
        assert "0 agents" in result.stdout


class TestCustomizationsSync:
    """Tests for customizations/ directory auto-sync."""


    def test_no_customizations_dir_is_ok(self, tmp_path):
        project = _setup_full_project(tmp_path)
        import shutil
        shutil.rmtree(project / "customizations")
        result = _run_hook(str(project))
        assert result.returncode == 0


class TestDocsSync:
    """Tests for docs/ directory auto-sync (tree strategy)."""


    def test_no_docs_dir_is_ok(self, tmp_path):
        project = _setup_full_project(tmp_path)
        import shutil
        shutil.rmtree(project / "docs")
        result = _run_hook(str(project))
        assert result.returncode == 0
        assert "0 docs" in result.stdout


class TestAutoDiscovery:
    """Tests that the SYNC_DIRS registry auto-discovers directories."""

    def test_missing_source_dir_skipped_gracefully(self, tmp_path):
        """If a registered dir does not exist, it is simply skipped."""
        project = _setup_full_project(tmp_path)
        import shutil
        shutil.rmtree(project / "squads")
        shutil.rmtree(project / "agents")
        shutil.rmtree(project / "customizations")
        shutil.rmtree(project / "docs")
        result = _run_hook(str(project))
        assert result.returncode == 0
        assert "0 squads" in result.stdout
        assert "0 agents" in result.stdout
        assert "0 docs" in result.stdout

    def test_all_registered_dirs_synced(self, tmp_path):
        """Verify that all 7 registered dirs sync when present."""
        project = _setup_full_project(tmp_path)
        result = _run_hook(str(project))
        assert result.returncode == 0
        # Check that all target dirs were created
        assert (project / ".claude" / "rules" / "cos").is_dir()
        assert (project / ".cognitive-os" / "skills").is_dir()
        assert (project / ".cognitive-os" / "squads").is_dir()
        assert (project / ".cognitive-os" / "templates").is_dir()
        assert (project / ".cognitive-os" / "agents").is_dir()
        assert (project / ".cognitive-os" / "customizations").is_dir()
        assert (project / ".cognitive-os" / "docs").is_dir()

    def test_sync_dirs_are_extensible(self, tmp_path):
        """Adding a new dir to the project root is enough to get it synced
        (after adding one line to the SYNC_DIRS array in the script)."""
        # This test documents the design: one line per new dir.
        # We verify by checking that all currently registered dirs work.
        project = _setup_full_project(tmp_path)
        result = _run_hook(str(project))
        assert result.returncode == 0
        # The status should include all component types
        for component in ["rules", "hooks", "skills", "squads", "agents", "docs"]:
            assert component in result.stdout


class TestBulkUpgrade:
    """Simulate an upgrade that adds multiple components at once."""


    def test_bulk_remove_stale(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))  # initial sync

        # Remove all rules and one skill
        for f in (project / "rules").glob("*.md"):
            f.unlink()
        import shutil
        shutil.rmtree(project / "skills" / "repo-scout")

        result = _run_hook(str(project))
        assert "FIXED" in result.stdout
        assert "removed" in result.stdout
        # Stale symlinks should be gone
        assert not list((project / ".claude" / "rules" / "cos").glob("*.md"))


class TestSymlinkContent:
    """Verify symlinks point to correct content, not just existence."""

    def test_rule_symlink_resolves_to_source(self, tmp_path):
        # Use RULES-COMPACT.md (a CORE_RULES file) which gets symlinked by the hook.
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        link = project / ".claude" / "rules" / "cos" / "RULES-COMPACT.md"
        assert link.read_text() == "# Compact\n"

    def test_canonical_rule_symlink_resolves_to_source(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        link = project / ".cognitive-os" / "rules" / "cos" / "RULES-COMPACT.md"
        assert link.read_text() == "# Compact\n"

    def test_skill_symlink_resolves_to_skill_md(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        skill_link = project / ".cognitive-os" / "skills" / "cos" / "repo-scout"
        assert (skill_link / "SKILL.md").read_text() == "# repo-scout\n"


    def test_squad_symlink_resolves(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        link = project / ".cognitive-os" / "squads" / "infra-team.yaml"
        assert link.read_text() == "name: infra\n"

    def test_agent_symlink_resolves(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        link = project / ".cognitive-os" / "agents" / "stack-validator.md"
        assert link.read_text() == "# Stack Validator\n"

    def test_doc_symlink_resolves(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        link = project / ".cognitive-os" / "docs" / "README.md"
        assert link.read_text() == "# Docs\n"


class TestPerformance:
    """Verify the hook completes quickly even with many components."""

    def test_completes_under_two_seconds_with_100_components(self, tmp_path):
        import time
        project = _setup_full_project(tmp_path)

        # Add 50 rules + 50 skills
        for i in range(50):
            (project / "rules" / f"perf-rule-{i:03d}.md").write_text(f"# R{i}\n")
        for i in range(50):
            skill = project / "skills" / f"perf-skill-{i:03d}"
            skill.mkdir()
            (skill / "SKILL.md").write_text(f"# S{i}\n")

        start = time.monotonic()
        result = _run_hook(str(project))
        elapsed = time.monotonic() - start

        assert result.returncode == 0
        assert elapsed < 2.0, f"Hook took {elapsed:.2f}s — should be under 2s"

    def test_idempotent_run_is_fast(self, tmp_path):
        import time
        project = _setup_full_project(tmp_path)

        # First run — creates everything
        _run_hook(str(project))

        # Second run — should be very fast (nothing to do)
        start = time.monotonic()
        result = _run_hook(str(project))
        elapsed = time.monotonic() - start

        assert "OK" in result.stdout
        assert elapsed < 1.0, f"Idempotent run took {elapsed:.2f}s — should be under 1s"


class TestEdgeCases:
    """Edge cases and error conditions."""

    def test_empty_rules_dir(self, tmp_path):
        project = _setup_full_project(tmp_path)
        for f in (project / "rules").glob("*.md"):
            f.unlink()
        result = _run_hook(str(project))
        assert result.returncode == 0
        assert "0 rules" in result.stdout

    def test_no_skills_dir(self, tmp_path):
        project = _setup_full_project(tmp_path)
        import shutil
        shutil.rmtree(project / "skills")
        result = _run_hook(str(project))
        assert result.returncode == 0

    def test_no_squads_dir(self, tmp_path):
        project = _setup_full_project(tmp_path)
        import shutil
        shutil.rmtree(project / "squads")
        result = _run_hook(str(project))
        assert result.returncode == 0
        assert "0 squads" in result.stdout


class TestRealRepo:
    """Test against the actual luum-agent-os repo."""

    def test_real_repo_sync(self):
        real_root = HOOK_PATH.parents[1]
        if not (real_root / "hooks" / "self-install.sh").exists():
            pytest.skip("not in luum-agent-os")
        result = _run_hook(str(real_root))
        assert result.returncode == 0
        assert "Self-hosting:" in result.stdout
        assert "rules" in result.stdout
        assert "skills" in result.stdout
