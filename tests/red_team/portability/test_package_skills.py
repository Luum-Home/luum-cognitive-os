# SCOPE: os-only
"""Aggregate portability proof for package-backed skills.

This is intentionally package-level: package skills are distributed through the
`packages/<package>/skills/<skill>/SKILL.md` surface, and a single aggregate proof
keeps every package skill from collapsing to the unusable `test_SKILL.py` path.
"""

from __future__ import annotations

from pathlib import Path

from lib.primitive_parser import parse_primitive_file

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_SKILLS = sorted((REPO_ROOT / "packages").glob("*/skills/*/SKILL.md"))


def test_package_skill_inventory_is_non_empty() -> None:
    assert PACKAGE_SKILLS, "expected package skill surfaces under packages/*/skills/*/SKILL.md"


def test_package_skills_have_portable_structural_contracts() -> None:
    findings: dict[str, list[str]] = {}
    for skill_path in PACKAGE_SKILLS:
        contract = parse_primitive_file(skill_path, REPO_ROOT)
        if not contract.is_primitive or contract.structural_findings:
            findings[skill_path.relative_to(REPO_ROOT).as_posix()] = list(contract.structural_findings)

    assert findings == {}


def test_package_skills_do_not_require_repo_cwd_for_contract_parsing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    sample = PACKAGE_SKILLS[:10]
    findings: dict[str, list[str]] = {}
    for skill_path in sample:
        contract = parse_primitive_file(skill_path, REPO_ROOT)
        if not contract.is_primitive or contract.structural_findings:
            findings[skill_path.relative_to(REPO_ROOT).as_posix()] = list(contract.structural_findings)

    assert findings == {}
