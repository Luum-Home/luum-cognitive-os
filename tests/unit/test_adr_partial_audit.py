from __future__ import annotations

import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "cos-adr-partial-audit"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_adr_partial_audit_emits_control_plane_findings(tmp_path: Path) -> None:
    write(tmp_path / "docs" / "06-Daily" / "reports" / "adr-partial-backlog-latest.json", json.dumps({
        "schema_version": "adr-partial-backlog/v1",
        "summary": {"total": 1, "by_implementation_status": {"partial": 1}, "missing_partial_remaining": 1},
        "items": [{
            "adr": "ADR-234",
            "path": "docs/02-Decisions/adrs/ADR-234-approval-policies-as-code.md",
            "implementation_status": "partial",
            "date": "2026-01-01",
            "classification_basis": "implemented contract slice",
            "remaining": "implemented contract slice",
            "partial_remaining": "",
            "implementation_files": [],
        }],
    }))
    proc = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(tmp_path), "--json", "--stale-days", "1"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "adr-partial-audit/v1"
    codes = {finding["code"] for finding in payload["findings"]}
    assert "adr-partial-missing-remaining" in codes
    assert "adr-partial-stale-without-followup" in codes


def test_repository_control_plane_manifest_registers_adr_partial_audit() -> None:
    manifest = Path(__file__).resolve().parents[2] / "manifests" / "control-plane-audits.yaml"
    text = manifest.read_text(encoding="utf-8")
    assert "adr-partial-lifecycle" in text
    assert "scripts/cos-adr-partial-audit" in text
    assert "expected_schema: adr-partial-audit/v1" in text
