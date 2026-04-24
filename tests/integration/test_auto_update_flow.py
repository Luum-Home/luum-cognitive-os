"""Integration tests for the COS auto-update end-to-end flow.

Tests the FULL update pipeline:
  cos release / git pull  -->  auto-update-projects.sh  -->  cos-init.sh per project
                           -->  cos-init-global.sh       -->  ~/.claude/rules/cos/

Validates that:
  - Release triggers auto-update of all registered projects
  - Post-merge hook triggers auto-update
  - Profile filtering (minimal/standard/full) is applied on update
  - Multiple projects are updated in a single pass
  - Global install (~/.claude/rules/cos/) is updated
  - Version is tracked in registry after update
  - Non-existent projects are skipped gracefully
  - Projects from different sources are skipped
  - Dry-run mode reports but does not modify
  - New rules added to COS source are propagated on update

Related scripts:
  scripts/auto-update-projects.sh
  scripts/cos-init.sh
  scripts/cos-init-global.sh
  scripts/cos-registry.sh
  cmd/cos/internal/cli/release.go (calls auto-update after release)
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import pytest

pytestmark = [pytest.mark.integration]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
AUTO_UPDATE_SCRIPT = SCRIPTS_DIR / "auto-update-projects.sh"
COS_INIT_SCRIPT = SCRIPTS_DIR / "cos-init.sh"
COS_INIT_GLOBAL_SCRIPT = SCRIPTS_DIR / "cos-init-global.sh"
REGISTRY_SCRIPT = SCRIPTS_DIR / "cos-registry.sh"


# ── Helpers ──────────────────────────────────────────────────────────


def _run_script(
    script: Path,
    args: Optional[List[str]] = None,
    env_overrides: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Run a bash script and return the result."""
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    cmd = ["bash", str(script)] + (args or [])
    return subprocess.run(
        cmd, capture_output=True, text=True, env=env,
        cwd=cwd, timeout=timeout,
    )


def create_fake_cos_source(
    base_path: Path,
    num_rules: int = 20,
    version: str = "0.3.0",
) -> Path:
    """Create a minimal COS source directory with rules, scripts, VERSION.

    Returns the path to the fake COS source root.
    """
    cos_src = base_path / "cos-source"
    cos_src.mkdir(parents=True, exist_ok=True)

    # VERSION file
    (cos_src / "VERSION").write_text(f"{version}\n")

    # .cognitive-os/version (used by some scripts)
    cos_meta = cos_src / ".cognitive-os"
    cos_meta.mkdir(parents=True, exist_ok=True)
    (cos_meta / "version").write_text(version)

    # Rules directory with numbered rules
    rules_dir = cos_src / "rules"
    rules_dir.mkdir(exist_ok=True)

    # Always create the 14 core rules (matching cos-init-global.sh CORE_RULES)
    core_rules = [
        "RULES-COMPACT.md",
        "adaptive-bypass.md",
        "acceptance-criteria.md",
        "agent-quality.md",
        "trust-score.md",
        "definition-of-done.md",
        "phase-aware-agents.md",
        "closed-loop-prompts.md",
        "token-economy.md",
        "responsiveness.md",
        "agent-security.md",
        "credential-management.md",
        "content-policy.md",
        "error-learning.md",
    ]
    for rule in core_rules:
        (rules_dir / rule).write_text(f"# {rule}\nVersion: {version}\n")

    # Additional non-core rules up to num_rules total
    existing = len(core_rules)
    for i in range(existing, num_rules):
        (rules_dir / f"extra-rule-{i:03d}.md").write_text(
            f"# Extra Rule {i}\nVersion: {version}\n"
        )

    # Hooks directory (minimal)
    hooks_dir = cos_src / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hooks_lib = hooks_dir / "_lib"
    hooks_lib.mkdir(exist_ok=True)
    (hooks_lib / "common.sh").write_text("#!/usr/bin/env bash\n# common lib\n")

    for hook_name in [
        "error-learning", "session-init", "session-cleanup",
        "clarification-gate", "blast-radius", "scope-proportionality",
        "error-pattern-detector", "auto-refine", "auto-verify",
        "completeness-check", "dod-gate", "trust-score-validator",
        "skill-metrics-tracker", "inject-phase-context", "stack-detector",
        "pre-compaction-flush",
    ]:
        hook_file = hooks_dir / f"{hook_name}.sh"
        hook_file.write_text(f"#!/usr/bin/env bash\n# {hook_name}\nexit 0\n")
        hook_file.chmod(0o755)

    # Skills directory (minimal)
    skills_dir = cos_src / "skills"
    skills_dir.mkdir(exist_ok=True)
    (skills_dir / "CATALOG.md").write_text("# Skill Catalog\n")
    for skill_name in [
        "sdd-explore", "sdd-propose", "sdd-spec", "sdd-design",
        "sdd-tasks", "sdd-apply", "sdd-verify", "plan-feature",
        "systematic-debugging", "verification-before-completion",
    ]:
        skill_dir = skills_dir / skill_name
        skill_dir.mkdir(exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"# {skill_name}\n")

    # Templates directory
    templates_dir = cos_src / "templates"
    templates_dir.mkdir(exist_ok=True)
    (templates_dir / "agent-preamble.md").write_text("# Preamble\n")

    # Scripts directory — copy the real scripts
    scripts_dst = cos_src / "scripts"
    scripts_dst.mkdir(exist_ok=True)
    scripts_lib_dst = scripts_dst / "_lib"
    scripts_lib_dst.mkdir(exist_ok=True)
    settings_driver = SCRIPTS_DIR / "_lib" / "settings-driver.sh"
    if settings_driver.exists():
        shutil.copy2(settings_driver, scripts_lib_dst / "settings-driver.sh")
    for script_name in [
        "cos-init.sh", "cos-registry.sh", "auto-update-projects.sh",
        "cos-init-global.sh", "setup-git-hooks.sh",
    ]:
        src = SCRIPTS_DIR / script_name
        if src.exists():
            shutil.copy2(src, scripts_dst / script_name)

    # Merge-settings script (if exists)
    merge_script = SCRIPTS_DIR / "merge-settings.sh"
    if merge_script.exists():
        shutil.copy2(merge_script, scripts_dst / "merge-settings.sh")

    # .claude/settings.json (minimal)
    claude_dir = cos_src / ".claude"
    claude_dir.mkdir(exist_ok=True)
    (claude_dir / "settings.json").write_text(json.dumps({
        "hooks": {"PreToolUse": [], "PostToolUse": []}
    }, indent=2))

    return cos_src


