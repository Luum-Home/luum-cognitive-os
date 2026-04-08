"""
Tests for Phase 1 of prompt-driven governance: clarification-gate prompt hook.

Validates that:
1. The prompt template exists and has the required structure
2. The template contains all scoring signals from the bash version
3. The template specifies JSON output format
4. The settings.json retains the bash version (parallel run period)
5. The enablement instructions document how to add the prompt hook
"""

import json
import os
import re

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestClarificationGatePromptTemplate:
    """Tests for the prompt hook template file."""

    TEMPLATE_PATH = os.path.join(
        PROJECT_ROOT, "templates", "prompt-hooks", "clarification-gate-prompt.md"
    )

    def test_template_file_exists(self):
        """The clarification gate prompt template must exist."""
        assert os.path.isfile(self.TEMPLATE_PATH), (
            f"Template not found at {self.TEMPLATE_PATH}. "
            "Phase 1 requires templates/prompt-hooks/clarification-gate-prompt.md"
        )

    def test_template_is_not_empty(self):
        """Template must contain substantial content."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()
        assert len(content) > 200, "Template is too short to contain meaningful scoring criteria"

    def test_template_has_scoring_signals(self):
        """Template must include all 7 scoring signals from the bash version."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read().lower()

        signals = [
            ("file paths", "no file paths"),
            ("scope", "unbounded scope"),
            ("technology", "technology"),
            ("action", "action"),
            ("questions", "question"),
            ("short", "short"),
            ("acceptance criteria", "acceptance criteria"),
        ]

        for name, keyword in signals:
            assert keyword in content, (
                f"Template missing scoring signal for '{name}'. "
                f"Expected keyword '{keyword}' in template content."
            )

    def test_template_has_point_values(self):
        """Template must specify point values for each signal."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        # Check for the specific point values matching the bash version
        expected_points = ["+15", "+20", "+10"]
        for points in expected_points:
            assert points in content, (
                f"Template missing point value '{points}'. "
                "Point values must match the bash hook for scoring parity."
            )

    def test_template_specifies_json_output(self):
        """Template must instruct the model to return JSON."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert "JSON" in content or "json" in content, (
            "Template must instruct the model to return JSON output"
        )

        # Check for the required JSON fields
        for field in ["score", "verdict", "questions"]:
            assert field in content, f"Template must specify '{field}' in the JSON output format"

    def test_template_has_verdict_thresholds(self):
        """Template must define PASS/WARN/BLOCK thresholds matching the bash version."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert "PASS" in content, "Template must define PASS verdict"
        assert "WARN" in content, "Template must define WARN verdict"
        assert "BLOCK" in content, "Template must define BLOCK verdict"

        # Verify threshold values match bash: 0-29=PASS, 30-60=WARN, 61-100=BLOCK
        assert "0-29" in content or "29" in content, (
            "Template must specify PASS threshold (0-29)"
        )
        assert "30-60" in content or "30" in content, (
            "Template must specify WARN threshold (30-60)"
        )
        assert "61-100" in content or "61" in content, (
            "Template must specify BLOCK threshold (61-100)"
        )

    def test_template_has_examples(self):
        """Template must include calibration examples per the design doc."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        # Design doc requires 2-3 examples
        example_count = content.lower().count("input:")
        assert example_count >= 2, (
            f"Template has {example_count} examples, minimum 2 required for calibration. "
            "The design doc specifies '2-3 examples' for each template."
        )

    def test_template_has_prompt_placeholder(self):
        """Template must include a placeholder for the agent prompt to evaluate."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert "{{prompt}}" in content or "{{agent_prompt}}" in content, (
            "Template must include a placeholder ({{prompt}} or {{agent_prompt}}) "
            "for the agent prompt to be evaluated."
        )

    def test_template_token_budget(self):
        """Template should fit within 500 tokens (~2000 chars) per design doc."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        # Rough estimate: 1 token ~ 4 chars. 500 tokens ~ 2000 chars.
        # Allow some margin (the design says 500 tokens for the template itself,
        # plus ~300 tokens for the agent prompt excerpt = ~800 total input).
        # We check the template alone stays reasonable.
        char_count = len(content)
        estimated_tokens = char_count / 4
        assert estimated_tokens < 800, (
            f"Template is ~{estimated_tokens:.0f} tokens ({char_count} chars). "
            "Design doc recommends templates fit within 500 tokens. "
            "Consider trimming for cost efficiency."
        )


