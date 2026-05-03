from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from scripts import cos_manifest_tier_claim_audit

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "cos-manifest-tier-claim-audit"


def primitive(
    pid: str,
    *,
    distribution: str,
    lifecycle_state: str = "advisory",
    maturity: str = "advisory",
    runtime_projection: bool = True,
    behavior_evidence: str = "",
    promotion_evidence: dict | None = None,
) -> dict:
    item = {
        "id": pid,
        "kind": "hook",
        "distribution": distribution,
        "lifecycle_state": lifecycle_state,
        "maturity": maturity,
        "governance_class": "runtime-safety" if maturity == "blocking" else "meta-governance",
        "risk_class": "blocking" if maturity == "blocking" else "advisory",
        "runtime_projection": runtime_projection,
        "exit_behavior": "exit_2" if maturity == "blocking" else "exit_0",
        "behavior_evidence": behavior_evidence,
        "evidence_commands": ["bash -n hooks/example.sh"],
    }
    if promotion_evidence is not None:
        item["promotion_evidence"] = promotion_evidence
    return item


def write_manifest(tmp_path: Path, primitives: list[dict]) -> Path:
    path = tmp_path / "primitive-lifecycle.yaml"
    path.write_text(yaml.safe_dump({"primitives": primitives}, sort_keys=False), encoding="utf-8")
    return path


def test_current_manifest_audit_runs_and_reports_candidates() -> None:
    proc = subprocess.run(
        [str(SCRIPT), "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = yaml.safe_load(proc.stdout)
    assert report["status"] in {"pass", "warn"}
    assert "counts_by_category" in report
    assert "candidate_second_demotes" in report


def test_core_advisory_without_strong_evidence_is_lab_candidate(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path,
        [primitive("hooks/noisy-advisory.sh", distribution="core", behavior_evidence="metrics-emitting-advisory")],
    )
    report = cos_manifest_tier_claim_audit.build_report(manifest)
    categories = {finding["category"] for finding in report["findings"]}
    assert "candidate_to_lab_or_advisory" in categories
    assert "candidate_second_demote" in categories


def test_core_blocking_with_promotion_evidence_is_not_flagged(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path,
        [
            primitive(
                "hooks/killer.sh",
                distribution="core",
                lifecycle_state="blocking",
                maturity="blocking",
                behavior_evidence="static-exit2-detected",
                promotion_evidence={"boring_reliability_command": "scripts/cos-boring-reliability --profile core"},
            )
        ],
    )
    report = cos_manifest_tier_claim_audit.build_report(manifest)
    assert report["finding_count"] == 0


def test_maintainer_without_explicit_evidence_is_classified_as_knowledge_dependent(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path,
        [primitive("scripts/maintainer-only", distribution="maintainer", runtime_projection=False, behavior_evidence="control-plane-smoke")],
    )
    report = cos_manifest_tier_claim_audit.build_report(manifest)
    assert report["findings"][0]["category"] == "maintainer_knowledge_dependent"
