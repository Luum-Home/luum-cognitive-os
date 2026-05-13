"""Unit tests for lib/repo_analyzer.py — dependency parsing, feature detection,
architecture detection, and report formatting.

All tests use temporary directories with synthetic files — no network access
or actual git cloning required.
"""

import json
import textwrap
from pathlib import Path

import pytest

from lib.repo_analyzer import RepoAnalyzer, RepoAnalysis

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def analyzer(tmp_path):
    """Create a RepoAnalyzer with a temp clone dir."""
    return RepoAnalyzer(clone_dir=str(tmp_path / "clones"))


@pytest.fixture
def make_repo(tmp_path):
    """Factory to create a fake repo directory with given files."""
    def _make(files: dict) -> Path:
        repo = tmp_path / "fake-repo"
        repo.mkdir(exist_ok=True)
        for rel_path, content in files.items():
            fpath = repo / rel_path
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content)
        return repo
    return _make


# ---------------------------------------------------------------------------
# Dependency detection: npm
# ---------------------------------------------------------------------------

class TestDetectNpmDeps:
    def test_parses_dependencies_and_dev_dependencies(self, analyzer, make_repo):
        repo = make_repo({
            "package.json": json.dumps({
                "dependencies": {
                    "express": "^4.18.0",
                    "lodash": "~4.17.21",
                },
                "devDependencies": {
                    "jest": "^29.0.0",
                },
            }),
        })
        deps = analyzer.detect_dependencies(repo)
        names = {d["name"] for d in deps}
        assert "express" in names
        assert "lodash" in names
        assert "jest" in names

        jest_dep = next(d for d in deps if d["name"] == "jest")
        assert jest_dep["dev_only"] is True
        assert jest_dep["source"] == "npm"

        express_dep = next(d for d in deps if d["name"] == "express")
        assert express_dep["dev_only"] is False
        assert express_dep["version"] == "^4.18.0"

    def test_handles_empty_package_json(self, analyzer, make_repo):
        repo = make_repo({"package.json": "{}"})
        deps = analyzer.detect_dependencies(repo)
        assert deps == []

    def test_skips_node_modules(self, analyzer, make_repo):
        repo = make_repo({
            "package.json": json.dumps({"dependencies": {"top": "1.0"}}),
            "node_modules/inner/package.json": json.dumps({"dependencies": {"nested": "2.0"}}),
        })
        deps = analyzer.detect_dependencies(repo)
        names = {d["name"] for d in deps}
        assert "top" in names
        assert "nested" not in names


# ---------------------------------------------------------------------------
# Dependency detection: pip
# ---------------------------------------------------------------------------

class TestDetectPipDeps:
    def test_parses_requirements_txt(self, analyzer, make_repo):
        repo = make_repo({
            "requirements.txt": textwrap.dedent("""\
                flask==2.3.0
                requests>=2.28
                # comment
                boto3~=1.26
                numpy
            """),
        })
        deps = analyzer.detect_dependencies(repo)
        names = {d["name"] for d in deps}
        assert "flask" in names
        assert "requests" in names
        assert "boto3" in names
        assert "numpy" in names

        flask_dep = next(d for d in deps if d["name"] == "flask")
        assert flask_dep["source"] == "pip"
        assert "2.3.0" in flask_dep["version"]

    def test_parses_pyproject_toml_deps_section(self, analyzer, make_repo):
        repo = make_repo({
            "pyproject.toml": textwrap.dedent("""\
                [project]
                name = "myproject"

                [project.dependencies]
                fastapi
                uvicorn

                [project.optional-dependencies]
                dev = ["pytest", "ruff"]
            """),
        })
        deps = analyzer.detect_dependencies(repo)
        names = {d["name"] for d in deps}
        assert "fastapi" in names
        assert "uvicorn" in names


# ---------------------------------------------------------------------------
# Dependency detection: Go
# ---------------------------------------------------------------------------

class TestDetectGoDeps:
    def test_parses_go_mod(self, analyzer, make_repo):
        repo = make_repo({
            "go.mod": textwrap.dedent("""\
                module github.com/example/myapp

                go 1.21

                require (
                    github.com/gin-gonic/gin v1.9.1
                    github.com/stretchr/testify v1.8.4
                )

                require github.com/single/dep v0.1.0
            """),
        })
        deps = analyzer.detect_dependencies(repo)
        names = {d["name"] for d in deps}
        assert "github.com/gin-gonic/gin" in names
        assert "github.com/stretchr/testify" in names
        assert "github.com/single/dep" in names

        gin_dep = next(d for d in deps if "gin" in d["name"])
        assert gin_dep["source"] == "go"
        assert gin_dep["version"] == "v1.9.1"