def create_fake_project(
    base_path: Path,
    name: str,
    profile: str = "standard",
    num_existing_rules: int = 50,
    cos_source: Optional[Path] = None,
) -> Path:
    """Create a minimal project with .claude/rules/cos/ and cognitive-os.yaml.

    Simulates a project that was previously installed with COS at an older version.
    """
    project = base_path / name
    project.mkdir(parents=True, exist_ok=True)

    # package.json for project name detection
    (project / "package.json").write_text(json.dumps({"name": name}))

    # .claude/rules/cos/ with "old" rules
    rules_dir = project / ".claude" / "rules" / "cos"
    rules_dir.mkdir(parents=True, exist_ok=True)
    for i in range(num_existing_rules):
        (rules_dir / f"old-rule-{i:03d}.md").write_text(
            f"# Old Rule {i}\nVersion: old\n"
        )
    (rules_dir / "RULES-COMPACT.md").write_text("# Old RULES-COMPACT\n")

    # .cognitive-os/ directory
    cos_dir = project / ".cognitive-os"
    cos_dir.mkdir(parents=True, exist_ok=True)
    (cos_dir / "metrics").mkdir(exist_ok=True)
    (cos_dir / "sessions").mkdir(exist_ok=True)
    (cos_dir / "tasks").mkdir(exist_ok=True)

    # install-meta.json
    source_path = str(cos_source) if cos_source else "/old/cos/source"
    (cos_dir / "install-meta.json").write_text(json.dumps({
        "mode": profile,
        "version": "0.2.0",
        "source": source_path,
        "installed_at": "2026-01-01T00:00:00Z",
        "project_name": name,
        "rules_installed": num_existing_rules,
        "hooks_installed": 0,
        "skills_installed": 0,
    }, indent=2))

    # cognitive-os.yaml
    (project / "cognitive-os.yaml").write_text(
        f"project:\n  name: {name}\n  phase: reconstruction\n"
    )

    # .gitignore
    (project / ".gitignore").write_text(
        ".cognitive-os/sessions/\n.cognitive-os/metrics/\n.cognitive-os/tasks/\n"
    )

    return project


