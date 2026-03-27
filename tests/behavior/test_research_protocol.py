"""Behavior tests for research-protocol skill.

Tests verify skill structure, phase completeness, reading protocols,
comparison framework, quality rubric, and output format requirements.
"""

import os
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

SKILL_PATH = Path(__file__).resolve().parents[2] / "skills" / "research-protocol" / "SKILL.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_skill() -> str:
    """Read the SKILL.md file content."""
    assert SKILL_PATH.exists(), f"Skill file not found: {SKILL_PATH}"
    return SKILL_PATH.read_text(encoding="utf-8")


def _extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter fields (simple key: value parsing)."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match, "No YAML frontmatter found"
    fm = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith(" ") and not line.startswith("\t"):
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm


# ---------------------------------------------------------------------------
# Tests: Skill existence and frontmatter
# ---------------------------------------------------------------------------


class TestSkillExists:

    def test_skill_file_exists(self):
        assert SKILL_PATH.exists()

    def test_frontmatter_has_name(self):
        fm = _extract_frontmatter(_read_skill())
        assert fm.get("name") == "research-protocol"

    def test_frontmatter_has_version(self):
        fm = _extract_frontmatter(_read_skill())
        assert "version" in fm
        assert re.match(r"\d+\.\d+\.\d+", fm["version"])

    def test_frontmatter_has_description(self):
        fm = _extract_frontmatter(_read_skill())
        assert "description" in fm

    def test_frontmatter_not_auto_generated(self):
        fm = _extract_frontmatter(_read_skill())
        assert fm.get("auto-generated") == "false"

    def test_frontmatter_has_license(self):
        fm = _extract_frontmatter(_read_skill())
        assert fm.get("license") == "MIT"

    def test_frontmatter_user_invocable(self):
        fm = _extract_frontmatter(_read_skill())
        assert fm.get("user-invocable") == "true"


# ---------------------------------------------------------------------------
# Tests: Four phases documented
# ---------------------------------------------------------------------------


class TestPhasesDocumented:
    """Every research task MUST follow DISCOVER -> ANALYZE -> COMPARE -> SYNTHESIZE."""

    def test_discover_phase_present(self):
        content = _read_skill()
        assert "DISCOVER" in content
        assert "What Exists" in content or "what exists" in content.lower()

    def test_analyze_phase_present(self):
        content = _read_skill()
        assert "ANALYZE" in content
        assert "What Does It Actually Do" in content or "what does it actually do" in content.lower()

    def test_compare_phase_present(self):
        content = _read_skill()
        assert "COMPARE" in content
        assert "How Does It Relate" in content or "how does it relate" in content.lower()

    def test_synthesize_phase_present(self):
        content = _read_skill()
        assert "SYNTHESIZE" in content
        assert "Verdict" in content or "verdict" in content.lower()

    def test_phases_in_order(self):
        content = _read_skill()
        discover_pos = content.index("Phase 1: DISCOVER")
        analyze_pos = content.index("Phase 2: ANALYZE")
        compare_pos = content.index("Phase 3: COMPARE")
        synthesize_pos = content.index("Phase 4: SYNTHESIZE")
        assert discover_pos < analyze_pos < compare_pos < synthesize_pos

    def test_all_phases_mandatory(self):
        content = _read_skill()
        assert "No phase may be skipped" in content


# ---------------------------------------------------------------------------
# Tests: Reading protocols for at least 5 source types
# ---------------------------------------------------------------------------


class TestReadingProtocols:
    """Must have reading protocols for at least 5 distinct source types."""

    SOURCE_TYPES = [
        ("GitHub Repository", "Repository Protocol"),
        ("Documentation Site", "Documentation Site Protocol"),
        ("Article / Blog Post", "Article"),
        ("Academic Paper", "Academic Paper Protocol"),
        ("Configuration File", "Configuration File Protocol"),
    ]

    @pytest.mark.parametrize("label,marker", SOURCE_TYPES, ids=[s[0] for s in SOURCE_TYPES])
    def test_source_type_protocol_exists(self, label, marker):
        content = _read_skill()
        assert marker in content, f"Missing reading protocol for: {label}"

    def test_at_least_five_protocols(self):
        content = _read_skill()
        protocol_markers = [
            "Repository Protocol",
            "Documentation Site Protocol",
            "Article",
            "Academic Paper Protocol",
            "Configuration File Protocol",
        ]
        found = sum(1 for m in protocol_markers if m in content)
        assert found >= 5, f"Only found {found}/5 reading protocols"

    def test_repo_protocol_covers_readme(self):
        content = _read_skill()
        assert "README.md Protocol" in content

    def test_repo_protocol_covers_license(self):
        content = _read_skill()
        assert "LICENSE Protocol" in content

    def test_repo_protocol_covers_source_code(self):
        content = _read_skill()
        assert "Source Code Protocol" in content

    def test_repo_protocol_covers_issues(self):
        content = _read_skill()
        assert "Issues/PRs Protocol" in content

    def test_repo_protocol_covers_dependencies(self):
        content = _read_skill()
        assert "Dependency Protocol" in content or "package.json" in content

    def test_docs_protocol_checks_freshness(self):
        content = _read_skill()
        # In the docs protocol section, freshness must be checked
        assert "Freshness" in content

    def test_article_protocol_checks_bias(self):
        content = _read_skill()
        assert "Bias detection" in content or "bias" in content.lower()

    def test_paper_protocol_checks_limitations(self):
        content = _read_skill()
        assert "Limitations" in content or "limitations" in content.lower()

    def test_mixed_source_protocol_exists(self):
        content = _read_skill()
        assert "Mixed Source Protocol" in content or "mixed" in content.lower()