# ---------------------------------------------------------------------------
# Dependency detection: Rust (Cargo)
# ---------------------------------------------------------------------------

class TestDetectCargoDeps:
    def test_parses_cargo_toml(self, analyzer, make_repo):
        repo = make_repo({
            "Cargo.toml": textwrap.dedent("""\
                [package]
                name = "myapp"
                version = "0.1.0"

                [dependencies]
                serde = "1.0"
                tokio = { version = "1", features = ["full"] }

                [dev-dependencies]
                criterion = "0.5"
            """),
        })
        deps = analyzer.detect_dependencies(repo)
        names = {d["name"] for d in deps}
        assert "serde" in names
        assert "criterion" in names

        criterion = next(d for d in deps if d["name"] == "criterion")
        assert criterion["dev_only"] is True
        assert criterion["source"] == "cargo"


# ---------------------------------------------------------------------------
# Dependency detection: multiple files
# ---------------------------------------------------------------------------

class TestDetectMultipleDepFiles:
    def test_finds_deps_from_multiple_sources(self, analyzer, make_repo):
        repo = make_repo({
            "package.json": json.dumps({"dependencies": {"react": "^18.0"}}),
            "requirements.txt": "django>=4.0\n",
            "go.mod": "module x\n\ngo 1.21\n\nrequire github.com/foo/bar v1.0.0\n",
        })
        deps = analyzer.detect_dependencies(repo)
        sources = {d["source"] for d in deps}
        assert "npm" in sources
        assert "pip" in sources
        assert "go" in sources
        assert len(deps) >= 3


# ---------------------------------------------------------------------------
# Docker service detection
# ---------------------------------------------------------------------------

class TestDetectDockerServices:
    def test_parses_docker_compose_services(self, analyzer, make_repo):
        repo = make_repo({
            "docker-compose.yml": textwrap.dedent("""\
                version: "3"
                services:
                  web:
                    build: .
                    ports:
                      - "3000:3000"
                  postgres:
                    image: postgres:16
                  redis:
                    image: redis:7
                volumes:
                  data:
            """),
        })
        analyzer.analyze.__wrapped__(analyzer, repo) if hasattr(analyzer.analyze, '__wrapped__') else None
        # Use private method directly
        services = analyzer._detect_docker_services(repo)
        assert "web" in services
        assert "postgres" in services
        assert "redis" in services


# ---------------------------------------------------------------------------
# CI/CD detection (GitHub Actions)
# ---------------------------------------------------------------------------

class TestDetectGitHubActions:
    def test_detects_github_workflows(self, analyzer, make_repo):
        repo = make_repo({
            ".github/workflows/ci.yml": "name: CI\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n",
            ".github/workflows/release.yml": "name: Release\non: push\n",
        })
        ci = analyzer._detect_ci_cd(repo)
        assert len(ci) == 1
        assert "GitHub Actions" in ci[0]
        assert "2 workflows" in ci[0]

    def test_detects_gitlab_ci(self, analyzer, make_repo):
        repo = make_repo({".gitlab-ci.yml": "stages:\n  - test\n"})
        ci = analyzer._detect_ci_cd(repo)
        assert "GitLab CI" in ci


# ---------------------------------------------------------------------------
# Plugin system detection
# ---------------------------------------------------------------------------

class TestDetectPluginSystem:
    def test_detects_plugins_directory(self, analyzer, make_repo):
        repo = make_repo({
            "plugins/auth/main.py": "# auth plugin",
            "plugins/logging/main.py": "# logging plugin",
        })
        ps = analyzer._detect_plugin_system(repo)
        assert ps is not None
        assert ps["type"] == "plugin"
        assert ps["count"] == 2

    def test_no_plugin_system(self, analyzer, make_repo):
        repo = make_repo({"src/main.py": "print('hello')"})
        ps = analyzer._detect_plugin_system(repo)
        assert ps is None


# ---------------------------------------------------------------------------
# Architecture detection
# ---------------------------------------------------------------------------

