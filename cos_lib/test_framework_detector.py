# SCOPE: os-only
"""Test Framework Detector — Auto-detect project test frameworks.

Scans project root for configuration files that indicate which test
frameworks are available. Returns structured detection results with
commands for running tests, coverage, and watch mode.

Works with any project: Python, Node, Go, Rust, JVM, Elixir, Ruby, Make.
No external dependencies — stdlib only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class DetectedFramework:
    """A detected test framework with run commands."""

    name: str  # "pytest", "jest", "go", "cargo", etc.
    command: str  # full command to run all tests
    coverage_command: Optional[str] = None  # command with coverage
    watch_command: Optional[str] = None  # command in watch mode
    config_file: str = ""  # file that triggered detection
    confidence: float = 0.5  # 0-1, higher = more certain

    def command_for_path(self, path: str) -> str:
        """Return command adjusted to run a specific path/pattern."""
        if self.name == "pytest":
            return f"python -m pytest {path}"
        if self.name == "jest":
            return f"npx jest {path}"
        if self.name == "vitest":
            return f"npx vitest run {path}"
        if self.name == "go":
            # If path looks like a directory, append /...
            if "/" in path and not path.endswith("..."):
                return f"go test ./{path}/..."
            return f"go test ./{path}"
        if self.name == "cargo":
            return f"cargo test {path}"
        if self.name == "gradle":
            return f"./gradlew test --tests {path}"
        if self.name == "maven":
            return f"mvn test -Dtest={path}"
        if self.name == "mix":
            return f"mix test {path}"
        if self.name == "rspec":
            return f"bundle exec rspec {path}"
        if self.name in ("npm", "yarn", "bun"):
            return f"{self.name} test -- {path}"
        if self.name == "make":
            return f"make test"
        return f"{self.command} {path}"


class TestFrameworkDetector:
    """Detect test frameworks from project files."""

    def detect(self, project_root: str) -> List[DetectedFramework]:
        """Detect all test frameworks in the project.

        Returns frameworks sorted by confidence (highest first).
        """
        root = Path(project_root)
        if not root.is_dir():
            return []

        frameworks: List[DetectedFramework] = []

        # Python: pytest
        fw = self._detect_pytest(root)
        if fw:
            frameworks.append(fw)

        # Node: vitest (check before jest — vitest.config takes precedence)
        fw = self._detect_vitest(root)
        if fw:
            frameworks.append(fw)

        # Node: jest
        fw = self._detect_jest(root)
        if fw:
            frameworks.append(fw)

        # Node: package.json test script (generic npm/yarn/bun)
        fw = self._detect_npm_test(root)
        if fw:
            # Skip if we already found jest or vitest
            existing_names = {f.name for f in frameworks}
            if "jest" not in existing_names and "vitest" not in existing_names:
                frameworks.append(fw)

        # Go
        fw = self._detect_go(root)
        if fw:
            frameworks.append(fw)

        # Rust
        fw = self._detect_cargo(root)
        if fw:
            frameworks.append(fw)

        # JVM: Gradle
        fw = self._detect_gradle(root)
        if fw:
            frameworks.append(fw)

        # JVM: Maven
        fw = self._detect_maven(root)
        if fw:
            frameworks.append(fw)

        # Elixir
        fw = self._detect_mix(root)
        if fw:
            frameworks.append(fw)

        # Ruby: rspec
        fw = self._detect_rspec(root)
        if fw:
            frameworks.append(fw)

        # Makefile with test target
        fw = self._detect_make(root)
        if fw:
            # Only add if no other framework found — make is a fallback
            if not frameworks:
                frameworks.append(fw)

        frameworks.sort(key=lambda f: f.confidence, reverse=True)
        return frameworks

    def detect_primary(self, project_root: str) -> Optional[DetectedFramework]:
        """Return the highest-confidence framework, or None."""
        frameworks = self.detect(project_root)
        return frameworks[0] if frameworks else None

    def format_detection(self, frameworks: List[DetectedFramework]) -> str:
        """Human-readable detection report."""
        if not frameworks:
            return "No test frameworks detected."

        lines = ["Detected test frameworks:", ""]
        for i, fw in enumerate(frameworks, 1):
            primary = " (primary)" if i == 1 else ""
            lines.append(
                f"  {i}. {fw.name}{primary} — confidence {fw.confidence:.0%}"
            )
            lines.append(f"     Config: {fw.config_file}")
            lines.append(f"     Run:    {fw.command}")
            if fw.coverage_command:
                lines.append(f"     Cover:  {fw.coverage_command}")
            if fw.watch_command:
                lines.append(f"     Watch:  {fw.watch_command}")
            lines.append("")
        return "\n".join(lines)

    # -----------------------------------------------------------------
    # Individual framework detectors
    # -----------------------------------------------------------------

    def _detect_pytest(self, root: Path) -> Optional[DetectedFramework]:
        """Detect pytest from config files or pyproject.toml."""
        # Direct pytest config files
        for cfg in ("pytest.ini", "setup.cfg", "tox.ini"):
            p = root / cfg
            if p.is_file():
                content = self._safe_read(p)
                if cfg == "pytest.ini" or "[tool:pytest]" in content or "[pytest]" in content:
                    return DetectedFramework(
                        name="pytest",
                        command="python -m pytest",
                        coverage_command="python -m pytest --cov --cov-report=term-missing",
                        watch_command="python -m pytest --watch" if self._has_package(root, "pytest-watch") else "python -m pytest-watch" if self._has_package(root, "pytest-watch") else None,
                        config_file=cfg,
                        confidence=0.95,
                    )

        # pyproject.toml with [tool.pytest.ini_options]
        pyproject = root / "pyproject.toml"
        if pyproject.is_file():
            content = self._safe_read(pyproject)
            if "[tool.pytest" in content:
                return DetectedFramework(
                    name="pytest",
                    command="python -m pytest",
                    coverage_command="python -m pytest --cov --cov-report=term-missing",
                    watch_command=None,
                    config_file="pyproject.toml",
                    confidence=0.90,
                )

        # Fallback: tests/ directory with conftest.py
        if (root / "conftest.py").is_file() or (root / "tests" / "conftest.py").is_file():
            return DetectedFramework(
                name="pytest",
                command="python -m pytest",
                coverage_command="python -m pytest --cov --cov-report=term-missing",
                watch_command=None,
                config_file="conftest.py",
                confidence=0.70,
            )

        return None

    def _detect_vitest(self, root: Path) -> Optional[DetectedFramework]:
        """Detect vitest from config files."""
        for pattern in ("vitest.config.ts", "vitest.config.js", "vitest.config.mts", "vitest.config.mjs"):
            if (root / pattern).is_file():
                return DetectedFramework(
                    name="vitest",
                    command="npx vitest run",
                    coverage_command="npx vitest run --coverage",
                    watch_command="npx vitest",
                    config_file=pattern,
                    confidence=0.95,
                )
        return None

    def _detect_jest(self, root: Path) -> Optional[DetectedFramework]:
        """Detect jest from config files or package.json."""
        for pattern in ("jest.config.js", "jest.config.ts", "jest.config.mjs", "jest.config.cjs", "jest.config.json"):
            if (root / pattern).is_file():
                return DetectedFramework(
                    name="jest",
                    command="npx jest",
                    coverage_command="npx jest --coverage",
                    watch_command="npx jest --watch",
                    config_file=pattern,
                    confidence=0.95,
                )

        # Check package.json for jest config section
        pkg = self._read_package_json(root)
        if pkg and "jest" in pkg:
            return DetectedFramework(
                name="jest",
                command="npx jest",
                coverage_command="npx jest --coverage",
                watch_command="npx jest --watch",
                config_file="package.json",
                confidence=0.85,
            )

        return None

    def _detect_npm_test(self, root: Path) -> Optional[DetectedFramework]:
        """Detect npm/yarn/bun test script from package.json."""
        pkg = self._read_package_json(root)
        if not pkg:
            return None

        scripts = pkg.get("scripts", {})
        if "test" not in scripts:
            return None

        # Determine package manager
        runner = "npm"
        if (root / "yarn.lock").is_file():
            runner = "yarn"
        elif (root / "bun.lockb").is_file() or (root / "bun.lock").is_file():
            runner = "bun"
        elif (root / "pnpm-lock.yaml").is_file():
            runner = "pnpm"

        scripts["test"]
        return DetectedFramework(
            name=runner,
            command=f"{runner} test",
            coverage_command=f"{runner} test -- --coverage" if runner != "bun" else "bun test --coverage",
            watch_command=f"{runner} test -- --watch" if runner != "bun" else "bun test --watch",
            config_file="package.json",
            confidence=0.75,
        )

    def _detect_go(self, root: Path) -> Optional[DetectedFramework]:
        """Detect Go test from go.mod."""
        if (root / "go.mod").is_file():
            return DetectedFramework(
                name="go",
                command="go test ./...",
                coverage_command="go test ./... -coverprofile=coverage.out && go tool cover -func=coverage.out",
                watch_command=None,
                config_file="go.mod",
                confidence=0.90,
            )
        return None

    def _detect_cargo(self, root: Path) -> Optional[DetectedFramework]:
        """Detect Rust/Cargo test from Cargo.toml."""
        if (root / "Cargo.toml").is_file():
            return DetectedFramework(
                name="cargo",
                command="cargo test",
                coverage_command="cargo tarpaulin --out Stdout",
                watch_command="cargo watch -x test",
                config_file="Cargo.toml",
                confidence=0.90,
            )
        return None

    def _detect_gradle(self, root: Path) -> Optional[DetectedFramework]:
        """Detect Gradle test from build files."""
        for cfg in ("build.gradle", "build.gradle.kts"):
            if (root / cfg).is_file():
                gradlew = "./gradlew" if (root / "gradlew").is_file() else "gradle"
                return DetectedFramework(
                    name="gradle",
                    command=f"{gradlew} test",
                    coverage_command=f"{gradlew} test jacocoTestReport",
                    watch_command=f"{gradlew} test --continuous",
                    config_file=cfg,
                    confidence=0.90,
                )
        return None

    def _detect_maven(self, root: Path) -> Optional[DetectedFramework]:
        """Detect Maven test from pom.xml."""
        if (root / "pom.xml").is_file():
            mvnw = "./mvnw" if (root / "mvnw").is_file() else "mvn"
            return DetectedFramework(
                name="maven",
                command=f"{mvnw} test",
                coverage_command=f"{mvnw} test jacoco:report",
                watch_command=None,
                config_file="pom.xml",
                confidence=0.90,
            )
        return None

    def _detect_mix(self, root: Path) -> Optional[DetectedFramework]:
        """Detect Elixir/Mix test from mix.exs."""
        if (root / "mix.exs").is_file():
            return DetectedFramework(
                name="mix",
                command="mix test",
                coverage_command="mix test --cover",
                watch_command="mix test --stale",
                config_file="mix.exs",
                confidence=0.90,
            )
        return None

    def _detect_rspec(self, root: Path) -> Optional[DetectedFramework]:
        """Detect RSpec from .rspec file or spec/ directory."""
        if (root / ".rspec").is_file():
            return DetectedFramework(
                name="rspec",
                command="bundle exec rspec",
                coverage_command="bundle exec rspec",  # simplecov configured in spec_helper
                watch_command="bundle exec guard",
                config_file=".rspec",
                confidence=0.90,
            )
        if (root / "spec").is_dir() and (root / "Gemfile").is_file():
            return DetectedFramework(
                name="rspec",
                command="bundle exec rspec",
                coverage_command="bundle exec rspec",
                watch_command="bundle exec guard",
                config_file="spec/",
                confidence=0.70,
            )
        return None

    def _detect_make(self, root: Path) -> Optional[DetectedFramework]:
        """Detect Makefile with a test target."""
        makefile = root / "Makefile"
        if not makefile.is_file():
            return None
        content = self._safe_read(makefile)
        # Look for a test: target (at start of line)
        for line in content.splitlines():
            stripped = line.rstrip()
            if stripped == "test:" or stripped.startswith("test:"):
                return DetectedFramework(
                    name="make",
                    command="make test",
                    coverage_command=None,
                    watch_command=None,
                    config_file="Makefile",
                    confidence=0.50,
                )
        return None

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _safe_read(path: Path, max_bytes: int = 64 * 1024) -> str:
        """Read a file safely, returning empty string on failure."""
        try:
            return path.read_text(errors="replace")[:max_bytes]
        except (OSError, UnicodeDecodeError):
            return ""

    @staticmethod
    def _read_package_json(root: Path) -> Optional[Dict]:
        """Read and parse package.json, returning None on failure."""
        pkg_path = root / "package.json"
        if not pkg_path.is_file():
            return None
        try:
            with open(pkg_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _has_package(root: Path, package_name: str) -> bool:
        """Check if a Python package is installed (best-effort)."""
        # Check requirements files
        for req_file in ("requirements.txt", "requirements-dev.txt", "requirements-test.txt"):
            p = root / req_file
            if p.is_file():
                try:
                    content = p.read_text(errors="replace")
                    if package_name in content:
                        return True
                except OSError:
                    pass
        # Check pyproject.toml
        pyproject = root / "pyproject.toml"
        if pyproject.is_file():
            try:
                content = pyproject.read_text(errors="replace")
                if package_name in content:
                    return True
            except OSError:
                pass
        return False
