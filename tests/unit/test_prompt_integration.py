"""Integration tests for lib/prompt_builder.py

Verifies that context_diet and prompt_cache are correctly wired together:
  - ContextDiet returns different rule sets for different task types.
  - PromptCache correctly marks content with cache_control breakpoints.
  - PromptBuilder composes both without breaking existing agent launch flow.
"""

from __future__ import annotations

import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rules_dir(tmp_path: Path) -> Path:
    """Create a minimal rules directory for tests that read from disk."""
    (tmp_path / "RULES-COMPACT.md").write_text("# RULES-COMPACT\n" + "A" * 2000)
    (tmp_path / "acceptance-criteria.md").write_text("# Acceptance Criteria\n" + "B" * 1600)
    (tmp_path / "trust-score.md").write_text("# Trust Score\n" + "C" * 1200)
    (tmp_path / "adversarial-review.md").write_text("# Adversarial Review\n" + "D" * 1200)
    (tmp_path / "error-learning.md").write_text("# Error Learning\n" + "E" * 800)
    (tmp_path / "closed-loop-prompts.md").write_text("# Closed Loop\n" + "F" * 800)
    (tmp_path / "definition-of-done.md").write_text("# DoD\n" + "G" * 800)
    (tmp_path / "phase-aware-agents.md").write_text("# Phase\n" + "H" * 600)
    (tmp_path / "adaptive-bypass.md").write_text("# Adaptive Bypass\n" + "I" * 600)
    (tmp_path / "agent-quality.md").write_text("# Agent Quality\n" + "J" * 1000)
    (tmp_path / "credential-management.md").write_text("# Credentials\n" + "K" * 400)
    return tmp_path


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """Create a minimal cognitive-os.yaml for tests."""
    config = tmp_path / "cognitive-os.yaml"
    config.write_text(
        "project:\n  phase: reconstruction\n  name: test-project\n"
    )
    return config


@pytest.fixture
def preamble_file(tmp_path: Path) -> Path:
    """Create a minimal agent-preamble.md template."""
    templates = tmp_path / "templates"
    templates.mkdir()
    preamble = templates / "agent-preamble.md"
    preamble.write_text(
        "# Agent Preamble\nYou are a sub-agent. Phase: {{phase}}\n"
    )
    (templates / "agent-planning.md").write_text(
        "# Agent Planning Template (ADR-038 Wave 4)\nPLAN:\n"
    )
    return preamble


@pytest.fixture
def project_dir(tmp_path: Path, rules_dir: Path, config_file: Path, preamble_file: Path) -> Path:
    """Full project fixture with config, rules, and preamble."""
    # Move rules into project_dir/rules/
    project_rules = tmp_path / "rules"
    project_rules.mkdir()
    for md_file in rules_dir.glob("*.md"):
        (project_rules / md_file.name).write_text(md_file.read_text())

    # Move config into project root
    (tmp_path / "cognitive-os.yaml").write_text(config_file.read_text())

    # Templates are already in tmp_path/templates/
    return tmp_path


# ---------------------------------------------------------------------------
# 1. context_diet returns different rule sets for different task types
# ---------------------------------------------------------------------------