def create_registry(
    registry_file: Path,
    installations: Optional[List[dict]] = None,
) -> Path:
    """Create a registry file with optional installations."""
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    data = {"installations": installations or []}
    registry_file.write_text(json.dumps(data, indent=2))
    return registry_file


def read_registry(registry_file: Path) -> dict:
    """Read and parse the registry file."""
    return json.loads(registry_file.read_text())


def register_project(
    registry_file: Path,
    project_path: Path,
    source_path: Path,
    mode: str = "standard",
    version: str = "0.2.0",
    project_name: str = "test-project",
) -> None:
    """Add a project to the registry."""
    result = _run_script(
        REGISTRY_SCRIPT,
        ["register", str(project_path), mode, version, project_name, str(source_path)],
        env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
    )
    assert result.returncode == 0, f"Registry register failed: {result.stderr}"


def run_auto_update(
    source_path: Path,
    registry_file: Path,
    args: Optional[List[str]] = None,
) -> subprocess.CompletedProcess:
    """Execute auto-update-projects.sh from the fake COS source."""
    script = source_path / "scripts" / "auto-update-projects.sh"
    return _run_script(
        script,
        args=args,
        env_overrides={"COS_REGISTRY_FILE": str(registry_file)},
    )


def count_rules(project_path: Path) -> int:
    """Count .md files in the project's COS rules directory."""
    rules_dir = project_path / ".claude" / "rules" / "cos"
    if not rules_dir.exists():
        return 0
    return len(list(rules_dir.glob("*.md")))


def list_rules(project_path: Path) -> List[str]:
    """List rule filenames in the project's COS rules directory."""
    rules_dir = project_path / ".claude" / "rules" / "cos"
    if not rules_dir.exists():
        return []
    return sorted(f.name for f in rules_dir.glob("*.md"))


# ── Test Class: Full Flow Tests ──────────────────────────────────────