class TestBashHookPreserved:
    """Tests that the bash clarification-gate is preserved for parallel run period."""

    BASH_HOOK_PATH = os.path.join(PROJECT_ROOT, "hooks", "clarification-gate.sh")
    SETTINGS_PATH = os.path.join(PROJECT_ROOT, ".claude", "settings.json")

    def test_bash_hook_still_exists(self):
        """The bash clarification-gate.sh must remain during parallel run period."""
        assert os.path.isfile(self.BASH_HOOK_PATH), (
            "hooks/clarification-gate.sh must be preserved during the parallel run period. "
            "Do not remove until prompt hook accuracy is validated."
        )

    def test_settings_has_bash_clarification_gate(self):
        """settings.json must still reference the bash clarification-gate hook."""
        with open(self.SETTINGS_PATH) as f:
            settings = json.load(f)

        pre_tool_use = settings.get("hooks", {}).get("PreToolUse", [])

        found_bash_gate = False
        for group in pre_tool_use:
            if "Agent" in group.get("matcher", ""):
                for hook in group.get("hooks", []):
                    if hook.get("type") == "command" and "clarification-gate" in hook.get(
                        "command", ""
                    ):
                        found_bash_gate = True
                        break

        assert found_bash_gate, (
            "settings.json must retain the bash clarification-gate.sh hook "
            "during the parallel run period."
        )


class TestEnablementDocumentation:
    """Tests that the enablement path is documented for the prompt hook."""

    TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "templates", "prompt-hooks")

    def test_prompt_hooks_directory_exists(self):
        """The templates/prompt-hooks/ directory must exist."""
        assert os.path.isdir(self.TEMPLATE_DIR), (
            "templates/prompt-hooks/ directory must exist for prompt hook templates"
        )

    def test_design_doc_exists(self):
        """The prompt-driven governance design doc must exist."""
        design_doc = os.path.join(PROJECT_ROOT, "docs", "prompt-driven-governance.md")
        assert os.path.isfile(design_doc), (
            "docs/prompt-driven-governance.md must exist with the implementation plan"
        )