class TestDetectArchitecture:
    def test_detects_clean_architecture(self, analyzer, make_repo):
        repo = make_repo({
            "domain/entities.py": "",
            "application/use_cases.py": "",
            "infrastructure/db.py": "",
        })
        patterns = analyzer.detect_architecture(repo)
        assert any("Clean Architecture" in p for p in patterns)

    def test_detects_monorepo(self, analyzer, make_repo):
        repo = make_repo({
            "packages/core/index.ts": "",
            "packages/cli/index.ts": "",
            "packages/web/index.ts": "",
        })
        patterns = analyzer.detect_architecture(repo)
        assert any("Monorepo" in p for p in patterns)

    def test_detects_mvc(self, analyzer, make_repo):
        repo = make_repo({
            "models/user.rb": "",
            "views/user.html": "",
            "controllers/user_controller.rb": "",
        })
        patterns = analyzer.detect_architecture(repo)
        assert any("MVC" in p for p in patterns)

    def test_detects_nested_clean_architecture(self, analyzer, make_repo):
        repo = make_repo({
            "internal/domain/entity.go": "",
            "internal/application/use_case.go": "",
            "internal/infrastructure/repo.go": "",
        })
        patterns = analyzer.detect_architecture(repo)
        assert any("Clean Architecture" in p and "internal" in p for p in patterns)


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

class TestFormatReport:
    def test_produces_markdown_with_all_sections(self, analyzer):
        analysis = RepoAnalysis(
            name="test-repo",
            url="https://github.com/test/repo",
            license="MIT",
            language_breakdown={"Python": 60.0, "Go": 30.0, "Shell": 10.0},
            total_files=150,
            total_lines=12000,
            dependencies=[
                {"name": "flask", "version": "2.0", "source": "pip", "dev_only": False},
                {"name": "pytest", "version": "7.0", "source": "pip", "dev_only": True},
            ],
            features=[
                {"name": "REST API", "description": "HTTP API server", "files_involved": ["api/"]},
            ],
            architecture_patterns=["Clean Architecture"],
            tools_integrated=[
                {"name": "Docker", "purpose": "Containerization", "how_integrated": "Dockerfile present"},
            ],
            api_endpoints=["GET /api/users", "POST /api/users"],
            config_files=["config.yaml", ".env.example"],
            ci_cd=["GitHub Actions (3 workflows)"],
            docker_services=["web", "postgres"],
            security_tools=["Semgrep"],
            plugin_system={"type": "plugin", "count": 5, "directories": ["plugins"]},
            test_coverage=25.0,
        )

        report = analyzer.format_report(analysis)

        # Check all major sections are present
        assert "# Repository Forensic Report: test-repo" in report
        assert "## Language Breakdown" in report
        assert "Python" in report
        assert "## Dependencies" in report
        assert "flask" in report
        assert "## Features" in report
        assert "REST API" in report
        assert "## Architecture Patterns" in report
        assert "Clean Architecture" in report
        assert "## Integrated Tools" in report
        assert "Docker" in report
        assert "## API Endpoints" in report
        assert "GET /api/users" in report
        assert "## CI/CD" in report
        assert "## Docker Services" in report
        assert "postgres" in report
        assert "## Security Tools" in report
        assert "Semgrep" in report
        assert "## Plugin System" in report
        assert "## Configuration Files" in report
        assert "## Test Presence" in report

    def test_report_with_comparison(self, analyzer):
        analysis = RepoAnalysis(name="test", url="https://example.com")
        comparison = {
            "features_they_have_we_dont": ["Custom Feature"],
            "features_we_have_they_dont": ["SDD Pipeline"],
            "tools_overlap": ["Docker"],
            "tools_they_have_we_dont": [],
            "tools_we_have_they_dont": [],
            "architecture_patterns": [],
        }
        report = analyzer.format_report(analysis, comparison=comparison)
        assert "Comparison with Cognitive OS" in report
        assert "Custom Feature" in report
        assert "SDD Pipeline" in report


# ---------------------------------------------------------------------------
# Integration: analyze luum-agent-os itself
# ---------------------------------------------------------------------------

