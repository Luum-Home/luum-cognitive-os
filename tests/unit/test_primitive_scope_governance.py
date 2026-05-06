from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
VALID_SCOPES = {"os-only", "project", "both"}
FAMILIES = ("hooks", "skills", "rules", "scripts", "templates")

SCRIPT_LEDGER_PATH = REPO / "scripts" / "primitive_readiness_ledger.py"
FAMILY_LEDGER_PATH = REPO / "scripts" / "primitive_family_readiness_ledger.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


script_ledger = _load_module("scope_test_script_ledger", SCRIPT_LEDGER_PATH)
family_ledger = _load_module("scope_test_family_ledger", FAMILY_LEDGER_PATH)


def _header_scope(path: Path) -> str | None:
    header = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:8])
    match = re.search(r"\bSCOPE:\s*([A-Za-z0-9_-]+)", header)
    return match.group(1) if match else None


def _write_matrix_fixture(root: Path) -> None:
    for scope in sorted(VALID_SCOPES):
        (root / "hooks").mkdir(parents=True, exist_ok=True)
        (root / "hooks" / f"{scope}.sh").write_text(f"#!/usr/bin/env bash\n# SCOPE: {scope}\necho {scope}\n")

        skill_dir = root / "skills" / scope
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_dir.joinpath("SKILL.md").write_text(
            f"<!-- SCOPE: {scope} -->\n---\nname: {scope}\naudience: {scope if scope == 'project' else 'both'}\n---\nUse this skill.\n"
        )

        (root / "rules").mkdir(parents=True, exist_ok=True)
        (root / "rules" / f"{scope}.md").write_text(f"<!-- SCOPE: {scope} -->\n# {scope}\n\nContextual Trigger: {scope}\n")

        (root / "scripts").mkdir(parents=True, exist_ok=True)
        (root / "scripts" / f"{scope}.py").write_text(f"# SCOPE: {scope}\nprint({scope!r})\n")

        (root / "templates").mkdir(parents=True, exist_ok=True)
        (root / "templates" / f"{scope}.md").write_text(f"<!-- SCOPE: {scope} -->\n# {scope} template\n")


def test_scope_marker_parser_covers_full_family_scope_matrix(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_matrix_fixture(root)

    paths_by_family = {
        "hooks": list((root / "hooks").glob("*.sh")),
        "skills": list((root / "skills").glob("*/SKILL.md")),
        "rules": list((root / "rules").glob("*.md")),
        "scripts": list((root / "scripts").glob("*.py")),
        "templates": list((root / "templates").glob("*.md")),
    }

    observed = {(family, _header_scope(path)) for family, paths in paths_by_family.items() for path in paths}
    expected = {(family, scope) for family in FAMILIES for scope in VALID_SCOPES}
    assert observed == expected


def test_script_ledger_reclassifies_when_skill_consumer_drifts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "runner.py").write_text("# SCOPE: both\nprint('runner')\n")

    before = {row.path: row for row in script_ledger.build_ledger(root)}["scripts/runner.py"]
    assert before.role == "maintainer-tool"
    assert before.role_source == "default"

    skill_dir = root / "skills" / "runner"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text("<!-- SCOPE: both -->\n---\nname: runner\n---\nRun scripts/runner.py\n")

    after = {row.path: row for row in script_ledger.build_ledger(root)}["scripts/runner.py"]
    assert after.role == "agentic-primitive"
    assert after.role_source == "usage:skill"
    assert after.skill_consumers == 1


def test_family_ledger_reclassifies_when_lifecycle_distribution_drifts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "hooks").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)
    (root / "hooks" / "guard.sh").write_text("#!/usr/bin/env bash\n# SCOPE: both\necho guard\n")

    def write_lifecycle(distribution: str, state: str) -> None:
        (root / "manifests" / "primitive-lifecycle.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "primitives": [
                        {
                            "id": "hooks/guard.sh",
                            "kind": "hook",
                            "lifecycle_state": state,
                            "distribution": distribution,
                            "supported_harnesses": ["codex"],
                        }
                    ],
                }
            )
        )

    write_lifecycle("lab", "sandbox")
    lab_row = family_ledger.build_ledger(root, "hooks")[0]
    assert lab_row.role == "lab"
    assert lab_row.consumer_accessibility == "lifecycle-declared-maintainer"

    write_lifecycle("core", "blocking")
    core_row = family_ledger.build_ledger(root, "hooks")[0]
    assert core_row.role == "runtime-safety"
    assert core_row.consumer_accessibility == "projected-consumer-surface"


def test_scope_governance_manifest_defines_reclassification_and_contradictions() -> None:
    manifest = yaml.safe_load((REPO / "manifests" / "primitive-scope-classification.yaml").read_text(encoding="utf-8"))
    assert manifest["id"] == "governance/scope-classification"
    assert set(manifest["allowed_scopes"]) == VALID_SCOPES
    assert set(manifest["families"]) == set(FAMILIES)
    assert {item["id"] for item in manifest["semantic_contradictions"]} == {
        "os-only-projected-to-project",
        "project-or-both-hardcoded-source-repo",
        "both-without-portability-proof",
    }
    assert "consumer reference added or removed" in manifest["drift_reclassification_triggers"]
