"""component_registry.py — Detect unregistered hooks, rules, skills, and packages.

Used by the /register-component skill and registration-check.sh hook to surface
OS components that are missing from the central registration files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

SCOPE = "os-only"


@dataclass
class RegistrationReport:
    hooks: List[str] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    packages: List[str] = field(default_factory=list)

    @property
    def total_unregistered(self) -> int:
        return len(self.hooks) + len(self.rules) + len(self.skills) + len(self.packages)


def _read_file_safe(path: Path) -> str:
    """Return file contents or empty string if unreadable."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def detect_unregistered_hooks(project_dir: str) -> List[str]:
    """Return hook filenames not referenced in scripts/apply-efficiency-profile.sh.

    Excludes scripts inside hooks/_lib/ (helper scripts, not standalone hooks).
    """
    project = Path(project_dir)
    hooks_dir = project / "hooks"
    profile_script = project / "scripts" / "apply-efficiency-profile.sh"

    if not hooks_dir.is_dir():
        return []

    profile_content = _read_file_safe(profile_script)

    unregistered: List[str] = []
    for hook_path in sorted(hooks_dir.iterdir()):
        # Skip directories (e.g. _lib/, _archived/)
        if not hook_path.is_file():
            continue
        # Only look at .sh files
        if hook_path.suffix != ".sh":
            continue
        # Exclude _lib/ helpers
        if hook_path.parent.name == "_lib":
            continue

        filename = hook_path.name
        if filename not in profile_content:
            unregistered.append(filename)

    return unregistered


def detect_unregistered_rules(project_dir: str) -> List[str]:
    """Return rule filenames not referenced in rules/RULES-COMPACT.md.

    Excludes RULES-COMPACT.md itself.
    """
    project = Path(project_dir)
    rules_dir = project / "rules"
    compact = rules_dir / "RULES-COMPACT.md"

    if not rules_dir.is_dir():
        return []

    compact_content = _read_file_safe(compact)

    unregistered: List[str] = []
    for rule_path in sorted(rules_dir.iterdir()):
        if not rule_path.is_file():
            continue
        if rule_path.suffix != ".md":
            continue
        if rule_path.name == "RULES-COMPACT.md":
            continue

        # Derive the ref-key used in RULES-COMPACT (filename without .md)
        ref_key = rule_path.stem  # e.g. "adaptive-bypass"
        filename = rule_path.name  # e.g. "adaptive-bypass.md"

        # Check by ref-key (backtick-bracket form) OR bare filename
        if ref_key not in compact_content and filename not in compact_content:
            unregistered.append(filename)

    return unregistered


def detect_unregistered_skills(project_dir: str) -> List[str]:
    """Return skill directory names not referenced in skills/CATALOG.md.

    Scans both skills/ and .cognitive-os/skills/.
    """
    project = Path(project_dir)
    catalog_path = project / "skills" / "CATALOG.md"
    catalog_content = _read_file_safe(catalog_path)

    skill_dirs_to_scan = [
        project / "skills",
        project / ".cognitive-os" / "skills",
    ]

    unregistered: List[str] = []
    for skills_root in skill_dirs_to_scan:
        if not skills_root.is_dir():
            continue
        for candidate in sorted(skills_root.iterdir()):
            if not candidate.is_dir():
                continue
            skill_md = candidate / "SKILL.md"
            if not skill_md.exists():
                continue
            skill_name = candidate.name
            if skill_name not in catalog_content:
                unregistered.append(skill_name)

    return unregistered


def detect_unregistered_packages(project_dir: str) -> List[str]:
    """Return package directory names not in packages/cos-index/index/packages.yaml."""
    project = Path(project_dir)
    packages_dir = project / "packages"
    index_path = project / "packages" / "cos-index" / "index" / "packages.yaml"

    if not packages_dir.is_dir():
        return []

    index_content = _read_file_safe(index_path)

    unregistered: List[str] = []
    for pkg_path in sorted(packages_dir.iterdir()):
        if not pkg_path.is_dir():
            continue
        cos_pkg_yaml = pkg_path / "cos-package.yaml"
        if not cos_pkg_yaml.exists():
            continue
        pkg_name = pkg_path.name
        # packages.yaml uses path: "packages/{name}" — check both the name and the path form
        if pkg_name not in index_content:
            unregistered.append(pkg_name)

    return unregistered


def detect_all_unregistered(project_dir: str) -> RegistrationReport:
    """Run all four detectors and return an aggregated RegistrationReport."""
    return RegistrationReport(
        hooks=detect_unregistered_hooks(project_dir),
        rules=detect_unregistered_rules(project_dir),
        skills=detect_unregistered_skills(project_dir),
        packages=detect_unregistered_packages(project_dir),
    )


def format_registration_report(report: RegistrationReport) -> str:
    """Return a human-readable registration status report."""
    total = report.total_unregistered
    lines: List[str] = [f"REGISTRATION CHECK: {total} unregistered component(s)"]

    def _section(title: str, items: List[str]) -> None:
        lines.append(f"\n{title}:")
        if items:
            for item in items:
                lines.append(f"  - {item}")
        else:
            lines.append("  (none)")

    _section("Hooks (not in scripts/apply-efficiency-profile.sh)", report.hooks)
    _section("Rules (not in rules/RULES-COMPACT.md)", report.rules)
    _section("Skills (not in skills/CATALOG.md)", report.skills)
    _section("Packages (not in packages/cos-index/index/packages.yaml)", report.packages)

    return "\n".join(lines)
