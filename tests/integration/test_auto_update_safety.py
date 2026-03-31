"""Integration tests for CRITICAL safety scenarios in auto-update and cos-init.

Root cause of the original bug:
  /project/.cognitive-os was a SYMLINK pointing to the COS source directory.
  When auto-update ran `rm -rf .cognitive-os/hooks` inside the project, it
  followed the symlink and destroyed the COS source's hooks/, skills/, and
  templates/ directories — 228 files lost.

Fixes validated by these tests:
  1. auto-update-projects.sh detects symlinks and replaces them before rm -rf.
  2. auto-update-projects.sh uses namespaced cos/ subdirectories for rm -rf.
  3. cos-init.sh detects symlinks and replaces them before mkdir -p.
  4. cos-init.sh installs to namespaced paths (.cognitive-os/hooks/cos/, etc.).

Related scripts:
  scripts/auto-update-projects.sh
  scripts/cos-init.sh
  scripts/cos-registry.sh
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


# ── Helpers ──────────────────────────────────────────────────────────


def _run_script(
    script: Path,
    args: Optional[List[str]] = None,
    env_overrides: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Run a bash script and return the result.

    Automatically isolates the COS registry to a temp file to prevent
    test pollution of ~/.cognitive-os/installations.json.
    """
    env = os.environ.copy()
    # Isolate registry: use cwd-based temp file to avoid polluting global registry
    if "COS_REGISTRY_FILE" not in (env_overrides or {}):
        _cwd = cwd or os.getcwd()
        env["COS_REGISTRY_FILE"] = os.path.join(_cwd, ".cos-test-registry.json")
    if env_overrides:
        env.update(env_overrides)
    cmd = ["bash", str(script)] + (args or [])
    return subprocess.run(
        cmd, capture_output=True, text=True, env=env,
        cwd=cwd, timeout=timeout,
    )


def create_fake_cos_source(base_path: Path, version: str = "0.3.0") -> Path:
    """Create a minimal fake COS source directory with scripts, rules, hooks,
    skills, and templates.

    Returns the path to the fake COS source root.
    """
    cos_src = base_path / "cos-source"
    cos_src.mkdir(parents=True, exist_ok=True)

    # VERSION file
    (cos_src / "VERSION").write_text(f"{version}\n")

    # .cognitive-os/version
    cos_meta = cos_src / ".cognitive-os"
    cos_meta.mkdir(parents=True, exist_ok=True)
    (cos_meta / "version").write_text(version)

    # Rules directory with core rules
    rules_dir = cos_src / "rules"
    rules_dir.mkdir(exist_ok=True)
    core_rules = [
        "RULES-COMPACT.md", "adaptive-bypass.md", "acceptance-criteria.md",
        "agent-quality.md", "trust-score.md", "definition-of-done.md",
        "phase-aware-agents.md", "closed-loop-prompts.md", "token-economy.md",
        "responsiveness.md", "agent-security.md", "credential-management.md",
        "content-policy.md", "error-learning.md",
    ]
    for rule in core_rules:
        (rules_dir / rule).write_text(f"# {rule}\nVersion: {version}\n")
    for i in range(5):
        (rules_dir / f"extra-rule-{i:03d}.md").write_text(
            f"# Extra Rule {i}\nVersion: {version}\n"
        )

    # Hooks directory
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

    # Skills directory
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
    (templates_dir / "quality-gates.md").write_text("# Quality Gates\n")

    # Scripts directory — copy real scripts so cos-init.sh works
    scripts_dst = cos_src / "scripts"
    scripts_dst.mkdir(exist_ok=True)
    for script_name in [
        "cos-init.sh", "cos-registry.sh", "auto-update-projects.sh",
        "merge-settings.sh",
    ]:
        src = SCRIPTS_DIR / script_name
        if src.exists():
            shutil.copy2(src, scripts_dst / script_name)

    # .claude/settings.json (minimal)
    claude_dir = cos_src / ".claude"
    claude_dir.mkdir(exist_ok=True)
    (claude_dir / "settings.json").write_text(json.dumps({
        "hooks": {"PreToolUse": [], "PostToolUse": []}
    }, indent=2))

    return cos_src


