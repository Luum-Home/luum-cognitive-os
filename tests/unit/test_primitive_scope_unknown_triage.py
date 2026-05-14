from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_scope_unknown_triage.py"
spec = importlib.util.spec_from_file_location("primitive_scope_unknown_triage", MODULE_PATH)
assert spec and spec.loader
primitive_scope_unknown_triage = importlib.util.module_from_spec(spec)
sys.modules["primitive_scope_unknown_triage"] = primitive_scope_unknown_triage
spec.loader.exec_module(primitive_scope_unknown_triage)


def write_report(root: Path, rows: list[dict]) -> None:
    report_dir = root / ".cognitive-os" / "reports"
    report_dir.mkdir(parents=True)
    (report_dir / "primitive-scope-classifier.json").write_text(json.dumps({"rows": rows}))


def test_unknown_triage_groups_declared_both_os_internal_heavy(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    primitive = root / "rules" / "startup-protocol.md"
    primitive.parent.mkdir(parents=True)
    primitive.write_text("# Startup\nUse .cognitive-os/ metrics and manifests/primitive-lifecycle.yaml for ADR-314 governance.\n")
    write_report(
        root,
        [
            {
                "path": "rules/startup-protocol.md",
                "declared_scope": "both",
                "suggested_scope": "unknown",
                "decision_source": "insufficient-evidence",
                "evidence": [],
                "paired_proof": None,
                "next_action": "add metadata",
            }
        ],
    )

    triage = primitive_scope_unknown_triage.build_triage(root)

    assert triage["summary"]["total_unknown"] == 1
    assert triage["rows"][0]["bucket"] == "declared-both-os-internal-heavy"
    assert "declared-both-missing-paired-proof" in triage["rows"][0]["gap_tags"]
    assert "rule-missing-scope-marker" in triage["rows"][0]["structural_findings"]


def test_unknown_triage_accepts_classifier_paired_portability_test_key(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    primitive = root / "hooks" / "_lib" / "bypass-resolver.sh"
    primitive.parent.mkdir(parents=True)
    primitive.write_text("#!/usr/bin/env bash\n# SCOPE: both\n# Uses .cognitive-os/ and manifests/ for bypass governance.\n")
    write_report(
        root,
        [
            {
                "path": "hooks/_lib/bypass-resolver.sh",
                "declared_scope": "both",
                "suggested_scope": "unknown",
                "decision_source": "insufficient-evidence",
                "evidence": [],
                "paired_portability_test": "tests/red_team/portability/test_bypass-resolver.py",
                "next_action": "add metadata",
            }
        ],
    )

    triage = primitive_scope_unknown_triage.build_triage(root)

    row = triage["rows"][0]
    assert "declared-both-missing-paired-proof" not in row["gap_tags"]
    assert row["bucket"] == "os-only-semantic-candidate"


def test_unknown_triage_groups_project_only_candidate(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    primitive = root / "scripts" / "project_scaffold.py"
    primitive.parent.mkdir(parents=True)
    primitive.write_text("# SCOPE: project\n# scaffold target project\nparser.add_argument('--project-dir')\n")
    write_report(
        root,
        [
            {
                "path": "scripts/project_scaffold.py",
                "declared_scope": "project",
                "suggested_scope": "unknown",
                "decision_source": "insufficient-evidence",
                "evidence": [],
                "paired_proof": None,
                "next_action": "add metadata",
            }
        ],
    )

    triage = primitive_scope_unknown_triage.build_triage(root)

    assert triage["rows"][0]["bucket"] == "project-only-semantic-candidate"
    assert triage["summary"]["by_bucket"] == {"project-only-semantic-candidate": 1}


def test_unknown_triage_preserves_conflicting_metadata(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    primitive = root / "scripts" / "status.py"
    primitive.parent.mkdir(parents=True)
    primitive.write_text("# status tool\n")
    write_report(
        root,
        [
            {
                "path": "scripts/status.py",
                "declared_scope": "project",
                "suggested_scope": "unknown",
                "decision_source": "conflicting-distribution-evidence",
                "evidence": [
                    {"source": "consumer-availability", "scope": "os-only", "weight": 80, "detail": "maintainer-only"},
                    {"source": "lifecycle", "scope": "project", "weight": 60, "detail": "consumer candidate"},
                ],
                "paired_proof": None,
                "next_action": "resolve conflict",
            }
        ],
    )

    triage = primitive_scope_unknown_triage.build_triage(root)

    assert triage["rows"][0]["bucket"] == "conflicting-metadata"
    assert "conflicting-distribution-evidence" in triage["rows"][0]["gap_tags"]


def test_unknown_triage_uses_parser_structural_findings(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    primitive = root / "rules" / "thin.md"
    primitive.parent.mkdir(parents=True)
    primitive.write_text("# Thin\n\nBody only.\n")
    write_report(
        root,
        [
            {
                "path": "rules/thin.md",
                "declared_scope": None,
                "suggested_scope": "unknown",
                "decision_source": "insufficient-evidence",
                "evidence": [],
                "paired_proof": None,
                "next_action": "add metadata",
            }
        ],
    )

    triage = primitive_scope_unknown_triage.build_triage(root)

    row = triage["rows"][0]
    assert row["bucket"] == "missing-scope-marker"
    assert "rule-missing-opening-section" in row["structural_findings"]
    assert "rule-missing-contextual-trigger" in row["gap_tags"]
    assert row["semantic_hints"]["kind"] == "rule"
