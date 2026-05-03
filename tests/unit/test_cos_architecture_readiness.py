from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import scripts.cos_architecture_readiness as readiness


def test_build_report_warns_for_known_wiring_gaps(tmp_path: Path) -> None:
    for rels in readiness.REQUIRED_RUNTIME_PRIMITIVES.values():
        for rel in rels:
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x", encoding="utf-8")
    (tmp_path / ".cognitive-os/runtime").mkdir(parents=True)

    with patch.object(readiness, "run_git_stash_list", return_value=[]), \
         patch.object(readiness, "check_adoption_tiers", return_value=readiness.Check("adoption", "pass", "ok")), \
         patch.object(readiness, "check_lifecycle_manifest", return_value=readiness.Check("lifecycle", "pass", "ok")), \
         patch.object(readiness, "check_active_surface", return_value=readiness.Check("active-surface", "pass", "ok")), \
         patch.object(readiness, "check_runtime_hook_reality", return_value=readiness.Check("runtime-hook-reality", "pass", "ok")), \
         patch.object(readiness, "check_core_session_start_budget", return_value=readiness.Check("core-session-start-budget", "pass", "ok")), \
         patch.object(readiness, "check_roi", return_value=readiness.Check("roi", "pass", "ok")), \
         patch.object(readiness, "check_lifecycle_recommendations", return_value=readiness.Check("demotion", "pass", "ok")), \
         patch.object(readiness, "check_product_claims", return_value=readiness.Check("product", "pass", "ok")), \
         patch.object(readiness, "check_governance_maturity_labels", return_value=readiness.Check("maturity", "pass", "ok")):
        report = readiness.build_report(tmp_path, 24)

    assert report["status"] == "warn"
    assert report["warn_count"] == 1
    assert any(check["id"] == "known-wiring-gaps" for check in report["checks"])


def test_missing_runtime_primitive_fails(tmp_path: Path) -> None:
    check = readiness.check_runtime_primitives(tmp_path)
    assert check.status == "fail"
    assert "branch_writer_lease" in check.details["missing"]


def test_json_report_is_serializable(tmp_path: Path) -> None:
    check = readiness.Check("x", "pass", "ok", {"items": [1, 2]})
    encoded = json.dumps({"checks": [check.__dict__]})
    assert '"status": "pass"' in encoded


def test_lifecycle_recommendations_check_reports_candidates(tmp_path: Path) -> None:
    recommendation = {"primitive_id": "x", "action": "demote", "reason": "test", "severity": "warn"}
    with patch.object(readiness.cos_governance_roi, "build_report", return_value={"roi": {"status": "negative"}}), \
         patch.object(readiness.primitive_lifecycle, "build_report", return_value={"recommendations": [recommendation]}):
        check = readiness.check_lifecycle_recommendations(tmp_path, 24)

    assert check.status == "pass"
    assert check.details["recommendation_count"] == 1
    assert check.details["recommendations"] == [recommendation]