def create_registry(
    registry_path: Path,
    projects: List[Dict],
) -> None:
    """Create a COS installations registry file."""
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(
        {"installations": projects}, indent=2,
    ))


def count_files_recursive(directory: Path) -> int:
    """Count all files recursively under a directory."""
    if not directory.exists():
        return 0
    return sum(1 for _ in directory.rglob("*") if _.is_file())


def list_files_recursive(directory: Path) -> List[str]:
    """List all file paths relative to directory."""
    if not directory.exists():
        return []
    return sorted(str(f.relative_to(directory)) for f in directory.rglob("*") if f.is_file())


# ── Safety Tests (CRITICAL) ─────────────────────────────────────────


class TestAutoUpdateSymlinkSafety:
    """Tests that auto-update detects and handles symlinks safely,
    preventing the catastrophic bug where rm -rf followed symlinks
    into the COS source directory."""

    def test_auto_update_detects_symlink_to_source(self, tmp_path):
        """CRITICAL: If .cognitive-os is a symlink to COS source, auto-update
        must replace the symlink with a real directory, NOT delete source files.
        """
        # Create a fake COS source with real files
        cos_src = create_fake_cos_source(tmp_path, version="0.4.0")

        # Count source files before
        source_hooks_before = list_files_recursive(cos_src / "hooks")
        source_skills_before = list_files_recursive(cos_src / "skills")
        source_templates_before = list_files_recursive(cos_src / "templates")
        total_source_before = (
            count_files_recursive(cos_src / "hooks")
            + count_files_recursive(cos_src / "skills")
            + count_files_recursive(cos_src / "templates")
        )
        assert total_source_before > 0, "Fake COS source must have files"

        # Create a project where .cognitive-os is a SYMLINK to the source
        project = tmp_path / "victim-project"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({"name": "victim"}))

        # Create the dangerous symlink: project/.cognitive-os -> cos_src
        os.symlink(str(cos_src), str(project / ".cognitive-os"))
        # Also need .claude dir for rules
        (project / ".claude" / "rules" / "cos").mkdir(parents=True)

        # Create registry pointing auto-update at this project
        registry = tmp_path / "registry.json"
        create_registry(registry, [{
            "path": str(project),
            "mode": "standard",
            "version": "0.3.0",  # Older than source 0.4.0 to trigger update
            "project_name": "victim",
            "source": str(cos_src),
            "installed_at": "2026-01-01T00:00:00Z",
        }])

        # Run auto-update
        result = _run_script(
            cos_src / "scripts" / "auto-update-projects.sh",
            env_overrides={"COS_REGISTRY_FILE": str(registry)},
            cwd=str(cos_src),
        )

        # The COS source files MUST still be intact
        source_hooks_after = list_files_recursive(cos_src / "hooks")
        source_skills_after = list_files_recursive(cos_src / "skills")
        source_templates_after = list_files_recursive(cos_src / "templates")

        assert source_hooks_after == source_hooks_before, (
            f"COS source hooks were destroyed! Before: {len(source_hooks_before)}, "
            f"After: {len(source_hooks_after)}"
        )
        assert source_skills_after == source_skills_before, (
            f"COS source skills were destroyed! Before: {len(source_skills_before)}, "
            f"After: {len(source_skills_after)}"
        )
        assert source_templates_after == source_templates_before, (
            f"COS source templates were destroyed! Before: {len(source_templates_before)}, "
            f"After: {len(source_templates_after)}"
        )

        # The symlink should have been replaced with a real directory
        cognitive_os_path = project / ".cognitive-os"
        assert not cognitive_os_path.is_symlink(), (
            ".cognitive-os should no longer be a symlink after auto-update"
        )
        assert cognitive_os_path.is_dir(), (
            ".cognitive-os should be a real directory after auto-update"
        )

    def test_auto_update_preserves_cos_source_files(self, tmp_path):
        """Normal auto-update (no symlink) must not modify COS source files."""
        cos_src = create_fake_cos_source(tmp_path, version="0.4.0")

        # Snapshot all source files before update
        source_files_before = list_files_recursive(cos_src)

        # Create a normal project (no symlink)
        project = tmp_path / "normal-project"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({"name": "normal"}))
        (project / ".claude" / "rules" / "cos").mkdir(parents=True)
        cos_dir = project / ".cognitive-os"
        cos_dir.mkdir()
        (cos_dir / "install-meta.json").write_text(json.dumps({
            "mode": "standard", "version": "0.3.0",
            "source": str(cos_src),
        }))
        (cos_dir / "hooks" / "cos").mkdir(parents=True)
        (cos_dir / "skills" / "cos").mkdir(parents=True)
        (cos_dir / "templates" / "cos").mkdir(parents=True)

        # Register the project
        registry = tmp_path / "registry.json"
        create_registry(registry, [{
            "path": str(project),
            "mode": "standard",
            "version": "0.3.0",
            "project_name": "normal",
            "source": str(cos_src),
            "installed_at": "2026-01-01T00:00:00Z",
        }])

        _run_script(
            cos_src / "scripts" / "auto-update-projects.sh",
            env_overrides={"COS_REGISTRY_FILE": str(registry)},
            cwd=str(cos_src),
        )

        # Verify source is identical
        source_files_after = list_files_recursive(cos_src)
        assert source_files_after == source_files_before, (
            "COS source files were modified during auto-update"
        )


