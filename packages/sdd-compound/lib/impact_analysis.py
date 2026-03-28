"""Change Impact Analysis module.

Given a list of changed files, analyzes:
- Direct imports: who imports these files?
- Test coverage: which tests exercise these files?
- Config dependencies: do any config files reference these?
- Docker services: which services use these files?
- SDD artifacts: any specs/designs that reference these files?

Python 3.9+ compatible.
"""

import os
import re
import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class RiskLevel(str, Enum):
    """Risk classification for a change set."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __lt__(self, other: "RiskLevel") -> bool:
        _order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        return _order.index(self) < _order.index(other)

    def __le__(self, other: "RiskLevel") -> bool:
        return self == other or self < other

    def __gt__(self, other: "RiskLevel") -> bool:
        return not self <= other

    def __ge__(self, other: "RiskLevel") -> bool:
        return not self < other


@dataclass
class ImpactReport:
    """Result of analyzing the impact of a set of changed files."""

    changed_files: List[str] = field(default_factory=list)
    direct_importers: Dict[str, List[str]] = field(default_factory=dict)
    affected_tests: Dict[str, List[str]] = field(default_factory=dict)
    config_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    docker_services: Dict[str, List[str]] = field(default_factory=dict)
    sdd_artifacts: Dict[str, List[str]] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    risk_reasons: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Import detection
# ---------------------------------------------------------------------------

# Patterns for detecting imports in various languages
_IMPORT_PATTERNS = {
    ".go": [
        re.compile(r'"[^"]*?/([^/"]+)"'),  # Go import paths
    ],
    ".ts": [
        re.compile(r"from\s+['\"]\.{0,2}/([^'\"]+)['\"]"),
        re.compile(r"require\s*\(\s*['\"]\.{0,2}/([^'\"]+)['\"]\s*\)"),
    ],
    ".tsx": [
        re.compile(r"from\s+['\"]\.{0,2}/([^'\"]+)['\"]"),
        re.compile(r"require\s*\(\s*['\"]\.{0,2}/([^'\"]+)['\"]\s*\)"),
    ],
    ".js": [
        re.compile(r"from\s+['\"]\.{0,2}/([^'\"]+)['\"]"),
        re.compile(r"require\s*\(\s*['\"]\.{0,2}/([^'\"]+)['\"]\s*\)"),
    ],
    ".py": [
        re.compile(r"from\s+(\S+)\s+import"),
        re.compile(r"import\s+(\S+)"),
    ],
    ".java": [
        re.compile(r"import\s+[\w.]+\.(\w+);"),
    ],
}

# Test file patterns by language
_TEST_PATTERNS = {
    ".go": ["_test.go"],
    ".ts": [".spec.ts", ".test.ts"],
    ".tsx": [".spec.tsx", ".test.tsx"],
    ".js": [".spec.js", ".test.js"],
    ".py": ["test_", "_test.py"],
    ".java": ["Test.java", "Tests.java"],
}

# Config file extensions
_CONFIG_EXTENSIONS = {".yaml", ".yml", ".json", ".toml", ".env", ".ini", ".cfg"}

# High-risk path patterns
_HIGH_RISK_PATHS = [
    "/auth/", "/security/", "/crypto/", "/payment/", "/billing/",
    "/migration/", "/migrate/", "/seeds/",
]

_CRITICAL_RISK_PATHS = [
    "/payment/", "/billing/", "/crypto/", "/encryption/",
    "docker-compose", ".env",
]


def _find_files_by_extension(
    project_dir: str, extensions: Set[str], exclude_dirs: Optional[Set[str]] = None
) -> List[str]:
    """Find all files matching given extensions under project_dir."""
    if exclude_dirs is None:
        exclude_dirs = {
            ".git", "node_modules", "vendor", "__pycache__",
            ".cognitive-os", "dist", "build", ".next",
        }

    results = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext in extensions:
                results.append(os.path.join(root, f))
    return results


def _extract_module_name(filepath: str) -> str:
    """Extract a simplified module/file name from a path for matching."""
    name = os.path.basename(filepath)
    # Remove extension
    name = os.path.splitext(name)[0]
    return name


def find_direct_importers(
    changed_files: List[str], project_dir: str
) -> Dict[str, List[str]]:
    """Find files that import any of the changed files.

    Returns a dict mapping each changed file to a list of files that import it.
    """
    result: Dict[str, List[str]] = {}

    # Build a set of module names from changed files for matching
    changed_modules: Dict[str, str] = {}
    for cf in changed_files:
        module_name = _extract_module_name(cf)
        changed_modules[module_name] = cf
        # Also store the relative path without extension for path-based imports
        rel = os.path.relpath(cf, project_dir)
        rel_no_ext = os.path.splitext(rel)[0]
        changed_modules[rel_no_ext] = cf

    # Get all source files
    source_exts = set(_IMPORT_PATTERNS.keys())
    all_source_files = _find_files_by_extension(project_dir, source_exts)

    for source_file in all_source_files:
        # Skip the changed files themselves
        abs_source = os.path.abspath(source_file)
        if abs_source in {os.path.abspath(cf) for cf in changed_files}:
            continue

        ext = os.path.splitext(source_file)[1]
        patterns = _IMPORT_PATTERNS.get(ext, [])
        if not patterns:
            continue

        try:
            with open(source_file, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except (OSError, IOError):
            continue

        for pattern in patterns:
            for match in pattern.finditer(content):
                imported = match.group(1)
                # Check if the imported module matches any changed file
                imported_base = os.path.basename(imported)
                imported_no_ext = os.path.splitext(imported_base)[0]

                for module_name, changed_file in changed_modules.items():
                    if (
                        imported_no_ext == module_name
                        or imported.endswith(module_name)
                        or module_name.endswith(imported_no_ext)
                    ):
                        if changed_file not in result:
                            result[changed_file] = []
                        rel_source = os.path.relpath(source_file, project_dir)
                        if rel_source not in result[changed_file]:
                            result[changed_file].append(rel_source)

    return result


def find_affected_tests(
    changed_files: List[str], project_dir: str
) -> Dict[str, List[str]]:
    """Find test files that likely exercise the changed files.

    Uses naming conventions and directory proximity to match tests.
    """
    result: Dict[str, List[str]] = {}

    # Collect all test files
    test_files: List[str] = []
    source_exts = set(_IMPORT_PATTERNS.keys())
    all_files = _find_files_by_extension(project_dir, source_exts)

    for f in all_files:
        basename = os.path.basename(f)
        ext = os.path.splitext(f)[1]
        test_suffixes = _TEST_PATTERNS.get(ext, [])
        for suffix in test_suffixes:
            if basename.endswith(suffix) or basename.startswith(suffix):
                test_files.append(f)
                break

    for changed_file in changed_files:
        module_name = _extract_module_name(changed_file)
        changed_dir = os.path.dirname(changed_file)
        matches: List[str] = []

        for test_file in test_files:
            test_basename = os.path.basename(test_file)
            test_dir = os.path.dirname(test_file)

            # Match by name: foo.go -> foo_test.go
            if module_name in test_basename:
                rel = os.path.relpath(test_file, project_dir)
                if rel not in matches:
                    matches.append(rel)
                continue

            # Match by directory proximity (same package/directory)
            if os.path.abspath(test_dir) == os.path.abspath(changed_dir):
                rel = os.path.relpath(test_file, project_dir)
                if rel not in matches:
                    matches.append(rel)

        if matches:
            result[changed_file] = matches

    return result


def find_config_dependencies(
    changed_files: List[str], project_dir: str
) -> Dict[str, List[str]]:
    """Find config files that reference any of the changed files."""
    result: Dict[str, List[str]] = {}

    config_files = _find_files_by_extension(project_dir, _CONFIG_EXTENSIONS)

    # Build search terms from changed files
    search_terms: Dict[str, str] = {}
    for cf in changed_files:
        basename = os.path.basename(cf)
        module = _extract_module_name(cf)
        rel = os.path.relpath(cf, project_dir)
        search_terms[basename] = cf
        search_terms[module] = cf
        search_terms[rel] = cf

    for config_file in config_files:
        try:
            with open(config_file, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except (OSError, IOError):
            continue

        for term, changed_file in search_terms.items():
            if term in content:
                if changed_file not in result:
                    result[changed_file] = []
                rel_config = os.path.relpath(config_file, project_dir)
                if rel_config not in result[changed_file]:
                    result[changed_file].append(rel_config)

    return result


def find_docker_services(
    changed_files: List[str], project_dir: str
) -> Dict[str, List[str]]:
    """Find Docker services that use/build from directories containing changed files."""
    result: Dict[str, List[str]] = {}

    # Find docker-compose files
    compose_files = []
    for f in os.listdir(project_dir):
        if f.startswith("docker-compose") and (f.endswith(".yml") or f.endswith(".yaml")):
            compose_files.append(os.path.join(project_dir, f))

    if not compose_files:
        return result

    for compose_file in compose_files:
        try:
            with open(compose_file, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except (OSError, IOError):
            continue

        # Simple YAML parsing: extract service names and their build contexts
        current_service = None
        services_section = False
        services: Dict[str, str] = {}

        for line in content.split("\n"):
            stripped = line.strip()
            if stripped == "services:":
                services_section = True
                continue
            if services_section and not line.startswith(" ") and not line.startswith("\t") and stripped:
                services_section = False
                continue
            if services_section:
                # Detect service name (2-space indent, no further nesting)
                if re.match(r"^  \S", line) and ":" in stripped:
                    current_service = stripped.split(":")[0].strip()
                # Detect build context
                if current_service and "build:" in stripped:
                    build_ctx = stripped.split("build:")[-1].strip()
                    if build_ctx and build_ctx != "|":
                        services[current_service] = build_ctx
                if current_service and "context:" in stripped:
                    ctx = stripped.split("context:")[-1].strip()
                    if ctx:
                        services[current_service] = ctx

        # Match changed files to services
        for changed_file in changed_files:
            rel = os.path.relpath(changed_file, project_dir)
            for service_name, build_ctx in services.items():
                # Normalize the build context
                ctx_clean = build_ctx.strip("./")
                if rel.startswith(ctx_clean) or ctx_clean in rel:
                    if changed_file not in result:
                        result[changed_file] = []
                    if service_name not in result[changed_file]:
                        result[changed_file].append(service_name)

    return result


def find_sdd_artifacts(
    changed_files: List[str], project_dir: str
) -> Dict[str, List[str]]:
    """Find SDD artifacts (specs, designs, tasks) that reference changed files."""
    result: Dict[str, List[str]] = {}

    # Search in common SDD artifact locations
    sdd_dirs = [
        os.path.join(project_dir, "openspec", "changes"),
        os.path.join(project_dir, ".cognitive-os", "plans"),
    ]

    sdd_files: List[str] = []
    for sdd_dir in sdd_dirs:
        if os.path.isdir(sdd_dir):
            for root, dirs, files in os.walk(sdd_dir):
                for f in files:
                    if f.endswith(".md") or f.endswith(".yaml") or f.endswith(".yml"):
                        sdd_files.append(os.path.join(root, f))

    if not sdd_files:
        return result

    for changed_file in changed_files:
        basename = os.path.basename(changed_file)
        module = _extract_module_name(changed_file)
        rel = os.path.relpath(changed_file, project_dir)

        for sdd_file in sdd_files:
            try:
                with open(sdd_file, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except (OSError, IOError):
                continue

            if basename in content or rel in content or module in content:
                if changed_file not in result:
                    result[changed_file] = []
                rel_sdd = os.path.relpath(sdd_file, project_dir)
                if rel_sdd not in result[changed_file]:
                    result[changed_file].append(rel_sdd)

    return result


def classify_risk(
    changed_files: List[str],
    importers: Dict[str, List[str]],
    tests: Dict[str, List[str]],
    services: Dict[str, List[str]],
) -> Tuple[RiskLevel, List[str]]:
    """Classify the overall risk level of a change set."""
    reasons: List[str] = []
    risk = RiskLevel.LOW

    # Check for critical path patterns
    for cf in changed_files:
        for pattern in _CRITICAL_RISK_PATHS:
            if pattern in cf:
                risk = RiskLevel.CRITICAL
                reasons.append(f"Critical path touched: {pattern} in {os.path.basename(cf)}")

    # Check for high-risk path patterns
    if risk != RiskLevel.CRITICAL:
        for cf in changed_files:
            for pattern in _HIGH_RISK_PATHS:
                if pattern in cf:
                    if risk < RiskLevel.HIGH:
                        risk = RiskLevel.HIGH
                    reasons.append(f"High-risk path touched: {pattern} in {os.path.basename(cf)}")

    # Many importers = high blast radius
    total_importers = sum(len(v) for v in importers.values())
    if total_importers > 10:
        if risk < RiskLevel.HIGH:
            risk = RiskLevel.HIGH
        reasons.append(f"High blast radius: {total_importers} files import changed files")
    elif total_importers > 5:
        if risk < RiskLevel.MEDIUM:
            risk = RiskLevel.MEDIUM
        reasons.append(f"Moderate blast radius: {total_importers} files import changed files")

    # Multiple services affected
    affected_services: Set[str] = set()
    for svc_list in services.values():
        affected_services.update(svc_list)
    if len(affected_services) > 2:
        if risk < RiskLevel.HIGH:
            risk = RiskLevel.HIGH
        reasons.append(f"Cross-service change: {len(affected_services)} services affected")
    elif len(affected_services) > 1:
        if risk < RiskLevel.MEDIUM:
            risk = RiskLevel.MEDIUM
        reasons.append(f"Multi-service change: {len(affected_services)} services affected")

    # No test coverage
    files_without_tests = [cf for cf in changed_files if cf not in tests]
    if files_without_tests and len(files_without_tests) == len(changed_files):
        if risk < RiskLevel.MEDIUM:
            risk = RiskLevel.MEDIUM
        reasons.append(f"No test coverage found for any changed file")
    elif files_without_tests:
        reasons.append(
            f"{len(files_without_tests)}/{len(changed_files)} changed files have no test coverage"
        )

    # Many files changed
    if len(changed_files) > 20:
        if risk < RiskLevel.HIGH:
            risk = RiskLevel.HIGH
        reasons.append(f"Large changeset: {len(changed_files)} files changed")
    elif len(changed_files) > 10:
        if risk < RiskLevel.MEDIUM:
            risk = RiskLevel.MEDIUM
        reasons.append(f"Moderate changeset: {len(changed_files)} files changed")

    if not reasons:
        reasons.append("No elevated risk factors detected")

    return risk, reasons


def analyze_impact(
    changed_files: List[str], project_dir: Optional[str] = None
) -> ImpactReport:
    """Main entry point: analyze the impact of a set of changed files.

    Args:
        changed_files: List of file paths (absolute or relative to project_dir).
        project_dir: Root of the project. Defaults to current working directory.

    Returns:
        ImpactReport with all analysis results.
    """
    if project_dir is None:
        project_dir = os.getcwd()

    # Normalize to absolute paths
    abs_files = []
    for f in changed_files:
        if os.path.isabs(f):
            abs_files.append(f)
        else:
            abs_files.append(os.path.join(project_dir, f))

    report = ImpactReport(changed_files=changed_files)
    report.direct_importers = find_direct_importers(abs_files, project_dir)
    report.affected_tests = find_affected_tests(abs_files, project_dir)
    report.config_dependencies = find_config_dependencies(abs_files, project_dir)
    report.docker_services = find_docker_services(abs_files, project_dir)
    report.sdd_artifacts = find_sdd_artifacts(abs_files, project_dir)
    report.risk_level, report.risk_reasons = classify_risk(
        abs_files, report.direct_importers, report.affected_tests, report.docker_services
    )

    return report


def format_impact_report(report: ImpactReport) -> str:
    """Format an ImpactReport as a human-readable string."""
    lines = []
    lines.append("=" * 60)
    lines.append("CHANGE IMPACT ANALYSIS REPORT")
    lines.append("=" * 60)
    lines.append("")

    # Risk level
    risk_emoji = {
        RiskLevel.LOW: "LOW",
        RiskLevel.MEDIUM: "MEDIUM",
        RiskLevel.HIGH: "HIGH",
        RiskLevel.CRITICAL: "CRITICAL",
    }
    lines.append(f"Risk Level: {risk_emoji[report.risk_level]}")
    lines.append("")
    for reason in report.risk_reasons:
        lines.append(f"  - {reason}")
    lines.append("")

    # Changed files
    lines.append(f"Changed Files ({len(report.changed_files)}):")
    for f in report.changed_files:
        lines.append(f"  - {f}")
    lines.append("")

    # Direct importers
    if report.direct_importers:
        total = sum(len(v) for v in report.direct_importers.values())
        lines.append(f"Direct Importers ({total} files):")
        for changed, importers in report.direct_importers.items():
            basename = os.path.basename(changed)
            lines.append(f"  {basename}:")
            for imp in importers:
                lines.append(f"    - {imp}")
        lines.append("")

    # Affected tests
    if report.affected_tests:
        total = sum(len(v) for v in report.affected_tests.values())
        lines.append(f"Affected Tests ({total} test files):")
        for changed, tests in report.affected_tests.items():
            basename = os.path.basename(changed)
            lines.append(f"  {basename}:")
            for t in tests:
                lines.append(f"    - {t}")
        lines.append("")

    # Config dependencies
    if report.config_dependencies:
        total = sum(len(v) for v in report.config_dependencies.values())
        lines.append(f"Config Dependencies ({total} config files):")
        for changed, configs in report.config_dependencies.items():
            basename = os.path.basename(changed)
            lines.append(f"  {basename}:")
            for c in configs:
                lines.append(f"    - {c}")
        lines.append("")

    # Docker services
    if report.docker_services:
        all_services: Set[str] = set()
        for svcs in report.docker_services.values():
            all_services.update(svcs)
        lines.append(f"Docker Services ({len(all_services)} services):")
        for changed, svcs in report.docker_services.items():
            basename = os.path.basename(changed)
            lines.append(f"  {basename}: {', '.join(svcs)}")
        lines.append("")

    # SDD artifacts
    if report.sdd_artifacts:
        total = sum(len(v) for v in report.sdd_artifacts.values())
        lines.append(f"SDD Artifacts ({total} references):")
        for changed, artifacts in report.sdd_artifacts.items():
            basename = os.path.basename(changed)
            lines.append(f"  {basename}:")
            for a in artifacts:
                lines.append(f"    - {a}")
        lines.append("")

    # Summary
    lines.append("-" * 60)
    lines.append("SUMMARY")
    lines.append(f"  Files changed: {len(report.changed_files)}")
    lines.append(f"  Importers affected: {sum(len(v) for v in report.direct_importers.values())}")
    lines.append(f"  Tests to run: {sum(len(v) for v in report.affected_tests.values())}")
    lines.append(f"  Services impacted: {len({s for svcs in report.docker_services.values() for s in svcs})}")
    lines.append(f"  Risk: {report.risk_level.value.upper()}")
    lines.append("=" * 60)

    return "\n".join(lines)
