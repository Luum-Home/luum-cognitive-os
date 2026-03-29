"""Behavior tests for the repo-forensics skill.

Validates:
- SKILL.md exists with correct frontmatter (audience: both)
- References the analysis pipeline steps
- CATALOG.md has an entry for repo-forensics
- lib/repo_analyzer.py exists and is importable

Related: skills/repo-forensics/SKILL.md, lib/repo_analyzer.py, skills/CATALOG.md
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestRepoForensicsSkillExists:
    """Verify the skill definition is present and well-formed."""

    def test_skill_md_exists(self):
        skill_path = PROJECT_ROOT / "skills" / "repo-forensics" / "SKILL.md"
        assert skill_path.exists(), "skills/repo-forensics/SKILL.md must exist"

    def test_skill_has_audience_both(self):
        skill_path = PROJECT_ROOT / "skills" / "repo-forensics" / "SKILL.md"
        content = skill_path.read_text()
        assert "audience: both" in content, "repo-forensics must have audience: both"

    def test_skill_has_name_in_frontmatter(self):
        skill_path = PROJECT_ROOT / "skills" / "repo-forensics" / "SKILL.md"
        content = skill_path.read_text()
        assert "name: repo-forensics" in content

    def test_skill_has_version(self):
        skill_path = PROJECT_ROOT / "skills" / "repo-forensics" / "SKILL.md"
        content = skill_path.read_text()
        assert re.search(r"version:\s*\d+\.\d+\.\d+", content), "Must have semver version"

    def test_skill_references_analysis_pipeline(self):
        skill_path = PROJECT_ROOT / "skills" / "repo-forensics" / "SKILL.md"
        content = skill_path.read_text()
        pipeline_steps = [
            "Clone",
            "dependencies",
            "features",
            "architecture",
            "tools",
            "endpoints",
            "Engram",
            "Cleanup",
        ]
        for step in pipeline_steps:
            assert step.lower() in content.lower(), f"Skill must reference pipeline step: {step}"

    def test_skill_references_repo_analyzer(self):
        skill_path = PROJECT_ROOT / "skills" / "repo-forensics" / "SKILL.md"
        content = skill_path.read_text()
        assert "repo_analyzer" in content or "RepoAnalyzer" in content, \
            "Skill must reference lib/repo_analyzer.py"

    def test_skill_has_invocation_section(self):
        skill_path = PROJECT_ROOT / "skills" / "repo-forensics" / "SKILL.md"
        content = skill_path.read_text()
        assert "/repo-forensics" in content, "Must document invocation command"

    def test_skill_documents_compare_flag(self):
        skill_path = PROJECT_ROOT / "skills" / "repo-forensics" / "SKILL.md"
        content = skill_path.read_text()
        assert "--compare" in content, "Must document --compare flag"

    def test_skill_documents_deps_only_flag(self):
        skill_path = PROJECT_ROOT / "skills" / "repo-forensics" / "SKILL.md"
        content = skill_path.read_text()
        assert "--deps-only" in content, "Must document --deps-only flag"

    def test_skill_documents_features_only_flag(self):
        skill_path = PROJECT_ROOT / "skills" / "repo-forensics" / "SKILL.md"
        content = skill_path.read_text()
        assert "--features-only" in content, "Must document --features-only flag"


class TestRepoForensicsCatalogEntry:
    """Verify CATALOG.md includes the repo-forensics skill."""

    def test_catalog_has_repo_forensics_entry(self):
        catalog_path = PROJECT_ROOT / "skills" / "CATALOG.md"
        assert catalog_path.exists(), "skills/CATALOG.md must exist"
        content = catalog_path.read_text()
        assert "repo-forensics" in content, "CATALOG.md must list repo-forensics skill"

    def test_catalog_entry_has_correct_invoke(self):
        catalog_path = PROJECT_ROOT / "skills" / "CATALOG.md"
        content = catalog_path.read_text()
        assert "/repo-forensics" in content, "CATALOG.md must show /repo-forensics invocation"

    def test_catalog_entry_audience_is_both(self):
        catalog_path = PROJECT_ROOT / "skills" / "CATALOG.md"
        content = catalog_path.read_text()
        # Find the line with repo-forensics and verify it includes "both"
        for line in content.splitlines():
            if "repo-forensics" in line and "|" in line:
                assert "both" in line, "CATALOG.md repo-forensics entry must have audience: both"
                break
        else:
            pytest.fail("repo-forensics not found as a table row in CATALOG.md")


class TestRepoAnalyzerLibExists:
    """Verify the library module exists and is importable."""

    def test_repo_analyzer_py_exists(self):
        lib_path = PROJECT_ROOT / "lib" / "repo_analyzer.py"
        assert lib_path.exists(), "lib/repo_analyzer.py must exist"

    def test_repo_analyzer_importable(self):
        """Verify we can import the module."""
        from lib.repo_analyzer import RepoAnalyzer, RepoAnalysis
        assert RepoAnalyzer is not None
        assert RepoAnalysis is not None

    def test_repo_analyzer_has_required_methods(self):
        from lib.repo_analyzer import RepoAnalyzer
        analyzer = RepoAnalyzer.__new__(RepoAnalyzer)
        required_methods = [
            "analyze",
            "detect_dependencies",
            "detect_features",
            "detect_tools",
            "detect_architecture",
            "compare_with_cos",
            "format_report",
            "cleanup",
        ]
        for method in required_methods:
            assert hasattr(analyzer, method), f"RepoAnalyzer must have method: {method}"

    def test_repo_analysis_has_required_fields(self):
        from lib.repo_analyzer import RepoAnalysis
        analysis = RepoAnalysis()
        required_fields = [
            "name", "url", "license", "language_breakdown", "total_files",
            "total_lines", "dependencies", "features", "architecture_patterns",
            "tools_integrated", "api_endpoints", "config_files", "test_coverage",
            "ci_cd", "docker_services", "security_tools", "plugin_system",
        ]
        for f in required_fields:
            assert hasattr(analysis, f), f"RepoAnalysis must have field: {f}"