class TestAutoUpdateNamespacePreservation:
    """Tests that auto-update only removes cos/-namespaced files and
    preserves project-custom hooks, skills, templates, and rules."""

    def test_auto_update_preserves_project_custom_hooks(self, tmp_path):
        """Custom hooks outside cos/ namespace must survive auto-update.

        Note: install-meta.json is NOT created here because projects with
        install-meta.json and no cos/ subdir trigger a migration path that
        removes the entire hooks/ directory. This test validates the primary
        namespace isolation for already-namespaced projects.
        """
        cos_src = create_fake_cos_source(tmp_path, version="0.4.0")

        project = tmp_path / "custom-hooks-project"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({"name": "custom-hooks"}))
        (project / ".claude" / "rules" / "cos").mkdir(parents=True)

        cos_dir = project / ".cognitive-os"
        cos_dir.mkdir()

        # Create COS-managed hooks in cos/ namespace
        (cos_dir / "hooks" / "cos").mkdir(parents=True)
        (cos_dir / "hooks" / "cos" / "old-cos-hook.sh").write_text("#!/bin/bash\nexit 0\n")

        # Create project-custom hook OUTSIDE cos/ namespace
        custom_hook = cos_dir / "hooks" / "my-custom-hook.sh"
        custom_hook.write_text("#!/bin/bash\n# My custom hook\necho 'custom'\n")
        custom_hook.chmod(0o755)

        # Also a custom hook in a subdirectory
        (cos_dir / "hooks" / "project-hooks").mkdir()
        custom_hook2 = cos_dir / "hooks" / "project-hooks" / "deploy.sh"
        custom_hook2.write_text("#!/bin/bash\n# Deploy hook\n")

        registry = tmp_path / "registry.json"
        create_registry(registry, [{
            "path": str(project), "mode": "standard", "version": "0.3.0",
            "project_name": "custom-hooks", "source": str(cos_src),
            "installed_at": "2026-01-01T00:00:00Z",
        }])

        _run_script(
            cos_src / "scripts" / "auto-update-projects.sh",
            env_overrides={"COS_REGISTRY_FILE": str(registry)},
            cwd=str(cos_src),
        )

        # Custom hooks must survive
        assert (cos_dir / "hooks" / "my-custom-hook.sh").exists(), (
            "Custom hook my-custom-hook.sh was deleted by auto-update"
        )
        assert (cos_dir / "hooks" / "project-hooks" / "deploy.sh").exists(), (
            "Custom hook project-hooks/deploy.sh was deleted by auto-update"
        )

    def test_auto_update_preserves_project_custom_skills(self, tmp_path):
        """Custom skills outside cos/ namespace must survive auto-update."""
        cos_src = create_fake_cos_source(tmp_path, version="0.4.0")

        project = tmp_path / "custom-skills-project"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({"name": "custom-skills"}))
        (project / ".claude" / "rules" / "cos").mkdir(parents=True)

        cos_dir = project / ".cognitive-os"
        cos_dir.mkdir()

        # COS-managed skills
        (cos_dir / "skills" / "cos" / "sdd-apply").mkdir(parents=True)
        (cos_dir / "skills" / "cos" / "sdd-apply" / "SKILL.md").write_text("# old\n")

        # Project-custom skill OUTSIDE cos/ namespace
        custom_skill_dir = cos_dir / "skills" / "my-custom-skill"
        custom_skill_dir.mkdir(parents=True)
        (custom_skill_dir / "SKILL.md").write_text("# My Custom Skill\nDo special things.\n")

        registry = tmp_path / "registry.json"
        create_registry(registry, [{
            "path": str(project), "mode": "standard", "version": "0.3.0",
            "project_name": "custom-skills", "source": str(cos_src),
            "installed_at": "2026-01-01T00:00:00Z",
        }])

        _run_script(
            cos_src / "scripts" / "auto-update-projects.sh",
            env_overrides={"COS_REGISTRY_FILE": str(registry)},
            cwd=str(cos_src),
        )

        assert (custom_skill_dir / "SKILL.md").exists(), (
            "Custom skill my-custom-skill/SKILL.md was deleted by auto-update"
        )

    def test_auto_update_preserves_project_custom_templates(self, tmp_path):
        """Custom templates outside cos/ namespace must survive auto-update."""
        cos_src = create_fake_cos_source(tmp_path, version="0.4.0")

        project = tmp_path / "custom-templates-project"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({"name": "custom-templates"}))
        (project / ".claude" / "rules" / "cos").mkdir(parents=True)

        cos_dir = project / ".cognitive-os"
        cos_dir.mkdir()

        # COS-managed templates
        (cos_dir / "templates" / "cos").mkdir(parents=True)
        (cos_dir / "templates" / "cos" / "agent-preamble.md").write_text("# old\n")

        # Project-custom template OUTSIDE cos/ namespace
        custom_template = cos_dir / "templates" / "my-project-template.md"
        custom_template.write_text("# Project-Specific Template\nCustom instructions.\n")

        registry = tmp_path / "registry.json"
        create_registry(registry, [{
            "path": str(project), "mode": "standard", "version": "0.3.0",
            "project_name": "custom-templates", "source": str(cos_src),
            "installed_at": "2026-01-01T00:00:00Z",
        }])

        _run_script(
            cos_src / "scripts" / "auto-update-projects.sh",
            env_overrides={"COS_REGISTRY_FILE": str(registry)},
            cwd=str(cos_src),
        )

        assert custom_template.exists(), (
            "Custom template my-project-template.md was deleted by auto-update"
        )

    def test_auto_update_preserves_project_rules(self, tmp_path):
        """Custom rules outside cos/ namespace must survive auto-update."""
        cos_src = create_fake_cos_source(tmp_path, version="0.4.0")

        project = tmp_path / "custom-rules-project"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({"name": "custom-rules"}))

        # COS-managed rules in cos/ namespace
        (project / ".claude" / "rules" / "cos").mkdir(parents=True)
        (project / ".claude" / "rules" / "cos" / "trust-score.md").write_text("# old\n")

        # Project-custom rule OUTSIDE cos/ namespace
        custom_rule = project / ".claude" / "rules" / "architecture.md"
        custom_rule.write_text("# Architecture Rules\nProject-specific patterns.\n")

        another_custom = project / ".claude" / "rules" / "team-conventions.md"
        another_custom.write_text("# Team Conventions\nOur coding standards.\n")

        cos_dir = project / ".cognitive-os"
        cos_dir.mkdir()
        (cos_dir / "install-meta.json").write_text(json.dumps({
            "mode": "standard", "version": "0.3.0", "source": str(cos_src),
        }))
        (cos_dir / "hooks" / "cos").mkdir(parents=True)
        (cos_dir / "skills" / "cos").mkdir(parents=True)
        (cos_dir / "templates" / "cos").mkdir(parents=True)

        registry = tmp_path / "registry.json"
        create_registry(registry, [{
            "path": str(project), "mode": "standard", "version": "0.3.0",
            "project_name": "custom-rules", "source": str(cos_src),
            "installed_at": "2026-01-01T00:00:00Z",
        }])

        _run_script(
            cos_src / "scripts" / "auto-update-projects.sh",
            env_overrides={"COS_REGISTRY_FILE": str(registry)},
            cwd=str(cos_src),
        )

        assert custom_rule.exists(), (
            "Custom rule architecture.md was deleted by auto-update"
        )
        assert another_custom.exists(), (
            "Custom rule team-conventions.md was deleted by auto-update"
        )