class TestAnalyzeThisRepo:
    """Integration test that analyzes the luum-agent-os repo directly
    (no cloning — reads from the actual project directory)."""

    def test_detect_deps_in_this_repo(self, analyzer):
        """Detect dependencies in the actual luum-agent-os repo."""
        project_root = Path(__file__).resolve().parent.parent.parent
        deps = analyzer.detect_dependencies(project_root)
        # We know this repo has at least pyproject.toml or requirements
        # The test validates the method runs without error on a real repo
        assert isinstance(deps, list)

    def test_detect_features_in_this_repo(self, analyzer):
        """Detect features in the actual luum-agent-os repo."""
        project_root = Path(__file__).resolve().parent.parent.parent
        features = analyzer.detect_features(project_root)
        assert isinstance(features, list)

    def test_detect_architecture_in_this_repo(self, analyzer):
        """Detect architecture patterns in the actual luum-agent-os repo."""
        project_root = Path(__file__).resolve().parent.parent.parent
        patterns = analyzer.detect_architecture(project_root)
        assert isinstance(patterns, list)

    def test_detect_tools_in_this_repo(self, analyzer):
        """Detect tools in the actual luum-agent-os repo."""
        project_root = Path(__file__).resolve().parent.parent.parent
        tools = analyzer.detect_tools(project_root)
        assert isinstance(tools, list)

    def test_format_report_on_this_repo(self, analyzer):
        """Build a full analysis object and format the report."""
        project_root = Path(__file__).resolve().parent.parent.parent
        analysis = RepoAnalysis(
            name="luum-agent-os",
            url="https://github.com/luum/luum-agent-os",
            license="MIT",
            language_breakdown={"Python": 50.0, "Shell": 30.0, "Markdown": 20.0},
            total_files=500,
            total_lines=50000,
            dependencies=analyzer.detect_dependencies(project_root),
            features=analyzer.detect_features(project_root),
            architecture_patterns=analyzer.detect_architecture(project_root),
            tools_integrated=analyzer.detect_tools(project_root),
        )
        report = analyzer.format_report(analysis)
        assert "luum-agent-os" in report
        assert "## Language Breakdown" in report


# ---------------------------------------------------------------------------
# License detection
# ---------------------------------------------------------------------------

class TestLicenseDetection:
    def test_detects_mit_license(self, analyzer, make_repo):
        repo = make_repo({
            "LICENSE": "MIT License\n\nPermission is hereby granted, free of charge...",
        })
        lic = analyzer._detect_license(repo)
        assert lic == "MIT"

    def test_detects_apache_license(self, analyzer, make_repo):
        repo = make_repo({
            "LICENSE": "Apache License\nVersion 2.0, January 2004\n...",
        })
        lic = analyzer._detect_license(repo)
        assert lic == "Apache-2.0"

    def test_detects_license_from_package_json(self, analyzer, make_repo):
        repo = make_repo({
            "package.json": json.dumps({"license": "BSD-3-Clause"}),
        })
        lic = analyzer._detect_license(repo)
        assert lic == "BSD-3-Clause"

    def test_no_license(self, analyzer, make_repo):
        repo = make_repo({"src/main.py": "print('hi')"})
        lic = analyzer._detect_license(repo)
        assert "No license" in lic


# ---------------------------------------------------------------------------
# Language counting
# ---------------------------------------------------------------------------

class TestLanguageCounting:
    def test_counts_lines_per_language(self, analyzer, make_repo):
        repo = make_repo({
            "main.py": "line1\nline2\nline3\n",
            "lib.go": "package main\nfunc main() {}\n",
            "app.ts": "const x = 1;\n",
        })
        counts = analyzer._count_languages(repo)
        assert counts.get("Python", 0) == 3
        assert counts.get("Go", 0) == 2
        assert counts.get("TypeScript", 0) == 1


# ---------------------------------------------------------------------------
# Endpoint detection
# ---------------------------------------------------------------------------

class TestEndpointDetection:
    def test_detects_express_routes(self, analyzer, make_repo):
        repo = make_repo({
            "routes.js": textwrap.dedent("""\
                app.get("/api/users", handler);
                app.post("/api/users", createHandler);
                router.delete("/api/users/:id", deleteHandler);
            """),
        })
        endpoints = analyzer._detect_endpoints(repo)
        assert "GET /api/users" in endpoints
        assert "POST /api/users" in endpoints
        assert "DELETE /api/users/:id" in endpoints

    def test_detects_flask_routes(self, analyzer, make_repo):
        repo = make_repo({
            "app.py": textwrap.dedent("""\
                @app.route("/health")
                def health():
                    return "ok"

                @app.get("/items")
                def list_items():
                    return []
            """),
        })
        endpoints = analyzer._detect_endpoints(repo)
        assert any("/health" in ep for ep in endpoints)
        assert any("/items" in ep for ep in endpoints)


