"""Behavior tests for skill auto-selection system.

Validates that the SkillRouter is importable, has sufficient routing
coverage, references real skills, and works for both languages.
"""

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Importability
# ---------------------------------------------------------------------------


class TestImportability:
    """SkillRouter must be importable from lib."""

    def test_skill_router_importable(self):
        from lib.skill_router import SkillRouter
        router = SkillRouter()
        assert router is not None

    def test_skill_match_importable(self):
        from lib.skill_router import SkillMatch
        match = SkillMatch(
            skill_name="test",
            confidence=0.9,
            reason="test reason",
            invoke_command="/test",
        )
        assert match.confidence == 0.9


# ---------------------------------------------------------------------------
# Routing table coverage
# ---------------------------------------------------------------------------


class TestRoutingTableCoverage:
    """Routing table must have sufficient entries."""

    def test_routing_table_has_more_than_15_entries(self):
        from lib.skill_router import SkillRouter
        router = SkillRouter()
        assert router.routing_entry_count > 15, (
            f"Routing table has only {router.routing_entry_count} entries, "
            "expected >15 for adequate coverage"
        )

    def test_routing_skills_cover_major_categories(self):
        from lib.skill_router import SkillRouter
        router = SkillRouter()
        skills = router.get_routing_skills()

        # These major skills must be in the routing table
        expected = {
            "repo-forensics",
            "plan-bug",
            "systematic-debugging",
            "run-tests",
            "security-audit",
            "agent-kpis",
            "deep-research",
            "skill-creator",
            "release-os",
            "scout",
            "self-review",
            "document-feature",
            "sre-agent",
            "recommend-library",
        }
        missing = expected - skills
        assert missing == set(), f"Major skills missing from routing table: {missing}"


# ---------------------------------------------------------------------------
# Skills exist on filesystem
# ---------------------------------------------------------------------------


class TestSkillsExistOnFilesystem:
    """Every skill in the routing table should have a directory in skills/."""

    def test_every_routing_skill_is_known(self):
        """Every skill in the routing table must exist either as a
        directory in skills/ or be listed in CATALOG.md."""
        from lib.skill_router import SkillRouter

        project_root = Path(__file__).resolve().parent.parent.parent
        skills_dir = project_root / "skills"

        if not skills_dir.exists():
            pytest.skip("skills/ directory not found")

        router = SkillRouter()
        routing_skills = router.get_routing_skills()
        catalog_skills = router.known_skills

        # Known aliases: meta-commands or different directory names
        aliases = {
            "sdd-new": None,  # meta-command, not a directory
            "sdd-verify": None,  # loaded as part of SDD pipeline
            "squad-report": "squad-manager",
            "cost-predict": "cost-predictor",
            "jupyter-exec": "jupyter-execute",
        }

        missing = []
        for skill_name in routing_skills:
            # Check alias mappings first
            if skill_name in aliases:
                mapped = aliases[skill_name]
                if mapped is None:
                    continue  # meta-command, always OK
                if (skills_dir / mapped).is_dir() or mapped in catalog_skills:
                    continue
            # Check directory exists OR listed in CATALOG
            elif (skills_dir / skill_name).is_dir() or skill_name in catalog_skills:
                continue
            missing.append(skill_name)

        assert missing == [], (
            f"Skills in routing table not found in skills/ or CATALOG.md: {missing}"
        )


# ---------------------------------------------------------------------------
# Bilingual support
# ---------------------------------------------------------------------------


class TestBilingualSupport:
    """Both English and Spanish patterns must produce matches."""

    def test_english_patterns_work(self):
        from lib.skill_router import SkillRouter
        router = SkillRouter()

        english_messages = [
            ("fix the auth bug", "/plan-bug"),
            ("run the tests", "/run-tests"),
            ("run a security audit", "/security-audit"),
            ("create a new skill", "/skill-creator"),
        ]

        for message, expected_command in english_messages:
            match = router.best_match(message)
            assert match is not None, f"No match for English: '{message}'"
            assert match.invoke_command == expected_command, (
                f"Expected {expected_command} for '{message}', "
                f"got {match.invoke_command}"
            )

    def test_spanish_patterns_work(self):
        from lib.skill_router import SkillRouter
        router = SkillRouter()

        spanish_messages = [
            ("arreglá el bug en el login", "/plan-bug"),
            ("corré los tests", "/run-tests"),
            ("revisá la seguridad del proyecto", "/security-audit"),
            ("necesito agregar un endpoint nuevo", "/sdd-new"),
        ]

        for message, expected_command in spanish_messages:
            match = router.best_match(message)
            assert match is not None, f"No match for Spanish: '{message}'"
            assert match.invoke_command == expected_command, (
                f"Expected {expected_command} for '{message}', "
                f"got {match.invoke_command}"
            )


# ---------------------------------------------------------------------------
# GitHub URL detection
# ---------------------------------------------------------------------------


class TestGitHubUrlDetectionBehavior:
    """GitHub URL detection must work across formats."""

    def test_github_url_detection_works(self):
        from lib.skill_router import SkillRouter
        router = SkillRouter()

        match = router.best_match("https://github.com/user/repo")
        assert match is not None
        assert match.skill_name == "repo-forensics"

    def test_github_url_in_sentence(self):
        from lib.skill_router import SkillRouter
        router = SkillRouter()

        match = router.best_match(
            "check out https://github.com/anthropics/claude-code please"
        )
        assert match is not None
        assert match.skill_name == "repo-forensics"


# ---------------------------------------------------------------------------
# Format suggestion output
# ---------------------------------------------------------------------------


class TestFormatSuggestionBehavior:
    """format_suggestion must produce human-readable output."""

    def test_format_suggestion_produces_readable_output(self):
        from lib.skill_router import SkillRouter
        router = SkillRouter()

        matches = router.match("run the tests")
        suggestion = router.format_suggestion(matches)

        assert isinstance(suggestion, str)
        assert len(suggestion) > 0
        assert "Suggested skill:" in suggestion
        assert "confidence:" in suggestion

    def test_format_suggestion_empty_for_no_matches(self):
        from lib.skill_router import SkillRouter
        router = SkillRouter()

        suggestion = router.format_suggestion([])
        assert suggestion == ""