# ── cos-init.sh Tests ───────────────────────────────────────────────


class TestCosInitSymlinkSafety:
    """Tests that cos-init detects and handles symlinks safely."""

    def test_cos_init_detects_cognitive_os_symlink(self, tmp_path):
        """CRITICAL: If .cognitive-os is a symlink, cos-init must replace it
        with a real directory before creating any subdirectories."""
        cos_src = create_fake_cos_source(tmp_path, version="0.4.0")

        project = tmp_path / "symlink-project"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({"name": "symlink-proj"}))

        # Create a target directory that would be the symlink destination
        symlink_target = tmp_path / "symlink-target"
        symlink_target.mkdir()
        (symlink_target / "existing-file.txt").write_text("should survive\n")

        # Create the dangerous symlink
        os.symlink(str(symlink_target), str(project / ".cognitive-os"))

        result = _run_script(
            cos_src / "scripts" / "cos-init.sh",
            args=["--standard"],
            cwd=str(project),
        )

        # The symlink must be replaced with a real directory
        cognitive_os_path = project / ".cognitive-os"
        assert not cognitive_os_path.is_symlink(), (
            ".cognitive-os should no longer be a symlink after cos-init"
        )
        assert cognitive_os_path.is_dir(), (
            ".cognitive-os should be a real directory after cos-init"
        )

        # The symlink target must not have been modified with COS subdirs
        target_contents = list_files_recursive(symlink_target)
        assert target_contents == ["existing-file.txt"], (
            f"Symlink target was modified by cos-init: {target_contents}"
        )

        # Output should contain the warning
        assert "symlink" in result.stdout.lower() or "symlink" in result.stderr.lower(), (
            "cos-init should warn about the symlink replacement"
        )

    def test_cos_init_detects_claude_symlink(self, tmp_path):
        """If .claude is a symlink, cos-init must replace it with a real directory."""
        cos_src = create_fake_cos_source(tmp_path, version="0.4.0")

        project = tmp_path / "claude-symlink-project"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({"name": "claude-sl"}))

        # Create symlink target
        symlink_target = tmp_path / "claude-symlink-target"
        symlink_target.mkdir()
        (symlink_target / "important-file.md").write_text("do not touch\n")

        # .claude is a symlink
        os.symlink(str(symlink_target), str(project / ".claude"))

        result = _run_script(
            cos_src / "scripts" / "cos-init.sh",
            args=["--standard"],
            cwd=str(project),
        )

        claude_path = project / ".claude"
        assert not claude_path.is_symlink(), (
            ".claude should no longer be a symlink after cos-init"
        )
        assert claude_path.is_dir(), (
            ".claude should be a real directory after cos-init"
        )

        # Symlink target unchanged
        target_contents = list_files_recursive(symlink_target)
        assert "important-file.md" in target_contents, (
            "Symlink target files were lost"
        )


