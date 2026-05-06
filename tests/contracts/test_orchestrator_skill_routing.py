"""Contract tests: orchestrator skill-routing observability gap closure.

Validates that SkillRouter.best_match() correctly identifies canonical skills
from natural-language orchestrator prompts. These tests close the gap identified
by the dogfood-score audit (skill_coverage = 24.07/100): the orchestrator must
be nudged toward canonical research skills rather than bespoke prompts.

Each test asserts:
  - best_match() returns a SkillMatch (not None)
  - invoke_command matches the expected canonical skill
  - confidence >= threshold (0.80 for primary, 0.70 for weaker signals)

Coverage scenarios:
  1. GitHub repo audit URL -> /repo-scout or /repo-forensics
  2. Reverse-engineer config schema intent -> /reverse-engineer
  3. Open-ended research protocol -> /deep-research
  4. Library recommendation/selection -> /recommend-library
  5. Ecosystem evaluation / plugin staleness -> /repo-forensics or /repo-scout
  6. Batch-audit multiple repos -> /repo-forensics
  7. Debug investigation -> /systematic-debugging or /plan-bug
"""

import pytest

from lib.skill_router import SkillRouter

pytestmark = pytest.mark.contract


@pytest.fixture(scope="module")
def router() -> SkillRouter:
    return SkillRouter()


# ─── Scenario 1: GitHub repo audit URL ───────────────────────────────────────


def test_audit_github_url_https_suggests_repo_skill(router: SkillRouter):
    """Auditing a GitHub repo via HTTPS URL should suggest /repo-forensics or /repo-scout.

    Note: the router matches the https:// URL regex; bare github.com/ without
    scheme does not match — this is intentional (mirrors real orchestrator prompts).
    """
    text = "audit https://github.com/HKUDS/OpenSpace and tell me if it's worth adopting"
    match = router.best_match(text)
    assert match is not None, f"Expected a match for: {text!r}"
    assert match.invoke_command in (
        "/repo-scout", "/repo-forensics"
    ), f"Got unexpected command: {match.invoke_command}"
    assert match.confidence >= 0.90, (
        f"URL match should yield high confidence, got {match.confidence:.2f}"
    )


def test_analyze_repo_suggests_repo_forensics(router: SkillRouter):
    """Explicit 'analyze this repo' phrasing should route to /repo-forensics."""
    text = "analyze https://github.com/anthropics/claude-code for architecture quality"
    match = router.best_match(text)
    assert match is not None, f"Expected a match for: {text!r}"
    assert match.invoke_command in ("/repo-forensics", "/repo-scout")
    assert match.confidence >= 0.90


# ─── Scenario 2: Reverse-engineer config schema ───────────────────────────────


def test_understand_internal_schema_suggests_reverse_engineer(router: SkillRouter):
    """Understanding an internal schema should suggest /reverse-engineer."""
    text = "I need to understand the config schema of an upstream application's internal routes"
    match = router.best_match(text)
    assert match is not None, f"Expected a match for: {text!r}"
    assert match.invoke_command == "/reverse-engineer", (
        f"Expected /reverse-engineer, got {match.invoke_command}"
    )
    assert match.confidence >= 0.75, (
        f"Confidence too low: {match.confidence:.2f}"
    )


def test_reverse_engineer_explicit_suggests_reverse_engineer(router: SkillRouter):
    """Explicit 'reverse engineer' phrase should match with high confidence."""
    text = "reverse engineer the config structure of the legacy service"
    match = router.best_match(text)
    assert match is not None
    assert match.invoke_command == "/reverse-engineer"
    assert match.confidence >= 0.90


# ─── Scenario 3: Open-ended research protocol ────────────────────────────────


def test_open_ended_research_intent(router: SkillRouter):
    """Open research questions should route to /deep-research or similar."""
    text = "research the landscape of open-source LLM orchestration frameworks"
    match = router.best_match(text)
    assert match is not None, f"Expected a match for: {text!r}"
    assert match.invoke_command in (
        "/deep-research", "/research-protocol", "/tool-discovery"
    ), f"Unexpected command: {match.invoke_command}"
    assert match.confidence >= 0.75


# ─── Scenario 4: Library recommendation ─────────────────────────────────────


def test_library_selection_suggests_recommend_library(router: SkillRouter):
    """Library selection questions should route to /recommend-library."""
    text = "which library should I use for distributed tracing in Go?"
    match = router.best_match(text)
    assert match is not None, f"Expected a match for: {text!r}"
    assert match.invoke_command == "/recommend-library", (
        f"Expected /recommend-library, got {match.invoke_command}"
    )
    assert match.confidence >= 0.80


def test_suggest_package_suggests_recommend_library(router: SkillRouter):
    """Suggesting a package should also map to /recommend-library."""
    text = "suggest a package for caching in Python with TTL support"
    match = router.best_match(text)
    assert match is not None, f"Expected a match for: {text!r}"
    assert match.invoke_command == "/recommend-library"
    assert match.confidence >= 0.80


# ─── Scenario 5: Ecosystem evaluation / plugin staleness ─────────────────────


def test_ecosystem_evaluation_suggests_repo_skill(router: SkillRouter):
    """Evaluating a repo for adoption should suggest /repo-forensics or /repo-scout."""
    text = (
        "evaluate this repo and tell me if plugins are stale: "
        "https://github.com/some-org/plugins"
    )
    match = router.best_match(text)
    assert match is not None, f"Expected a match for: {text!r}"
    assert match.invoke_command in (
        "/repo-scout", "/repo-forensics", "/eval-repo"
    ), f"Unexpected command: {match.invoke_command}"
    assert match.confidence >= 0.80


# ─── Scenario 6: Batch-audit multiple repos ───────────────────────────────────


def test_batch_audit_repos_suggests_repo_forensics(router: SkillRouter):
    """Batch-auditing GitHub repos should suggest a repo analysis skill."""
    text = (
        "audit https://github.com/org/repo-a and https://github.com/org/repo-b "
        "for security issues and adoption fit"
    )
    match = router.best_match(text)
    assert match is not None, f"Expected a match for: {text!r}"
    assert match.invoke_command in ("/repo-forensics", "/repo-scout")
    assert match.confidence >= 0.90


# ─── Scenario 7: Debug investigation ─────────────────────────────────────────


def test_debug_failing_endpoint(router: SkillRouter):
    """Debugging a failing endpoint should suggest /systematic-debugging or /plan-bug."""
    text = "debug why the payment endpoint doesn't return 200 after the migration"
    match = router.best_match(text)
    assert match is not None, f"Expected a match for: {text!r}"
    assert match.invoke_command in (
        "/systematic-debugging", "/plan-bug"
    ), f"Unexpected command: {match.invoke_command}"
    assert match.confidence >= 0.80
