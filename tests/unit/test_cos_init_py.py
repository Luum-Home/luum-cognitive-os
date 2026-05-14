"""Unit tests for scripts/cos_init.py — Phase 2.1 + 2.2 + 2.3 bootstrap.

Phase 2.1: detect_harness() port from scripts/_lib/settings-driver.sh::cos_detect_harness.
Phase 2.2: scope_allows() and skill_scope_allows() ports from scripts/cos-init.sh.
Phase 2.3: install_rule(), install_hook(), install_skill_dir() ports from scripts/cos-init.sh.
All tests are pure Python (no subprocess) — they test the Python logic in isolation.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure scripts/ is importable without hyphens (snake_case filename per rules/python-naming.md)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import cos_init

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestDetectHarnessClaude:
    def test_claude_dir_only(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When only .claude/settings.json exists, detect_harness returns 'claude'."""
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{}")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "claude"

    def test_default_is_claude(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no markers are present and no env vars set, default is 'claude'."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "claude"

    def test_both_dirs_present_defaults_to_claude_without_install_metadata(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When both .claude/settings.json AND .codex/hooks.json exist, neither
        marker-only branch wins — falls through to default 'claude'."""
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{}")
        (tmp_path / ".codex").mkdir()
        (tmp_path / ".codex" / "hooks.json").write_text("{}")
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "claude"

    def test_install_metadata_resolves_dual_marker_projects(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Install metadata preserves the selected harness during migrations."""
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{}")
        (tmp_path / ".codex").mkdir()
        (tmp_path / ".codex" / "hooks.json").write_text("{}")
        (tmp_path / ".cognitive-os").mkdir()
        (tmp_path / ".cognitive-os" / "install-meta.json").write_text(
            '{"harness": "codex", "settings_driver": ".codex/hooks.json"}'
        )
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "codex"


class TestDetectHarnessCodex:
    def test_codex_dir_only(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When only .codex/hooks.json exists, detect_harness returns 'codex'."""
        (tmp_path / ".codex").mkdir()
        (tmp_path / ".codex" / "hooks.json").write_text("{}")
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "codex"

    def test_codex_env_project_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CODEX_PROJECT_DIR env var triggers codex detection."""
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.setenv("CODEX_PROJECT_DIR", str(tmp_path))
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "codex"

    def test_codex_env_session_id(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CODEX_SESSION_ID env var triggers codex detection."""
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.setenv("CODEX_SESSION_ID", "sess-abc123")
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "codex"

    def test_codex_env_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CODEX_HOME env var triggers codex detection."""
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.setenv("CODEX_HOME", "/workspace/codex-home")
        assert cos_init.detect_harness(str(tmp_path)) == "codex"


class TestDetectHarnessExplicitOverride:
    def test_env_override_beats_filesystem(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """COGNITIVE_OS_HARNESS env var wins over filesystem markers."""
        # Set up claude markers to confirm env override beats them
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{}")
        monkeypatch.setenv("COGNITIVE_OS_HARNESS", "codex")
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "codex"

    def test_env_override_explicit_claude(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """COGNITIVE_OS_HARNESS=claude works as an explicit override."""
        monkeypatch.setenv("COGNITIVE_OS_HARNESS", "claude")
        assert cos_init.detect_harness(str(tmp_path)) == "claude"


# ── Phase 2.2: scope_allows() unit tests ─────────────────────────────

class TestScopeAllows:
    def test_install_scope_all_always_allows(self, tmp_path: Path) -> None:
        """install_scope='all' skips all filtering — every file passes."""
        f = tmp_path / "test.sh"
        f.write_text("# SCOPE: os-only\n# rest\n")
        assert cos_init.scope_allows(str(f), install_scope="all") is True

    def test_no_scope_header_is_universal(self, tmp_path: Path) -> None:
        """Files with no SCOPE header are always included (untagged = universal)."""
        f = tmp_path / "no_header.sh"
        f.write_text("#!/bin/bash\n# just a script\necho hello\n")
        assert cos_init.scope_allows(str(f), install_scope="both") is True

    def test_hash_scope_project_allowed_under_both(self, tmp_path: Path) -> None:
        """# SCOPE: project is allowed when install_scope=both."""
        f = tmp_path / "project_rule.md"
        f.write_text("# SCOPE: project\n# content\n")
        assert cos_init.scope_allows(str(f), install_scope="both") is True

    def test_hash_scope_both_allowed_under_project(self, tmp_path: Path) -> None:
        """# SCOPE: both is allowed when install_scope=project."""
        f = tmp_path / "both_rule.sh"
        f.write_text("# SCOPE: both\n# content\n")
        assert cos_init.scope_allows(str(f), install_scope="project") is True

    def test_hash_scope_os_only_blocked_under_both(self, tmp_path: Path) -> None:
        """# SCOPE: os-only is blocked when install_scope=both."""
        f = tmp_path / "os_only.sh"
        f.write_text("# SCOPE: os-only\n# content\n")
        assert cos_init.scope_allows(str(f), install_scope="both") is False

    def test_html_scope_project_allowed(self, tmp_path: Path) -> None:
        """<!-- SCOPE: project --> HTML form is parsed and allowed under project install."""
        f = tmp_path / "doc.md"
        f.write_text("<!-- SCOPE: project -->\n# content\n")
        assert cos_init.scope_allows(str(f), install_scope="project") is True

    def test_html_scope_os_only_blocked(self, tmp_path: Path) -> None:
        """<!-- SCOPE: os-only --> HTML form is blocked under both install."""
        f = tmp_path / "os_doc.md"
        f.write_text("<!-- SCOPE: os-only -->\n# content\n")
        assert cos_init.scope_allows(str(f), install_scope="both") is False

    def test_nonexistent_file_passes(self, tmp_path: Path) -> None:
        """Non-existent paths pass the filter (matches bash: [ -f ] || return 0)."""
        assert cos_init.scope_allows(str(tmp_path / "nonexistent.sh"), install_scope="both") is True

    def test_unknown_scope_tag_passes(self, tmp_path: Path) -> None:
        """Unknown SCOPE tags are permissive — file is included."""
        f = tmp_path / "weird.sh"
        f.write_text("# SCOPE: experimental\n# content\n")
        assert cos_init.scope_allows(str(f), install_scope="both") is True

    def test_scope_only_checked_in_first_3_lines(self, tmp_path: Path) -> None:
        """SCOPE header on line 4 is ignored — only first 3 lines scanned."""
        f = tmp_path / "late_header.sh"
        f.write_text("line1\nline2\nline3\n# SCOPE: os-only\n")
        # os-only on line 4 should NOT be detected → file passes
        assert cos_init.scope_allows(str(f), install_scope="both") is True


# ── Phase 2.2: skill_scope_allows() unit tests ───────────────────────

class TestSkillScopeAllows:
    def _make_skill(self, skill_dir: Path, frontmatter: str) -> None:
        """Write a minimal SKILL.md with the given frontmatter line."""
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n# Skill\n")

    def test_install_scope_all_always_allows(self, tmp_path: Path) -> None:
        """install_scope='all' skips filtering — even os-only skills pass."""
        skill_dir = tmp_path / "my-skill"
        self._make_skill(skill_dir, "audience: os-only")
        assert cos_init.skill_scope_allows(str(skill_dir), install_scope="all") is True

    def test_missing_skill_md_passes(self, tmp_path: Path) -> None:
        """Missing SKILL.md → allow (matches bash: [ -f ] || return 0)."""
        skill_dir = tmp_path / "no-skill-md"
        skill_dir.mkdir()
        assert cos_init.skill_scope_allows(str(skill_dir), install_scope="both") is True

    def test_audience_both_is_allowed(self, tmp_path: Path) -> None:
        """audience: both → True under any install_scope."""
        skill_dir = tmp_path / "skill-both"
        self._make_skill(skill_dir, "audience: both")
        assert cos_init.skill_scope_allows(str(skill_dir), install_scope="both") is True

    def test_audience_project_is_allowed(self, tmp_path: Path) -> None:
        """audience: project → True under project install_scope."""
        skill_dir = tmp_path / "skill-project"
        self._make_skill(skill_dir, "audience: project")
        assert cos_init.skill_scope_allows(str(skill_dir), install_scope="project") is True

    def test_audience_adopters_is_allowed(self, tmp_path: Path) -> None:
        """audience: adopters → True (per bash mapping — external adopters)."""
        skill_dir = tmp_path / "skill-adopters"
        self._make_skill(skill_dir, "audience: adopters")
        assert cos_init.skill_scope_allows(str(skill_dir), install_scope="both") is True

    def test_audience_human_is_allowed(self, tmp_path: Path) -> None:
        """audience: human → True (human-facing skill is project-installable)."""
        skill_dir = tmp_path / "skill-human"
        self._make_skill(skill_dir, "audience: human")
        assert cos_init.skill_scope_allows(str(skill_dir), install_scope="both") is True

    def test_audience_os_only_is_blocked(self, tmp_path: Path) -> None:
        """audience: os-only → False under project install_scope."""
        skill_dir = tmp_path / "skill-os-only"
        self._make_skill(skill_dir, "audience: os-only")
        assert cos_init.skill_scope_allows(str(skill_dir), install_scope="project") is False

    def test_audience_os_dev_is_blocked(self, tmp_path: Path) -> None:
        """audience: os-dev → False under both install_scope."""
        skill_dir = tmp_path / "skill-os-dev"
        self._make_skill(skill_dir, "audience: os-dev")
        assert cos_init.skill_scope_allows(str(skill_dir), install_scope="both") is False

    def test_scope_field_fallback(self, tmp_path: Path) -> None:
        """scope: field (not audience:) is also parsed."""
        skill_dir = tmp_path / "skill-scope-field"
        self._make_skill(skill_dir, "scope: os-only")
        assert cos_init.skill_scope_allows(str(skill_dir), install_scope="both") is False

    def test_no_audience_field_passes(self, tmp_path: Path) -> None:
        """SKILL.md with no audience/scope field → allow."""
        skill_dir = tmp_path / "skill-no-field"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\ntitle: My Skill\n---\n# Skill\n")
        assert cos_init.skill_scope_allows(str(skill_dir), install_scope="both") is True

    def test_scope_marker_os_only_overrides_audience_both(self, tmp_path: Path) -> None:
        """Canonical SCOPE marker blocks project install even when legacy audience says both."""
        skill_dir = tmp_path / "skill-marker-os-only"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("<!-- SCOPE: os-only -->\n---\naudience: both\n---\n# Skill\n")
        assert cos_init.skill_scope_allows(str(skill_dir), install_scope="project") is False

    def test_scope_marker_both_overrides_audience_os_only(self, tmp_path: Path) -> None:
        """Canonical SCOPE marker allows project install when legacy audience is stale."""
        skill_dir = tmp_path / "skill-marker-both"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("<!-- SCOPE: both -->\n---\naudience: os-only\n---\n# Skill\n")
        assert cos_init.skill_scope_allows(str(skill_dir), install_scope="project") is True


# ── Phase 2.3: install_rule() unit tests ─────────────────────────────

class TestInstallRule:
    def _make_source(self, src_dir: Path, name: str, content: str = "# rule") -> Path:
        src_dir.mkdir(parents=True, exist_ok=True)
        f = src_dir / f"{name}.md"
        f.write_text(content)
        return f

    def test_symlink_mode_installs_to_single_dest(self, tmp_path: Path) -> None:
        """install_rule copies the rule file to the destination directory."""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        self._make_source(src, "trust-score")
        dest.mkdir()
        status = cos_init.install_rule("trust-score", str(src), [str(dest)])
        assert status == "installed"
        assert (dest / "trust-score.md").is_file()

    def test_copy_mode_installs_to_multiple_dests(self, tmp_path: Path) -> None:
        """install_rule copies to all provided destination directories."""
        src = tmp_path / "src"
        dest1 = tmp_path / "dest1"
        dest2 = tmp_path / "dest2"
        self._make_source(src, "adaptive-bypass")
        dest1.mkdir()
        dest2.mkdir()
        status = cos_init.install_rule("adaptive-bypass", str(src), [str(dest1), str(dest2)])
        assert status == "installed"
        assert (dest1 / "adaptive-bypass.md").is_file()
        assert (dest2 / "adaptive-bypass.md").is_file()

    def test_missing_source_returns_skipped(self, tmp_path: Path) -> None:
        """Source file missing → 'skipped' (matches bash: [ -f ] || return)."""
        src = tmp_path / "src"
        src.mkdir()
        dest = tmp_path / "dest"
        dest.mkdir()
        status = cos_init.install_rule("nonexistent", str(src), [str(dest)])
        assert status == "skipped"
        assert not (dest / "nonexistent.md").exists()

    def test_target_dir_created_if_missing(self, tmp_path: Path) -> None:
        """Destination directory is created automatically if it does not exist."""
        src = tmp_path / "src"
        self._make_source(src, "token-economy")
        dest = tmp_path / "deep" / "nested" / "dest"
        # dest does NOT exist yet
        status = cos_init.install_rule("token-economy", str(src), [str(dest)])
        assert status == "installed"
        assert (dest / "token-economy.md").is_file()

    def test_idempotent_reinstall(self, tmp_path: Path) -> None:
        """Re-installing over an existing file succeeds without error."""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        self._make_source(src, "definition-of-done", "# v1")
        dest.mkdir()
        cos_init.install_rule("definition-of-done", str(src), [str(dest)])
        # Overwrite source and reinstall
        (src / "definition-of-done.md").write_text("# v2")
        status = cos_init.install_rule("definition-of-done", str(src), [str(dest)])
        assert status == "installed"
        assert (dest / "definition-of-done.md").read_text() == "# v2"

    def test_content_preserved(self, tmp_path: Path) -> None:
        """Rule file content is preserved exactly after copy."""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        content = "# Trust Score\n\nSome content.\n"
        self._make_source(src, "trust-score", content)
        dest.mkdir()
        cos_init.install_rule("trust-score", str(src), [str(dest)])
        assert (dest / "trust-score.md").read_text() == content


# ── Phase 2.3: install_hook() unit tests ─────────────────────────────

class TestInstallHook:
    def _make_source(self, src_dir: Path, name: str, content: str = "#!/bin/bash\necho hi\n") -> Path:
        src_dir.mkdir(parents=True, exist_ok=True)
        f = src_dir / f"{name}.sh"
        f.write_text(content)
        return f

    def test_installs_hook_to_dest(self, tmp_path: Path) -> None:
        """install_hook copies the hook file to the destination directory."""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        self._make_source(src, "auto-refine")
        dest.mkdir()
        status = cos_init.install_hook("auto-refine", str(src), str(dest))
        assert status == "installed"
        assert (dest / "auto-refine.sh").is_file()

    def test_executable_bit_set_on_sh_file(self, tmp_path: Path) -> None:
        """install_hook sets executable bit on the installed .sh file."""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        self._make_source(src, "error-learning")
        dest.mkdir()
        cos_init.install_hook("error-learning", str(src), str(dest))
        installed = dest / "error-learning.sh"
        assert os.access(str(installed), os.X_OK), "Installed hook should be executable"

    def test_missing_source_returns_skipped(self, tmp_path: Path) -> None:
        """Source file missing → 'skipped' (matches bash: [ -f ] || return)."""
        src = tmp_path / "src"
        src.mkdir()
        dest = tmp_path / "dest"
        dest.mkdir()
        status = cos_init.install_hook("nonexistent", str(src), str(dest))
        assert status == "skipped"
        assert not (dest / "nonexistent.sh").exists()

    def test_target_dir_created_if_missing(self, tmp_path: Path) -> None:
        """Destination directory is created automatically if it does not exist."""
        src = tmp_path / "src"
        self._make_source(src, "dod-gate")
        dest = tmp_path / "deep" / "hooks"
        status = cos_init.install_hook("dod-gate", str(src), str(dest))
        assert status == "installed"
        assert (dest / "dod-gate.sh").is_file()

    def test_idempotent_reinstall(self, tmp_path: Path) -> None:
        """Re-installing over an existing hook succeeds without error."""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        self._make_source(src, "blast-radius", "#!/bin/bash\n# v1\n")
        dest.mkdir()
        cos_init.install_hook("blast-radius", str(src), str(dest))
        (src / "blast-radius.sh").write_text("#!/bin/bash\n# v2\n")
        status = cos_init.install_hook("blast-radius", str(src), str(dest))
        assert status == "installed"
        assert (dest / "blast-radius.sh").read_text() == "#!/bin/bash\n# v2\n"

    def test_content_preserved(self, tmp_path: Path) -> None:
        """Hook file content is preserved exactly after copy."""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        content = "#!/bin/bash\n# test hook\necho done\n"
        self._make_source(src, "session-init", content)
        dest.mkdir()
        cos_init.install_hook("session-init", str(src), str(dest))
        assert (dest / "session-init.sh").read_text() == content


# ── Phase 2.3: install_skill_dir() unit tests ────────────────────────

class TestInstallSkillDir:
    def _make_skill(self, skills_src: Path, name: str, audience: str = "project") -> Path:
        """Create a minimal skill directory with SKILL.md."""
        skill_dir = skills_src / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"---\naudience: {audience}\n---\n# Skill\n")
        (skill_dir / "README.md").write_text(f"# {name}\n")
        return skill_dir

    def test_installs_to_kernel_and_creates_driver_symlink(self, tmp_path: Path) -> None:
        """install_skill_dir copies to kernel and creates relative symlink in driver."""
        src = tmp_path / "skills"
        kernel = tmp_path / ".cognitive-os" / "skills" / "cos"
        driver = tmp_path / ".claude" / "skills"
        skill_dir = self._make_skill(src, "plan-feature")
        kernel.mkdir(parents=True)
        driver.mkdir(parents=True)
        status = cos_init.install_skill_dir(str(skill_dir), str(kernel), str(driver))
        assert status == "installed"
        assert (kernel / "plan-feature" / "SKILL.md").is_file()
        assert (driver / "plan-feature").is_symlink()

    def test_full_copy_mode_copies_contents(self, tmp_path: Path) -> None:
        """Skill directory is fully copied to kernel dest (all files preserved)."""
        src = tmp_path / "skills"
        kernel = tmp_path / "kernel"
        driver = tmp_path / "driver"
        skill_dir = self._make_skill(src, "exhaustive-prompt")
        # Add a subdirectory
        (skill_dir / "examples").mkdir()
        (skill_dir / "examples" / "sample.md").write_text("example")
        kernel.mkdir()
        driver.mkdir()
        cos_init.install_skill_dir(str(skill_dir), str(kernel), str(driver))
        assert (kernel / "exhaustive-prompt" / "examples" / "sample.md").is_file()

    def test_scope_filtered_returns_skipped(self, tmp_path: Path) -> None:
        """Skill with audience: os-only → 'skipped' (not installed)."""
        src = tmp_path / "skills"
        kernel = tmp_path / "kernel"
        driver = tmp_path / "driver"
        skill_dir = self._make_skill(src, "os-internal", audience="os-only")
        kernel.mkdir()
        driver.mkdir()
        status = cos_init.install_skill_dir(
            str(skill_dir), str(kernel), str(driver), install_scope="both"
        )
        assert status == "skipped"
        assert not (kernel / "os-internal").exists()

    def test_missing_source_dir_returns_error(self, tmp_path: Path) -> None:
        """Source directory does not exist → 'error'."""
        kernel = tmp_path / "kernel"
        driver = tmp_path / "driver"
        kernel.mkdir()
        driver.mkdir()
        status = cos_init.install_skill_dir(
            str(tmp_path / "nonexistent-skill"),
            str(kernel),
            str(driver),
        )
        assert status == "error"

    def test_target_dirs_created_if_missing(self, tmp_path: Path) -> None:
        """Kernel and driver destination directories are created if they don't exist."""
        src = tmp_path / "skills"
        kernel = tmp_path / "deep" / "kernel"
        driver = tmp_path / "deep" / "driver"
        skill_dir = self._make_skill(src, "compose-prompt")
        # Neither kernel nor driver exist yet
        status = cos_init.install_skill_dir(str(skill_dir), str(kernel), str(driver))
        assert status == "installed"
        assert (kernel / "compose-prompt" / "SKILL.md").is_file()

    def test_idempotent_reinstall(self, tmp_path: Path) -> None:
        """Re-installing an already installed skill succeeds without error."""
        src = tmp_path / "skills"
        kernel = tmp_path / "kernel"
        driver = tmp_path / "driver"
        skill_dir = self._make_skill(src, "agent-dashboard")
        kernel.mkdir()
        driver.mkdir()
        cos_init.install_skill_dir(str(skill_dir), str(kernel), str(driver))
        # Add a new file and reinstall
        (skill_dir / "extra.md").write_text("extra")
        status = cos_init.install_skill_dir(str(skill_dir), str(kernel), str(driver))
        assert status == "installed"
        assert (kernel / "agent-dashboard" / "extra.md").is_file()


# ── Template scope filtering (component-scope-classification DoD items 1 + 3) ──

class TestTemplateInstallScopeFilter:
    """Verify scope_allows() correctly filters templates by <!-- SCOPE: ... --> header.

    DoD items from .cognitive-os/plans/features/component-scope-classification.md:
      - Item 1: All 433 components have a scope tag (templates confirmed 2026-04-30)
      - Item 3: cos install (cos_init.py main) skips os-only components

    Templates use <!-- SCOPE: {scope} --> comment on the first line (plan step 4).
    The installer calls scope_allows() for each .md before copying.
    """

    def test_scope_allows_filters_template_os_only(self, tmp_path: Path) -> None:
        """scope_allows() blocks templates tagged '<!-- SCOPE: os-only -->'."""
        tmpl = tmp_path / "project-gotchas.md"
        tmpl.write_text("<!-- SCOPE: os-only -->\n# Project Gotchas\n")
        assert cos_init.scope_allows(str(tmpl), install_scope="both") is False

    def test_scope_allows_passes_template_both(self, tmp_path: Path) -> None:
        """scope_allows() passes templates tagged '<!-- SCOPE: both -->'."""
        tmpl = tmp_path / "quality-gates.md"
        tmpl.write_text("<!-- SCOPE: both -->\n# Quality Gates\n")
        assert cos_init.scope_allows(str(tmpl), install_scope="both") is True

    def test_scope_allows_passes_template_project(self, tmp_path: Path) -> None:
        """scope_allows() passes templates tagged '<!-- SCOPE: project -->'."""
        tmpl = tmp_path / "fintech-gates.md"
        tmpl.write_text("<!-- SCOPE: project -->\n# Fintech Gates\n")
        assert cos_init.scope_allows(str(tmpl), install_scope="both") is True

    def test_real_template_scope_tags_present(self) -> None:
        """All real templates in templates/ must have a '<!-- SCOPE: ...' tag on line 1.

        DoD item 1: every component has a scope tag.
        Templates use '<!-- SCOPE: {scope} -->' on the first line (per plan step 4).
        """
        templates_dir = PROJECT_ROOT / "templates"
        if not templates_dir.is_dir():
            return  # templates/ not present in this environment

        missing = []
        for tmpl in sorted(templates_dir.glob("*.md")):
            try:
                first_line = tmpl.read_text(encoding="utf-8", errors="replace").splitlines()[0]
            except (OSError, IndexError):
                first_line = ""
            if "<!-- SCOPE:" not in first_line:
                missing.append(tmpl.name)

        assert not missing, (
            f"Templates lacking '<!-- SCOPE: ...' tag on line 1: {missing}\n"
            f"Add '<!-- SCOPE: both -->' (or os-only/project) as the very first line."
        )

    def test_real_os_only_templates_are_filtered(self) -> None:
        """Templates tagged os-only in the real repo are correctly blocked by scope_allows().

        This verifies the integration between scope tags on disk and scope_allows(),
        ensuring cos_init.py main()'s template install loop actually filters them.
        """
        templates_dir = PROJECT_ROOT / "templates"
        if not templates_dir.is_dir():
            return

        for tmpl in sorted(templates_dir.glob("*.md")):
            try:
                first_line = tmpl.read_text(encoding="utf-8", errors="replace").splitlines()[0]
            except (OSError, IndexError):
                continue
            if "<!-- SCOPE: os-only" in first_line:
                assert cos_init.scope_allows(str(tmpl), install_scope="both") is False, (
                    f"Expected {tmpl.name} to be blocked (os-only), but scope_allows returned True"
                )


def test_registry_register_skips_ephemeral_without_explicit_registry(tmp_path, monkeypatch):
    """cos-init must not write tmp/canary installs to the production registry."""
    import scripts.cos_init as cos_init

    home = tmp_path / "home"
    home.mkdir()
    project = tmp_path / "cos-canary-default"
    project.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("COS_REGISTRY_FILE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    cos_init._registry_register(
        str(project),
        "default",
        "0.21.0",
        "cos-canary-default",
        str(PROJECT_ROOT),
    )

    assert not (home / ".cognitive-os" / "installations.json").exists()


def test_registry_register_honors_explicit_registry_for_tmp_install(tmp_path, monkeypatch):
    """Test registries can still model tmp installs explicitly."""
    import scripts.cos_init as cos_init

    registry_file = tmp_path / "registry.json"
    project = tmp_path / "cos-canary-default"
    project.mkdir()
    monkeypatch.setenv("COS_REGISTRY_FILE", str(registry_file))
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    cos_init._registry_register(
        str(project),
        "default",
        "0.21.0",
        "cos-canary-default",
        str(PROJECT_ROOT),
    )

    data = json.loads(registry_file.read_text())
    assert data["installations"][0]["project_name"] == "cos-canary-default"

