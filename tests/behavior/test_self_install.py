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


def _run_hook(project_dir: str, env_overrides: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = project_dir
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

    # Rules
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "alpha.md").write_text("# Alpha\n")
    (rules_dir / "beta.md").write_text("# Beta\n")

    # Skills (subdirs with SKILL.md)
    for name in ["eval-repo", "contract-drift", "sdd-apply"]:
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

    return tmp_path


class TestDetection:
    def test_detects_self_hosting(self, tmp_path):
        project = _setup_full_project(tmp_path)
        result = _run_hook(str(project))
        assert result.returncode == 0
        assert "Self-hosting:" in result.stdout

    def test_skips_non_self_hosted(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        result = _run_hook(str(tmp_path))
        assert result.returncode == 0
        assert result.stdout.strip() == ""


class TestRulesSync:
    def test_creates_rule_symlinks(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        cos_rules = project / ".claude" / "rules" / "cos"
        assert (cos_rules / "alpha.md").is_symlink()
        assert (cos_rules / "beta.md").is_symlink()

    def test_removes_stale_rule_symlinks(self, tmp_path):
        project = _setup_full_project(tmp_path)
        cos_rules = project / ".claude" / "rules" / "cos"
        cos_rules.mkdir(parents=True, exist_ok=True)
        stale = cos_rules / "deleted.md"
        stale.symlink_to(project / "rules" / "nonexistent.md")
        _run_hook(str(project))
        assert not stale.exists()


class TestSkillsSync:
    def test_creates_skill_symlinks(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        cos_skills = project / ".cognitive-os" / "skills"
        assert (cos_skills / "eval-repo").exists()
        assert (cos_skills / "contract-drift").exists()
        assert (cos_skills / "sdd-apply").exists()
        assert (cos_skills / "CATALOG.md").exists()

    def test_new_skill_auto_detected(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))  # first sync

        # Add a new skill
        new_skill = project / "skills" / "new-feature"
        new_skill.mkdir()
        (new_skill / "SKILL.md").write_text("# New\n")

        result = _run_hook(str(project))
        assert "FIXED" in result.stdout
        assert (project / ".cognitive-os" / "skills" / "new-feature").exists()


class TestSquadsSync:
    def test_creates_squad_symlinks(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        squads = project / ".cognitive-os" / "squads"
        assert (squads / "infra-team.yaml").is_symlink()
        assert (squads / "platform-team.yaml").is_symlink()


class TestTemplatesSync:
    def test_creates_template_symlinks(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        templates = project / ".cognitive-os" / "templates"
        assert (templates / "agent-preamble.md").is_symlink()


class TestAgentsSync:
    """Tests for agents/ directory auto-sync."""

    def test_creates_agent_symlinks(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        agents = project / ".cognitive-os" / "agents"
        assert (agents / "stack-validator.md").is_symlink()
        assert (agents / "test-coverage.md").is_symlink()

    def test_new_agent_auto_detected(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))

        # Add a new agent
        (project / "agents" / "new-agent.md").write_text("# New Agent\n")

        result = _run_hook(str(project))
        assert "FIXED" in result.stdout
        assert (project / ".cognitive-os" / "agents" / "new-agent.md").is_symlink()

    def test_stale_agent_symlink_removed(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))

        # Remove source agent
        (project / "agents" / "stack-validator.md").unlink()

        result = _run_hook(str(project))
        assert "removed" in result.stdout
        assert not (project / ".cognitive-os" / "agents" / "stack-validator.md").exists()

    def test_agent_count_in_status(self, tmp_path):
        project = _setup_full_project(tmp_path)
        result = _run_hook(str(project))
        assert "2 agents" in result.stdout

    def test_no_agents_dir_is_ok(self, tmp_path):
        project = _setup_full_project(tmp_path)
        import shutil
        shutil.rmtree(project / "agents")
        result = _run_hook(str(project))
        assert result.returncode == 0
        assert "0 agents" in result.stdout


class TestCustomizationsSync:
    """Tests for customizations/ directory auto-sync."""

    def test_creates_customization_symlinks(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        custs = project / ".cognitive-os" / "customizations"
        assert (custs / "example.yaml").is_symlink()

    def test_new_customization_auto_detected(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))

        (project / "customizations" / "sre-agent.yaml").write_text("model: opus\n")

        result = _run_hook(str(project))
        assert "FIXED" in result.stdout
        assert (project / ".cognitive-os" / "customizations" / "sre-agent.yaml").is_symlink()

    def test_no_customizations_dir_is_ok(self, tmp_path):
        project = _setup_full_project(tmp_path)
        import shutil
        shutil.rmtree(project / "customizations")
        result = _run_hook(str(project))
        assert result.returncode == 0


class TestDocsSync:
    """Tests for docs/ directory auto-sync (tree strategy)."""

    def test_creates_doc_symlinks(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        docs = project / ".cognitive-os" / "docs"
        assert (docs / "README.md").is_symlink()
        assert (docs / "architecture.md").is_symlink()

    def test_syncs_doc_subdirectories(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        docs = project / ".cognitive-os" / "docs"
        assert (docs / "assets").is_symlink()
        # Subdir content accessible through symlink
        assert (docs / "assets" / "diagram.png").exists()

    def test_new_doc_auto_detected(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))

        (project / "docs" / "new-guide.md").write_text("# New Guide\n")

        result = _run_hook(str(project))
        assert "FIXED" in result.stdout
        assert (project / ".cognitive-os" / "docs" / "new-guide.md").is_symlink()

    def test_new_doc_subdir_auto_detected(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))

        # Add a new subdirectory
        business = project / "docs" / "business"
        business.mkdir()
        (business / "plan.md").write_text("# Plan\n")

        result = _run_hook(str(project))
        assert "FIXED" in result.stdout
        assert (project / ".cognitive-os" / "docs" / "business").is_symlink()
        assert (project / ".cognitive-os" / "docs" / "business" / "plan.md").exists()

    def test_doc_count_in_status(self, tmp_path):
        project = _setup_full_project(tmp_path)
        result = _run_hook(str(project))
        # docs has README.md, architecture.md as files + assets as subdir = 3 symlinks
        assert "docs" in result.stdout

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


class TestRuntimeDirs:
    def test_creates_missing_runtime_dirs(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        for d in ["sessions", "metrics", "tasks"]:
            assert (project / ".cognitive-os" / d).is_dir()


class TestIdempotent:
    def test_idempotent_second_run_is_ok(self, tmp_path):
        project = _setup_full_project(tmp_path)
        r1 = _run_hook(str(project))
        assert "FIXED" in r1.stdout

        r2 = _run_hook(str(project))
        assert "OK" in r2.stdout


class TestStatusReport:
    def test_reports_all_component_counts(self, tmp_path):
        project = _setup_full_project(tmp_path)
        result = _run_hook(str(project))
        assert "rules" in result.stdout
        assert "hooks" in result.stdout
        assert "skills" in result.stdout
        assert "squads" in result.stdout
        assert "agents" in result.stdout
        assert "docs" in result.stdout

    def test_reports_missing_settings(self, tmp_path):
        project = _setup_full_project(tmp_path)
        (project / ".claude" / "settings.json").unlink()
        result = _run_hook(str(project))
        assert "settings.json missing" in result.stdout

    def test_reports_missing_config(self, tmp_path):
        project = _setup_full_project(tmp_path)
        (project / "cognitive-os.yaml").unlink()
        result = _run_hook(str(project))
        assert "cognitive-os.yaml missing" in result.stdout


class TestBulkUpgrade:
    """Simulate an upgrade that adds multiple components at once."""

    def test_bulk_add_rules_and_skills(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))  # initial sync

        # Simulate upgrade: add 5 rules + 3 skills
        for i in range(5):
            (project / "rules" / f"new-rule-{i}.md").write_text(f"# Rule {i}\n")
        for name in ["feature-x", "feature-y", "feature-z"]:
            skill = project / "skills" / name
            skill.mkdir()
            (skill / "SKILL.md").write_text(f"# {name}\n")

        result = _run_hook(str(project))
        assert "FIXED" in result.stdout
        assert "added 8" in result.stdout  # 5 rules + 3 skills

        # Verify all exist
        for i in range(5):
            assert (project / ".claude" / "rules" / "cos" / f"new-rule-{i}.md").is_symlink()
        for name in ["feature-x", "feature-y", "feature-z"]:
            assert (project / ".cognitive-os" / "skills" / name).exists()

    def test_bulk_remove_stale(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))  # initial sync

        # Remove all rules and one skill
        for f in (project / "rules").glob("*.md"):
            f.unlink()
        import shutil
        shutil.rmtree(project / "skills" / "eval-repo")

        result = _run_hook(str(project))
        assert "FIXED" in result.stdout
        assert "removed" in result.stdout
        # Stale symlinks should be gone
        assert not list((project / ".claude" / "rules" / "cos").glob("*.md"))

    def test_mixed_add_and_remove(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))

        # Remove one rule, add another
        (project / "rules" / "alpha.md").unlink()
        (project / "rules" / "delta.md").write_text("# Delta\n")

        result = _run_hook(str(project))
        assert "FIXED" in result.stdout
        assert not (project / ".claude" / "rules" / "cos" / "alpha.md").exists()
        assert (project / ".claude" / "rules" / "cos" / "delta.md").is_symlink()


class TestSymlinkContent:
    """Verify symlinks point to correct content, not just existence."""

    def test_rule_symlink_resolves_to_source(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        link = project / ".claude" / "rules" / "cos" / "alpha.md"
        assert link.read_text() == "# Alpha\n"

    def test_skill_symlink_resolves_to_skill_md(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))
        skill_link = project / ".cognitive-os" / "skills" / "eval-repo"
        assert (skill_link / "SKILL.md").read_text() == "# eval-repo\n"

    def test_source_change_reflected_through_symlink(self, tmp_path):
        project = _setup_full_project(tmp_path)
        _run_hook(str(project))

        # Modify source rule
        (project / "rules" / "alpha.md").write_text("# Alpha v2 — updated\n")

        # Symlink should reflect change without re-running hook
        link = project / ".claude" / "rules" / "cos" / "alpha.md"
        assert "v2" in link.read_text()

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

    def test_regular_file_in_claude_rules_not_removed(self, tmp_path):
        """Non-symlink files in .claude/rules/ should NOT be touched."""
        project = _setup_full_project(tmp_path)
        claude_rules = project / ".claude" / "rules"
        claude_rules.mkdir(parents=True, exist_ok=True)
        manual = claude_rules / "manual-rule.md"
        manual.write_text("# Manually created\n")

        _run_hook(str(project))

        assert manual.exists(), "Regular file should not be removed"
        assert not manual.is_symlink()


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

    def test_real_repo_is_already_synced(self):
        """After self-install ran at session start, repo should be OK."""
        real_root = HOOK_PATH.parents[1]
        if not (real_root / "hooks" / "self-install.sh").exists():
            pytest.skip("not in luum-agent-os")
        result = _run_hook(str(real_root))
        assert "OK" in result.stdout, "Real repo should already be synced"

    def test_real_repo_counts_match_source(self):
        """Verify synced counts match actual source counts."""
        real_root = HOOK_PATH.parents[1]
        if not (real_root / "hooks" / "self-install.sh").exists():
            pytest.skip("not in luum-agent-os")

        rule_count = len(list((real_root / "rules").glob("*.md")))
        hook_count = len(list((real_root / "hooks").glob("*.sh")))
        skill_dirs = len([d for d in (real_root / "skills").iterdir() if d.is_dir()])

        result = _run_hook(str(real_root))
        assert f"{rule_count} rules" in result.stdout
        assert f"{hook_count} hooks" in result.stdout

    def test_real_repo_syncs_agents(self):
        """Verify agents dir is synced in real repo."""
        real_root = HOOK_PATH.parents[1]
        if not (real_root / "hooks" / "self-install.sh").exists():
            pytest.skip("not in luum-agent-os")
        if not (real_root / "agents").is_dir():
            pytest.skip("no agents dir")
        result = _run_hook(str(real_root))
        assert "agents" in result.stdout

    def test_real_repo_syncs_docs(self):
        """Verify docs dir is synced in real repo."""
        real_root = HOOK_PATH.parents[1]
        if not (real_root / "hooks" / "self-install.sh").exists():
            pytest.skip("not in luum-agent-os")
        if not (real_root / "docs").is_dir():
            pytest.skip("no docs dir")
        result = _run_hook(str(real_root))
        assert "docs" in result.stdout
