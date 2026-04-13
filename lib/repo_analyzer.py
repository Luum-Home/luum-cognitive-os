# scope: both
"""Repo Analyzer — Deep forensic analysis of git repositories.

Clones repos, analyzes code, dependencies, architecture, features, tools,
and produces exhaustive structured reports. Designed for evaluating external
repos and comparing them with Cognitive OS.

Author: luum
Python 3.9+ compatible. No external deps (uses git CLI for cloning).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RepoAnalysis:
    """Structured result of a full repository analysis."""

    name: str = ""
    url: str = ""
    license: str = "Unknown"
    language_breakdown: Dict[str, float] = field(default_factory=dict)
    total_files: int = 0
    total_lines: int = 0
    dependencies: List[dict] = field(default_factory=list)
    features: List[dict] = field(default_factory=list)
    architecture_patterns: List[str] = field(default_factory=list)
    tools_integrated: List[dict] = field(default_factory=list)
    api_endpoints: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    test_coverage: Optional[float] = None
    ci_cd: List[str] = field(default_factory=list)
    docker_services: List[str] = field(default_factory=list)
    security_tools: List[str] = field(default_factory=list)
    plugin_system: Optional[dict] = None


# ---------------------------------------------------------------------------
# Language detection helpers
# ---------------------------------------------------------------------------

# Extension -> language name mapping
LANG_EXTENSIONS: Dict[str, str] = {
    ".py": "Python",
    ".go": "Go",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".cs": "C#",
    ".swift": "Swift",
    ".php": "PHP",
    ".lua": "Lua",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".fish": "Shell",
    ".md": "Markdown",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".proto": "Protobuf",
    ".graphql": "GraphQL",
    ".gql": "GraphQL",
    ".dart": "Dart",
    ".zig": "Zig",
    ".nim": "Nim",
    ".r": "R",
    ".R": "R",
    ".scala": "Scala",
    ".clj": "Clojure",
    ".erl": "Erlang",
    ".hrl": "Erlang",
    ".v": "V",
    ".sol": "Solidity",
}

# Directories to skip during file scanning
SKIP_DIRS = {
    ".git", "node_modules", "vendor", "venv", ".venv", "__pycache__",
    "target", "build", "dist", ".next", ".nuxt", "coverage", ".tox",
    "eggs", ".eggs", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "site-packages", "bower_components", ".terraform", ".cache",
}


# ---------------------------------------------------------------------------
# RepoAnalyzer
# ---------------------------------------------------------------------------

class RepoAnalyzer:
    """Full forensic analyzer for git repositories."""

    def __init__(self, clone_dir: str = "/tmp/cos-repo-analysis"):
        self.clone_dir = Path(clone_dir)
        self.clone_dir.mkdir(parents=True, exist_ok=True)

    # ----- public API -----

    def analyze(self, repo_url: str, depth: str = "full") -> RepoAnalysis:
        """Full analysis pipeline.

        Args:
            repo_url: Git-cloneable URL.
            depth: "full" (everything) or "quick" (deps + features only).

        Returns:
            RepoAnalysis dataclass with all findings.
        """
        repo_path = self._clone(repo_url)
        analysis = RepoAnalysis(
            name=repo_path.name,
            url=repo_url,
        )

        # Always run these
        analysis.license = self._detect_license(repo_path)
        lang_lines = self._count_languages(repo_path)
        total = sum(lang_lines.values()) or 1
        analysis.language_breakdown = {
            lang: round(lines / total * 100, 1) for lang, lines in lang_lines.items()
        }
        analysis.total_lines = total
        analysis.total_files = self._count_files(repo_path)
        analysis.dependencies = self.detect_dependencies(repo_path)
        analysis.features = self.detect_features(repo_path)
        analysis.config_files = self._find_config_files(repo_path)

        if depth == "full":
            analysis.architecture_patterns = self.detect_architecture(repo_path)
            analysis.tools_integrated = self.detect_tools(repo_path)
            analysis.api_endpoints = self._detect_endpoints(repo_path)
            analysis.ci_cd = self._detect_ci_cd(repo_path)
            analysis.docker_services = self._detect_docker_services(repo_path)
            analysis.security_tools = self._detect_security_tools(repo_path)
            analysis.plugin_system = self._detect_plugin_system(repo_path)
            analysis.test_coverage = self._estimate_test_presence(repo_path)

        return analysis

    # ----- dependency detection -----

    def detect_dependencies(self, repo_path: str | Path) -> List[dict]:
        """Parse ALL dependency files found in the repo."""
        repo_path = Path(repo_path)
        deps: List[dict] = []

        # package.json (npm/yarn/pnpm)
        for pjson in repo_path.rglob("package.json"):
            if any(skip in pjson.parts for skip in SKIP_DIRS):
                continue
            deps.extend(self._parse_package_json(pjson))

        # requirements.txt (pip)
        for req in repo_path.rglob("requirements*.txt"):
            if any(skip in req.parts for skip in SKIP_DIRS):
                continue
            deps.extend(self._parse_requirements_txt(req))

        # pyproject.toml (pip/poetry/flit)
        for pyp in repo_path.rglob("pyproject.toml"):
            if any(skip in pyp.parts for skip in SKIP_DIRS):
                continue
            deps.extend(self._parse_pyproject_toml(pyp))

        # go.mod
        for gomod in repo_path.rglob("go.mod"):
            if any(skip in gomod.parts for skip in SKIP_DIRS):
                continue
            deps.extend(self._parse_go_mod(gomod))

        # Cargo.toml (rust)
        for cargo in repo_path.rglob("Cargo.toml"):
            if any(skip in cargo.parts for skip in SKIP_DIRS):
                continue
            deps.extend(self._parse_cargo_toml(cargo))

        # build.gradle / build.gradle.kts (gradle)
        for gradle in list(repo_path.rglob("build.gradle")) + list(repo_path.rglob("build.gradle.kts")):
            if any(skip in gradle.parts for skip in SKIP_DIRS):
                continue
            deps.extend(self._parse_gradle(gradle))

        # pom.xml (maven)
        for pom in repo_path.rglob("pom.xml"):
            if any(skip in pom.parts for skip in SKIP_DIRS):
                continue
            deps.extend(self._parse_pom_xml(pom))

        # Gemfile (ruby)
        for gemfile in repo_path.rglob("Gemfile"):
            if any(skip in gemfile.parts for skip in SKIP_DIRS):
                continue
            deps.extend(self._parse_gemfile(gemfile))

        # mix.exs (elixir)
        for mix in repo_path.rglob("mix.exs"):
            if any(skip in mix.parts for skip in SKIP_DIRS):
                continue
            deps.extend(self._parse_mix_exs(mix))

        return deps

    # ----- feature detection -----

    def detect_features(self, repo_path: str | Path) -> List[dict]:
        """Detect features from README, CHANGELOG, directory structure, CLI."""
        repo_path = Path(repo_path)
        features: List[dict] = []

        # README headings/feature lists
        for readme_name in ("README.md", "readme.md", "README.rst", "README"):
            readme = repo_path / readme_name
            if readme.exists():
                features.extend(self._extract_readme_features(readme))
                break

        # CHANGELOG feature entries
        for cl_name in ("CHANGELOG.md", "changelog.md", "CHANGES.md", "HISTORY.md"):
            changelog = repo_path / cl_name
            if changelog.exists():
                features.extend(self._extract_changelog_features(changelog))
                break

        # Directory-based feature detection
        features.extend(self._detect_dir_features(repo_path))

        # CLI command detection
        features.extend(self._detect_cli_commands(repo_path))

        return features

    # ----- tool detection -----

    def detect_tools(self, repo_path: str | Path) -> List[dict]:
        """Detect integrated development/CI/security/monitoring tools."""
        repo_path = Path(repo_path)
        tools: List[dict] = []

        # Docker
        dockerfiles = list(repo_path.rglob("Dockerfile*"))
        compose_files = list(repo_path.rglob("docker-compose*"))
        if dockerfiles or compose_files:
            tools.append({
                "name": "Docker",
                "purpose": "Containerization",
                "how_integrated": f"{len(dockerfiles)} Dockerfile(s), {len(compose_files)} compose file(s)",
            })

        # CI/CD
        ci_systems = self._detect_ci_cd(repo_path)
        for ci in ci_systems:
            tools.append({"name": ci, "purpose": "CI/CD", "how_integrated": "config file present"})

        # Linting
        lint_configs = {
            ".eslintrc*": "ESLint",
            ".prettierrc*": "Prettier",
            "ruff.toml": "Ruff",
            ".ruff.toml": "Ruff",
            ".golangci.yml": "golangci-lint",
            ".golangci.yaml": "golangci-lint",
            "rustfmt.toml": "rustfmt",
            ".rubocop.yml": "RuboCop",
            "credo.exs": "Credo",
        }
        for pattern, name in lint_configs.items():
            if list(repo_path.glob(pattern)):
                tools.append({"name": name, "purpose": "Linting", "how_integrated": "config file"})

        # Testing frameworks (detect from config files)
        test_configs = {
            "jest.config*": "Jest",
            "vitest.config*": "Vitest",
            "pytest.ini": "pytest",
            "setup.cfg": "pytest/setuptools",
            "conftest.py": "pytest",
            "cypress.config*": "Cypress",
            "playwright.config*": "Playwright",
            ".nycrc*": "NYC/Istanbul",
        }
        for pattern, name in test_configs.items():
            if list(repo_path.glob(pattern)):
                tools.append({"name": name, "purpose": "Testing", "how_integrated": "config file"})

        # Security tools
        security_configs = {
            ".semgrep*": "Semgrep",
            ".snyk": "Snyk",
            ".trivyignore": "Trivy",
            ".bandit": "Bandit",
            ".safety": "Safety",
        }
        for pattern, name in security_configs.items():
            if list(repo_path.glob(pattern)):
                tools.append({"name": name, "purpose": "Security", "how_integrated": "config file"})

        # Monitoring / Observability
        monitoring_patterns = {
            "prometheus": "Prometheus",
            "grafana": "Grafana",
            "sentry": "Sentry",
            "datadog": "Datadog",
            "newrelic": "New Relic",
            "opentelemetry": "OpenTelemetry",
            "jaeger": "Jaeger",
        }
        for compose_file in compose_files:
            try:
                content = compose_file.read_text(errors="replace").lower()
                for keyword, name in monitoring_patterns.items():
                    if keyword in content:
                        tools.append({
                            "name": name,
                            "purpose": "Monitoring/Observability",
                            "how_integrated": f"referenced in {compose_file.name}",
                        })
            except Exception:
                pass

        return tools

    # ----- architecture detection -----

    def detect_architecture(self, repo_path: str | Path) -> List[str]:
        """Detect architecture patterns from directory structure and files."""
        repo_path = Path(repo_path)
        patterns: List[str] = []

        # Get top-level and second-level dirs
        top_dirs = {d.name for d in repo_path.iterdir() if d.is_dir() and not d.name.startswith(".")}

        # Monorepo detection
        monorepo_markers = {"packages", "apps", "services", "modules", "libs", "crates", "workspaces"}
        if monorepo_markers & top_dirs:
            sub_count = 0
            for marker in monorepo_markers & top_dirs:
                sub_count += len([d for d in (repo_path / marker).iterdir() if d.is_dir()])
            if sub_count >= 2:
                patterns.append(f"Monorepo ({sub_count} sub-packages)")

        # Clean Architecture
        clean_markers = {"domain", "application", "infrastructure"}
        if clean_markers.issubset(top_dirs):
            patterns.append("Clean Architecture (domain/application/infrastructure)")
        # Check nested (e.g., internal/ or src/)
        for nest in ("internal", "src", "app"):
            nested = repo_path / nest
            if nested.is_dir():
                nested_dirs = {d.name for d in nested.iterdir() if d.is_dir()}
                if clean_markers.issubset(nested_dirs):
                    patterns.append(f"Clean Architecture ({nest}/domain|application|infrastructure)")
                    break

        # MVC
        mvc_markers = {"models", "views", "controllers"}
        if mvc_markers.issubset(top_dirs):
            patterns.append("MVC (models/views/controllers)")
        for nest in ("app", "src"):
            nested = repo_path / nest
            if nested.is_dir():
                nested_dirs = {d.name for d in nested.iterdir() if d.is_dir()}
                if mvc_markers.issubset(nested_dirs):
                    patterns.append(f"MVC ({nest}/models|views|controllers)")
                    break

        # Hexagonal / Ports & Adapters
        hex_markers = {"ports", "adapters"}
        for root_dir in [repo_path] + [repo_path / d for d in ("internal", "src", "app") if (repo_path / d).is_dir()]:
            sub_dirs = {d.name for d in root_dir.iterdir() if d.is_dir()}
            if hex_markers.issubset(sub_dirs):
                patterns.append("Hexagonal Architecture (ports/adapters)")
                break

        # Plugin / Extension system
        plugin_dirs = {"plugins", "extensions", "addons", "contrib", "modules"}
        found_plugin_dirs = plugin_dirs & top_dirs
        if found_plugin_dirs:
            patterns.append(f"Plugin System (directories: {', '.join(sorted(found_plugin_dirs))})")

        # Microservices
        dockerfiles = list(repo_path.rglob("Dockerfile"))
        # Exclude root Dockerfile
        service_dockerfiles = [d for d in dockerfiles if d.parent != repo_path]
        if len(service_dockerfiles) >= 2:
            patterns.append(f"Microservices ({len(service_dockerfiles)} service Dockerfiles)")

        # Event-driven
        event_keywords = {"kafka", "rabbitmq", "nats", "redis streams", "pubsub", "event_bus", "eventbus"}
        all_text_sample = self._sample_source_text(repo_path, max_files=50)
        lower_sample = all_text_sample.lower()
        found_events = [kw for kw in event_keywords if kw.replace(" ", "") in lower_sample.replace(" ", "")]
        if found_events:
            patterns.append(f"Event-Driven ({', '.join(found_events)})")

        # Serverless
        serverless_markers = {"serverless.yml", "serverless.yaml", "template.yaml", "sam.yaml"}
        for marker in serverless_markers:
            if (repo_path / marker).exists():
                patterns.append("Serverless")
                break

        # CQRS
        if "commands" in top_dirs and "queries" in top_dirs:
            patterns.append("CQRS (commands/queries)")

        return patterns

    # ----- COS comparison -----

    def compare_with_cos(self, analysis: RepoAnalysis) -> dict:
        """Compare analyzed repo with Cognitive OS features."""
        cos_features = {
            "SDD Pipeline", "Hook System", "Agent Orchestration", "Engram Memory",
            "Security Scanning", "Auto-Repair", "Trust Scoring", "Agent KPIs",
            "Model Routing", "Cost Dashboard", "Rate Limiting", "Crash Recovery",
            "Plugin/Skill System", "Docker Integration", "CI/CD", "Linting",
            "Testing Framework", "Squad Protocol", "Prompt Composition",
            "Context Management", "Error Learning", "Impact Analysis",
        }
        cos_tools = {
            "Semgrep", "Aguara", "Promptfoo", "Docker", "Git", "pytest",
        }

        their_feature_names = {f["name"] for f in analysis.features}
        their_tool_names = {t["name"] for t in analysis.tools_integrated}

        return {
            "features_they_have_we_dont": sorted(their_feature_names - cos_features),
            "features_we_have_they_dont": sorted(cos_features - their_feature_names),
            "tools_overlap": sorted(cos_tools & their_tool_names),
            "tools_they_have_we_dont": sorted(their_tool_names - cos_tools),
            "tools_we_have_they_dont": sorted(cos_tools - their_tool_names),
            "architecture_patterns": analysis.architecture_patterns,
        }

    # ----- report formatting -----

    def format_report(self, analysis: RepoAnalysis, comparison: Optional[dict] = None) -> str:
        """Produce exhaustive markdown report."""
        lines: List[str] = []
        lines.append(f"# Repository Forensic Report: {analysis.name}")
        lines.append("")
        lines.append(f"**URL**: {analysis.url}")
        lines.append(f"**License**: {analysis.license}")
        lines.append(f"**Total files**: {analysis.total_files}")
        lines.append(f"**Total lines**: {analysis.total_lines:,}")
        lines.append("")

        # Language breakdown
        lines.append("## Language Breakdown")
        lines.append("")
        if analysis.language_breakdown:
            lines.append("| Language | Percentage |")
            lines.append("|----------|-----------|")
            for lang, pct in sorted(analysis.language_breakdown.items(), key=lambda x: -x[1]):
                if pct >= 0.5:
                    lines.append(f"| {lang} | {pct}% |")
        else:
            lines.append("No source files detected.")
        lines.append("")

        # Dependencies
        lines.append("## Dependencies")
        lines.append("")
        if analysis.dependencies:
            lines.append(f"**Total**: {len(analysis.dependencies)}")
            lines.append("")
            by_source: Dict[str, List[dict]] = {}
            for dep in analysis.dependencies:
                src = dep.get("source", "unknown")
                by_source.setdefault(src, []).append(dep)
            for src, deps in sorted(by_source.items()):
                lines.append(f"### {src} ({len(deps)})")
                lines.append("")
                lines.append("| Name | Version | Dev Only |")
                lines.append("|------|---------|----------|")
                for d in sorted(deps, key=lambda x: x.get("name", "")):
                    dev = "Yes" if d.get("dev_only") else ""
                    lines.append(f"| {d.get('name', '?')} | {d.get('version', '?')} | {dev} |")
                lines.append("")
        else:
            lines.append("No dependencies detected.")
            lines.append("")

        # Features
        lines.append("## Features")
        lines.append("")
        if analysis.features:
            for feat in analysis.features:
                name = feat.get("name", "Unknown")
                desc = feat.get("description", "")
                files = feat.get("files_involved", [])
                lines.append(f"- **{name}**: {desc}")
                if files:
                    lines.append(f"  - Files: {', '.join(files[:5])}")
        else:
            lines.append("No features detected from README/CHANGELOG.")
        lines.append("")

        # Architecture
        lines.append("## Architecture Patterns")
        lines.append("")
        if analysis.architecture_patterns:
            for pattern in analysis.architecture_patterns:
                lines.append(f"- {pattern}")
        else:
            lines.append("No specific architecture patterns detected.")
        lines.append("")

        # Tools
        lines.append("## Integrated Tools")
        lines.append("")
        if analysis.tools_integrated:
            lines.append("| Tool | Purpose | Integration |")
            lines.append("|------|---------|-------------|")
            for tool in analysis.tools_integrated:
                lines.append(
                    f"| {tool.get('name', '?')} | {tool.get('purpose', '?')} | {tool.get('how_integrated', '?')} |"
                )
        else:
            lines.append("No tools detected.")
        lines.append("")

        # API endpoints
        if analysis.api_endpoints:
            lines.append("## API Endpoints")
            lines.append("")
            for ep in analysis.api_endpoints[:50]:
                lines.append(f"- `{ep}`")
            if len(analysis.api_endpoints) > 50:
                lines.append(f"- ... and {len(analysis.api_endpoints) - 50} more")
            lines.append("")

        # CI/CD
        if analysis.ci_cd:
            lines.append("## CI/CD")
            lines.append("")
            for ci in analysis.ci_cd:
                lines.append(f"- {ci}")
            lines.append("")

        # Docker
        if analysis.docker_services:
            lines.append("## Docker Services")
            lines.append("")
            for svc in analysis.docker_services:
                lines.append(f"- {svc}")
            lines.append("")

        # Security
        if analysis.security_tools:
            lines.append("## Security Tools")
            lines.append("")
            for tool in analysis.security_tools:
                lines.append(f"- {tool}")
            lines.append("")

        # Plugin system
        if analysis.plugin_system:
            lines.append("## Plugin System")
            lines.append("")
            ps = analysis.plugin_system
            lines.append(f"- **Type**: {ps.get('type', 'Unknown')}")
            lines.append(f"- **Count**: {ps.get('count', 0)} plugins/extensions")
            if ps.get("directories"):
                lines.append(f"- **Directories**: {', '.join(ps['directories'])}")
            lines.append("")

        # Config files
        if analysis.config_files:
            lines.append("## Configuration Files")
            lines.append("")
            for cf in analysis.config_files[:30]:
                lines.append(f"- `{cf}`")
            if len(analysis.config_files) > 30:
                lines.append(f"- ... and {len(analysis.config_files) - 30} more")
            lines.append("")

        # Test coverage estimate
        if analysis.test_coverage is not None:
            lines.append("## Test Presence")
            lines.append("")
            lines.append(f"- **Test file ratio**: {analysis.test_coverage:.1f}% of source files have test counterparts")
            lines.append("")

        # Comparison with COS
        if comparison:
            lines.append("## Comparison with Cognitive OS")
            lines.append("")
            if comparison.get("features_they_have_we_dont"):
                lines.append("### Features They Have (COS Does Not)")
                for f in comparison["features_they_have_we_dont"]:
                    lines.append(f"- {f}")
                lines.append("")
            if comparison.get("features_we_have_they_dont"):
                lines.append("### Features COS Has (They Do Not)")
                for f in comparison["features_we_have_they_dont"]:
                    lines.append(f"- {f}")
                lines.append("")
            if comparison.get("tools_overlap"):
                lines.append("### Shared Tools")
                for t in comparison["tools_overlap"]:
                    lines.append(f"- {t}")
                lines.append("")

        return "\n".join(lines)

    # ----- cleanup -----

    def cleanup(self):
        """Remove all cloned repos."""
        if self.clone_dir.exists():
            shutil.rmtree(self.clone_dir, ignore_errors=True)

    # ======================================================================
    # Private helpers
    # ======================================================================

    def _clone(self, repo_url: str) -> Path:
        """Clone repo (shallow for speed). Returns path to cloned repo."""
        # Normalize URL
        url = repo_url.strip()
        if not url.startswith(("http://", "https://", "git@", "ssh://")):
            # Assume GitHub shorthand
            url = f"https://github.com/{url}"
        if not url.endswith(".git"):
            url_with_git = url + ".git"
        else:
            url_with_git = url

        # Extract repo name from URL
        name = url.rstrip("/").split("/")[-1].removesuffix(".git")
        dest = self.clone_dir / name

        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)

        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", url_with_git, str(dest)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            # Try without .git suffix
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--single-branch", url, str(dest)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to clone {repo_url}: {result.stderr.strip()}")

        return dest

    def _detect_license(self, repo_path: Path) -> str:
        """Detect license from LICENSE file or package metadata."""
        for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING"):
            lpath = repo_path / name
            if lpath.exists():
                try:
                    content = lpath.read_text(errors="replace")[:2000].lower()
                    if "mit license" in content or "permission is hereby granted" in content:
                        return "MIT"
                    elif "apache license" in content and "version 2" in content:
                        return "Apache-2.0"
                    elif "gnu general public license" in content:
                        if "version 3" in content:
                            return "GPL-3.0"
                        elif "version 2" in content:
                            return "GPL-2.0"
                        return "GPL"
                    elif "gnu lesser general public" in content:
                        return "LGPL"
                    elif "bsd" in content:
                        if "3-clause" in content or "three clause" in content:
                            return "BSD-3-Clause"
                        return "BSD-2-Clause"
                    elif "mozilla public license" in content:
                        return "MPL-2.0"
                    elif "isc license" in content:
                        return "ISC"
                    elif "gnu affero" in content:
                        return "AGPL-3.0"
                    elif "server side public license" in content:
                        return "SSPL"
                    elif "unlicense" in content:
                        return "Unlicense"
                    elif "creative commons" in content:
                        return "CC"
                    else:
                        return f"Custom ({name} present)"
                except Exception:
                    return f"Unknown ({name} unreadable)"

        # Check package.json
        pjson = repo_path / "package.json"
        if pjson.exists():
            try:
                data = json.loads(pjson.read_text(errors="replace"))
                if "license" in data:
                    return str(data["license"])
            except Exception:
                pass

        # Check pyproject.toml
        pyp = repo_path / "pyproject.toml"
        if pyp.exists():
            try:
                content = pyp.read_text(errors="replace")
                m = re.search(r'license\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    return m.group(1)
                m = re.search(r'license\s*=\s*\{[^}]*text\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    return m.group(1)
            except Exception:
                pass

        # Check Cargo.toml
        cargo = repo_path / "Cargo.toml"
        if cargo.exists():
            try:
                content = cargo.read_text(errors="replace")
                m = re.search(r'license\s*=\s*"([^"]+)"', content)
                if m:
                    return m.group(1)
            except Exception:
                pass

        return "No license found"

    def _count_languages(self, repo_path: Path) -> Dict[str, int]:
        """Count lines of code per language."""
        lang_lines: Dict[str, int] = {}
        for fpath in self._walk_source_files(repo_path):
            ext = fpath.suffix.lower()
            lang = LANG_EXTENSIONS.get(ext)
            if lang:
                try:
                    line_count = sum(1 for _ in fpath.open("r", errors="replace"))
                    lang_lines[lang] = lang_lines.get(lang, 0) + line_count
                except Exception:
                    pass
        return lang_lines

    def _count_files(self, repo_path: Path) -> int:
        """Count total source files (excluding skipped dirs)."""
        return sum(1 for _ in self._walk_source_files(repo_path))

    def _walk_source_files(self, repo_path: Path):
        """Yield all source files, skipping vendor/build/hidden dirs."""
        for dirpath, dirnames, filenames in os.walk(repo_path):
            # Filter out skip dirs in-place
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for fname in filenames:
                fpath = Path(dirpath) / fname
                if fpath.suffix.lower() in LANG_EXTENSIONS:
                    yield fpath

    def _find_config_files(self, repo_path: Path) -> List[str]:
        """Find configuration files at the repo root and common locations."""
        config_patterns = [
            "*.yaml", "*.yml", "*.toml", "*.json", "*.ini", "*.cfg",
            ".env*", "Makefile", "Taskfile*", "justfile", "Rakefile",
            "Procfile", "Brewfile", "Dockerfile*", "docker-compose*",
        ]
        configs: List[str] = []
        for pattern in config_patterns:
            for match in repo_path.glob(pattern):
                if match.is_file() and match.name not in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml"):
                    configs.append(str(match.relative_to(repo_path)))
        return sorted(set(configs))

    # ----- Dependency parsers -----

    def _parse_package_json(self, path: Path) -> List[dict]:
        """Parse npm package.json."""
        deps = []
        try:
            data = json.loads(path.read_text(errors="replace"))
            for name, ver in (data.get("dependencies") or {}).items():
                deps.append({"name": name, "version": str(ver), "source": "npm", "dev_only": False})
            for name, ver in (data.get("devDependencies") or {}).items():
                deps.append({"name": name, "version": str(ver), "source": "npm", "dev_only": True})
        except Exception:
            pass
        return deps

    def _parse_requirements_txt(self, path: Path) -> List[dict]:
        """Parse pip requirements.txt."""
        deps = []
        try:
            for line in path.read_text(errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Handle ==, >=, ~= etc.
                m = re.match(r"^([a-zA-Z0-9_.-]+)\s*([><=~!]+\s*[\w.*]+)?", line)
                if m:
                    name = m.group(1)
                    version = m.group(2).strip() if m.group(2) else "*"
                    deps.append({"name": name, "version": version, "source": "pip", "dev_only": False})
        except Exception:
            pass
        return deps

    def _parse_pyproject_toml(self, path: Path) -> List[dict]:
        """Parse pyproject.toml dependencies (basic regex, no toml lib)."""
        deps = []
        try:
            content = path.read_text(errors="replace")
            # Look for dependencies array
            in_deps = False
            in_dev_deps = False
            for line in content.splitlines():
                stripped = line.strip()
                if re.match(r"\[.*dependencies\]", stripped, re.IGNORECASE):
                    in_deps = True
                    in_dev_deps = "dev" in stripped.lower() or "optional" in stripped.lower()
                    continue
                if stripped.startswith("[") and in_deps:
                    in_deps = False
                    continue
                if in_deps:
                    # Handle "package>=1.0" or 'package = ">=1.0"' style
                    m = re.match(r'^["\']?([a-zA-Z0-9_.-]+)["\']?\s*(?:[><=~!]+\s*[\w.*]+)?', stripped)
                    if m and not stripped.startswith("#"):
                        name = m.group(1)
                        deps.append({"name": name, "version": "*", "source": "pip", "dev_only": in_dev_deps})
        except Exception:
            pass
        return deps

    def _parse_go_mod(self, path: Path) -> List[dict]:
        """Parse go.mod file."""
        deps = []
        try:
            content = path.read_text(errors="replace")
            in_require = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("require ("):
                    in_require = True
                    continue
                if in_require and stripped == ")":
                    in_require = False
                    continue
                if in_require:
                    parts = stripped.split()
                    if len(parts) >= 2 and not parts[0].startswith("//"):
                        deps.append({
                            "name": parts[0],
                            "version": parts[1],
                            "source": "go",
                            "dev_only": False,
                        })
                elif stripped.startswith("require "):
                    parts = stripped.split()
                    if len(parts) >= 3:
                        deps.append({
                            "name": parts[1],
                            "version": parts[2],
                            "source": "go",
                            "dev_only": False,
                        })
        except Exception:
            pass
        return deps

    def _parse_cargo_toml(self, path: Path) -> List[dict]:
        """Parse Cargo.toml dependencies (basic regex)."""
        deps = []
        try:
            content = path.read_text(errors="replace")
            in_deps = False
            in_dev_deps = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped == "[dependencies]":
                    in_deps = True
                    in_dev_deps = False
                    continue
                elif stripped == "[dev-dependencies]":
                    in_deps = True
                    in_dev_deps = True
                    continue
                elif stripped.startswith("["):
                    in_deps = False
                    continue
                if in_deps:
                    m = re.match(r'^([a-zA-Z0-9_-]+)\s*=\s*"?([^"]+)"?', stripped)
                    if m:
                        deps.append({
                            "name": m.group(1),
                            "version": m.group(2).strip(),
                            "source": "cargo",
                            "dev_only": in_dev_deps,
                        })
        except Exception:
            pass
        return deps

    def _parse_gradle(self, path: Path) -> List[dict]:
        """Parse build.gradle dependencies (basic pattern matching)."""
        deps = []
        try:
            content = path.read_text(errors="replace")
            # Match patterns like: implementation 'group:artifact:version'
            for m in re.finditer(
                r'(?:implementation|api|compileOnly|testImplementation|runtimeOnly)\s*[\("\'(]([^"\')\n]+)',
                content,
            ):
                coord = m.group(1).strip("' \"")
                parts = coord.split(":")
                if len(parts) >= 2:
                    name = f"{parts[0]}:{parts[1]}"
                    version = parts[2] if len(parts) >= 3 else "*"
                    dev_only = "test" in m.group(0).lower()
                    deps.append({"name": name, "version": version, "source": "gradle", "dev_only": dev_only})
        except Exception:
            pass
        return deps

    def _parse_pom_xml(self, path: Path) -> List[dict]:
        """Parse Maven pom.xml dependencies (basic regex, no XML lib)."""
        deps = []
        try:
            content = path.read_text(errors="replace")
            # Find <dependency> blocks
            for m in re.finditer(
                r"<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>"
                r"(?:\s*<version>([^<]+)</version>)?",
                content,
            ):
                deps.append({
                    "name": f"{m.group(1)}:{m.group(2)}",
                    "version": m.group(3) or "*",
                    "source": "maven",
                    "dev_only": False,
                })
        except Exception:
            pass
        return deps

    def _parse_gemfile(self, path: Path) -> List[dict]:
        """Parse Ruby Gemfile."""
        deps = []
        try:
            for line in path.read_text(errors="replace").splitlines():
                line = line.strip()
                m = re.match(r"gem\s+['\"]([^'\"]+)['\"](?:,\s*['\"]([^'\"]+)['\"])?", line)
                if m:
                    deps.append({
                        "name": m.group(1),
                        "version": m.group(2) or "*",
                        "source": "gem",
                        "dev_only": False,
                    })
        except Exception:
            pass
        return deps

    def _parse_mix_exs(self, path: Path) -> List[dict]:
        """Parse Elixir mix.exs deps."""
        deps = []
        try:
            content = path.read_text(errors="replace")
            for m in re.finditer(r'\{:(\w+),\s*"~>\s*([^"]+)"', content):
                deps.append({
                    "name": m.group(1),
                    "version": f"~> {m.group(2)}",
                    "source": "hex",
                    "dev_only": False,
                })
        except Exception:
            pass
        return deps

    # ----- Feature extraction helpers -----

    def _extract_readme_features(self, readme_path: Path) -> List[dict]:
        """Extract features from README headings and bullet lists."""
        features = []
        try:
            content = readme_path.read_text(errors="replace")
            lines = content.splitlines()
            in_features_section = False
            for i, line in enumerate(lines):
                # Detect feature-related headings
                if re.match(r"^#{1,3}\s*(features|capabilities|what it does|highlights|key features)", line, re.I):
                    in_features_section = True
                    continue
                elif re.match(r"^#{1,3}\s", line) and in_features_section:
                    in_features_section = False
                    continue

                if in_features_section and line.strip().startswith(("-", "*", "+")):
                    text = re.sub(r"^[-*+]\s*", "", line.strip())
                    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # Remove bold
                    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # Remove links
                    if len(text) > 5:
                        features.append({
                            "name": text[:80],
                            "description": text,
                            "files_involved": [],
                        })
        except Exception:
            pass
        return features

    def _extract_changelog_features(self, changelog_path: Path) -> List[dict]:
        """Extract recent features from CHANGELOG."""
        features = []
        try:
            content = changelog_path.read_text(errors="replace")[:5000]  # Only recent entries
            for m in re.finditer(r"(?:feat|add|new)(?:\([^)]+\))?:\s*(.+)", content, re.I):
                text = m.group(1).strip()
                if len(text) > 5:
                    features.append({
                        "name": text[:80],
                        "description": f"From CHANGELOG: {text}",
                        "files_involved": [],
                    })
        except Exception:
            pass
        return features[:20]  # Cap at 20

    def _detect_dir_features(self, repo_path: Path) -> List[dict]:
        """Detect features from well-known directory names."""
        features = []
        feature_dirs = {
            "api": "REST/HTTP API",
            "graphql": "GraphQL API",
            "grpc": "gRPC API",
            "cli": "Command-line interface",
            "sdk": "SDK/Client library",
            "ui": "User interface",
            "web": "Web application",
            "mobile": "Mobile application",
            "docs": "Documentation",
            "examples": "Usage examples",
            "benchmarks": "Performance benchmarks",
            "migrations": "Database migrations",
            "scripts": "Automation scripts",
        }
        for dir_name, desc in feature_dirs.items():
            if (repo_path / dir_name).is_dir():
                features.append({
                    "name": desc,
                    "description": f"Detected from {dir_name}/ directory",
                    "files_involved": [f"{dir_name}/"],
                })
        return features

    def _detect_cli_commands(self, repo_path: Path) -> List[dict]:
        """Detect CLI commands from common patterns."""
        features = []
        # Check for cobra (Go CLI)
        cmd_dir = repo_path / "cmd"
        if cmd_dir.is_dir():
            for sub in cmd_dir.iterdir():
                if sub.is_dir():
                    features.append({
                        "name": f"CLI: {sub.name}",
                        "description": f"Go CLI binary from cmd/{sub.name}/",
                        "files_involved": [f"cmd/{sub.name}/"],
                    })

        # Check for bin/ scripts
        bin_dir = repo_path / "bin"
        if bin_dir.is_dir():
            for script in bin_dir.iterdir():
                if script.is_file():
                    features.append({
                        "name": f"Script: {script.name}",
                        "description": f"Executable script from bin/{script.name}",
                        "files_involved": [f"bin/{script.name}"],
                    })

        return features

    # ----- CI/CD detection -----

    def _detect_ci_cd(self, repo_path: Path) -> List[str]:
        """Detect CI/CD systems."""
        ci_systems = []
        if (repo_path / ".github" / "workflows").is_dir():
            workflows = list((repo_path / ".github" / "workflows").glob("*.yml")) + \
                        list((repo_path / ".github" / "workflows").glob("*.yaml"))
            ci_systems.append(f"GitHub Actions ({len(workflows)} workflows)")
        if (repo_path / ".gitlab-ci.yml").exists():
            ci_systems.append("GitLab CI")
        if (repo_path / ".circleci").is_dir():
            ci_systems.append("CircleCI")
        if (repo_path / "Jenkinsfile").exists():
            ci_systems.append("Jenkins")
        if (repo_path / ".travis.yml").exists():
            ci_systems.append("Travis CI")
        if (repo_path / "azure-pipelines.yml").exists():
            ci_systems.append("Azure Pipelines")
        if (repo_path / "bitbucket-pipelines.yml").exists():
            ci_systems.append("Bitbucket Pipelines")
        if (repo_path / ".buildkite").is_dir():
            ci_systems.append("Buildkite")
        if (repo_path / ".drone.yml").exists():
            ci_systems.append("Drone CI")
        if (repo_path / "taskcluster").is_dir():
            ci_systems.append("TaskCluster")
        return ci_systems

    # ----- Docker detection -----

    def _detect_docker_services(self, repo_path: Path) -> List[str]:
        """Extract service names from docker-compose files."""
        services = []
        for compose in repo_path.rglob("docker-compose*"):
            if any(skip in compose.parts for skip in SKIP_DIRS):
                continue
            try:
                content = compose.read_text(errors="replace")
                # Simple YAML service extraction (no yaml lib)
                in_services = False
                for line in content.splitlines():
                    if line.strip() == "services:":
                        in_services = True
                        continue
                    if in_services:
                        # Service names are indented exactly 2 spaces
                        m = re.match(r"^  ([a-zA-Z0-9_-]+):", line)
                        if m:
                            services.append(m.group(1))
                        elif line.strip() and not line.startswith(" "):
                            in_services = False
            except Exception:
                pass
        return sorted(set(services))

    # ----- Security tools detection -----

    def _detect_security_tools(self, repo_path: Path) -> List[str]:
        """Detect security scanning tools."""
        tools = []
        checks = {
            ".semgrep*": "Semgrep",
            ".snyk": "Snyk",
            ".trivyignore": "Trivy",
            ".bandit": "Bandit",
            ".safety": "Safety",
            ".scorecard.yml": "OpenSSF Scorecard",
            "security.md": "Security Policy",
            "SECURITY.md": "Security Policy",
        }
        for pattern, name in checks.items():
            if list(repo_path.glob(pattern)):
                tools.append(name)

        # Check GitHub Actions for security workflows
        workflows_dir = repo_path / ".github" / "workflows"
        if workflows_dir.is_dir():
            for wf in workflows_dir.glob("*.y*ml"):
                try:
                    content = wf.read_text(errors="replace").lower()
                    if "codeql" in content:
                        tools.append("CodeQL")
                    if "trivy" in content:
                        tools.append("Trivy (CI)")
                    if "snyk" in content:
                        tools.append("Snyk (CI)")
                    if "semgrep" in content:
                        tools.append("Semgrep (CI)")
                    if "dependabot" in content or "renovate" in content:
                        tools.append("Dependency Updates (CI)")
                except Exception:
                    pass

        # Check for dependabot config
        if (repo_path / ".github" / "dependabot.yml").exists():
            tools.append("Dependabot")
        if (repo_path / "renovate.json").exists() or (repo_path / ".renovaterc").exists():
            tools.append("Renovate")

        return sorted(set(tools))

    # ----- Endpoint detection -----

    def _detect_endpoints(self, repo_path: Path) -> List[str]:
        """Detect API endpoints from route definitions."""
        endpoints = []

        # Common route patterns
        route_patterns = [
            # Express/Koa/Fastify: app.get("/path", ...)
            r'(?:app|router|server)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            # Go gin/chi/echo: r.GET("/path", ...)
            r'(?:r|router|group|e)\.(GET|POST|PUT|DELETE|PATCH|Handle|HandleFunc)\s*\(\s*["\']([^"\']+)["\']',
            # Python Flask/FastAPI: @app.route("/path")
            r'@(?:app|router|bp)\.(route|get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            # NestJS: @Get("/path")
            r'@(Get|Post|Put|Delete|Patch)\s*\(\s*["\']([^"\']+)["\']',
        ]

        for fpath in self._walk_source_files(repo_path):
            if fpath.suffix.lower() not in (".go", ".ts", ".js", ".py", ".rb", ".java", ".kt"):
                continue
            try:
                content = fpath.read_text(errors="replace")
                for pattern in route_patterns:
                    for m in re.finditer(pattern, content, re.IGNORECASE):
                        method = m.group(1).upper()
                        path = m.group(2)
                        endpoints.append(f"{method} {path}")
            except Exception:
                pass

        return sorted(set(endpoints))

    # ----- Plugin system detection -----

    def _detect_plugin_system(self, repo_path: Path) -> Optional[dict]:
        """Detect if the repo has a plugin/extension system."""
        plugin_dirs_map = {
            "plugins": "plugin",
            "extensions": "extension",
            "addons": "addon",
            "contrib": "contrib",
            "providers": "provider",
        }

        for dirname, ptype in plugin_dirs_map.items():
            pdir = repo_path / dirname
            if pdir.is_dir():
                items = [d.name for d in pdir.iterdir() if d.is_dir() and not d.name.startswith(".")]
                if items:
                    return {
                        "type": ptype,
                        "count": len(items),
                        "directories": [dirname],
                        "items": items[:20],
                    }

        return None

    # ----- Test presence estimation -----

    def _estimate_test_presence(self, repo_path: Path) -> Optional[float]:
        """Estimate test file ratio compared to source files."""
        source_files = 0
        test_files = 0
        for fpath in self._walk_source_files(repo_path):
            name = fpath.name.lower()
            if any(t in name for t in ("_test.", ".test.", ".spec.", "test_")):
                test_files += 1
            else:
                source_files += 1
        total = source_files + test_files
        if total == 0:
            return None
        return round(test_files / total * 100, 1)

    # ----- Text sampling -----

    def _sample_source_text(self, repo_path: Path, max_files: int = 50) -> str:
        """Read a sample of source file contents for keyword detection."""
        texts = []
        count = 0
        for fpath in self._walk_source_files(repo_path):
            if count >= max_files:
                break
            try:
                texts.append(fpath.read_text(errors="replace")[:2000])
                count += 1
            except Exception:
                pass
        return "\n".join(texts)