class TestContextDietRuleSelection:
    """Verify context_diet.get_minimal_rules returns task-appropriate rules."""

    def test_implementation_rules_differ_from_review(self) -> None:
        from lib.context_diet import get_minimal_rules

        impl_rules = set(get_minimal_rules("implementation"))
        review_rules = set(get_minimal_rules("review"))

        assert impl_rules != review_rules

    def test_implementation_has_closed_loop(self) -> None:
        from lib.context_diet import get_minimal_rules

        rules = get_minimal_rules("implementation")
        assert "closed-loop-prompts.md" in rules

    def test_review_has_adversarial(self) -> None:
        from lib.context_diet import get_minimal_rules

        rules = get_minimal_rules("review")
        assert "adversarial-review.md" in rules

    def test_debugging_has_error_learning(self) -> None:
        from lib.context_diet import get_minimal_rules

        rules = get_minimal_rules("debugging")
        assert "error-learning.md" in rules

    def test_archiving_is_minimal(self) -> None:
        from lib.context_diet import get_minimal_rules, ALWAYS_INCLUDED

        rules = get_minimal_rules("archiving")
        # archiving should only have always-included rules
        for rule in rules:
            assert rule in ALWAYS_INCLUDED

    def test_unknown_type_returns_always_included_only(self) -> None:
        from lib.context_diet import get_minimal_rules, ALWAYS_INCLUDED

        rules = get_minimal_rules("totally_unknown_task_type")
        assert set(rules) == set(ALWAYS_INCLUDED)

    def test_rules_compact_always_first(self) -> None:
        from lib.context_diet import get_minimal_rules, TASK_RULES

        for task_type in TASK_RULES:
            rules = get_minimal_rules(task_type)
            assert rules[0] == "RULES-COMPACT.md"

    def test_context_diet_class_returns_different_rules(self) -> None:
        from lib.context_diet import ContextDiet

        diet = ContextDiet({"project": {"phase": "reconstruction"}})
        impl_rules = diet.select_rules("implement")
        review_rules = diet.select_rules("review")
        archive_rules = diet.select_rules("archive")

        assert set(impl_rules) != set(review_rules)
        assert len(archive_rules) < len(impl_rules)

    def test_context_diet_explore_is_minimal(self) -> None:
        from lib.context_diet import ContextDiet

        diet = ContextDiet({"project": {"phase": "reconstruction"}})
        explore_rules = diet.select_rules("explore")
        # explore is minimal — only RULES-COMPACT.md
        assert explore_rules == ["RULES-COMPACT.md"]

    def test_context_diet_production_phase_adds_phase_rules(self) -> None:
        from lib.context_diet import ContextDiet

        diet_prod = ContextDiet({"project": {"phase": "production"}})
        diet_reco = ContextDiet({"project": {"phase": "reconstruction"}})

        prod_rules = set(diet_prod.select_rules("implement"))
        set(diet_reco.select_rules("implement"))

        # Production adds phase-aware-agents.md
        assert "phase-aware-agents.md" in prod_rules


# ---------------------------------------------------------------------------
# 2. prompt_cache correctly marks content with cache_control
# ---------------------------------------------------------------------------