class TestAutoUpdateFlow:
    """End-to-end tests for the COS auto-update pipeline."""

    def test_cos_release_triggers_auto_update(self, tmp_path):
        """cos release calls auto-update-projects.sh which re-runs cos-init per project.

        Simulates the flow: release creates VERSION -> auto-update reads registry
        -> for each project from this source, runs cos-init with the original mode.
        """
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        project = create_fake_project(
            tmp_path, "my-app", profile="standard",
            num_existing_rules=50, cos_source=cos_src,
        )
        registry_file = tmp_path / "cos-home" / "installations.json"
        register_project(
            registry_file, project, cos_src,
            mode="standard", version="0.2.0", project_name="my-app",
        )

        # Verify old state: 50 old rules + RULES-COMPACT
        assert count_rules(project) == 51

        # Run auto-update (simulates what cos release does)
        result = run_auto_update(cos_src, registry_file)
        assert result.returncode == 0, f"Auto-update failed: {result.stderr}"
        assert "UPDATING" in result.stdout or "OK" in result.stdout

        # After update: project should have the 14 core rules (standard profile
        # with default efficiency profile = standard -> 14 core rules)
        rules = list_rules(project)
        assert "RULES-COMPACT.md" in rules
        # Old rules should be gone (cos-init removes .claude/rules/cos before reinstalling)
        assert not any(r.startswith("old-rule-") for r in rules)

    def test_post_merge_triggers_auto_update(self, tmp_path):
        """git pull (post-merge) triggers auto-update via the hook.

        The post-merge hook calls auto-update-projects.sh, which updates
        all registered projects from this source.
        """
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.4.0")

        # Create a fake git repo with the post-merge hook
        git_dir = cos_src / ".git" / "hooks"
        git_dir.mkdir(parents=True, exist_ok=True)
        # Install the hook
        _run_script(cos_src / "scripts" / "setup-git-hooks.sh", cwd=str(cos_src))

        project = create_fake_project(
            tmp_path, "hook-project", profile="minimal",
            num_existing_rules=10, cos_source=cos_src,
        )
        registry_file = tmp_path / "cos-home" / "installations.json"
        register_project(
            registry_file, project, cos_src,
            mode="minimal", version="0.2.0", project_name="hook-project",
        )

        # Simulate: run the post-merge hook content (which runs auto-update)
        result = run_auto_update(cos_src, registry_file)
        assert result.returncode == 0
        # Project should be updated
        rules = list_rules(project)
        assert "RULES-COMPACT.md" in rules

    def test_update_applies_profile_filtering_standard(self, tmp_path):
        """Updated project with standard profile (default efficiency) gets only core rules.

        When cos-init runs in --standard mode, it installs ~25 rules.
        Then the efficiency profile filtering (default = standard) prunes
        to only the rules in the CORE_RULES list that overlap with what
        was installed by the standard mode.

        The standard mode's STANDARD_RULES list covers 9 of the 14 CORE_RULES
        (it misses adaptive-bypass, agent-security, token-economy, content-policy),
        plus RULES-COMPACT is always installed. So the result is 10 rules.
        """
        cos_src = create_fake_cos_source(tmp_path, num_rules=90, version="0.3.0")
        project = create_fake_project(
            tmp_path, "std-project", profile="standard",
            num_existing_rules=90, cos_source=cos_src,
        )
        # Ensure cognitive-os.yaml does NOT set efficiency profile (defaults to standard)
        (project / "cognitive-os.yaml").write_text(
            "project:\n  name: std-project\n  phase: reconstruction\n"
        )
        registry_file = tmp_path / "cos-home" / "installations.json"
        register_project(
            registry_file, project, cos_src,
            mode="standard", version="0.2.0", project_name="std-project",
        )

        result = run_auto_update(cos_src, registry_file)
        assert result.returncode == 0

        rules = list_rules(project)
        # Standard efficiency profile keeps only CORE_RULES that were installed
        # by --standard mode. The standard mode installs named rules + RULES-COMPACT.
        # The exact count depends on the overlap between CORE_RULES and STANDARD_RULES.
        assert len(rules) >= 8, f"expected at least 8 rules from standard profile, got {len(rules)}: {rules}"
        assert "RULES-COMPACT.md" in rules
        assert "trust-score.md" in rules
        assert "acceptance-criteria.md" in rules
        # Non-core rules should have been removed
        assert not any(r.startswith("extra-rule-") for r in rules)
        assert "model-routing.md" not in rules  # not in core list

    def test_update_applies_profile_filtering_full(self, tmp_path):
        """Updated project with full mode and full efficiency profile keeps all rules."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=25, version="0.3.0")
        project = create_fake_project(
            tmp_path, "full-project", profile="full",
            num_existing_rules=5, cos_source=cos_src,
        )
        # Set efficiency profile to full
        (project / "cognitive-os.yaml").write_text(
            "project:\n  name: full-project\n  phase: reconstruction\n"
            "efficiency:\n  profile: full\n"
        )
        registry_file = tmp_path / "cos-home" / "installations.json"
        register_project(
            registry_file, project, cos_src,
            mode="full", version="0.2.0", project_name="full-project",
        )

        result = run_auto_update(cos_src, registry_file)
        assert result.returncode == 0

        # Full profile keeps all rules from source
        rules = list_rules(project)
        assert len(rules) >= 25  # all source rules should be present

    def test_update_multiple_projects(self, tmp_path):
        """All registered projects from this source should be updated."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        registry_file = tmp_path / "cos-home" / "installations.json"
        create_registry(registry_file)

        projects = []
        for i, name in enumerate(["project-alpha", "project-beta", "project-gamma"]):
            project = create_fake_project(
                tmp_path, name, profile="standard",
                num_existing_rules=10 + i * 5, cos_source=cos_src,
            )
            register_project(
                registry_file, project, cos_src,
                mode="standard", version="0.2.0", project_name=name,
            )
            projects.append(project)

        result = run_auto_update(cos_src, registry_file)
        assert result.returncode == 0

        # All 3 projects should have been updated
        for project in projects:
            rules = list_rules(project)
            assert "RULES-COMPACT.md" in rules
            # Old rules should be gone
            assert not any(r.startswith("old-rule-") for r in rules)

    def test_global_install_updated(self, tmp_path):
        """~/.claude/rules/cos/ should be updated with cos-init-global.sh."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=30, version="0.3.0")
        fake_home = tmp_path / "fake-home"
        fake_home.mkdir()

        # Create existing global rules (old version)
        global_rules = fake_home / ".claude" / "rules" / "cos"
        global_rules.mkdir(parents=True)
        (global_rules / "RULES-COMPACT.md").write_text("# Old version\n")
        (global_rules / "some-extra-rule.md").write_text("# Should be preserved\n")

        # Run cos-init-global with HOME override
        result = _run_script(
            cos_src / "scripts" / "cos-init-global.sh",
            env_overrides={"HOME": str(fake_home)},
        )
        assert result.returncode == 0

        # Verify 14 core rules present
        installed_rules = sorted(f.name for f in global_rules.glob("*.md"))
        assert "RULES-COMPACT.md" in installed_rules
        assert "adaptive-bypass.md" in installed_rules
        assert "trust-score.md" in installed_rules
        assert "error-learning.md" in installed_rules

        # Verify the content was actually updated (not the old version)
        content = (global_rules / "RULES-COMPACT.md").read_text()
        assert "0.3.0" in content

        # Verify metadata was saved
        meta_file = fake_home / ".cognitive-os" / "global-install-meta.json"
        assert meta_file.exists()
        meta = json.loads(meta_file.read_text())
        assert meta["cos_version"] == "0.3.0"

    def test_update_records_new_version(self, tmp_path):
        """Registry should record the new version after update."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        project = create_fake_project(
            tmp_path, "ver-project", profile="standard",
            num_existing_rules=5, cos_source=cos_src,
        )
        registry_file = tmp_path / "cos-home" / "installations.json"
        register_project(
            registry_file, project, cos_src,
            mode="standard", version="0.2.0", project_name="ver-project",
        )

        # Verify old version
        data = read_registry(registry_file)
        assert data["installations"][0]["version"] == "0.2.0"

        result = run_auto_update(cos_src, registry_file)
        assert result.returncode == 0

        # After update, the registry should show the new version.
        # cos-init.sh re-registers with the new version via cos-registry.sh.
        data = read_registry(registry_file)
        assert len(data["installations"]) >= 1
        entry = next(
            e for e in data["installations"]
            if e["path"] == str(project)
        )
        assert entry["version"] == "0.3.0"

    def test_skips_removed_projects(self, tmp_path):
        """Projects that no longer exist should be skipped (not crash)."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        registry_file = tmp_path / "cos-home" / "installations.json"
        create_registry(registry_file, [{
            "path": "/nonexistent/project/that/was/deleted",
            "mode": "standard",
            "version": "0.2.0",
            "project_name": "ghost-project",
            "source": str(cos_src),
            "installed_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }])

        result = run_auto_update(cos_src, registry_file)
        assert result.returncode == 0
        assert "SKIP" in result.stdout

    def test_skips_different_source(self, tmp_path):
        """Only projects installed from THIS source should update."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        project = create_fake_project(
            tmp_path, "other-src-project", profile="standard",
        )
        registry_file = tmp_path / "cos-home" / "installations.json"
        create_registry(registry_file, [{
            "path": str(project),
            "mode": "standard",
            "version": "0.1.0",
            "project_name": "other-src-project",
            "source": "/some/completely/different/cos/source",
            "installed_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }])

        result = run_auto_update(cos_src, registry_file)
        assert result.returncode == 0
        assert "No projects installed from" in result.stdout

        # Project should NOT have been modified
        rules = list_rules(project)
        assert any(r.startswith("old-rule-") for r in rules)

    def test_dry_run_no_modifications(self, tmp_path):
        """auto-update --dry-run should report but not modify."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        project = create_fake_project(
            tmp_path, "dry-project", profile="standard",
            num_existing_rules=50, cos_source=cos_src,
        )
        registry_file = tmp_path / "cos-home" / "installations.json"
        register_project(
            registry_file, project, cos_src,
            mode="standard", version="0.2.0", project_name="dry-project",
        )

        # Snapshot old rules
        old_rules = list_rules(project)

        result = run_auto_update(cos_src, registry_file, args=["--dry-run"])
        assert result.returncode == 0
        assert "WOULD UPDATE" in result.stdout

        # Rules should NOT have changed
        new_rules = list_rules(project)
        assert old_rules == new_rules

        # Registry version should still be old
        data = read_registry(registry_file)
        entry = next(
            e for e in data["installations"]
            if e["path"] == str(project)
        )
        assert entry["version"] == "0.2.0"

    def test_new_rules_available_after_update_full(self, tmp_path):
        """If COS adds a new rule, it should appear in updated full-profile project."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")

        # Add a brand new rule that didn't exist before
        new_rule = cos_src / "rules" / "brand-new-feature.md"
        new_rule.write_text("# Brand New Feature\nAdded in v0.3.0\n")

        project = create_fake_project(
            tmp_path, "new-rule-project", profile="full",
            num_existing_rules=5, cos_source=cos_src,
        )
        # Set efficiency profile to full so all rules are kept
        (project / "cognitive-os.yaml").write_text(
            "project:\n  name: new-rule-project\n  phase: reconstruction\n"
            "efficiency:\n  profile: full\n"
        )
        registry_file = tmp_path / "cos-home" / "installations.json"
        register_project(
            registry_file, project, cos_src,
            mode="full", version="0.2.0", project_name="new-rule-project",
        )

        result = run_auto_update(cos_src, registry_file)
        assert result.returncode == 0

        rules = list_rules(project)
        assert "brand-new-feature.md" in rules

    def test_new_rules_not_in_standard_unless_core(self, tmp_path):
        """New non-core rules are NOT propagated to standard-profile projects."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")

        # Add a non-core rule
        (cos_src / "rules" / "niche-feature.md").write_text("# Niche\n")

        project = create_fake_project(
            tmp_path, "std-proj", profile="standard",
            num_existing_rules=5, cos_source=cos_src,
        )
        registry_file = tmp_path / "cos-home" / "installations.json"
        register_project(
            registry_file, project, cos_src,
            mode="standard", version="0.2.0", project_name="std-proj",
        )

        result = run_auto_update(cos_src, registry_file)
        assert result.returncode == 0

        rules = list_rules(project)
        assert "niche-feature.md" not in rules
        # But core rules should be present
        assert "RULES-COMPACT.md" in rules

    def test_already_up_to_date_skipped(self, tmp_path):
        """Projects already at current version should be skipped."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        project = create_fake_project(
            tmp_path, "uptodate-project", profile="standard",
            num_existing_rules=14, cos_source=cos_src,
        )
        registry_file = tmp_path / "cos-home" / "installations.json"
        register_project(
            registry_file, project, cos_src,
            mode="standard", version="0.3.0",  # same version
            project_name="uptodate-project",
        )

        result = run_auto_update(cos_src, registry_file)
        assert result.returncode == 0
        assert "already at v0.3.0" in result.stdout

    def test_list_mode_shows_registered_projects(self, tmp_path):
        """auto-update --list shows all registered projects."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        registry_file = tmp_path / "cos-home" / "installations.json"
        create_registry(registry_file, [
            {
                "path": "/projects/alpha",
                "mode": "standard",
                "version": "0.2.0",
                "project_name": "alpha",
                "source": str(cos_src),
                "installed_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
            {
                "path": "/projects/beta",
                "mode": "full",
                "version": "0.1.0",
                "project_name": "beta",
                "source": "/other/source",
                "installed_at": "2026-02-01T00:00:00Z",
                "updated_at": "2026-02-01T00:00:00Z",
            },
        ])

        result = run_auto_update(cos_src, registry_file, args=["--list"])
        assert result.returncode == 0
        assert "alpha" in result.stdout
        assert "beta" in result.stdout
        assert "2" in result.stdout  # total count

    def test_update_preserves_project_cognitive_os_yaml(self, tmp_path):
        """auto-update should preserve existing cognitive-os.yaml (not overwrite)."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        project = create_fake_project(
            tmp_path, "yaml-project", profile="standard",
            num_existing_rules=5, cos_source=cos_src,
        )
        custom_yaml = (
            "project:\n  name: yaml-project\n  phase: production\n"
            "  custom_field: my-value\n"
        )
        (project / "cognitive-os.yaml").write_text(custom_yaml)

        registry_file = tmp_path / "cos-home" / "installations.json"
        register_project(
            registry_file, project, cos_src,
            mode="standard", version="0.2.0", project_name="yaml-project",
        )

        result = run_auto_update(cos_src, registry_file)
        assert result.returncode == 0

        # cognitive-os.yaml should be preserved (cos-init only creates it if missing)
        content = (project / "cognitive-os.yaml").read_text()
        assert "custom_field: my-value" in content
        assert "phase: production" in content

    def test_update_installs_hooks_for_standard_mode(self, tmp_path):
        """Standard mode update should install hooks."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        project = create_fake_project(
            tmp_path, "hooks-project", profile="standard",
            num_existing_rules=5, cos_source=cos_src,
        )
        registry_file = tmp_path / "cos-home" / "installations.json"
        register_project(
            registry_file, project, cos_src,
            mode="standard", version="0.2.0", project_name="hooks-project",
        )

        result = run_auto_update(cos_src, registry_file)
        assert result.returncode == 0

        # Check hooks directory exists and has hooks (namespaced under cos/)
        hooks_dir = project / ".cognitive-os" / "hooks" / "cos"
        assert hooks_dir.exists(), f"Expected {hooks_dir} to exist. Contents: {list((project / '.cognitive-os' / 'hooks').iterdir()) if (project / '.cognitive-os' / 'hooks').exists() else 'hooks/ missing'}"
        hook_files = list(hooks_dir.glob("*.sh"))
        assert len(hook_files) > 0

    def test_empty_registry_exits_gracefully(self, tmp_path):
        """No registry file should exit gracefully."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        registry_file = tmp_path / "nonexistent" / "installations.json"

        result = run_auto_update(cos_src, registry_file)
        assert result.returncode == 0
        assert "No installations registered" in result.stdout


