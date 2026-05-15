"""Contract for agentic primitive classification metadata."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from lib.primitive_parser import parse_primitive_file

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
VALID_SCOPES = {"os-only", "project", "both"}
VALID_AUDIENCES = {"project", "os", "os-dev", "os-only", "both", "adopters", "human"}
PRIMITIVE_ROOTS = {"hooks", "skills", "rules", "templates", "scripts"}


def _header_scope(path: Path) -> str | None:
    header = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:8])
    match = re.search(r"\bSCOPE:\s*([A-Za-z0-9_-]+)", header)
    return match.group(1) if match else None


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    first = text.find("---")
    second = text.find("---", first + 3) if first >= 0 else -1
    assert first >= 0 and second >= 0, f"{path.relative_to(REPO)} must have YAML frontmatter"
    data = yaml.safe_load(text[first + 3 : second]) or {}
    assert isinstance(data, dict), f"{path.relative_to(REPO)} frontmatter must parse as a mapping"
    return data


def _skill_referenced_scripts() -> set[Path]:
    refs: set[Path] = set()
    for skill in (REPO / "skills").glob("*/SKILL.md"):
        text = skill.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"(?<![\w./-])scripts/[A-Za-z0-9_./-]+", text):
            raw = match.group(0).rstrip("`),.:;\"'")
            path = REPO / raw
            if path.is_file() and path.suffix in {".py", ".sh"}:
                refs.add(path)
    return refs


def test_agentic_primitive_roots_have_product_zone_guardrails() -> None:
    manifest = yaml.safe_load((REPO / "manifests" / "product-zones.yaml").read_text(encoding="utf-8"))
    guardrails = {item["root"] for item in manifest["root_guardrails"]}
    missing = sorted(PRIMITIVE_ROOTS - guardrails)
    assert not missing, f"Primitive roots missing root guardrails: {missing}"


def test_hooks_rules_and_templates_declare_valid_scope() -> None:
    paths = (
        list((REPO / "hooks").rglob("*.sh"))
        + list((REPO / "rules").rglob("*.md"))
        + list((REPO / "templates").rglob("*.md"))
    )
    failures = [f"{p.relative_to(REPO)} -> {_header_scope(p)}" for p in paths if _header_scope(p) not in VALID_SCOPES]
    assert not failures, "Invalid or missing SCOPE:\n" + "\n".join(failures)


def test_skills_declare_scope_audience_and_platforms_when_user_invocable() -> None:
    failures: list[str] = []
    for path in sorted((REPO / "skills").glob("*/SKILL.md")):
        rel = path.relative_to(REPO)
        scope = parse_primitive_file(path, REPO).scope_marker
        if scope not in VALID_SCOPES:
            failures.append(f"{rel}: invalid SCOPE {scope!r}")
        data = _frontmatter(path)
        audience = data.get("audience")
        if audience not in VALID_AUDIENCES:
            failures.append(f"{rel}: invalid audience {audience!r}")
        if data.get("user-invocable") is True:
            platforms = data.get("platforms")
            if not isinstance(platforms, list) or not platforms or not all(isinstance(item, str) and item for item in platforms):
                failures.append(f"{rel}: user-invocable skill must declare non-empty platforms list")
    assert not failures, "Skill classification failures:\n" + "\n".join(failures)


def test_skill_referenced_scripts_declare_valid_scope() -> None:
    failures = [f"{p.relative_to(REPO)} -> {_header_scope(p)}" for p in sorted(_skill_referenced_scripts()) if _header_scope(p) not in VALID_SCOPES]
    assert not failures, "Skill-referenced scripts missing valid SCOPE:\n" + "\n".join(failures)


def test_install_scope_contract_proves_project_os_only_and_both_paths() -> None:
    text = (REPO / "tests" / "integration" / "test_install_scope.py").read_text(encoding="utf-8")
    required = ["COS_INSTALL_SCOPE=project", "scope=project", "SCOPE:os-only", "SCOPE:both", "SCOPE:project", "scope=all"]
    missing = [marker for marker in required if marker not in text]
    assert not missing, f"Install/omission proof missing markers: {missing}"
