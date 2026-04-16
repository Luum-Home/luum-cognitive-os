"""Unit tests for lib/skill_router.py

Validates skill auto-selection from conversation context, including
English and Spanish pattern matching, GitHub URL detection, confidence
scoring, fallback handling, routing table integrity, and audience filtering.
"""

import pytest

from lib.skill_router import (
    SkillMatch,
    SkillRouter,
    _audience_matches_context,
    _detect_audience_context,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def router() -> SkillRouter:
    # Use 'project' context so all project-audience skills are visible.
    # Audience-specific tests create their own routers with explicit context.
    return SkillRouter(audience_context="project")


@pytest.fixture
def os_dev_router() -> SkillRouter:
    """Router in os-dev context (shows os-dev and os-audience skills)."""
    return SkillRouter(audience_context="os-dev")


# ---------------------------------------------------------------------------
# GitHub URL detection
# ---------------------------------------------------------------------------


class TestGitHubUrlDetection:
    """GitHub URLs should match /repo-forensics or /eval-repo."""

    def test_github_url_matches_repo_forensics(self, router: SkillRouter):
        match = router.best_match(
            "Can you analyze https://github.com/garagon/aguara for me?"
        )
        assert match is not None
        assert match.invoke_command == "/repo-forensics"
        assert match.confidence >= 0.90

    def test_github_url_with_subpath(self, router: SkillRouter):
        match = router.best_match(
            "Check out https://github.com/anthropics/claude-code"
        )
        assert match is not None
        assert match.skill_name == "repo-forensics"

    def test_github_url_with_https(self, router: SkillRouter):
        match = router.best_match("https://github.com/some-org/some-repo")
        assert match is not None
        assert match.skill_name == "repo-forensics"

    def test_github_url_in_spanish_context(self, router: SkillRouter):
        match = router.best_match(
            "investigá este repo https://github.com/luum/luum-agent-os"
        )
        assert match is not None
        assert match.invoke_command == "/repo-forensics"
        assert match.confidence >= 0.90

    def test_multiple_url_formats(self, router: SkillRouter):
        urls = [
            "https://github.com/user/repo",
            "http://github.com/user/repo",
            "https://github.com/user-name/repo.name",
        ]
        for url in urls:
            match = router.best_match(f"Analyze {url}")
            assert match is not None, f"Failed for URL: {url}"
            assert match.skill_name == "repo-forensics"


# ---------------------------------------------------------------------------
# Bug fix detection
# ---------------------------------------------------------------------------


class TestBugFixDetection:
    """Bug-related messages should match /plan-bug."""

    def test_fix_bug_english(self, router: SkillRouter):
        match = router.best_match("fix the auth bug in user handler")
        assert match is not None
        assert match.invoke_command == "/plan-bug"
        assert match.confidence >= 0.85

    def test_fix_bug_spanish(self, router: SkillRouter):
        match = router.best_match("arreglá el bug en el handler de usuarios")
        assert match is not None
        assert match.invoke_command == "/plan-bug"

    def test_there_is_a_bug(self, router: SkillRouter):
        match = router.best_match("there's a bug in the payment module")
        assert match is not None
        assert match.invoke_command == "/plan-bug"

    def test_hay_un_error(self, router: SkillRouter):
        match = router.best_match("hay un error en el módulo de pagos")
        assert match is not None
        assert match.invoke_command == "/plan-bug"


# ---------------------------------------------------------------------------
# Feature request detection
# ---------------------------------------------------------------------------


class TestFeatureRequestDetection:
    """Feature requests should match /sdd-new."""

    def test_add_feature_english(self, router: SkillRouter):
        match = router.best_match("I need to add JWT authentication to the API")
        assert match is not None
        assert match.invoke_command == "/sdd-new"

    def test_spanish_feature_request(self, router: SkillRouter):
        match = router.best_match("necesito agregar autenticación JWT al servicio")
        assert match is not None
        assert match.invoke_command == "/sdd-new"

    def test_build_new_service(self, router: SkillRouter):
        match = router.best_match("build a new payment service endpoint")
        assert match is not None
        assert match.invoke_command == "/sdd-new"

    def test_construir_modulo(self, router: SkillRouter):
        match = router.best_match("armemos un nuevo módulo de pagos")
        assert match is not None
        assert match.invoke_command == "/sdd-new"


# ---------------------------------------------------------------------------
# Test execution detection
# ---------------------------------------------------------------------------


class TestRunTestsDetection:
    """Test-running messages should match /run-tests."""

    def test_run_tests_english(self, router: SkillRouter):
        match = router.best_match("run the tests")
        assert match is not None
        assert match.invoke_command == "/run-tests"
        assert match.confidence >= 0.90

    def test_run_tests_spanish(self, router: SkillRouter):
        match = router.best_match("corré los tests")
        assert match is not None
        assert match.invoke_command == "/run-tests"

    def test_pytest_mention(self, router: SkillRouter):
        match = router.best_match("run pytest on the unit tests")
        assert match is not None
        assert match.invoke_command == "/run-tests"


# ---------------------------------------------------------------------------
# Security detection
# ---------------------------------------------------------------------------


class TestSecurityDetection:
    """Security-related messages should match appropriate security skills."""

    def test_security_audit_english(self, os_dev_router: SkillRouter):
        match = os_dev_router.best_match("run a security audit on the project")
        assert match is not None
        assert match.invoke_command == "/security-audit"
        assert match.confidence >= 0.85

    def test_security_audit_spanish(self, os_dev_router: SkillRouter):
        match = os_dev_router.best_match("revisá la seguridad del proyecto")
        assert match is not None
        assert match.invoke_command == "/security-audit"

    def test_red_team(self, os_dev_router: SkillRouter):
        match = os_dev_router.best_match("run red team testing on the prompts")
        assert match is not None
        assert match.invoke_command == "/red-team"


# ---------------------------------------------------------------------------
# No match for greetings
# ---------------------------------------------------------------------------


class TestNoMatchCases:
    """Greetings and ambiguous messages should return None."""

    def test_no_match_for_greeting(self, router: SkillRouter):
        match = router.best_match("hola")
        assert match is None

    def test_no_match_for_thanks(self, router: SkillRouter):
        match = router.best_match("thanks!")
        assert match is None

    def test_no_match_for_empty(self, router: SkillRouter):
        match = router.best_match("")
        assert match is None

    def test_no_match_for_none_equivalent(self, router: SkillRouter):
        match = router.best_match("   ")
        assert match is None

    def test_no_match_for_simple_question(self, router: SkillRouter):
        match = router.best_match("what time is it?")
        assert match is None


# ---------------------------------------------------------------------------
# Multiple matches sorted by confidence
# ---------------------------------------------------------------------------


class TestMultipleMatches:
    """Messages with multiple signals should return sorted matches."""

    def test_multiple_matches_sorted(self, router: SkillRouter):
        # A message that could match multiple skills
        matches = router.match(
            "fix the security bug in the auth module"
        )
        assert len(matches) >= 2
        # Verify sorted by confidence descending
        for i in range(len(matches) - 1):
            assert matches[i].confidence >= matches[i + 1].confidence

    def test_best_match_returns_highest(self, router: SkillRouter):
        matches = router.match(
            "fix the security bug in the auth module"
        )
        best = router.best_match(
            "fix the security bug in the auth module"
        )
        assert best is not None
        assert matches[0].skill_name == best.skill_name
        assert matches[0].confidence == best.confidence


# ---------------------------------------------------------------------------
# format_suggestion
# ---------------------------------------------------------------------------


class TestFormatSuggestion:
    """format_suggestion should produce readable output."""

    def test_format_suggestion_with_matches(self, router: SkillRouter):
        matches = router.match("run the tests")
        suggestion = router.format_suggestion(matches)
        assert "Suggested skill:" in suggestion
        assert "/run-tests" in suggestion
        assert "confidence:" in suggestion

    def test_format_suggestion_empty(self, router: SkillRouter):
        suggestion = router.format_suggestion([])
        assert suggestion == ""

    def test_format_suggestion_shows_alternatives(self, router: SkillRouter):
        matches = router.match("fix the security bug in auth")
        if len(matches) > 1:
            suggestion = router.format_suggestion(matches)
            assert "Alternatives:" in suggestion


# ---------------------------------------------------------------------------
# Spanish patterns
# ---------------------------------------------------------------------------


class TestSpanishPatterns:
    """Spanish language patterns should work correctly."""

    def test_investiga(self, router: SkillRouter):
        match = router.best_match("investigá este tema de performance")
        assert match is not None
        assert match.invoke_command == "/deep-research"

    def test_arregla(self, router: SkillRouter):
        match = router.best_match("arreglá el bug en el login")
        assert match is not None
        assert match.invoke_command == "/plan-bug"

    def test_necesito(self, router: SkillRouter):
        match = router.best_match("necesito agregar un endpoint nuevo")
        assert match is not None
        assert match.invoke_command == "/sdd-new"

    def test_corre_los_tests(self, router: SkillRouter):
        match = router.best_match("corré los tests de integración")
        assert match is not None
        assert match.invoke_command == "/run-tests"

    def test_documenta(self, router: SkillRouter):
        match = router.best_match("documentá la feature de autenticación")
        assert match is not None
        assert match.invoke_command == "/document-feature"


# ---------------------------------------------------------------------------
# Routing table integrity
# ---------------------------------------------------------------------------


class TestRoutingTableIntegrity:
    """Every skill in the routing table should exist in CATALOG.md."""

    def test_all_routing_entries_have_existing_skills(self, router: SkillRouter):
        """Every skill referenced in the routing table must exist in CATALOG.md."""
        if not router.known_skills:
            pytest.skip("CATALOG.md not found or empty")

        missing = router.validate_routing_table()
        # Allow some skills that may be referenced by invoke_command name
        # but stored under a different directory name, or exist as
        # directories but are not yet listed in CATALOG.md
        known_aliases = {
            "sdd-new",  # meta-command, not a directory
            "sdd-verify",  # loaded as part of SDD pipeline
            "squad-report",  # alias for squad-manager
            "cost-predict",  # alias for cost-predictor
            "jupyter-exec",  # alias for jupyter-execute
            "agent-stress-test",  # exists as dir, not in CATALOG
            "red-team",  # exists as dir, not in CATALOG
            "skill-creator",  # exists as dir, not in CATALOG
            "vulnerability-scan",  # exists as dir, not in CATALOG
        }
        actual_missing = [s for s in missing if s not in known_aliases]
        assert actual_missing == [], (
            f"Skills in routing table missing from CATALOG.md: {actual_missing}"
        )

    def test_routing_table_has_sufficient_entries(self, router: SkillRouter):
        """Routing table should have at least 15 entries."""
        assert router.routing_entry_count >= 15

    def test_known_skills_loaded(self, router: SkillRouter):
        """CATALOG.md should be parsed with a reasonable number of skills."""
        # If running from the project root, we should find skills
        if router.known_skills:
            assert len(router.known_skills) >= 10


# ---------------------------------------------------------------------------
# Debugging / edge case patterns
# ---------------------------------------------------------------------------


class TestDebugging:
    """Debugging-related messages."""

    def test_no_funciona(self, router: SkillRouter):
        match = router.best_match("el endpoint de login no funciona")
        assert match is not None
        assert match.invoke_command == "/systematic-debugging"

    def test_doesnt_work(self, router: SkillRouter):
        match = router.best_match("the payment endpoint doesn't work")
        assert match is not None
        assert match.invoke_command == "/systematic-debugging"


# ---------------------------------------------------------------------------
# Specific skill matches
# ---------------------------------------------------------------------------


class TestSpecificSkills:
    """Test specific skill matches for various intents."""

    def test_stress_test(self, os_dev_router: SkillRouter):
        match = os_dev_router.best_match("run a stress test on the agent")
        assert match is not None
        assert match.invoke_command == "/agent-stress-test"

    def test_release(self, router: SkillRouter):
        match = router.best_match("let's tag a new release version")
        assert match is not None
        assert match.invoke_command == "/release-os"

    def test_scout(self, router: SkillRouter):
        match = router.best_match("scout the codebase before implementing")
        assert match is not None
        assert match.invoke_command == "/scout"

    def test_recommend_library(self, router: SkillRouter):
        match = router.best_match("which library should I use for caching?")
        assert match is not None
        assert match.invoke_command == "/recommend-library"

    def test_kpi(self, router: SkillRouter):
        match = router.best_match("show me the agent KPIs")
        assert match is not None
        assert match.invoke_command == "/agent-kpis"

    def test_self_improve(self, router: SkillRouter):
        match = router.best_match("run self-improvement on the system")
        assert match is not None
        assert match.invoke_command == "/self-improve"

    def test_impact_analysis(self, router: SkillRouter):
        match = router.best_match("what's the blast radius of this change?")
        assert match is not None
        assert match.invoke_command == "/impact-analysis"

    def test_singularity(self, router: SkillRouter):
        match = router.best_match("start the singularity daemon")
        assert match is not None
        assert match.invoke_command == "/singularity"

    def test_create_skill(self, router: SkillRouter):
        match = router.best_match("create a new skill for database migrations")
        assert match is not None
        assert match.invoke_command == "/skill-creator"

    def test_resume_tasks(self, router: SkillRouter):
        match = router.best_match("what was left from the previous session?")
        assert match is not None
        assert match.invoke_command == "/resume-tasks"


# ---------------------------------------------------------------------------
# Fallback handling
# ---------------------------------------------------------------------------


class TestFallbackHandling:
    """Fallback skills should appear in matches at lower confidence."""

    def test_repo_forensics_fallback(self, router: SkillRouter):
        matches = router.match(
            "analyze https://github.com/some/repo for architecture"
        )
        names = [m.skill_name for m in matches]
        assert "repo-forensics" in names
        assert "eval-repo" in names

        # Fallback should have lower confidence
        primary = next(m for m in matches if m.skill_name == "repo-forensics")
        fallback = next(m for m in matches if m.skill_name == "eval-repo")
        assert primary.confidence > fallback.confidence

    def test_bug_fix_fallback(self, router: SkillRouter):
        matches = router.match("fix the auth bug")
        names = [m.skill_name for m in matches]
        assert "plan-bug" in names
        assert "systematic-debugging" in names


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    """Same skill should not appear twice in results."""

    def test_no_duplicate_skills(self, router: SkillRouter):
        matches = router.match(
            "fix the security bug and run a security audit"
        )
        skill_names = [m.skill_name for m in matches]
        assert len(skill_names) == len(set(skill_names))


# ---------------------------------------------------------------------------
# Audience filtering
# ---------------------------------------------------------------------------


class TestAudienceMatchesContext:
    """Unit tests for the _audience_matches_context helper."""

    def test_both_always_matches_project(self):
        assert _audience_matches_context("both", "project") is True

    def test_both_always_matches_os_dev(self):
        assert _audience_matches_context("both", "os-dev") is True

    def test_human_always_matches_project(self):
        assert _audience_matches_context("human", "project") is True

    def test_human_always_matches_os_dev(self):
        assert _audience_matches_context("human", "os-dev") is True

    def test_os_dev_excluded_in_project_context(self):
        assert _audience_matches_context("os-dev", "project") is False

    def test_os_excluded_in_project_context(self):
        assert _audience_matches_context("os", "project") is False

    def test_os_dev_included_in_os_dev_context(self):
        assert _audience_matches_context("os-dev", "os-dev") is True

    def test_os_included_in_os_dev_context(self):
        assert _audience_matches_context("os", "os-dev") is True

    def test_project_included_in_project_context(self):
        assert _audience_matches_context("project", "project") is True

    def test_project_excluded_in_os_dev_context(self):
        assert _audience_matches_context("project", "os-dev") is False

    def test_unknown_audience_defaults_to_visible(self):
        """Unknown audience values should be treated as visible (backward compat)."""
        assert _audience_matches_context("unknown-value", "project") is True
        assert _audience_matches_context("unknown-value", "os-dev") is True


class TestAudienceRouterFiltering:
    """Integration tests: SkillRouter respects audience context."""

    def test_project_context_hides_os_dev_skills(self):
        """Skills tagged 'os-dev' should not appear when context is 'project'."""
        router = SkillRouter(audience_context="project")
        # Force all entries to os-dev to confirm they are hidden
        for entry in router._routing_table:
            entry.audience = "os-dev"
        matches = router.match("run a stress test on the agent")
        assert matches == [], "os-dev skills should be filtered out in project context"

    def test_os_dev_context_hides_project_skills(self):
        """Skills tagged 'project' should not appear when context is 'os-dev'."""
        router = SkillRouter(audience_context="os-dev")
        for entry in router._routing_table:
            entry.audience = "project"
        matches = router.match("run a stress test on the agent")
        assert matches == [], "project skills should be filtered out in os-dev context"

    def test_both_skills_always_appear(self):
        """Skills tagged 'both' should appear in any context."""
        for ctx in ("project", "os-dev"):
            router = SkillRouter(audience_context=ctx)
            for entry in router._routing_table:
                entry.audience = "both"
            matches = router.match("run the tests")
            assert len(matches) > 0, f"'both' skills must appear in '{ctx}' context"

    def test_human_skills_always_appear(self):
        """Skills tagged 'human' should appear in any context."""
        for ctx in ("project", "os-dev"):
            router = SkillRouter(audience_context=ctx)
            for entry in router._routing_table:
                entry.audience = "human"
            matches = router.match("run the tests")
            assert len(matches) > 0, f"'human' skills must appear in '{ctx}' context"

    def test_audience_context_stored_on_router(self):
        """audience_context property should reflect the value passed in."""
        router_proj = SkillRouter(audience_context="project")
        assert router_proj.audience_context == "project"

        router_os = SkillRouter(audience_context="os-dev")
        assert router_os.audience_context == "os-dev"

    def test_missing_audience_defaults_to_both(self):
        """Entries with no audience (default 'both') are visible in all contexts."""
        for ctx in ("project", "os-dev"):
            router = SkillRouter(audience_context=ctx)
            # Leave audience at default ("both") for all entries
            for entry in router._routing_table:
                entry.audience = "both"
            matches = router.match("run the tests")
            assert len(matches) > 0


class TestDetectAudienceContext:
    """Tests for _detect_audience_context()."""

    def test_luum_agent_os_in_path_returns_os_dev(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/home/user/luum-agent-os")
        assert _detect_audience_context() == "os-dev"

    def test_cognitive_os_in_path_returns_os_dev(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/home/user/cognitive-os")
        assert _detect_audience_context() == "os-dev"

    def test_luum_cognitive_os_in_path_returns_os_dev(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/home/user/luum-cognitive-os")
        assert _detect_audience_context() == "os-dev"

    def test_unrelated_path_returns_project(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/home/user/my-app")
        assert _detect_audience_context() == "project"

    def test_no_env_var_uses_cwd(self, monkeypatch):
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        # Just verify it returns a valid value without crashing
        result = _detect_audience_context()
        assert result in ("os-dev", "project")