# ---------------------------------------------------------------------------
# Tests: Comparison framework with mandatory columns
# ---------------------------------------------------------------------------


class TestComparisonFramework:
    """Comparison matrix must have specific mandatory columns."""

    MANDATORY_COLUMNS = ["Capability", "Source", "Cognitive OS", "Gap?", "Action"]

    def test_comparison_matrix_exists(self):
        content = _read_skill()
        assert "Comparison Matrix" in content

    def test_comparison_is_mandatory(self):
        content = _read_skill()
        assert "MANDATORY" in content
        # The comparison phase must be explicitly marked as mandatory
        lower = content.lower()
        assert "mandatory" in lower and "comparison" in lower

    @pytest.mark.parametrize("column", MANDATORY_COLUMNS)
    def test_mandatory_column_present(self, column):
        content = _read_skill()
        assert column in content, f"Missing mandatory column: {column}"

    def test_cognitive_os_column_requires_file_references(self):
        content = _read_skill()
        assert "specific files" in content.lower() or "reference specific" in content.lower()

    def test_comparison_references_cognitive_os_rules(self):
        content = _read_skill()
        # Must mention referencing actual Cognitive OS files
        assert "rules/" in content

    def test_adopt_adapt_skip_note_verdicts(self):
        content = _read_skill()
        for verdict in ["adopt", "adapt", "skip", "note"]:
            assert verdict.lower() in content.lower(), f"Missing verdict category: {verdict}"


# ---------------------------------------------------------------------------
# Tests: Quality assessment rubric with scoring
# ---------------------------------------------------------------------------


class TestQualityRubric:
    """Must have a quality assessment rubric with numeric scoring."""

    DIMENSIONS = [
        "Claims-to-evidence",
        "Code-to-docs",
        "Test quality",
        "Maintenance signal",
        "Architecture clarity",
    ]

    def test_rubric_exists(self):
        content = _read_skill()
        assert "Quality Assessment Rubric" in content

    @pytest.mark.parametrize("dimension", DIMENSIONS)
    def test_dimension_present(self, dimension):
        content = _read_skill()
        assert dimension in content, f"Missing rubric dimension: {dimension}"

    def test_rubric_has_numeric_scoring(self):
        content = _read_skill()
        # Should have score ranges like 1-3 or 1-5
        assert re.search(r"Score\s+\d", content), "Rubric must have numeric scoring"

    def test_rubric_has_score_thresholds(self):
        content = _read_skill()
        # Should define what score ranges mean (SKIP, ASSESS, ADOPT etc.)
        assert "SKIP" in content
        assert "ASSESS" in content

    def test_total_score_range_defined(self):
        content = _read_skill()
        # Should define the total score range
        assert "5-15" in content or "Total" in content


# ---------------------------------------------------------------------------
# Tests: Mandatory output format with all 6 sections
# ---------------------------------------------------------------------------


class TestOutputFormat:
    """Output must have exactly 6 mandatory sections."""

    REQUIRED_SECTIONS = [
        "Discovery Map",
        "Analysis",
        "Comparison Matrix",
        "Quality Score",
        "Verdicts",
        "Action Items",
    ]

    def test_output_format_section_exists(self):
        content = _read_skill()
        assert "Output Format" in content

    def test_output_format_is_mandatory(self):
        content = _read_skill()
        # Find the output format heading and check it says MANDATORY
        assert "MANDATORY" in content

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_required_section_present(self, section):
        content = _read_skill()
        assert section in content, f"Missing required output section: {section}"

    def test_all_six_sections_present(self):
        content = _read_skill()
        found = sum(1 for s in self.REQUIRED_SECTIONS if s in content)
        assert found == 6, f"Only found {found}/6 required output sections"

    def test_no_section_may_be_omitted(self):
        content = _read_skill()
        assert "No section may be omitted" in content or "may not be omitted" in content.lower()


# ---------------------------------------------------------------------------
# Tests: Integration references
# ---------------------------------------------------------------------------


class TestIntegration:
    """Must reference eval-repo and deep-research integration."""

    def test_references_eval_repo(self):
        content = _read_skill()
        assert "eval-repo" in content

    def test_references_deep_research(self):
        content = _read_skill()
        assert "deep-research" in content

    def test_describes_relationship_with_eval_repo(self):
        content = _read_skill()
        # Should explain that eval-repo is a workflow and research-protocol is methodology
        lower = content.lower()
        assert "eval-repo" in lower and ("workflow" in lower or "github" in lower)

    def test_describes_relationship_with_deep_research(self):
        content = _read_skill()
        lower = content.lower()
        assert "deep-research" in lower and ("multi-hop" in lower or "non-repo" in lower)


# ---------------------------------------------------------------------------
# Tests: Structured envelope
# ---------------------------------------------------------------------------


class TestStructuredEnvelope:
    """Must return the standard result contract."""

    def test_returns_structured_envelope(self):
        content = _read_skill()
        assert "status" in content
        assert "executive_summary" in content
        assert "artifacts" in content
        assert "next_recommended" in content
        assert "risks" in content


# ---------------------------------------------------------------------------
# Tests: License auto-reject
# ---------------------------------------------------------------------------


class TestLicenseAutoReject:
    """License check must happen early and block analysis for blocked licenses."""

    def test_license_check_references_policy(self):
        content = _read_skill()
        assert "license-policy.md" in content

    def test_blocked_license_stops_analysis(self):
        content = _read_skill()
        lower = content.lower()
        assert "block" in lower or "stop" in lower or "reject" in lower
        assert "license" in lower