class TestCosInitNamespacing:
    """Tests that cos-init installs to cos/ namespaced subdirectories."""

    def test_cos_init_installs_to_cos_namespace(self, tmp_path):
        """cos-init --standard must install all COS components under cos/ subdirs."""
        cos_src = create_fake_cos_source(tmp_path, version="0.4.0")

        project = tmp_path / "namespace-project"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({"name": "ns-proj"}))

        result = _run_script(
            cos_src / "scripts" / "cos-init.sh",
            args=["--standard"],
            cwd=str(project),
        )

        assert result.returncode == 0, (
            f"cos-init failed: stdout={result.stdout}, stderr={result.stderr}"
        )

        # Hooks must be under .cognitive-os/hooks/cos/
        hooks_cos = project / ".cognitive-os" / "hooks" / "cos"
        assert hooks_cos.is_dir(), "hooks/cos/ directory not created"
        hook_files = list(hooks_cos.glob("*.sh"))
        assert len(hook_files) > 0, "No hooks installed in cos/ namespace"

        # Skills must be under .cognitive-os/skills/cos/
        skills_cos = project / ".cognitive-os" / "skills" / "cos"
        assert skills_cos.is_dir(), "skills/cos/ directory not created"
        skill_dirs = [d for d in skills_cos.iterdir() if d.is_dir()]
        assert len(skill_dirs) > 0, "No skills installed in cos/ namespace"

        # Templates must be under .cognitive-os/templates/cos/
        templates_cos = project / ".cognitive-os" / "templates" / "cos"
        assert templates_cos.is_dir(), "templates/cos/ directory not created"
        template_files = list(templates_cos.glob("*.md"))
        assert len(template_files) > 0, "No templates installed in cos/ namespace"

        # Rules must be under .claude/rules/cos/
        rules_cos = project / ".claude" / "rules" / "cos"
        assert rules_cos.is_dir(), "rules/cos/ directory not created"
        rule_files = list(rules_cos.glob("*.md"))
        assert len(rule_files) > 0, "No rules installed in cos/ namespace"

        # Verify NO hooks/skills/templates installed outside cos/ namespace
        # (only the cos/ subdir should be there, plus possibly _lib from hooks)
        hooks_dir = project / ".cognitive-os" / "hooks"
        non_cos_hooks = [
            f for f in hooks_dir.iterdir()
            if f.name != "cos" and f.name != "_lib"
        ]
        assert len(non_cos_hooks) == 0, (
            f"Hooks installed outside cos/ namespace: {[f.name for f in non_cos_hooks]}"
        )

    def test_cos_init_does_not_modify_source(self, tmp_path):
        """Running cos-init must not modify the COS source directory."""
        cos_src = create_fake_cos_source(tmp_path, version="0.4.0")

        # Snapshot source files before
        source_files_before = list_files_recursive(cos_src)
        source_count_before = len(source_files_before)

        project = tmp_path / "safe-project"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({"name": "safe"}))

        result = _run_script(
            cos_src / "scripts" / "cos-init.sh",
            args=["--standard"],
            cwd=str(project),
        )

        assert result.returncode == 0, (
            f"cos-init failed: {result.stdout} {result.stderr}"
        )

        # Source must be unchanged
        source_files_after = list_files_recursive(cos_src)
        assert source_files_after == source_files_before, (
            f"COS source was modified by cos-init! "
            f"Before: {source_count_before} files, After: {len(source_files_after)} files. "
            f"Diff: added={set(source_files_after) - set(source_files_before)}, "
            f"removed={set(source_files_before) - set(source_files_after)}"
        )

    def test_cos_init_self_hosting_guard(self, tmp_path):
        """Running cos-init inside the COS source directory itself must fail."""
        cos_src = create_fake_cos_source(tmp_path, version="0.4.0")

        # Create the self-hosting guard file that cos-init checks for
        (cos_src / "hooks" / "self-install.sh").write_text("#!/bin/bash\n# self-install\n")

        result = _run_script(
            cos_src / "scripts" / "cos-init.sh",
            args=["--standard"],
            cwd=str(cos_src),
        )

        assert result.returncode != 0, (
            "cos-init should fail (non-zero exit) when run inside the COS source"
        )
        assert "cannot run" in result.stdout.lower() or "cannot run" in result.stderr.lower(), (
            f"Expected self-hosting guard message. stdout={result.stdout}, stderr={result.stderr}"
        )


