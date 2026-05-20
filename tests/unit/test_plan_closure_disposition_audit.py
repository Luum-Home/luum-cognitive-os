from __future__ import annotations

from pathlib import Path

from scripts import plan_closure_disposition_audit as audit


def test_audit_distinguishes_disposition_from_implementation(tmp_path: Path) -> None:
    root = tmp_path
    plan = root / ".cognitive-os" / "plans" / "architecture" / "legacy-plan.md"
    plan.parent.mkdir(parents=True)
    ledger = root / "docs" / "06-Daily" / "reports" / "plan-closure-disposition-2026-05-20.md"
    ledger.parent.mkdir(parents=True)
    successor = root / ".cognitive-os" / "plans" / "architecture" / "implementation-backlog-from-plan-closure-2026-05-20.md"
    successor.write_text("# successor\n", encoding="utf-8")
    plan.write_text(
        "- [x] Worker lease tests implemented. (closed: transferred to headless follow-up; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)\n",
        encoding="utf-8",
    )
    ledger.write_text("## .cognitive-os/plans/architecture/legacy-plan.md\n", encoding="utf-8")

    payload = audit.audit(root)

    assert payload["status"] == "pass"
    assert payload["closed_by_disposition_count"] == 1
    assert payload["rows"][0]["status"] == "transferred"
    assert payload["rows"][0]["findings"] == []


def test_audit_fails_when_disposition_lacks_ledger_proof(tmp_path: Path) -> None:
    root = tmp_path
    plan = root / ".cognitive-os" / "plans" / "architecture" / "legacy-plan.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("- [x] Closed without proof. (closed: transferred elsewhere)\n", encoding="utf-8")

    payload = audit.audit(root)

    assert payload["status"] == "fail"
    findings = {item["finding"] for item in payload["blockers"]}
    assert "missing-disposition-ledger-proof" in findings
    assert "missing-disposition-ledger-file" in findings
    assert "missing-successor-active-plan" in findings