class TestPromptCacheCacheControl:
    """Verify prompt_cache applies cache_control markers correctly."""

    def test_system_prompt_block_has_cache_control(self) -> None:
        from lib.prompt_cache import apply_cache_to_system_prompt

        result = apply_cache_to_system_prompt("You are a helpful agent.")
        assert len(result) == 1
        block = result[0]
        assert block["type"] == "text"
        assert "cache_control" in block
        assert block["cache_control"]["type"] == "ephemeral"

    def test_message_cache_marks_system_message(self) -> None:
        from lib.prompt_cache import apply_message_cache

        messages = [
            {"role": "system", "content": "System rules here"},
            {"role": "user", "content": "Do the task"},
        ]
        result = apply_message_cache(messages)
        # System message content should be wrapped with cache_control
        sys_content = result[0]["content"]
        assert isinstance(sys_content, list)
        assert sys_content[0]["cache_control"]["type"] == "ephemeral"

    def test_original_messages_not_mutated(self) -> None:
        from lib.prompt_cache import apply_message_cache

        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Hello"},
        ]
        original_system = messages[0]["content"]
        apply_message_cache(messages)
        # Original should be unchanged (still a string)
        assert messages[0]["content"] == original_system

    def test_max_4_cache_breakpoints(self) -> None:
        from lib.prompt_cache import apply_message_cache

        messages = (
            [{"role": "system", "content": "System"}]
            + [
                {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg{i}"}
                for i in range(8)
            ]
        )
        result = apply_message_cache(messages)

        count = 0
        for msg in result:
            content = msg.get("content")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "cache_control" in item:
                        count += 1
            elif "cache_control" in msg:
                count += 1
        assert count <= 4

    def test_1h_ttl_propagated_to_block(self) -> None:
        from lib.prompt_cache import apply_cache_to_system_prompt

        result = apply_cache_to_system_prompt("System prompt", cache_ttl="1h")
        assert result[0]["cache_control"]["ttl"] == "1h"

    def test_empty_message_list(self) -> None:
        from lib.prompt_cache import apply_message_cache

        assert apply_message_cache([]) == []


# ---------------------------------------------------------------------------
# 3. PromptBuilder integration — wires both modules without breaking flow
# ---------------------------------------------------------------------------


class TestPromptBuilderIntegration:
    """Verify PromptBuilder correctly combines context_diet and prompt_cache."""

    def test_build_system_prompt_returns_list(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(project_dir))
        result = builder.build_system_prompt(task_type="implement")
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_build_system_prompt_has_cache_control(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(project_dir), enable_cache=True)
        result = builder.build_system_prompt(task_type="implement")
        block = result[-1]  # last block carries the marker
        assert "cache_control" in block
        assert block["cache_control"]["type"] == "ephemeral"

    def test_build_system_prompt_no_cache_when_disabled(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(project_dir), enable_cache=False)
        result = builder.build_system_prompt(task_type="implement")
        block = result[-1]
        assert "cache_control" not in block

    def test_build_system_prompt_contains_preamble(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(project_dir))
        result = builder.build_system_prompt(
            task_type="implement",
            preamble="CUSTOM_PREAMBLE_TEXT",
        )
        block = result[-1]
        assert "CUSTOM_PREAMBLE_TEXT" in block["text"]

    def test_build_system_prompt_different_rules_per_task(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(project_dir))
        impl_result = builder.build_system_prompt(task_type="implement")
        review_result = builder.build_system_prompt(task_type="review")

        impl_text = impl_result[-1]["text"]
        review_text = review_result[-1]["text"]

        # Different task types should yield different content
        assert impl_text != review_text

    def test_build_messages_starts_with_system(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(project_dir))
        messages = builder.build_messages(
            task_type="debug",
            conversation=[{"role": "user", "content": "Fix this bug"}],
        )
        assert messages[0]["role"] == "system"

    def test_build_messages_conversation_appended(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(project_dir))
        user_msg = {"role": "user", "content": "Task description"}
        messages = builder.build_messages(task_type="implement", conversation=[user_msg])

        # System + at least one user message
        assert len(messages) >= 2
        roles = [m["role"] for m in messages]
        assert "system" in roles
        assert "user" in roles

    def test_build_messages_cache_applied_to_system(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(project_dir), enable_cache=True)
        messages = builder.build_messages(
            task_type="review",
            conversation=[{"role": "user", "content": "Review the code"}],
        )
        sys_content = messages[0]["content"]
        assert isinstance(sys_content, list)
        assert sys_content[0]["cache_control"]["type"] == "ephemeral"

    def test_selected_rules_delegated_to_diet(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder
        from lib.context_diet import ContextDiet

        builder = PromptBuilder.from_project(str(project_dir))
        diet = ContextDiet({"project": {"phase": "reconstruction"}})

        builder_rules = set(builder.selected_rules("implement"))
        diet_rules = set(diet.select_rules("implement"))

        # PromptBuilder.selected_rules should match ContextDiet.select_rules
        assert builder_rules == diet_rules

    def test_phase_exposed(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(project_dir))
        assert builder.phase == "reconstruction"

    def test_from_project_works_with_missing_config(self, tmp_path: Path) -> None:
        """PromptBuilder.from_project should not raise when config is missing."""
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(tmp_path))
        result = builder.build_system_prompt(task_type="implement")
        assert isinstance(result, list)

    def test_archive_task_has_fewer_rules_than_implement(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(project_dir))
        archive_rules = builder.selected_rules("archive")
        impl_rules = builder.selected_rules("implement")

        assert len(archive_rules) <= len(impl_rules)

    def test_preamble_phase_interpolated(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(project_dir))
        result = builder.build_system_prompt(task_type="implement")
        text = result[-1]["text"]
        # {{phase}} should be replaced with actual phase value
        assert "{{phase}}" not in text
        assert "reconstruction" in text

    def test_planning_task_includes_separate_planning_template(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(project_dir), enable_cache=False)
        result = builder.build_system_prompt(task_type="planning")
        text = result[-1]["text"]
        assert "Agent Planning Template (ADR-038 Wave 4)" in text
        assert "PLAN:" in text

    def test_implementation_task_omits_planning_template(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(project_dir), enable_cache=False)
        result = builder.build_system_prompt(task_type="implement")
        text = result[-1]["text"]
        assert "Agent Planning Template (ADR-038 Wave 4)" not in text

    def test_build_prompt_for_hook_returns_string(self, project_dir: Path) -> None:
        from lib.prompt_builder import build_prompt_for_hook

        output = build_prompt_for_hook(
            task_type="implement",
            project_dir=str(project_dir),
        )
        assert isinstance(output, str)
        assert "PROMPT BUILDER" in output
        assert "implement" in output

    def test_build_prompt_for_hook_graceful_on_bad_dir(self) -> None:
        from lib.prompt_builder import build_prompt_for_hook

        # Should not raise even with a nonexistent project dir
        output = build_prompt_for_hook(task_type="debug", project_dir="/nonexistent/path")
        assert isinstance(output, str)

    def test_cache_ttl_1h_propagated(self, project_dir: Path) -> None:
        from lib.prompt_builder import PromptBuilder

        builder = PromptBuilder.from_project(str(project_dir), cache_ttl="1h")
        result = builder.build_system_prompt(task_type="implement")
        block = result[-1]
        assert "cache_control" in block
        assert block["cache_control"].get("ttl") == "1h"


# ---------------------------------------------------------------------------
# 4. Verify existing imports still work (no breakage)
# ---------------------------------------------------------------------------


class TestNoBreakageOfExistingModules:
    """Ensure importing prompt_builder does not break context_diet or prompt_cache."""

    def test_context_diet_importable_independently(self) -> None:
        from lib.context_diet import get_minimal_rules, ContextDiet

        rules = get_minimal_rules("implementation")
        assert isinstance(rules, list)
        diet = ContextDiet({"project": {"phase": "reconstruction"}})
        assert diet.phase == "reconstruction"

    def test_prompt_cache_importable_independently(self) -> None:
        from lib.prompt_cache import apply_cache_to_system_prompt, apply_message_cache

        blocks = apply_cache_to_system_prompt("test")
        assert isinstance(blocks, list)

        msgs = apply_message_cache([{"role": "system", "content": "test"}])
        assert isinstance(msgs, list)

    def test_prompt_builder_importable(self) -> None:
        from lib.prompt_builder import PromptBuilder, build_prompt_for_hook

        assert callable(PromptBuilder.from_project)
        assert callable(build_prompt_for_hook)

    def test_both_modules_coexist_without_error(self) -> None:
        """Importing both modules in the same session must not cause errors."""
        from lib.context_diet import ContextDiet, get_minimal_rules
        from lib.prompt_cache import apply_cache_to_system_prompt
        from lib.prompt_builder import PromptBuilder

        # Use both independently
        get_minimal_rules("review")
        diet = ContextDiet({"project": {"phase": "production"}})
        content = diet.get_lean_context("review")
        apply_cache_to_system_prompt(content)

        # And through the builder
        builder = PromptBuilder(diet=diet, project_dir=".", enable_cache=True)
        result = builder.build_system_prompt(task_type="review", preamble="Test preamble")

        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[-1]["cache_control"]["type"] == "ephemeral"
