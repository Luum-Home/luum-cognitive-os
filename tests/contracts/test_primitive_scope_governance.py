from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
VALID_SCOPES = {"os-only", "project", "both"}
FAMILIES = ("hooks", "skills", "rules", "scripts", "templates")
HARD_CODED_SOURCE_PATTERNS = (str(REPO), "/" + "Users" + "/matias", "/" + "Users" + "/")


def _header_scope(path: Path) -> str | None:
    header = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:8])
    match = re.search(r"\bSCOPE:\s*([A-Za-z0-9_-]+)", header)
    return match.group(1) if match else None


def _family_paths(family: str) -> list[Path]:
    if family == "hooks":
        return [p for p in (REPO / "hooks").rglob("*.sh") if p.is_file()]
    if family == "skills":
        roots = (REPO / "skills", REPO / ".codex" / "skills")
        return [p for root in roots if root.exists() for p in root.rglob("SKILL.md") if p.is_file()]
    if family == "rules":
        return [p for p in (REPO / "rules").rglob("*.md") if p.is_file()]
    if family == "scripts":
        return [p for p in (REPO / "scripts").rglob("*") if p.is_file() and p.suffix in {"", ".py", ".sh", ".js", ".mjs", ".txt"}]
    if family == "templates":
        return [p for p in (REPO / "templates").rglob("*.md") if p.is_file()]
    raise AssertionError(f"unknown family: {family}")


def test_scope_classification_governance_has_lifecycle_and_dedicated_adr() -> None:
    manifest_path = REPO / "manifests" / "primitive-scope-classification.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest["kind"] == "governance-primitive"
    assert manifest["owner_adr"] == "ADR-019"
    assert (REPO / "docs" / "02-Decisions" / "adrs" / "ADR-019-scope-tagging.md").is_file()

    lifecycle = yaml.safe_load((REPO / "manifests" / "primitive-lifecycle.yaml").read_text(encoding="utf-8"))
    rows = {item["id"]: item for item in lifecycle["primitives"]}
    row = rows.get("manifests/primitive-scope-classification.yaml")
    assert row is not None, "scope classification governance primitive must have lifecycle metadata"
    assert row["kind"] == "manifest"
    assert row["lifecycle_state"] in {"blocking", "candidate", "sandbox"}
    assert row["owner_adr"] == manifest["owner_adr"]
    assert "tests/contracts/test_primitive_scope_governance.py" in "\n".join(row["evidence_commands"])


def test_consumer_availability_exact_paths_are_not_nested_under_patterns() -> None:
    manifest = yaml.safe_load((REPO / "manifests" / "primitive-consumer-availability.yaml").read_text(encoding="utf-8"))
    items = manifest.get("items", [])
    patterns = manifest.get("patterns", [])

    misplaced_paths = [row["path"] for row in patterns if isinstance(row, dict) and row.get("path")]
    misplaced_patterns = [row["pattern"] for row in items if isinstance(row, dict) and row.get("pattern")]

    assert not misplaced_paths, "exact consumer-availability rows must live under items, not patterns:\n" + "\n".join(misplaced_paths)
    assert not misplaced_patterns, "pattern consumer-availability rows must live under patterns, not items:\n" + "\n".join(misplaced_patterns)


def test_behavior_evidence_exact_primitives_are_not_nested_under_patterns() -> None:
    manifest = yaml.safe_load((REPO / "manifests" / "primitive-behavior-evidence.yaml").read_text(encoding="utf-8"))
    evidence = manifest.get("evidence", [])
    patterns = manifest.get("patterns", [])

    misplaced_primitives = [row["primitive"] for row in patterns if isinstance(row, dict) and row.get("primitive")]
    misplaced_patterns = [row["pattern"] for row in evidence if isinstance(row, dict) and row.get("pattern")]

    assert not misplaced_primitives, "exact behavior-evidence rows must live under evidence, not patterns:\n" + "\n".join(misplaced_primitives)
    assert not misplaced_patterns, "pattern behavior-evidence rows must live under patterns, not evidence:\n" + "\n".join(misplaced_patterns)


@pytest.mark.timeout(180)
def test_every_family_has_regenerable_or_contract_classification_surface() -> None:
    manifest = yaml.safe_load((REPO / "manifests" / "primitive-scope-classification.yaml").read_text(encoding="utf-8"))
    coverage = {family: meta["coverage"] for family, meta in manifest["families"].items()}
    assert coverage == {
        "hooks": "primitive_family_readiness_ledger",
        "skills": "primitive_family_readiness_ledger",
        "rules": "primitive_family_readiness_ledger",
        "scripts": "primitive_readiness_ledger",
        "templates": "scope_contract",
    }

    script_result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "primitive_readiness_ledger.py"), "--project-dir", str(REPO)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert script_result.returncode == 0, script_result.stderr + script_result.stdout
    scripts_report = json.loads((REPO / "docs" / "06-Daily" / "reports" / "primitive-readiness-ledger-scripts-latest.json").read_text())
    assert scripts_report["target_family"] == "scripts"
    assert scripts_report["summary"]["total_scripts"] > 0

    for family in ("hooks", "skills", "rules"):
        result = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "primitive_family_readiness_ledger.py"), "--project-dir", str(REPO), "--target-family", family],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr + result.stdout
        payload = json.loads((REPO / "docs" / "06-Daily" / "reports" / f"primitive-readiness-ledger-{family}-latest.json").read_text())
        assert payload["target_family"] == family
        assert payload["summary"]["total"] == len(_family_paths(family))

    template_failures = [str(p.relative_to(REPO)) for p in _family_paths("templates") if _header_scope(p) not in VALID_SCOPES]
    assert not template_failures, "templates rely on scope_contract and must declare valid scope:\n" + "\n".join(template_failures)


@pytest.mark.parametrize("family", FAMILIES)
def test_repository_scope_markers_are_valid_when_present(family: str) -> None:
    invalid = []
    for path in _family_paths(family):
        scope = _header_scope(path)
        if scope is not None and scope not in VALID_SCOPES:
            invalid.append(f"{path.relative_to(REPO)} -> {scope}")
    assert not invalid, "invalid scope markers:\n" + "\n".join(invalid)


def test_project_and_both_primitives_do_not_embed_source_checkout_paths() -> None:
    failures = []
    for family in FAMILIES:
        for path in _family_paths(family):
            scope = _header_scope(path)
            if scope not in {"project", "both"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if any(pattern in text for pattern in HARD_CODED_SOURCE_PATTERNS):
                failures.append(str(path.relative_to(REPO)))
    assert not failures, "project/both primitives must not hardcode source checkout or developer-home paths:\n" + "\n".join(failures)


@pytest.mark.parametrize("harness", ["claude", "codex", "shell-ci"])
def test_default_consumer_projection_contains_no_os_only_markers(tmp_path: Path, harness: str) -> None:
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "cos_init.py"), "--default", "--harness", harness],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr + result.stdout

    projected_roots = [tmp_path / ".cognitive-os", tmp_path / ".claude", tmp_path / ".codex", tmp_path / "scripts"]
    projected_files = [p for root in projected_roots if root.exists() for p in root.rglob("*") if p.is_file()]
    offenders = []
    for path in projected_files:
        try:
            header = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:8])
        except OSError:
            continue
        if re.search(r"\bSCOPE:\s*os-only\b", header):
            offenders.append(str(path.relative_to(tmp_path)))
    assert not offenders, f"{harness} default consumer projection includes os-only primitives:\n" + "\n".join(offenders)
