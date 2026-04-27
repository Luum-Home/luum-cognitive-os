"""Unit tests for scripts/cos_init.py — Phase 2.1 + 2.2 bootstrap.

Phase 2.1: detect_harness() port from scripts/_lib/settings-driver.sh::cos_detect_harness.
Phase 2.2: scope_allows() and skill_scope_allows() ports from scripts/cos-init.sh.
All tests are pure Python (no subprocess) — they test the Python logic in isolation.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure scripts/ is importable without hyphens (snake_case filename per rules/python-naming.md)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import cos_init


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

    def test_both_dirs_present_defaults_to_claude(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When both .claude/settings.json AND .codex/hooks.json exist, neither
        priority-2 nor priority-3 fires — falls through to default 'claude'."""
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{}")
        (tmp_path / ".codex").mkdir()
        (tmp_path / ".codex" / "hooks.json").write_text("{}")
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "claude"


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
        monkeypatch.setenv("CODEX_HOME", "/home/codex")
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