# ── Integration Tests ────────────────────────────────────────────────


class TestFullUpdateCycle:
    """End-to-end tests for the full update lifecycle."""

    def test_full_update_cycle(self, tmp_path):
        """Register a project, run auto-update, verify: COS source intact,
        project has COS components, project custom files preserved.

        The project is set up WITHOUT install-meta.json to avoid triggering
        the migration path that deletes flat-layout directories. cos-init
        will create install-meta.json as part of the update.
        """
        cos_src = create_fake_cos_source(tmp_path, version="0.5.0")

        # Create a project with custom + COS content (already namespaced)
        project = tmp_path / "full-cycle-project"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({"name": "full-cycle"}))

        cos_dir = project / ".cognitive-os"
        cos_dir.mkdir()
        (cos_dir / "hooks" / "cos").mkdir(parents=True)
        (cos_dir / "hooks" / "cos" / "old-hook.sh").write_text("#!/bin/bash\n# old\n")
        (cos_dir / "skills" / "cos").mkdir(parents=True)
        (cos_dir / "templates" / "cos").mkdir(parents=True)

        (project / ".claude" / "rules" / "cos").mkdir(parents=True)
        (project / ".claude" / "rules" / "cos" / "old-rule.md").write_text("# old\n")

        # Project-custom content (must survive)
        custom_hook = cos_dir / "hooks" / "my-deploy.sh"
        custom_hook.write_text("#!/bin/bash\necho deploy\n")
        custom_rule = project / ".claude" / "rules" / "my-arch.md"
        custom_rule.write_text("# My Architecture\n")

        # Snapshot COS source
        source_snapshot = list_files_recursive(cos_src)

        # Create registry
        registry = tmp_path / "registry.json"
        create_registry(registry, [{
            "path": str(project), "mode": "standard", "version": "0.3.0",
            "project_name": "full-cycle", "source": str(cos_src),
            "installed_at": "2026-01-01T00:00:00Z",
        }])

        # Run auto-update
        result = _run_script(
            cos_src / "scripts" / "auto-update-projects.sh",
            env_overrides={"COS_REGISTRY_FILE": str(registry)},
            cwd=str(cos_src),
        )

        # 1. COS source must be intact
        assert list_files_recursive(cos_src) == source_snapshot, (
            "COS source was modified during full update cycle"
        )

        # 2. Project should have COS components
        assert (cos_dir / "hooks" / "cos").is_dir(), (
            "hooks/cos/ should exist after update"
        )
        # Should have new hooks from the update
        new_hooks = list(Path(cos_dir / "hooks" / "cos").glob("*.sh"))
        assert len(new_hooks) > 0, "No COS hooks after update"

        # 3. Custom files must survive
        assert custom_hook.exists(), "Custom hook my-deploy.sh was deleted"
        assert custom_rule.exists(), "Custom rule my-arch.md was deleted"

    def test_realpath_does_not_resolve_to_cos_source(self, tmp_path):
        """After cos-init, realpath of project/.cognitive-os must NOT
        point to the COS source directory."""
        cos_src = create_fake_cos_source(tmp_path, version="0.4.0")

        project = tmp_path / "realpath-project"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({"name": "rp-proj"}))

        result = _run_script(
            cos_src / "scripts" / "cos-init.sh",
            args=["--standard"],
            cwd=str(project),
        )

        assert result.returncode == 0, (
            f"cos-init failed: {result.stdout} {result.stderr}"
        )

        # .cognitive-os must be a real directory, not a symlink
        cognitive_os = project / ".cognitive-os"
        assert cognitive_os.is_dir()
        assert not cognitive_os.is_symlink()

        # realpath must resolve to within the project, never to COS source
        resolved = os.path.realpath(str(cognitive_os))
        cos_src_resolved = os.path.realpath(str(cos_src))
        assert not resolved.startswith(cos_src_resolved), (
            f".cognitive-os resolves to COS source! "
            f"resolved={resolved}, cos_src={cos_src_resolved}"
        )

        # Same check for .claude
        claude_dir = project / ".claude"
        if claude_dir.exists():
            claude_resolved = os.path.realpath(str(claude_dir))
            assert not claude_resolved.startswith(cos_src_resolved), (
                f".claude resolves to COS source! "
                f"resolved={claude_resolved}, cos_src={cos_src_resolved}"
            )
