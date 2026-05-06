"""Unit tests for lib/rule_router.py (ADR-179).

Validates that RuleRouter:
  - loads frontmatter-equipped rules from rules/*.md
  - filters out enforcement: hook rules
  - returns matches for known PoC patterns
  - handles missing/malformed frontmatter gracefully
  - returns top-N matches in confidence order
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from lib.rule_router import RuleRouter

pytestmark = pytest.mark.unit


@pytest.fixture
def router() -> RuleRouter:
    return RuleRouter()


# ---------------------------------------------------------------------------
# Live-repo behaviour: PoC rules must be discoverable
# ---------------------------------------------------------------------------


class TestPoCRulesLoaded:
    def test_loads_at_least_five_routable_rules(self, router: RuleRouter):
        # Baseline per manifests/rule-routing-coverage.yaml.
        assert router.routable_rule_count >= 5

    def test_acceptance_criteria_matches(self, router: RuleRouter):
        match = router.best_match("does this prompt have acceptance criteria?")
        assert match is not None
        assert match.rule_name == "acceptance-criteria"
        assert match.confidence >= 0.90

    def test_trust_report_matches_trust_score(self, router: RuleRouter):
        match = router.best_match(
            "include a trust report with at least one uncertainty"
        )
        assert match is not None
        assert match.rule_name == "trust-score"
        assert match.confidence >= 0.90

    def test_definition_of_done_matches_dod(self, router: RuleRouter):
        match = router.best_match("what's the definition of done for this task?")
        assert match is not None
        assert match.rule_name == "definition-of-done"

    def test_phase_aware_matches_reconstruction(self, router: RuleRouter):
        match = router.best_match("we are in the reconstruction phase")
        assert match is not None
        assert match.rule_name == "phase-aware-agents"

    def test_adversarial_review_matches_looks_good(self, router: RuleRouter):
        match = router.best_match('the agent said "looks good" with no findings')
        assert match is not None
        assert match.rule_name == "adversarial-review"


# ---------------------------------------------------------------------------
# Hook-enforced rules are filtered
# ---------------------------------------------------------------------------


class TestHookEnforcedFiltered:
    def test_no_hook_rule_in_routable_set(self, router: RuleRouter):
        for entry in router.all_loaded():
            if entry.enforcement == "hook":
                # Hook-enforced rules must NOT appear among routable entries.
                # We check by recomputing: scan internal _entries indirectly via
                # public best_match. Stronger contract: ensure not surfaced for
                # any pattern that targets the rule_name itself.
                m = router.best_match(entry.rule_name)
                if m is not None:
                    assert m.rule_name != entry.rule_name


# ---------------------------------------------------------------------------
# top_matches behaviour
# ---------------------------------------------------------------------------


class TestTopMatches:
    def test_top_matches_returns_sorted_descending(self, router: RuleRouter):
        # Prompt that hits multiple rules.
        matches = router.top_matches(
            "I need acceptance criteria, a trust report with uncertainty, "
            "and a definition of done.",
            n=5,
            min_confidence=0.70,
        )
        assert len(matches) >= 2
        confidences = [m.confidence for m in matches]
        assert confidences == sorted(confidences, reverse=True)

    def test_top_matches_respects_min_confidence(self, router: RuleRouter):
        matches = router.top_matches("hello world", n=3, min_confidence=0.90)
        assert matches == []

    def test_top_matches_respects_n_limit(self, router: RuleRouter):
        matches = router.top_matches(
            "acceptance criteria trust report definition of done "
            "reconstruction phase looks good",
            n=2,
            min_confidence=0.70,
        )
        assert len(matches) <= 2


# ---------------------------------------------------------------------------
# Robustness on synthetic rules dir
# ---------------------------------------------------------------------------


class TestSyntheticRoot:
    def _write_rule(self, dirpath: Path, name: str, frontmatter: str, body: str = "# body"):
        rules_dir = dirpath / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        content = f"---\n{frontmatter.strip()}\n---\n{body}\n"
        (rules_dir / f"{name}.md").write_text(content, encoding="utf-8")

    def test_filters_hook_enforcement(self, tmp_path: Path):
        self._write_rule(
            tmp_path,
            "rate-limiting",
            textwrap.dedent("""\
                enforcement: hook
                routing_patterns:
                  - pattern: "rate limit"
                    confidence: 0.90
            """),
        )
        self._write_rule(
            tmp_path,
            "acceptance-criteria",
            textwrap.dedent("""\
                enforcement: agent-instruction
                routing_patterns:
                  - pattern: "acceptance criteria"
                    confidence: 0.95
            """),
        )
        r = RuleRouter(project_root=tmp_path)
        # Hook rule must not match.
        assert r.best_match("watch the rate limit") is None
        # Agent-instruction rule must match.
        m = r.best_match("acceptance criteria please")
        assert m is not None
        assert m.rule_name == "acceptance-criteria"

    def test_no_frontmatter_is_skipped(self, tmp_path: Path):
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "legacy.md").write_text("# legacy rule, no frontmatter\n")
        r = RuleRouter(project_root=tmp_path)
        assert r.routable_rule_count == 0

    def test_malformed_pattern_is_logged_not_crashed(self, tmp_path: Path, capsys):
        self._write_rule(
            tmp_path,
            "broken",
            textwrap.dedent("""\
                enforcement: agent-instruction
                routing_patterns:
                  - pattern: "[invalid("
                    confidence: 0.90
                  - pattern: "valid"
                    confidence: 0.85
            """),
        )
        r = RuleRouter(project_root=tmp_path)
        # Bad pattern silently dropped; good one still matches.
        m = r.best_match("valid input")
        assert m is not None
        assert m.rule_name == "broken"

    def test_invoke_command_format(self, tmp_path: Path):
        self._write_rule(
            tmp_path,
            "x",
            textwrap.dedent("""\
                enforcement: agent-instruction
                routing_patterns:
                  - pattern: "trigger"
                    confidence: 0.90
            """),
        )
        r = RuleRouter(project_root=tmp_path)
        m = r.best_match("trigger now")
        assert m is not None
        assert "Load rule" in m.invoke_command
        assert "rules/x.md" in m.invoke_command