class TestTemplateCompatibility:
    """Tests that the prompt template is compatible with the bash hook's behavior."""

    TEMPLATE_PATH = os.path.join(
        PROJECT_ROOT, "templates", "prompt-hooks", "clarification-gate-prompt.md"
    )

    def test_template_handles_vague_prompt(self):
        """Template examples should show BLOCK for vague prompts."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        # The template should have an example where a vague prompt gets BLOCK
        assert '"BLOCK"' in content, (
            "Template must include at least one example with BLOCK verdict "
            "to calibrate the model on what constitutes an ambiguous prompt."
        )

    def test_template_handles_clear_prompt(self):
        """Template examples should show PASS for clear prompts."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert '"PASS"' in content, (
            "Template must include at least one example with PASS verdict "
            "to calibrate the model on what constitutes a clear prompt."
        )

    def test_template_scoring_range(self):
        """Template must specify the 0-100 scoring range."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert "0-100" in content, "Template must specify the 0-100 scoring range"


class TestAssumptionTrackerPromptTemplate:
    """Tests for the assumption-tracker prompt hook template."""

    TEMPLATE_PATH = os.path.join(
        PROJECT_ROOT, "templates", "prompt-hooks", "assumption-tracker-prompt.md"
    )

    def test_template_file_exists(self):
        """The assumption tracker prompt template must exist."""
        assert os.path.isfile(self.TEMPLATE_PATH), (
            f"Template not found at {self.TEMPLATE_PATH}. "
            "Expected templates/prompt-hooks/assumption-tracker-prompt.md"
        )

    def test_template_is_not_empty(self):
        """Template must contain substantial content."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()
        assert len(content) > 200, "Template is too short to contain meaningful detection criteria"

    def test_template_specifies_json_output(self):
        """Template must instruct the model to return JSON."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert "JSON" in content or "json" in content, (
            "Template must instruct the model to return JSON output"
        )
        for field in ["assumption_count", "assumptions", "severity"]:
            assert field in content, f"Template must specify '{field}' in the JSON output format"

    def test_template_has_high_confidence_patterns(self):
        """Template must list HIGH confidence assumption patterns."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read().lower()

        high_patterns = ["i assume", "i'm assuming", "presumably", "without more info"]
        for pattern in high_patterns:
            assert pattern in content, (
                f"Template missing HIGH confidence pattern '{pattern}'"
            )

    def test_template_has_medium_confidence_patterns(self):
        """Template must list MEDIUM confidence assumption patterns."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read().lower()

        medium_patterns = ["i think", "probably", "likely", "it seems", "appears to be"]
        for pattern in medium_patterns:
            assert pattern in content, (
                f"Template missing MEDIUM confidence pattern '{pattern}'"
            )

    def test_template_has_severity_thresholds(self):
        """Template must define ok/warn severity thresholds."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert '"ok"' in content or "'ok'" in content, "Template must define 'ok' severity"
        assert '"warn"' in content or "'warn'" in content, "Template must define 'warn' severity"

    def test_template_has_examples(self):
        """Template must include calibration examples."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        example_count = content.lower().count("input:")
        assert example_count >= 2, (
            f"Template has {example_count} examples, minimum 2 required for calibration."
        )

    def test_template_has_output_placeholder(self):
        """Template must include a placeholder for the agent output to scan."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert "{{agent_output}}" in content, (
            "Template must include {{agent_output}} placeholder for the agent response to scan."
        )

    def test_template_threshold_at_3(self):
        """Template must specify the 3+ assumption threshold for warn severity."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert "3" in content, (
            "Template must specify the threshold of 3+ assumptions for warn severity"
        )


class TestPromptQualityPromptTemplate:
    """Tests for the prompt-quality prompt hook template."""

    TEMPLATE_PATH = os.path.join(
        PROJECT_ROOT, "templates", "prompt-hooks", "prompt-quality-prompt.md"
    )

    def test_template_file_exists(self):
        """The prompt quality prompt template must exist."""
        assert os.path.isfile(self.TEMPLATE_PATH), (
            f"Template not found at {self.TEMPLATE_PATH}. "
            "Expected templates/prompt-hooks/prompt-quality-prompt.md"
        )

    def test_template_is_not_empty(self):
        """Template must contain substantial content."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()
        assert len(content) > 200, "Template is too short to contain meaningful scoring criteria"

    def test_template_specifies_json_output(self):
        """Template must instruct the model to return JSON."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert "JSON" in content or "json" in content, (
            "Template must instruct the model to return JSON output"
        )
        for field in ["score", "specificity", "actionability", "context", "measurability", "scope_clarity", "level", "suggestions"]:
            assert field in content, f"Template must specify '{field}' in the JSON output format"

    def test_template_has_five_dimensions(self):
        """Template must score on all 5 quality dimensions."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read().lower()

        dimensions = ["specificity", "actionability", "context", "measurability", "scope clarity"]
        for dim in dimensions:
            assert dim in content, f"Template missing quality dimension '{dim}'"

    def test_template_has_dimension_ranges(self):
        """Template must specify 0-20 range for each dimension."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert "0-20" in content, "Template must specify 0-20 range for each dimension"
        assert "0-100" in content, "Template must specify 0-100 total scoring range"

    def test_template_has_quality_levels(self):
        """Template must define warning/info/good quality levels."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert '"warning"' in content or "'warning'" in content, "Template must define 'warning' level"
        assert '"info"' in content or "'info'" in content, "Template must define 'info' level"
        assert '"good"' in content or "'good'" in content, "Template must define 'good' level"

    def test_template_has_level_thresholds(self):
        """Template must define threshold values for quality levels."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        # < 30 = warning, 30-60 = info, > 60 = good
        assert "30" in content, "Template must specify threshold value 30"
        assert "60" in content, "Template must specify threshold value 60"

    def test_template_has_examples(self):
        """Template must include calibration examples."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        example_count = content.lower().count("input:")
        assert example_count >= 2, (
            f"Template has {example_count} examples, minimum 2 required for calibration."
        )

    def test_template_has_prompt_placeholder(self):
        """Template must include a placeholder for the agent prompt to evaluate."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert "{{prompt}}" in content, (
            "Template must include {{prompt}} placeholder for the agent prompt to evaluate."
        )


class TestScopeCreepPromptTemplate:
    """Tests for the scope-creep-detector prompt hook template."""

    TEMPLATE_PATH = os.path.join(
        PROJECT_ROOT, "templates", "prompt-hooks", "scope-creep-prompt.md"
    )

    def test_template_file_exists(self):
        """The scope creep prompt template must exist."""
        assert os.path.isfile(self.TEMPLATE_PATH), (
            f"Template not found at {self.TEMPLATE_PATH}. "
            "Expected templates/prompt-hooks/scope-creep-prompt.md"
        )

    def test_template_is_not_empty(self):
        """Template must contain substantial content."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()
        assert len(content) > 200, "Template is too short to contain meaningful detection criteria"

    def test_template_specifies_json_output(self):
        """Template must instruct the model to return JSON."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert "JSON" in content or "json" in content, (
            "Template must instruct the model to return JSON output"
        )
        for field in ["in_scope", "match_type", "matched_path", "file_path"]:
            assert field in content, f"Template must specify '{field}' in the JSON output format"

    def test_template_has_matching_rules(self):
        """Template must define exact, prefix, and substring matching rules."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read().lower()

        for rule in ["exact", "prefix", "substring"]:
            assert rule in content, f"Template missing matching rule '{rule}'"

    def test_template_has_scope_placeholders(self):
        """Template must include placeholders for scope data injection."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert "{{approved_paths}}" in content, (
            "Template must include {{approved_paths}} placeholder"
        )
        assert "{{file_path}}" in content, (
            "Template must include {{file_path}} placeholder"
        )

    def test_template_has_examples(self):
        """Template must include calibration examples."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        # Count examples by looking for "Approved paths:" markers
        example_count = content.count("Approved paths:")
        assert example_count >= 2, (
            f"Template has {example_count} examples, minimum 2 required for calibration."
        )

    def test_template_has_boolean_in_scope(self):
        """Template must return boolean in_scope field."""
        with open(self.TEMPLATE_PATH) as f:
            content = f.read()

        assert "true" in content and "false" in content, (
            "Template must show both true and false values for in_scope field"
        )
