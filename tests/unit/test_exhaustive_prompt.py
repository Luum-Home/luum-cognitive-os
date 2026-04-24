"""Behavioral tests for skills/exhaustive-prompt — ADR-059 Phase 1 pilot.

exhaustive-prompt generates agent prompts with scope enumeration.
The skill is agent-instructional but has a well-defined OUTPUT FORMAT
that can be tested for structural compliance (no LLM calls needed).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

pytestmark = pytest.mark.unit

# Required sections in an exhaustive prompt output (from SKILL.md)
REQUIRED_SECTIONS = [
    "## Context",
    "## Scope",
    "## ACCEPTANCE CRITERIA:",
    "## VERIFICATION:",
    "## Definition of Done:",
]

VALID_DOD_LEVELS = {"trivial", "small", "medium", "large", "critical"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def build_sample_exhaustive_prompt(
    task: str = "Rename old-service to new-service",
    scope_items: list[str] | None = None,
    dod_level: str = "medium",
) -> str:
    """Build a minimal exhaustive prompt matching the SKILL.md output format."""
    if scope_items is None:
        scope_items = [
            "1. apps/service/config.go — line 5: 'old-service' -> 'new-service'",
            "2. apps/service/README.md — line 1: 'old-service' -> 'new-service'",
        ]
    scope_block = "\n".join(scope_items)

    return f"""# Task: {task}

## Context
This renames the service to match the new brand identity.

## Scope
{scope_block}
Total: {len(scope_items)} items

## FILES TO PROCESS ({len(scope_items)} files, exhaustive):
{scope_block}

## Instructions
1. Replace every occurrence of 'old-service' with 'new-service'
2. Verify no occurrences remain

## Patterns to Follow
- Use exact replacement, preserve case

## ACCEPTANCE CRITERIA:
1. Zero remaining occurrences: `grep -rl 'old-service' . | wc -l` = 0
2. Build passes: `go build ./...` exits 0

## VERIFICATION:
Run ALL commands. ALL must pass.
1. `grep -rl 'old-service' .` — Expected: empty output
2. `go build ./...` — Expected: exit code 0

## Definition of Done: {dod_level}
- [ ] code_compiles
- [ ] unit_tests_added
- [ ] coverage_maintained
"""


# ---------------------------------------------------------------------------
# 1. Imports / invocation — SKILL.md exists with correct frontmatter
# ---------------------------------------------------------------------------


class TestExhaustivePromptSkillExists:
    def test_skill_md_present(self):
        skill_md = PROJECT_ROOT / "skills" / "exhaustive-prompt" / "SKILL.md"
        assert skill_md.exists()

    def test_skill_md_has_acceptance_criteria_section(self):
        """SKILL.md itself must document the ACCEPTANCE CRITERIA: output format."""
        skill_md = PROJECT_ROOT / "skills" / "exhaustive-prompt" / "SKILL.md"
        content = skill_md.read_text()
        assert "ACCEPTANCE CRITERIA:" in content

    def test_skill_md_has_verification_section(self):
        """SKILL.md must document the VERIFICATION: output section."""
        skill_md = PROJECT_ROOT / "skills" / "exhaustive-prompt" / "SKILL.md"
        content = skill_md.read_text()
        assert "VERIFICATION" in content


# ---------------------------------------------------------------------------
# 2. Contract test — exhaustive prompt output format validation
# ---------------------------------------------------------------------------


class TestExhaustivePromptContract:
    def test_all_required_sections_present(self):
        """A well-formed exhaustive prompt must contain all required sections."""
        prompt = build_sample_exhaustive_prompt()
        for section in REQUIRED_SECTIONS:
            assert section in prompt, f"Missing required section: {section}"

    def test_scope_total_count_matches_item_list(self):
        """Total: N items must match the actual number of scope items listed."""
        items = [f"{i}. file_{i}.go" for i in range(1, 8)]
        prompt = build_sample_exhaustive_prompt(scope_items=items)

        total_match = re.search(r"Total:\s*(\d+)\s*items", prompt)
        assert total_match, "Missing 'Total: N items' in Scope section"
        declared_total = int(total_match.group(1))
        assert declared_total == len(items), (
            f"Declared total {declared_total} != actual items {len(items)}"
        )

    def test_dod_level_is_valid(self):
        """Definition of Done level must be one of the 5 valid complexity levels."""
        for level in VALID_DOD_LEVELS:
            prompt = build_sample_exhaustive_prompt(dod_level=level)
            assert f"## Definition of Done: {level}" in prompt

    def test_acceptance_criteria_has_verifiable_commands(self):
        """Acceptance criteria must contain backtick-quoted commands."""
        prompt = build_sample_exhaustive_prompt()
        criteria_start = prompt.find("## ACCEPTANCE CRITERIA:")
        assert criteria_start >= 0
        criteria_section = prompt[criteria_start:]
        # Should have at least one backtick-quoted command
        assert "`" in criteria_section, (
            "ACCEPTANCE CRITERIA section must contain backtick-quoted commands"
        )


# ---------------------------------------------------------------------------
# 3. Happy path — anti-pattern detection documented in SKILL.md
# ---------------------------------------------------------------------------


class TestExhaustivePromptHappyPath:
    def test_anti_pattern_no_vague_scope(self):
        """A prompt saying 'all files' without listing them violates the skill's contract."""
        vague_prompt = "Rename all files to use the new service name."
        has_file_list = bool(re.search(r"^\d+\.", vague_prompt, re.MULTILINE))
        has_total = "Total:" in vague_prompt
        assert not has_file_list and not has_total, (
            "A vague prompt should NOT have file lists — it needs /exhaustive-prompt first"
        )

    def test_exhaustive_prompt_not_vague(self):
        """The output of /exhaustive-prompt must have numbered file list."""
        prompt = build_sample_exhaustive_prompt()
        numbered_items = re.findall(r"^\d+\.", prompt, re.MULTILINE)
        assert len(numbered_items) >= 1, (
            "Exhaustive prompt must have at least one numbered scope item"
        )

    def test_skill_documents_anti_patterns(self):
        """SKILL.md must document the Anti-Patterns section."""
        skill_md = PROJECT_ROOT / "skills" / "exhaustive-prompt" / "SKILL.md"
        content = skill_md.read_text()
        assert "Anti-Pattern" in content or "DO NOT" in content


# ---------------------------------------------------------------------------
# 4. Error handling — degenerate inputs
# ---------------------------------------------------------------------------


class TestExhaustivePromptErrorHandling:
    def test_empty_scope_prompt_is_incomplete(self):
        """A prompt with empty scope list is missing the exhaustive enumeration."""
        prompt = build_sample_exhaustive_prompt(scope_items=[])
        total_match = re.search(r"Total:\s*(\d+)\s*items", prompt)
        if total_match:
            assert int(total_match.group(1)) == 0, (
                "Zero-scope prompt should declare Total: 0 items"
            )

    def test_verification_section_requires_expected_output(self):
        """Each verification command must state its Expected: value."""
        prompt = build_sample_exhaustive_prompt()
        verification_start = prompt.find("## VERIFICATION:")
        assert verification_start >= 0
        verification_section = prompt[verification_start:]
        assert "Expected:" in verification_section, (
            "VERIFICATION section must include Expected: for each command"
        )