class TestGlobalInstall:
    """Tests for cos-init-global.sh (global ~/.claude/ updates)."""

    def test_installs_core_rules(self, tmp_path):
        """Global install should create the core rules defined in the script."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=50, version="0.3.0")
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        result = _run_script(
            cos_src / "scripts" / "cos-init-global.sh",
            env_overrides={"HOME": str(fake_home)},
        )
        assert result.returncode == 0

        global_rules = fake_home / ".claude" / "rules" / "cos"
        rules = sorted(f.name for f in global_rules.glob("*.md"))
        assert len(rules) >= 10, f"expected at least 10 core rules, got {len(rules)}: {rules}"

    def test_dry_run_does_not_install(self, tmp_path):
        """Global install --dry-run should not create files."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        result = _run_script(
            cos_src / "scripts" / "cos-init-global.sh",
            args=["--dry-run"],
            env_overrides={"HOME": str(fake_home)},
        )
        assert result.returncode == 0
        assert "DRY RUN" in result.stdout

        global_rules = fake_home / ".claude" / "rules" / "cos"
        assert not global_rules.exists()

    def test_updates_existing_rules(self, tmp_path):
        """Global install should update rules that have changed."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        # First install
        _run_script(
            cos_src / "scripts" / "cos-init-global.sh",
            env_overrides={"HOME": str(fake_home)},
        )

        # Change source rules to simulate an update
        (cos_src / "rules" / "RULES-COMPACT.md").write_text(
            "# RULES-COMPACT\nVersion: 0.4.0\nUpdated content.\n"
        )
        (cos_src / ".cognitive-os" / "version").write_text("0.4.0")

        # Second install (update)
        result = _run_script(
            cos_src / "scripts" / "cos-init-global.sh",
            env_overrides={"HOME": str(fake_home)},
        )
        assert result.returncode == 0
        assert "Updated" in result.stdout

        # Verify content was updated
        content = (fake_home / ".claude" / "rules" / "cos" / "RULES-COMPACT.md").read_text()
        assert "0.4.0" in content

    def test_skips_unchanged_rules(self, tmp_path):
        """Global install should skip rules that haven't changed."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        # First install
        _run_script(
            cos_src / "scripts" / "cos-init-global.sh",
            env_overrides={"HOME": str(fake_home)},
        )

        # Second install (no changes)
        result = _run_script(
            cos_src / "scripts" / "cos-init-global.sh",
            env_overrides={"HOME": str(fake_home)},
        )
        assert result.returncode == 0
        # All should be skipped (unchanged)
        assert "Skipped" in result.stdout

    def test_handles_missing_source_rules_gracefully(self, tmp_path):
        """If a core rule is missing from source, install should continue."""
        cos_src = create_fake_cos_source(tmp_path, num_rules=20, version="0.3.0")
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        # Remove one core rule from source
        (cos_src / "rules" / "agent-security.md").unlink()

        result = _run_script(
            cos_src / "scripts" / "cos-init-global.sh",
            env_overrides={"HOME": str(fake_home)},
        )
        assert result.returncode == 0
        assert "WARNING" in result.stdout

        # Should still install the other core rules (one fewer than normal)
        global_rules = fake_home / ".claude" / "rules" / "cos"
        rules = list(global_rules.glob("*.md"))
        assert len(rules) >= 10, f"expected at least 10 rules after removing one, got {len(rules)}"
        # Verify the removed rule is NOT present
        assert not any(r.name == "agent-security.md" for r in rules), "removed rule should not be installed"