# ---------------------------------------------------------------------------
# Gradle dependency parsing
# ---------------------------------------------------------------------------

class TestGradleDeps:
    def test_parses_gradle_deps(self, analyzer, make_repo):
        repo = make_repo({
            "build.gradle": textwrap.dedent("""\
                dependencies {
                    implementation 'org.springframework.boot:spring-boot-starter-web:3.1.0'
                    testImplementation 'junit:junit:4.13'
                }
            """),
        })
        deps = analyzer.detect_dependencies(repo)
        names = {d["name"] for d in deps}
        assert "org.springframework.boot:spring-boot-starter-web" in names
        junit = next(d for d in deps if "junit" in d["name"])
        assert junit["dev_only"] is True
        assert junit["source"] == "gradle"


# ---------------------------------------------------------------------------
# Maven dependency parsing
# ---------------------------------------------------------------------------

class TestMavenDeps:
    def test_parses_pom_xml(self, analyzer, make_repo):
        repo = make_repo({
            "pom.xml": textwrap.dedent("""\
                <project>
                    <dependencies>
                        <dependency>
                            <groupId>org.apache.commons</groupId>
                            <artifactId>commons-lang3</artifactId>
                            <version>3.12.0</version>
                        </dependency>
                    </dependencies>
                </project>
            """),
        })
        deps = analyzer.detect_dependencies(repo)
        assert len(deps) >= 1
        assert deps[0]["name"] == "org.apache.commons:commons-lang3"
        assert deps[0]["version"] == "3.12.0"
        assert deps[0]["source"] == "maven"


# ---------------------------------------------------------------------------
# Gemfile parsing
# ---------------------------------------------------------------------------

class TestGemfileDeps:
    def test_parses_gemfile(self, analyzer, make_repo):
        repo = make_repo({
            "Gemfile": textwrap.dedent("""\
                source 'https://rubygems.org'
                gem 'rails', '~> 7.0'
                gem 'puma'
            """),
        })
        deps = analyzer.detect_dependencies(repo)
        names = {d["name"] for d in deps}
        assert "rails" in names
        assert "puma" in names
        rails = next(d for d in deps if d["name"] == "rails")
        assert rails["source"] == "gem"


# ---------------------------------------------------------------------------
# mix.exs parsing
# ---------------------------------------------------------------------------

class TestMixExsDeps:
    def test_parses_mix_exs(self, analyzer, make_repo):
        repo = make_repo({
            "mix.exs": textwrap.dedent("""\
                defmodule MyApp.MixProject do
                  defp deps do
                    [
                      {:phoenix, "~> 1.7"},
                      {:ecto, "~> 3.10"}
                    ]
                  end
                end
            """),
        })
        deps = analyzer.detect_dependencies(repo)
        names = {d["name"] for d in deps}
        assert "phoenix" in names
        assert "ecto" in names
        phoenix = next(d for d in deps if d["name"] == "phoenix")
        assert phoenix["source"] == "hex"


# ---------------------------------------------------------------------------
# COS comparison
# ---------------------------------------------------------------------------

class TestCOSComparison:
    def test_comparison_identifies_differences(self, analyzer):
        analysis = RepoAnalysis(
            name="other-repo",
            url="https://github.com/other/repo",
            features=[
                {"name": "Custom Dashboard", "description": "...", "files_involved": []},
                {"name": "SDD Pipeline", "description": "...", "files_involved": []},
            ],
            tools_integrated=[
                {"name": "Docker", "purpose": "Containerization", "how_integrated": "..."},
                {"name": "Trivy", "purpose": "Security", "how_integrated": "..."},
            ],
        )
        comparison = analyzer.compare_with_cos(analysis)
        assert "Custom Dashboard" in comparison["features_they_have_we_dont"]
        assert "Docker" in comparison["tools_overlap"]
        assert "Trivy" in comparison["tools_they_have_we_dont"]


# ---------------------------------------------------------------------------
# Test presence estimation
# ---------------------------------------------------------------------------

class TestTestPresence:
    def test_estimates_test_ratio(self, analyzer, make_repo):
        repo = make_repo({
            "main.py": "print('hello')\n",
            "utils.py": "def foo(): pass\n",
            "test_main.py": "def test_main(): pass\n",
        })
        ratio = analyzer._estimate_test_presence(repo)
        assert ratio is not None
        # 1 test file / 3 total = 33.3%
        assert 30 < ratio < 40
