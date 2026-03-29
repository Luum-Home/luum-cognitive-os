"""Unit tests for lib/test_framework_detector.py

Validates auto-detection of test frameworks from project files.
Each test creates a temporary directory with specific config files
and verifies the detector returns the correct framework.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from lib.test_framework_detector import DetectedFramework, TestFrameworkDetector

pytestmark = pytest.mark.unit


@pytest.fixture
def detector():
    return TestFrameworkDetector()


@pytest.fixture
def tmp_project(tmp_path):
    """Return a temporary directory to use as a fake project root."""
    return tmp_path


# ---------------------------------------------------------------------------
# Individual framework detection
# ---------------------------------------------------------------------------


class TestDetectPytest:
    """Detect pytest from various config files."""

    def test_pytest_ini(self, detector, tmp_project):
        (tmp_project / "pytest.ini").write_text("[pytest]\naddopts = -v\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "pytest"
        assert result.config_file == "pytest.ini"
        assert result.confidence >= 0.90
        assert "pytest" in result.command

    def test_pyproject_toml_with_pytest(self, detector, tmp_project):
        (tmp_project / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\naddopts = '-v'\n"
        )
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "pytest"
        assert result.config_file == "pyproject.toml"

    def test_conftest_fallback(self, detector, tmp_project):
        (tmp_project / "conftest.py").write_text("# conftest\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "pytest"
        assert result.confidence < 0.90  # lower confidence for fallback

    def test_coverage_command(self, detector, tmp_project):
        (tmp_project / "pytest.ini").write_text("[pytest]\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.coverage_command is not None
        assert "--cov" in result.coverage_command


class TestDetectJest:
    """Detect jest from config files."""

    def test_jest_config_js(self, detector, tmp_project):
        (tmp_project / "jest.config.js").write_text("module.exports = {};\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "jest"
        assert result.config_file == "jest.config.js"
        assert result.confidence >= 0.90

    def test_jest_config_ts(self, detector, tmp_project):
        (tmp_project / "jest.config.ts").write_text("export default {};\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "jest"

    def test_jest_in_package_json(self, detector, tmp_project):
        pkg = {"jest": {"testEnvironment": "node"}, "scripts": {"test": "jest"}}
        (tmp_project / "package.json").write_text(json.dumps(pkg))
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "jest"
        assert result.config_file == "package.json"

    def test_watch_command(self, detector, tmp_project):
        (tmp_project / "jest.config.js").write_text("module.exports = {};\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.watch_command is not None
        assert "--watch" in result.watch_command


class TestDetectVitest:
    """Detect vitest from config files."""

    def test_vitest_config_ts(self, detector, tmp_project):
        (tmp_project / "vitest.config.ts").write_text("export default {};\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "vitest"
        assert result.config_file == "vitest.config.ts"
        assert result.confidence >= 0.90

    def test_vitest_config_js(self, detector, tmp_project):
        (tmp_project / "vitest.config.js").write_text("export default {};\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "vitest"


class TestDetectGo:
    """Detect go test from go.mod."""

    def test_go_mod(self, detector, tmp_project):
        (tmp_project / "go.mod").write_text("module example.com/app\n\ngo 1.22\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "go"
        assert result.config_file == "go.mod"
        assert "go test" in result.command
        assert result.confidence >= 0.85

    def test_go_coverage_command(self, detector, tmp_project):
        (tmp_project / "go.mod").write_text("module example.com/app\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.coverage_command is not None
        assert "coverprofile" in result.coverage_command


class TestDetectCargo:
    """Detect cargo test from Cargo.toml."""

    def test_cargo_toml(self, detector, tmp_project):
        (tmp_project / "Cargo.toml").write_text(
            '[package]\nname = "myapp"\nversion = "0.1.0"\n'
        )
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "cargo"
        assert result.config_file == "Cargo.toml"
        assert "cargo test" in result.command
        assert result.confidence >= 0.85


class TestDetectGradle:
    """Detect gradle test from build files."""

    def test_build_gradle(self, detector, tmp_project):
        (tmp_project / "build.gradle").write_text("apply plugin: 'java'\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "gradle"
        assert result.config_file == "build.gradle"

    def test_build_gradle_kts(self, detector, tmp_project):
        (tmp_project / "build.gradle.kts").write_text("plugins { java }\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "gradle"

    def test_gradlew_preferred(self, detector, tmp_project):
        (tmp_project / "build.gradle").write_text("apply plugin: 'java'\n")
        (tmp_project / "gradlew").write_text("#!/bin/sh\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert "./gradlew" in result.command


class TestDetectMaven:
    """Detect maven test from pom.xml."""

    def test_pom_xml(self, detector, tmp_project):
        (tmp_project / "pom.xml").write_text("<project></project>\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "maven"
        assert result.config_file == "pom.xml"


class TestDetectNpmTest:
    """Detect npm/yarn/bun test from package.json."""

    def test_npm_test_script(self, detector, tmp_project):
        pkg = {"scripts": {"test": "node --test"}}
        (tmp_project / "package.json").write_text(json.dumps(pkg))
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "npm"
        assert result.config_file == "package.json"

    def test_yarn_detected_from_lockfile(self, detector, tmp_project):
        pkg = {"scripts": {"test": "node --test"}}
        (tmp_project / "package.json").write_text(json.dumps(pkg))
        (tmp_project / "yarn.lock").write_text("")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "yarn"
        assert "yarn test" in result.command

    def test_bun_detected_from_lockfile(self, detector, tmp_project):
        pkg = {"scripts": {"test": "node --test"}}
        (tmp_project / "package.json").write_text(json.dumps(pkg))
        (tmp_project / "bun.lockb").write_text("")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "bun"

    def test_no_test_script_no_detect(self, detector, tmp_project):
        pkg = {"scripts": {"start": "node index.js"}}
        (tmp_project / "package.json").write_text(json.dumps(pkg))
        # No other framework files
        result = detector.detect_primary(str(tmp_project))
        assert result is None

    def test_jest_preferred_over_npm(self, detector, tmp_project):
        """When jest.config.js exists alongside package.json test script,
        jest is preferred (higher confidence)."""
        pkg = {"scripts": {"test": "jest"}}
        (tmp_project / "package.json").write_text(json.dumps(pkg))
        (tmp_project / "jest.config.js").write_text("module.exports = {};\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "jest"


class TestDetectMix:
    """Detect Elixir mix test."""

    def test_mix_exs(self, detector, tmp_project):
        (tmp_project / "mix.exs").write_text("defmodule MyApp.MixProject do\nend\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "mix"
        assert result.config_file == "mix.exs"


class TestDetectRspec:
    """Detect Ruby rspec."""

    def test_rspec_file(self, detector, tmp_project):
        (tmp_project / ".rspec").write_text("--format documentation\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "rspec"
        assert result.config_file == ".rspec"

    def test_spec_dir_with_gemfile(self, detector, tmp_project):
        (tmp_project / "spec").mkdir()
        (tmp_project / "Gemfile").write_text("source 'https://rubygems.org'\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "rspec"
        assert result.confidence < 0.90  # lower confidence for heuristic


class TestDetectMake:
    """Detect Makefile with test target."""

    def test_makefile_with_test_target(self, detector, tmp_project):
        (tmp_project / "Makefile").write_text("test:\n\techo running tests\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "make"
        assert result.config_file == "Makefile"
        assert result.confidence <= 0.50  # low confidence fallback

    def test_makefile_without_test_target(self, detector, tmp_project):
        (tmp_project / "Makefile").write_text("build:\n\techo building\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is None

    def test_makefile_not_primary_when_other_exists(self, detector, tmp_project):
        """Makefile test target should not be detected when a real framework exists."""
        (tmp_project / "Makefile").write_text("test:\n\tpytest\n")
        (tmp_project / "pytest.ini").write_text("[pytest]\n")
        result = detector.detect_primary(str(tmp_project))
        assert result is not None
        assert result.name == "pytest"  # pytest wins over make


# ---------------------------------------------------------------------------
# Multi-framework and edge cases
# ---------------------------------------------------------------------------


class TestMultipleFrameworks:
    """Projects with multiple test frameworks."""

    def test_detect_multiple(self, detector, tmp_project):
        """Polyglot project: pytest + go test detected together."""
        (tmp_project / "pytest.ini").write_text("[pytest]\n")
        (tmp_project / "go.mod").write_text("module example.com/app\n")
        results = detector.detect(str(tmp_project))
        names = {r.name for r in results}
        assert "pytest" in names
        assert "go" in names
        assert len(results) >= 2

    def test_primary_returns_highest_confidence(self, detector, tmp_project):
        """Primary should return the highest-confidence framework."""
        (tmp_project / "pytest.ini").write_text("[pytest]\n")  # 0.95
        (tmp_project / "go.mod").write_text("module example.com/app\n")  # 0.90
        primary = detector.detect_primary(str(tmp_project))
        assert primary is not None
        # Both are high confidence, but pytest.ini should be >= go.mod
        assert primary.confidence >= 0.90

    def test_sorted_by_confidence(self, detector, tmp_project):
        """Results should be sorted by confidence descending."""
        (tmp_project / "pytest.ini").write_text("[pytest]\n")
        (tmp_project / "go.mod").write_text("module example.com/app\n")
        results = detector.detect(str(tmp_project))
        confidences = [r.confidence for r in results]
        assert confidences == sorted(confidences, reverse=True)


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_detect_none_empty_dir(self, detector, tmp_project):
        """Empty directory returns empty list."""
        results = detector.detect(str(tmp_project))
        assert results == []

    def test_detect_none_nonexistent_dir(self, detector):
        """Non-existent directory returns empty list."""
        results = detector.detect("/nonexistent/path/12345")
        assert results == []

    def test_primary_returns_none_empty(self, detector, tmp_project):
        """Empty directory returns None for primary."""
        result = detector.detect_primary(str(tmp_project))
        assert result is None

    def test_corrupt_package_json(self, detector, tmp_project):
        """Corrupt JSON does not crash the detector."""
        (tmp_project / "package.json").write_text("{invalid json!!")
        results = detector.detect(str(tmp_project))
        # Should not crash, may return empty or partial results
        assert isinstance(results, list)

    def test_empty_package_json(self, detector, tmp_project):
        """Empty package.json does not detect npm test."""
        (tmp_project / "package.json").write_text("{}")
        results = detector.detect(str(tmp_project))
        # No test script, so no npm detection
        npm_results = [r for r in results if r.name in ("npm", "yarn", "bun")]
        assert len(npm_results) == 0


class TestFormatDetection:
    """Test the human-readable format output."""

    def test_format_no_frameworks(self, detector):
        result = detector.format_detection([])
        assert "No test frameworks detected" in result

    def test_format_with_frameworks(self, detector, tmp_project):
        (tmp_project / "pytest.ini").write_text("[pytest]\n")
        frameworks = detector.detect(str(tmp_project))
        result = detector.format_detection(frameworks)
        assert "pytest" in result
        assert "primary" in result.lower()
        assert "confidence" in result.lower()


class TestCommandForPath:
    """Test path-specific command generation."""

    def test_pytest_path(self):
        fw = DetectedFramework(name="pytest", command="python -m pytest")
        assert fw.command_for_path("tests/unit/") == "python -m pytest tests/unit/"

    def test_go_path(self):
        fw = DetectedFramework(name="go", command="go test ./...")
        assert fw.command_for_path("internal/users") == "go test ./internal/users/..."

    def test_jest_path(self):
        fw = DetectedFramework(name="jest", command="npx jest")
        assert fw.command_for_path("src/__tests__/auth.test.ts") == "npx jest src/__tests__/auth.test.ts"


class TestThisProject:
    """Detect frameworks in the actual luum-agent-os project."""

    def test_detect_in_luum_agent_os(self, detector):
        """luum-agent-os should detect at least pytest."""
        project_root = str(Path(__file__).resolve().parent.parent.parent)
        results = detector.detect(project_root)
        names = {r.name for r in results}
        assert "pytest" in names, f"Expected pytest in {names}"