def test_active_surface_check_reports_counts_by_tier(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    manifest_dir.joinpath("primitive-lifecycle.yaml").write_text(
        """schema_version: 1
primitives:
  - id: hooks/core
    kind: hook
    owner_adr: ADR-127
    lifecycle_state: blocking
    maturity: blocking
    distribution: core
    governance_class: runtime-safety
    risk_class: blocking
    supported_harnesses: [codex]
    projection_targets: [.codex/hooks.json]
    evidence_commands: [python3 -m pytest tests/unit/test_cos_architecture_readiness.py -q]
    rollback_or_repair_command: disable hook
    sunset_criteria: archive after replacement
  - id: scripts/lab
    kind: script
    owner_adr: ADR-127
    lifecycle_state: sandbox
    maturity: observe
    distribution: lab
    governance_class: meta-governance
    risk_class: advisory
    supported_harnesses: [shell]
    projection_targets: [scripts/lab]
    evidence_commands: [python3 -m pytest tests/unit/test_cos_architecture_readiness.py -q]
    rollback_or_repair_command: leave in lab
    sunset_criteria: archive after no use
""",
        encoding="utf-8",
    )

    check = readiness.check_active_surface(tmp_path)

    assert check.status == "pass"
    assert check.details["counts_by_tier"]["core"] == 1
    assert check.details["counts_by_tier"]["lab"] == 1
    assert check.details["active_counts_by_tier"]["lab"] == 0
    assert check.details["default_visible_count"] == 1


def test_readiness_report_includes_active_surface(tmp_path: Path) -> None:
    for rels in readiness.REQUIRED_RUNTIME_PRIMITIVES.values():
        for rel in rels:
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x", encoding="utf-8")
    (tmp_path / ".cognitive-os/runtime").mkdir(parents=True)

    with patch.object(readiness, "run_git_stash_list", return_value=[]), \
         patch.object(readiness, "check_adoption_tiers", return_value=readiness.Check("adoption", "pass", "ok")), \
         patch.object(readiness, "check_lifecycle_manifest", return_value=readiness.Check("lifecycle", "pass", "ok")), \
         patch.object(readiness, "check_active_surface", return_value=readiness.Check("active-primitive-surface", "pass", "ok", {"counts_by_tier": {"core": 1}})), \
         patch.object(readiness, "check_runtime_hook_reality", return_value=readiness.Check("runtime-hook-reality", "pass", "ok")), \
         patch.object(readiness, "check_core_session_start_budget", return_value=readiness.Check("core-session-start-budget", "pass", "ok")), \
         patch.object(readiness, "check_roi", return_value=readiness.Check("roi", "pass", "ok")), \
         patch.object(readiness, "check_lifecycle_recommendations", return_value=readiness.Check("demotion", "pass", "ok")), \
         patch.object(readiness, "check_product_claims", return_value=readiness.Check("product", "pass", "ok")), \
         patch.object(readiness, "check_governance_maturity_labels", return_value=readiness.Check("maturity", "pass", "ok")):
        report = readiness.build_report(tmp_path, 24)

    assert any(check["id"] == "active-primitive-surface" for check in report["checks"])


def test_product_claims_fail_missing_readme_hook_claim(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("`missing-hook.sh` blocks bad claims\n", encoding="utf-8")

    check = readiness.check_product_claims(tmp_path)

    assert check.status == "fail"
    assert check.details["findings"][0]["id"] == "readme-missing-shell-claim"


def test_product_claims_fail_stale_model_readiness_naming(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "business"
    docs.mkdir(parents=True)
    docs.joinpath("x.md").write_text("Run cos-opus-readiness for the Opus critique.\n", encoding="utf-8")

    check = readiness.check_product_claims(tmp_path)

    assert check.status == "fail"
    assert any(finding["id"] == "stale-model-branded-product-copy" for finding in check.details["findings"])


def test_governance_maturity_labels_require_trust_and_blast(tmp_path: Path) -> None:
    manifest = tmp_path / "manifests" / "primitive-lifecycle.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """schema_version: 1
primitives:
  - id: hooks/trust-score-validator.sh
    maturity: advisory
  - id: hooks/blast-radius.sh
    maturity: observe
""",
        encoding="utf-8",
    )

    check = readiness.check_governance_maturity_labels(tmp_path)

    assert check.status == "pass"
    assert check.details["missing"] == []
    assert check.details["contradictions"] == []


def test_governance_maturity_labels_fail_on_duplicate_overlay(tmp_path: Path) -> None:
    manifest = tmp_path / "manifests" / "primitive-lifecycle.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """schema_version: 1
primitives:
  - id: hooks/trust-score-validator.sh
    maturity: advisory
  - id: hooks/blast-radius.sh
    maturity: observe
""",
        encoding="utf-8",
    )
    overlay = tmp_path / "manifests" / "governance-maturity.yaml"
    overlay.write_text("schema_version: 1\nprimitives: []\n", encoding="utf-8")

    check = readiness.check_governance_maturity_labels(tmp_path)

    assert check.status == "fail"
    assert check.details["contradictions"] == ["manifests/governance-maturity.yaml"]


def test_runtime_hook_reality_check_passes_with_clean_report(tmp_path: Path) -> None:
    report = {
        "summary": {"status": "pass", "counts": {"real_blocking": 1}},
        "findings": [],
    }
    with patch.object(readiness.runtime_hook_reality, "build_report", return_value=report):
        check = readiness.check_runtime_hook_reality(tmp_path)

    assert check.status == "pass"
    assert check.details["summary"] == report["summary"]


def test_runtime_hook_reality_check_fails_on_findings(tmp_path: Path) -> None:
    report = {
        "summary": {"status": "fail", "counts": {}},
        "findings": [{"id": "blocking-hook-without-exit2", "hook": "hooks/x.sh"}],
    }
    with patch.object(readiness.runtime_hook_reality, "build_report", return_value=report):
        check = readiness.check_runtime_hook_reality(tmp_path)

    assert check.status == "fail"
    assert check.details["findings"] == report["findings"]


def test_core_session_start_budget_check_fails_lab_hooks(tmp_path: Path) -> None:
    report = {
        "profile": "core",
        "session_start_hook_count": 4,
        "counts_by_tier": {"core": 3, "lab": 1, "team": 0, "maintainer": 0, "unknown": 0},
        "budget": {"max_session_start_hooks": 5, "allow_lab": False},
        "findings": [{"id": "core-session-start-lab-hooks", "severity": "fail"}],
        "candidates_to_move": [],
        "fail_count": 1,
    }
    with patch.object(readiness.session_start_budget, "build_report", return_value=report):
        check = readiness.check_core_session_start_budget(tmp_path)

    assert check.status == "fail"
    assert check.details["findings"][0]["id"] == "core-session-start-lab-hooks"
