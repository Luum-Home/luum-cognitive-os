"""Tests for lib/component_registry.py — component registration detection."""

import pytest
from pathlib import Path

from lib.component_registry import (
    RegistrationReport,
    detect_all_unregistered,
    detect_unregistered_hooks,
    detect_unregistered_packages,
    detect_unregistered_rules,
    detect_unregistered_skills,
    format_registration_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_profile_script(tmp_path: Path, hooks: list[str]) -> Path:
    """Write a minimal apply-efficiency-profile.sh that references the given hook names."""
    content = "#!/usr/bin/env bash\n# apply-efficiency-profile.sh\n"
    for h in hooks:
        content += f'hook_entry "{h}"\n'
    p = tmp_path / "scripts" / "apply-efficiency-profile.sh"
    _write(p, content)
    return p


def _make_compact(tmp_path: Path, ref_keys: list[str]) -> Path:
    """Write a minimal RULES-COMPACT.md that references the given ref-keys."""
    lines = ["# COS Rules Index\n"]
    for k in ref_keys:
        lines.append(f"[`{k}`]\n")
    p = tmp_path / "rules" / "RULES-COMPACT.md"
    _write(p, "".join(lines))
    return p


def _make_catalog(tmp_path: Path, skill_names: list[str]) -> Path:
    """Write a minimal CATALOG.md that references the given skill names."""
    lines = ["# Catalog\n", "| Skill | Description | Invoke | Audience |\n"]
    for name in skill_names:
        lines.append(f"| {name} | desc | `/cmd` | both |\n")
    p = tmp_path / "skills" / "CATALOG.md"
    _write(p, "".join(lines))
    return p


def _make_packages_yaml(tmp_path: Path, pkg_names: list[str]) -> Path:
    """Write a minimal packages.yaml that references the given package names."""
    lines = ["packages:\n"]
    for name in pkg_names:
        lines.append(f'  - name: "@luum/{name}"\n')
        lines.append(f'    path: "packages/{name}"\n')
    p = tmp_path / "packages" / "cos-index" / "index" / "packages.yaml"
    _write(p, "".join(lines))
    return p


# ---------------------------------------------------------------------------
# R1 — detect_unregistered_hooks: new hook NOT in profile → flagged
# ---------------------------------------------------------------------------

def test_detects_unregistered_hook(tmp_path):
    _write(tmp_path / "hooks" / "new-hook.sh", "#!/usr/bin/env bash\n")
    _make_profile_script(tmp_path, hooks=[])  # does NOT mention new-hook.sh

    result = detect_unregistered_hooks(str(tmp_path))
    assert "new-hook.sh" in result


# ---------------------------------------------------------------------------
# R2 — detect_unregistered_hooks: existing hook IN profile → NOT flagged
# ---------------------------------------------------------------------------

def test_registered_hook_not_flagged(tmp_path):
    _write(tmp_path / "hooks" / "existing.sh", "#!/usr/bin/env bash\n")
    _make_profile_script(tmp_path, hooks=["existing.sh"])

    result = detect_unregistered_hooks(str(tmp_path))
    assert "existing.sh" not in result


# ---------------------------------------------------------------------------
# R3 — detect_unregistered_rules: new rule NOT in RULES-COMPACT → flagged
# ---------------------------------------------------------------------------

def test_detects_unregistered_rule(tmp_path):
    _write(tmp_path / "rules" / "new-rule.md", "# New Rule\n")
    _make_compact(tmp_path, ref_keys=[])  # does NOT mention new-rule

    result = detect_unregistered_rules(str(tmp_path))
    assert "new-rule.md" in result


# ---------------------------------------------------------------------------
# R4 — detect_unregistered_skills: new skill NOT in CATALOG → flagged
# ---------------------------------------------------------------------------

def test_detects_unregistered_skill(tmp_path):
    _write(tmp_path / "skills" / "new-skill" / "SKILL.md", "---\nname: new-skill\n---\n")
    _make_catalog(tmp_path, skill_names=[])  # does NOT mention new-skill

    result = detect_unregistered_skills(str(tmp_path))
    assert "new-skill" in result


# ---------------------------------------------------------------------------
# R5 — detect_unregistered_packages: new package NOT in packages.yaml → flagged
# ---------------------------------------------------------------------------

def test_detects_unregistered_package(tmp_path):
    _write(tmp_path / "packages" / "new-pkg" / "cos-package.yaml", "name: '@luum/new-pkg'\n")
    _make_packages_yaml(tmp_path, pkg_names=[])  # does NOT mention new-pkg

    result = detect_unregistered_packages(str(tmp_path))
    assert "new-pkg" in result


# ---------------------------------------------------------------------------
# R6 — detect_all_unregistered: aggregates all four detectors
# ---------------------------------------------------------------------------

def test_detect_all_unregistered_aggregates(tmp_path):
    # Create one unregistered item of each type
    _write(tmp_path / "hooks" / "orphan-hook.sh", "#!/usr/bin/env bash\n")
    _make_profile_script(tmp_path, hooks=[])

    _write(tmp_path / "rules" / "orphan-rule.md", "# Orphan\n")
    _make_compact(tmp_path, ref_keys=[])

    _write(tmp_path / "skills" / "orphan-skill" / "SKILL.md", "---\nname: orphan-skill\n---\n")
    _make_catalog(tmp_path, skill_names=[])

    _write(tmp_path / "packages" / "orphan-pkg" / "cos-package.yaml", "name: '@luum/orphan-pkg'\n")
    _make_packages_yaml(tmp_path, pkg_names=[])

    report = detect_all_unregistered(str(tmp_path))
    assert report.total_unregistered == 4
    assert "orphan-hook.sh" in report.hooks
    assert "orphan-rule.md" in report.rules
    assert "orphan-skill" in report.skills
    assert "orphan-pkg" in report.packages


# ---------------------------------------------------------------------------
# R7 — detect_all_unregistered: everything registered → total == 0
# ---------------------------------------------------------------------------

def test_all_registered_returns_zero(tmp_path):
    _write(tmp_path / "hooks" / "known.sh", "#!/usr/bin/env bash\n")
    _make_profile_script(tmp_path, hooks=["known.sh"])

    _write(tmp_path / "rules" / "known-rule.md", "# Known\n")
    _make_compact(tmp_path, ref_keys=["known-rule"])

    _write(tmp_path / "skills" / "known-skill" / "SKILL.md", "---\nname: known-skill\n---\n")
    _make_catalog(tmp_path, skill_names=["known-skill"])

    _write(tmp_path / "packages" / "known-pkg" / "cos-package.yaml", "name: '@luum/known-pkg'\n")
    _make_packages_yaml(tmp_path, pkg_names=["known-pkg"])

    report = detect_all_unregistered(str(tmp_path))
    assert report.total_unregistered == 0


# ---------------------------------------------------------------------------
# R8 — detect_unregistered_hooks: _lib/ helper scripts excluded
# ---------------------------------------------------------------------------

def test_excludes_lib_helpers_from_hooks(tmp_path):
    _write(tmp_path / "hooks" / "_lib" / "common.sh", "#!/usr/bin/env bash\n")
    _make_profile_script(tmp_path, hooks=[])  # _lib/common.sh is NOT listed, but should be ignored

    result = detect_unregistered_hooks(str(tmp_path))
    # common.sh lives in hooks/_lib/, not directly in hooks/ — excluded
    assert "common.sh" not in result


# ---------------------------------------------------------------------------
# format_registration_report smoke test
# ---------------------------------------------------------------------------

def test_format_registration_report_structure():
    report = RegistrationReport(
        hooks=["new-hook.sh"],
        rules=["new-rule.md"],
        skills=["new-skill"],
        packages=["new-pkg"],
    )
    output = format_registration_report(report)
    assert "REGISTRATION CHECK: 4" in output
    assert "new-hook.sh" in output
    assert "new-rule.md" in output
    assert "new-skill" in output
    assert "new-pkg" in output


def test_format_registration_report_zero():
    report = RegistrationReport()
    output = format_registration_report(report)
    assert "REGISTRATION CHECK: 0" in output
    assert "(none)" in output
