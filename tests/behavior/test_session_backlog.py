"""Tests for /session-backlog and /session-wrapup skills.

Validates:
- Both SKILL.md files exist with valid frontmatter
- session-backlog covers all 6 mandatory scan sources
- session-wrapup chains session-backlog + engram save + session summary
- Both skills have audience: both
"""

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.behavior

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent.parent


def _skill_path(name: str) -> Path:
    return PROJECT_ROOT / "skills" / name / "SKILL.md"


def _parse_frontmatter(path: Path) -> dict:
    """Extract YAML frontmatter from a SKILL.md file."""
    content = path.read_text()
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def _skill_content(name: str) -> str:
    return _skill_path(name).read_text()


# ---------------------------------------------------------------------------
# Existence and frontmatter tests
# ---------------------------------------------------------------------------


class TestSkillFilesExist:
    def test_session_backlog_skill_exists(self):
        assert _skill_path("session-backlog").exists(), (
            "skills/session-backlog/SKILL.md not found"
        )

    def test_session_wrapup_skill_exists(self):
        assert _skill_path("session-wrapup").exists(), (
            "skills/session-wrapup/SKILL.md not found"
        )


class TestFrontmatterValid:
    def test_session_backlog_frontmatter_has_required_fields(self):
        fm = _parse_frontmatter(_skill_path("session-backlog"))
        assert fm.get("name") == "session-backlog"
        assert fm.get("description"), "description must not be empty"
        assert fm.get("version"), "version must not be empty"
        assert fm.get("audience") == "both"

    def test_session_wrapup_frontmatter_has_required_fields(self):
        fm = _parse_frontmatter(_skill_path("session-wrapup"))
        assert fm.get("name") == "session-wrapup"
        assert fm.get("description"), "description must not be empty"
        assert fm.get("version"), "version must not be empty"
        assert fm.get("audience") == "both"

    def test_session_backlog_has_tags(self):
        fm = _parse_frontmatter(_skill_path("session-backlog"))
        tags = fm.get("tags", [])
        assert "session" in tags, "session-backlog should be tagged with 'session'"
        assert "backlog" in tags, "session-backlog should be tagged with 'backlog'"

    def test_session_wrapup_has_tags(self):
        fm = _parse_frontmatter(_skill_path("session-wrapup"))
        tags = fm.get("tags", [])
        assert "session" in tags, "session-wrapup should be tagged with 'session'"
        assert "closing" in tags or "summary" in tags, (
            "session-wrapup should be tagged with 'closing' or 'summary'"
        )


class TestAudienceBoth:
    def test_session_backlog_audience_is_both(self):
        fm = _parse_frontmatter(_skill_path("session-backlog"))
        assert fm.get("audience") == "both"

    def test_session_wrapup_audience_is_both(self):
        fm = _parse_frontmatter(_skill_path("session-wrapup"))
        assert fm.get("audience") == "both"


# ---------------------------------------------------------------------------
# session-backlog content: 6 mandatory scan sources
# ---------------------------------------------------------------------------


class TestSessionBacklogScanSources:
    """session-backlog must instruct scanning of all 6 defined sources."""

    def _content(self) -> str:
        return _skill_content("session-backlog")

    def test_scans_plan_files(self):
        content = self._content()
        # Source A: plan files
        assert ".cognitive-os/plans" in content, (
            "session-backlog must scan .cognitive-os/plans/ for plan files"
        )

    def test_scans_engram_queued_items(self):
        content = self._content()
        # Source B: engram queries
        assert "mem_search" in content, (
            "session-backlog must call mem_search to find engram queued items"
        )
        # Should query for queued/pending/deferred items
        assert any(
            kw in content for kw in ("queued", "deferred", "pending")
        ), "session-backlog must search engram for queued/deferred/pending items"

    def test_scans_active_tasks(self):
        content = self._content()
        # Source C: active-tasks.json
        assert "active-tasks.json" in content, (
            "session-backlog must read .cognitive-os/tasks/active-tasks.json"
        )
        assert "dispatch-queue.json" in content, (
            "session-backlog must read .cognitive-os/tasks/dispatch-queue.json"
        )

    def test_scans_session_todos(self):
        content = self._content()
        # Source D: session TODOs / session summaries
        assert any(
            kw in content for kw in ("Next Steps", "session summary", "session TODOs")
        ), "session-backlog must scan session TODOs or session summaries"

    def test_scans_audit_results(self):
        content = self._content()
        # Source E: audit results with unimplemented recommendations
        assert any(
            kw in content
            for kw in ("audit", "verify-report", "CONCERN", "BLOCKER", "recommendations")
        ), "session-backlog must scan audit results for unimplemented recommendations"

    def test_scans_git_state(self):
        content = self._content()
        # Source F: git state
        assert "git" in content, (
            "session-backlog must check git state (uncommitted changes, branches)"
        )
        assert any(
            kw in content for kw in ("git status", "git stash", "branch", "uncommitted")
        ), "session-backlog must check git status, stash, or branches"


