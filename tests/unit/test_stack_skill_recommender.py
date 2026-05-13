"""Unit tests for lib/stack_skill_recommender.py

Validates stack detection from project files, skill recommendation mapping,
combo detection, formatting output, and edge cases.

Author: luum
"""

import json
from pathlib import Path

import pytest

from lib.stack_skill_recommender import (
    StackSkillRecommender,
)

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(tmp_path: Path, files: dict) -> str:
    """Create a temporary project directory with the given files.

    files is a dict of {relative_path: content_string}.
    Directories are created automatically.
    """
    for rel_path, content in files.items():
        fpath = tmp_path / rel_path
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding="utf-8")
    return str(tmp_path)


# ---------------------------------------------------------------------------
# detect_stack tests
# ---------------------------------------------------------------------------


class TestDetectStack:
    """Test technology detection from project files."""

    def test_detect_go_from_go_mod(self, tmp_path):
        project = _make_project(tmp_path, {
            "go.mod": "module example.com/myapp\n\ngo 1.22\n",
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "go" in detected

    def test_detect_typescript_from_tsconfig(self, tmp_path):
        project = _make_project(tmp_path, {
            "tsconfig.json": '{"compilerOptions": {"target": "es2020"}}',
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "typescript" in detected

    def test_detect_python_from_pyproject(self, tmp_path):
        project = _make_project(tmp_path, {
            "pyproject.toml": '[project]\nname = "myapp"\n',
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "python" in detected

    def test_detect_python_from_requirements_txt(self, tmp_path):
        project = _make_project(tmp_path, {
            "requirements.txt": "flask==3.0\nrequests==2.31\n",
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "python" in detected
        assert "flask" in detected

    def test_detect_rust_from_cargo_toml(self, tmp_path):
        project = _make_project(tmp_path, {
            "Cargo.toml": '[package]\nname = "myapp"\nversion = "0.1.0"\n',
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "rust" in detected

    def test_detect_java_from_build_gradle(self, tmp_path):
        project = _make_project(tmp_path, {
            "build.gradle": "plugins { id 'java' }\n",
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "java" in detected

    def test_detect_react_from_package_json(self, tmp_path):
        pkg = {"dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"}}
        project = _make_project(tmp_path, {
            "package.json": json.dumps(pkg),
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "react" in detected

    def test_detect_nextjs_from_config(self, tmp_path):
        project = _make_project(tmp_path, {
            "next.config.js": "module.exports = {};\n",
            "package.json": json.dumps({"dependencies": {"next": "14.0.0"}}),
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "nextjs" in detected

    def test_detect_docker_from_dockerfile(self, tmp_path):
        project = _make_project(tmp_path, {
            "Dockerfile": "FROM golang:1.22\nCOPY . /app\n",
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "docker" in detected

    def test_detect_docker_from_compose(self, tmp_path):
        project = _make_project(tmp_path, {
            "docker-compose.yml": "version: '3'\nservices:\n  app:\n    build: .\n",
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "docker" in detected

    def test_detect_tailwind_from_config(self, tmp_path):
        project = _make_project(tmp_path, {
            "tailwind.config.js": "module.exports = { content: [] };\n",
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "tailwind" in detected

    def test_detect_fastapi_from_pyproject(self, tmp_path):
        project = _make_project(tmp_path, {
            "pyproject.toml": '[project]\nname = "api"\ndependencies = ["fastapi>=0.100"]\n',
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "python" in detected
        assert "fastapi" in detected

    def test_detect_nestjs_from_package_json(self, tmp_path):
        pkg = {"dependencies": {"@nestjs/core": "^10.0.0"}}
        project = _make_project(tmp_path, {
            "package.json": json.dumps(pkg),
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "nestjs" in detected

    def test_detect_vue_from_package_json(self, tmp_path):
        pkg = {"dependencies": {"vue": "^3.0.0"}}
        project = _make_project(tmp_path, {
            "package.json": json.dumps(pkg),
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "vue" in detected

    def test_detect_angular_from_package_json(self, tmp_path):
        pkg = {"dependencies": {"@angular/core": "^17.0.0"}}
        project = _make_project(tmp_path, {
            "package.json": json.dumps(pkg),
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "angular" in detected

    def test_detect_prisma_from_package_json(self, tmp_path):
        pkg = {"devDependencies": {"prisma": "^5.0.0"}}
        project = _make_project(tmp_path, {
            "package.json": json.dumps(pkg),
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "prisma" in detected

    def test_detect_terraform_from_main_tf(self, tmp_path):
        project = _make_project(tmp_path, {
            "main.tf": 'resource "aws_instance" "example" {}\n',
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "terraform" in detected

    def test_empty_project_returns_empty(self, tmp_path):
        project = str(tmp_path)
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert detected == set()

    def test_nonexistent_path_returns_empty(self):
        r = StackSkillRecommender()
        detected = r.detect_stack("/nonexistent/path/that/does/not/exist")
        assert detected == set()

    def test_multiple_technologies_detected(self, tmp_path):
        """A project can have multiple technologies."""
        pkg = {"dependencies": {"react": "^18.0.0", "next": "14.0.0"}}
        project = _make_project(tmp_path, {
            "package.json": json.dumps(pkg),
            "tsconfig.json": "{}",
            "tailwind.config.js": "module.exports = {};",
            "Dockerfile": "FROM node:20\n",
        })
        r = StackSkillRecommender()
        detected = r.detect_stack(project)
        assert "react" in detected
        assert "nextjs" in detected
        assert "typescript" in detected
        assert "tailwind" in detected
        assert "docker" in detected


# ---------------------------------------------------------------------------
# recommend / recommend_for_stack tests
# ---------------------------------------------------------------------------


class TestRecommend:
    """Test skill recommendation from detected stack."""

    def test_recommend_returns_skills_for_go(self, tmp_path):
        project = _make_project(tmp_path, {"go.mod": "module example.com/m\n\ngo 1.22\n"})
        r = StackSkillRecommender()
        recs = r.recommend(project)
        skill_names = [rec.skill_name for rec in recs]
        assert "go-testing" in skill_names

    def test_recommend_returns_skills_for_python(self, tmp_path):
        project = _make_project(tmp_path, {"pyproject.toml": '[project]\nname = "x"\n'})
        r = StackSkillRecommender()
        recs = r.recommend(project)
        skill_names = [rec.skill_name for rec in recs]
        assert "test-driven-development" in skill_names

    def test_recommend_returns_skills_for_typescript(self, tmp_path):
        project = _make_project(tmp_path, {"tsconfig.json": "{}"})
        r = StackSkillRecommender()
        recs = r.recommend(project)
        skill_names = [rec.skill_name for rec in recs]
        assert "typescript-patterns" in skill_names

    def test_empty_project_returns_empty_recommendations(self, tmp_path):
        r = StackSkillRecommender()
        recs = r.recommend(str(tmp_path))
        assert recs == []

    def test_recommendations_sorted_by_priority(self, tmp_path):
        """Recommended skills come before optional and suggested."""
        pkg = {"dependencies": {"react": "^18", "next": "14"}}
        project = _make_project(tmp_path, {
            "package.json": json.dumps(pkg),
            "tsconfig.json": "{}",
            "Dockerfile": "FROM node:20\n",
        })
        r = StackSkillRecommender()
        recs = r.recommend(project)
        priorities = [rec.priority for rec in recs]
        # All recommended items should appear before optional items
        recommended_indices = [i for i, p in enumerate(priorities) if p == "recommended"]
        optional_indices = [i for i, p in enumerate(priorities) if p == "optional"]
        suggested_indices = [i for i, p in enumerate(priorities) if p == "suggested"]

        if recommended_indices and optional_indices:
            assert max(recommended_indices) < min(optional_indices)
        if optional_indices and suggested_indices:
            assert max(optional_indices) < min(suggested_indices)

    def test_no_duplicate_skill_names(self, tmp_path):
        """Deduplication: each skill name appears at most once."""
        pkg = {"dependencies": {"react": "^18", "next": "14"}}
        project = _make_project(tmp_path, {
            "package.json": json.dumps(pkg),
            "tsconfig.json": "{}",
            "tailwind.config.js": "module.exports = {};",
        })
        r = StackSkillRecommender()
        recs = r.recommend(project)
        skill_names = [rec.skill_name for rec in recs]
        assert len(skill_names) == len(set(skill_names)), f"Duplicate skills found: {skill_names}"


# ---------------------------------------------------------------------------
# Combo detection tests
# ---------------------------------------------------------------------------


class TestComboDetection:
    """Test combo-based skill recommendations."""

    def test_react_typescript_combo(self, tmp_path):
        pkg = {"dependencies": {"react": "^18"}}
        project = _make_project(tmp_path, {
            "package.json": json.dumps(pkg),
            "tsconfig.json": "{}",
        })
        r = StackSkillRecommender()
        recs = r.recommend(project)
        skill_names = [rec.skill_name for rec in recs]
        assert "react-typescript" in skill_names

    def test_go_docker_combo(self, tmp_path):
        project = _make_project(tmp_path, {
            "go.mod": "module example.com/m\n\ngo 1.22\n",
            "Dockerfile": "FROM golang:1.22\n",
        })
        r = StackSkillRecommender()
        recs = r.recommend(project)
        skill_names = [rec.skill_name for rec in recs]
        assert "go-docker" in skill_names

    def test_nextjs_tailwind_combo(self, tmp_path):
        pkg = {"dependencies": {"next": "14"}}
        project = _make_project(tmp_path, {
            "package.json": json.dumps(pkg),
            "next.config.js": "module.exports = {};",
            "tailwind.config.js": "module.exports = {};",
        })
        r = StackSkillRecommender()
        recs = r.recommend(project)
        skill_names = [rec.skill_name for rec in recs]
        assert "nextjs-tailwind" in skill_names

    def test_python_fastapi_combo(self, tmp_path):
        project = _make_project(tmp_path, {
            "pyproject.toml": '[project]\nname = "api"\ndependencies = ["fastapi"]\n',
        })
        r = StackSkillRecommender()
        recs = r.recommend(project)
        skill_names = [rec.skill_name for rec in recs]
        assert "fastapi-full" in skill_names


# ---------------------------------------------------------------------------
# format_recommendations tests
# ---------------------------------------------------------------------------


class TestFormatRecommendations:
    """Test human-readable output formatting."""

    def test_format_produces_readable_output(self, tmp_path):
        project = _make_project(tmp_path, {
            "go.mod": "module example.com/m\n\ngo 1.22\n",
            "Dockerfile": "FROM golang:1.22\n",
        })
        r = StackSkillRecommender()
        recs = r.recommend(project)
        output = r.format_recommendations(recs)

        assert "Recommended skills" in output
        assert "go-testing" in output
        assert "[recommended]" in output

    def test_format_empty_recommendations(self):
        r = StackSkillRecommender()
        output = r.format_recommendations([])
        assert "No skill recommendations" in output

    def test_format_includes_install_commands(self, tmp_path):
        project = _make_project(tmp_path, {
            "Dockerfile": "FROM node:20\n",
        })
        r = StackSkillRecommender()
        recs = r.recommend(project)
        output = r.format_recommendations(recs)
        assert "Install external skills with:" in output or "Built-in skills" in output

    def test_format_shows_builtin_invocations(self, tmp_path):
        project = _make_project(tmp_path, {
            "go.mod": "module example.com/m\n\ngo 1.22\n",
        })
        r = StackSkillRecommender()
        recs = r.recommend(project)
        output = r.format_recommendations(recs)
        assert "Built-in skills" in output
        assert "/go-testing" in output


# ---------------------------------------------------------------------------
# Test on THIS project (luum-agent-os)
# ---------------------------------------------------------------------------


class TestOnLuumAgentOS:
    """Test detection on the actual luum-agent-os project.

    Note: luum-agent-os has go.mod in cmd/cos/ (not root), pyproject.toml at
    root, and docker-compose.cognitive-os.yml (non-standard name). The root-level
    detection finds Python (from pyproject.toml) and FastAPI (from deps).
    """

    def test_detects_python(self):
        r = StackSkillRecommender()
        detected = r.detect_stack(str(PROJECT_ROOT))
        assert "python" in detected, f"Expected 'python' in {detected}"

    def test_detects_go_in_cmd_cos_subdirectory(self):
        """go.mod lives in cmd/cos/, not at root. Detect from subdirectory."""
        r = StackSkillRecommender()
        cos_dir = PROJECT_ROOT / "cmd" / "cos"
        if cos_dir.is_dir():
            detected = r.detect_stack(str(cos_dir))
            assert "go" in detected, f"Expected 'go' in {detected}"

    def test_recommend_produces_results_for_this_project(self):
        r = StackSkillRecommender()
        recs = r.recommend(str(PROJECT_ROOT))
        assert len(recs) > 0, "Expected at least one recommendation for luum-agent-os"

        skill_names = [rec.skill_name for rec in recs]
        assert "test-driven-development" in skill_names, f"Expected TDD in {skill_names}"


# ---------------------------------------------------------------------------
# recommend_for_stack direct tests
# ---------------------------------------------------------------------------


class TestRecommendForStack:
    """Test recommend_for_stack with explicit technology sets."""

    def test_single_tech(self):
        r = StackSkillRecommender()
        recs = r.recommend_for_stack({"go"})
        assert len(recs) > 0
        assert recs[0].skill_name == "go-testing"

    def test_unknown_tech_returns_empty(self):
        r = StackSkillRecommender()
        recs = r.recommend_for_stack({"cobol"})
        assert recs == []

    def test_empty_set_returns_empty(self):
        r = StackSkillRecommender()
        recs = r.recommend_for_stack(set())
        assert recs == []

    def test_all_recommendations_have_required_fields(self):
        r = StackSkillRecommender()
        recs = r.recommend_for_stack({"go", "python", "docker", "typescript", "react"})
        for rec in recs:
            assert rec.skill_name, f"Missing skill_name: {rec}"
            assert rec.reason, f"Missing reason: {rec}"
            assert rec.source in ("cos-builtin", "skills.sh", "community"), f"Invalid source: {rec.source}"
            assert rec.install_command, f"Missing install_command: {rec}"
            assert rec.priority in ("recommended", "optional", "suggested"), f"Invalid priority: {rec.priority}"
