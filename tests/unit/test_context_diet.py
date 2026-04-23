"""Unit tests for lib/context_diet.py

Validates token estimation, minimal rule set selection, and report generation
for the Context Diet feature (Level 2 of the Agent Efficiency Strategy).
"""

import pytest
from pathlib import Path

from lib.context_diet import (
    ALWAYS_INCLUDED,
    CHARS_PER_TOKEN,
    ContextDiet,
    PREAMBLE_TOKENS,
    TASK_PROMPT_TOKENS,
    TASK_RULES,
    estimate_minimal_tokens,
    estimate_rules_tokens,
    format_diet_report,
    get_minimal_rules,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rules_dir(tmp_path: Path) -> Path:
    """Create a minimal rules directory with a few fake rule files."""
    (tmp_path / "acceptance-criteria.md").write_text("A" * 4000)   # ~1000 tokens
    (tmp_path / "trust-score.md").write_text("B" * 2000)           # ~500 tokens
    (tmp_path / "RULES-COMPACT.md").write_text("C" * 6000)         # ~1500 tokens
    (tmp_path / "adversarial-review.md").write_text("D" * 3200)    # ~800 tokens
    (tmp_path / "error-learning.md").write_text("E" * 1600)        # ~400 tokens
    return tmp_path


# ---------------------------------------------------------------------------
# estimate_rules_tokens
# ---------------------------------------------------------------------------


class TestEstimateRulesTokens:
    def test_counts_all_md_files(self, rules_dir: Path) -> None:
        """Should sum character sizes of all .md files."""
        total = estimate_rules_tokens(str(rules_dir))
        # 4000 + 2000 + 6000 + 3200 + 1600 = 16800 chars / 4 = 4200 tokens
        assert total == 4200

    def test_returns_zero_for_missing_dir(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent"
        assert estimate_rules_tokens(str(missing)) == 0

    def test_empty_directory_returns_zero(self, tmp_path: Path) -> None:
        assert estimate_rules_tokens(str(tmp_path)) == 0

    def test_ignores_non_md_files(self, tmp_path: Path) -> None:
        """Non-.md files should not be counted."""
        (tmp_path / "somefile.txt").write_text("A" * 4000)
        (tmp_path / "script.sh").write_text("B" * 2000)
        (tmp_path / "rule.md").write_text("C" * 800)
        total = estimate_rules_tokens(str(tmp_path))
        assert total == 200  # only rule.md: 800 / 4

    def test_returns_integer(self, rules_dir: Path) -> None:
        result = estimate_rules_tokens(str(rules_dir))
        assert isinstance(result, int)

    def test_single_file(self, tmp_path: Path) -> None:
        (tmp_path / "single.md").write_text("X" * 400)
        assert estimate_rules_tokens(str(tmp_path)) == 100

    def test_uses_chars_per_token_constant(self, tmp_path: Path) -> None:
        """Result should equal total_chars // CHARS_PER_TOKEN."""
        (tmp_path / "a.md").write_text("Y" * (CHARS_PER_TOKEN * 50))
        assert estimate_rules_tokens(str(tmp_path)) == 50


# ---------------------------------------------------------------------------
# get_minimal_rules
# ---------------------------------------------------------------------------


class TestGetMinimalRules:
    def test_implementation_includes_required_rules(self) -> None:
        rules = get_minimal_rules("implementation")
        assert "acceptance-criteria.md" in rules
        assert "closed-loop-prompts.md" in rules
        assert "trust-score.md" in rules

    def test_review_includes_adversarial_review(self) -> None:
        rules = get_minimal_rules("review")
        assert "adversarial-review.md" in rules
        assert "trust-score.md" in rules
        assert "agent-quality.md" in rules

    def test_debugging_includes_error_learning(self) -> None:
        rules = get_minimal_rules("debugging")
        assert "error-learning.md" in rules
        assert "closed-loop-prompts.md" in rules

    def test_docs_returns_always_included_only(self) -> None:
        rules = get_minimal_rules("docs")
        # docs has no task-specific rules beyond always-included
        for rule in rules:
            assert rule in ALWAYS_INCLUDED

    def test_archiving_returns_always_included_only(self) -> None:
        rules = get_minimal_rules("archiving")
        for rule in rules:
            assert rule in ALWAYS_INCLUDED

    def test_always_included_present_in_all_types(self) -> None:
        for task_type in TASK_RULES:
            rules = get_minimal_rules(task_type)
            for always_rule in ALWAYS_INCLUDED:
                assert always_rule in rules, (
                    f"{always_rule} missing from {task_type} rules"
                )

    def test_rules_compact_is_first(self) -> None:
        """RULES-COMPACT.md should always be the first entry."""
        for task_type in TASK_RULES:
            rules = get_minimal_rules(task_type)
            assert rules[0] == "RULES-COMPACT.md"

    def test_no_duplicates(self) -> None:
        for task_type in TASK_RULES:
            rules = get_minimal_rules(task_type)
            assert len(rules) == len(set(rules)), (
                f"Duplicate rules in {task_type}: {rules}"
            )

    def test_unknown_task_type_returns_always_included(self) -> None:
        rules = get_minimal_rules("unknown_task")
        assert set(rules) == set(ALWAYS_INCLUDED)

    def test_implementation_smaller_than_all_rules(self) -> None:
        """Minimal rule set should be much smaller than the full rule set."""
        rules = get_minimal_rules("implementation")
        # Full rule set has 70+ files; minimal should have < 10
        assert len(rules) <= 10

    def test_returns_list_of_strings(self) -> None:
        rules = get_minimal_rules("implementation")
        assert isinstance(rules, list)
        assert all(isinstance(r, str) for r in rules)

    def test_all_rule_names_end_with_md(self) -> None:
        for task_type in TASK_RULES:
            for rule in get_minimal_rules(task_type):
                assert rule.endswith(".md"), (
                    f"Rule {rule!r} in {task_type} does not end with .md"
                )


# ---------------------------------------------------------------------------
# estimate_minimal_tokens
# ---------------------------------------------------------------------------


class TestEstimateMinimalTokens:
    def test_uses_disk_files_when_rules_dir_provided(self, rules_dir: Path) -> None:
        """When rules_dir is given and files exist, should read actual sizes."""
        # RULES-COMPACT.md is 6000 chars = 1500 tokens
        # adaptive-bypass.md not in fixture, so skipped
        # agent-quality.md not in fixture, so skipped
        # credential-management.md not in fixture, so skipped
        # For "archiving" (only ALWAYS_INCLUDED), only RULES-COMPACT.md present
        # so result should reflect only the files that actually exist
        result = estimate_minimal_tokens("archiving", str(rules_dir))
        assert isinstance(result, int)
        assert result > 0

    def test_fallback_when_no_rules_dir(self) -> None:
        """Without rules_dir, should use per-rule estimate."""
        result = estimate_minimal_tokens("implementation")
        assert result > 0
        assert isinstance(result, int)

    def test_implementation_gt_archiving(self) -> None:
        """Implementation needs more rules than archiving."""
        impl_tokens = estimate_minimal_tokens("implementation")
        arch_tokens = estimate_minimal_tokens("archiving")
        assert impl_tokens > arch_tokens

    def test_nonexistent_rules_dir_uses_fallback(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent"
        result = estimate_minimal_tokens("implementation", str(missing))
        assert result > 0

    def test_empty_rules_dir_returns_zero(self, tmp_path: Path) -> None:
        """Empty directory means no files found = 0 tokens from disk."""
        result = estimate_minimal_tokens("implementation", str(tmp_path))
        assert result == 0


# ---------------------------------------------------------------------------
# format_diet_report
# ---------------------------------------------------------------------------


class TestFormatDietReport:
    def test_returns_non_empty_string(self, rules_dir: Path) -> None:
        report = format_diet_report(str(rules_dir))
        assert isinstance(report, str)
        assert len(report) > 0

    def test_report_contains_task_types(self, rules_dir: Path) -> None:
        report = format_diet_report(str(rules_dir))
        for task_type in TASK_RULES:
            assert task_type in report

    def test_report_contains_current_baseline(self, rules_dir: Path) -> None:
        report = format_diet_report(str(rules_dir))
        assert "Current baseline" in report
        assert "TOTAL" in report

    def test_report_contains_recommendations(self, rules_dir: Path) -> None:
        report = format_diet_report(str(rules_dir))
        assert "Recommendations" in report
        assert "model_capability.level" in report

    def test_report_mentions_target(self, rules_dir: Path) -> None:
        report = format_diet_report(str(rules_dir))
        assert "10,000 tokens" in report

    def test_report_handles_missing_dir(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent"
        report = format_diet_report(str(missing))
        assert "Context Diet Report" in report

    def test_report_shows_savings_percentage(self, rules_dir: Path) -> None:
        report = format_diet_report(str(rules_dir))
        assert "saves" in report
        assert "%" in report

    def test_report_header(self, rules_dir: Path) -> None:
        report = format_diet_report(str(rules_dir))
        assert "Context Diet Report" in report

    def test_report_includes_system_prompt_line(self, rules_dir: Path) -> None:
        report = format_diet_report(str(rules_dir))
        assert "System prompt" in report

    def test_report_optimal_section(self, rules_dir: Path) -> None:
        report = format_diet_report(str(rules_dir))
        assert "Optimal per task type" in report


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestModuleConstants:
    def test_chars_per_token_is_positive(self) -> None:
        assert CHARS_PER_TOKEN > 0

    def test_preamble_tokens_positive(self) -> None:
        assert PREAMBLE_TOKENS > 0

    def test_task_prompt_tokens_positive(self) -> None:
        assert TASK_PROMPT_TOKENS > 0

    def test_always_included_is_not_empty(self) -> None:
        assert len(ALWAYS_INCLUDED) > 0

    def test_always_included_contains_rules_compact(self) -> None:
        assert "RULES-COMPACT.md" in ALWAYS_INCLUDED

    def test_task_rules_has_expected_keys(self) -> None:
        expected_keys = {"implementation", "review", "debugging", "docs", "archiving"}
        assert set(TASK_RULES.keys()) == expected_keys

    def test_task_rules_values_are_lists(self) -> None:
        for task, rules in TASK_RULES.items():
            assert isinstance(rules, list), f"{task} rules should be a list"


class TestContextDietRulesDirResolution:
    def test_from_yaml_prefers_canonical_rules_dir(self, tmp_path: Path) -> None:
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("project:\n  phase: reconstruction\n")
        canonical = tmp_path / ".cognitive-os" / "rules" / "cos"
        driver = tmp_path / ".claude" / "rules" / "cos"
        canonical.mkdir(parents=True)
        driver.mkdir(parents=True)

        diet = ContextDiet.from_yaml(str(config))
        assert diet.rules_dir == str(canonical)

    def test_from_yaml_falls_back_to_claude_rules(self, tmp_path: Path) -> None:
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("project:\n  phase: reconstruction\n")
        driver = tmp_path / ".claude" / "rules" / "cos"
        driver.mkdir(parents=True)

        diet = ContextDiet.from_yaml(str(config))
        assert diet.rules_dir == str(driver)

    def test_from_yaml_falls_back_to_repo_rules_source(self, tmp_path: Path) -> None:
        config = tmp_path / "cognitive-os.yaml"
        config.write_text("project:\n  phase: reconstruction\n")
        repo_rules = tmp_path / "rules"
        repo_rules.mkdir(parents=True)

        diet = ContextDiet.from_yaml(str(config))
        assert diet.rules_dir == str(repo_rules)