class TestSessionBacklogOutputFormat:
    """session-backlog must produce a structured backlog document."""

    def _content(self) -> str:
        return _skill_content("session-backlog")

    def test_defines_priority_tiers(self):
        content = self._content()
        assert "Priority 1" in content
        assert "Priority 2" in content
        assert "Priority 3" in content
        assert "Priority 4" in content

    def test_writes_backlog_to_file(self):
        content = self._content()
        assert "backlog.md" in content, (
            "session-backlog must write the backlog to a .md file"
        )

    def test_saves_to_engram(self):
        content = self._content()
        assert "mem_save" in content, (
            "session-backlog must save the backlog to engram"
        )
        assert "session/backlog" in content, (
            "session-backlog must use topic_key starting with 'session/backlog'"
        )

    def test_includes_recommendations_section(self):
        content = self._content()
        assert "Recommendations for Next Session" in content or "next session" in content.lower()


# ---------------------------------------------------------------------------
# session-wrapup content: chains backlog + engram + summary
# ---------------------------------------------------------------------------


class TestSessionWrapupChaining:
    """session-wrapup must chain session-backlog, engram save, and session summary."""

    def _content(self) -> str:
        return _skill_content("session-wrapup")

    def test_invokes_session_backlog(self):
        content = self._content()
        assert "session-backlog" in content, (
            "session-wrapup must invoke /session-backlog"
        )

    def test_saves_to_engram(self):
        content = self._content()
        assert "mem_save" in content, (
            "session-wrapup must call mem_save to persist session state"
        )

    def test_calls_session_summary(self):
        content = self._content()
        assert "mem_session_summary" in content, (
            "session-wrapup must call mem_session_summary"
        )

    def test_reports_accomplishments(self):
        content = self._content()
        assert any(
            kw in content for kw in ("Accomplished", "accomplished", "completed")
        ), "session-wrapup must report what was accomplished"

    def test_reports_next_steps(self):
        content = self._content()
        assert any(
            kw in content for kw in ("Next Steps", "next steps", "top priority")
        ), "session-wrapup must report next steps from the backlog"

    def test_checks_git_log(self):
        content = self._content()
        assert "git" in content and "log" in content, (
            "session-wrapup must check git log to identify commits made this session"
        )


# ---------------------------------------------------------------------------
# CATALOG.md registration
# ---------------------------------------------------------------------------


class TestCatalogRegistration:
    """Both skills must be registered in CATALOG.md."""

    def _catalog(self) -> str:
        return (PROJECT_ROOT / "skills" / "CATALOG.md").read_text()

    def test_session_backlog_in_catalog(self):
        catalog = self._catalog()
        assert "session-backlog" in catalog, (
            "session-backlog must be listed in CATALOG.md"
        )

    def test_session_wrapup_in_catalog(self):
        catalog = self._catalog()
        assert "session-wrapup" in catalog, (
            "session-wrapup must be listed in CATALOG.md"
        )

    def test_session_backlog_invoke_in_catalog(self):
        catalog = self._catalog()
        assert "/session-backlog" in catalog, (
            "CATALOG.md must show /session-backlog invoke command"
        )

    def test_session_wrapup_invoke_in_catalog(self):
        catalog = self._catalog()
        assert "/session-wrapup" in catalog, (
            "CATALOG.md must show /session-wrapup invoke command"
        )
