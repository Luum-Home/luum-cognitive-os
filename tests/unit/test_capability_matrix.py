from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "cos-capability-matrix"
MANIFEST = PROJECT_ROOT / "manifests" / "capability-coverage.yaml"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_matrix(project: Path, manifest: Path, *args: str) -> dict:
    proc = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(project), "--manifest", str(manifest), "--json", *args],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout, proc.stderr
    payload = json.loads(proc.stdout)
    payload["returncode"] = proc.returncode
    return payload


def test_current_capability_matrix_passes_and_covers_recent_adrs() -> None:
    payload = run_matrix(PROJECT_ROOT, MANIFEST)

    assert payload["status"] == "pass"
    assert payload["summary"]["block"] == 0
    assert payload["summary"]["capabilities"] >= 20
    covered = {row["owner_adr"] for row in payload["matrix"]}
    for number in range(230, 253):
        assert f"ADR-{number}" in covered


def test_capability_matrix_blocks_uncovered_accepted_adr(tmp_path: Path) -> None:
    write(tmp_path / "docs/02-Decisions/adrs/ADR-999-demo.md", "# ADR-999\n\n## Status\nAccepted\n")
    manifest = tmp_path / "capabilities.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "capability-coverage/v1",
                "policy": {
                    "adr_coverage": {"min": 999, "max": 999, "require_accepted_or_resolved_adr_covered": True},
                    "public_claim_allowed_levels": ["REAL", "PARTIAL", "RESOLVED"],
                    "real_requires": {"implementation": True, "consumers": True, "tests": True, "receipt_or_audit": True},
                    "generated_outputs": {"matrix_md": "docs/07-Capabilities/capabilities/MATRIX.md", "latest_json": "docs/06-Daily/reports/capability-coverage-latest.json"},
                },
                "capabilities": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    payload = run_matrix(tmp_path, manifest)

    assert payload["status"] == "block"
    assert any(f["code"] == "accepted-adr-uncovered" for f in payload["findings"])


def test_capability_matrix_blocks_real_capability_without_behavioral_evidence(tmp_path: Path) -> None:
    write(tmp_path / "docs/02-Decisions/adrs/ADR-100-demo.md", "# ADR-100\n\n## Status\nAccepted\n")
    write(tmp_path / "lib/demo.py", "")
    manifest = tmp_path / "capabilities.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "capability-coverage/v1",
                "policy": {
                    "adr_coverage": {"min": 100, "max": 100, "require_accepted_or_resolved_adr_covered": True},
                    "public_claim_allowed_levels": ["REAL", "PARTIAL", "RESOLVED"],
                    "real_requires": {"implementation": True, "consumers": True, "tests": True, "receipt_or_audit": True},
                    "generated_outputs": {"matrix_md": "docs/07-Capabilities/capabilities/MATRIX.md", "latest_json": "docs/06-Daily/reports/capability-coverage-latest.json"},
                },
                "capabilities": [
                    {
                        "id": "demo",
                        "label": "Demo",
                        "owner_adr": "ADR-100",
                        "reality_level": "REAL",
                        "public_claim": False,
                        "primitive_types": ["lib"],
                        "implementation": ["lib/demo.py"],
                        "consumers": [],
                        "tests": [],
                        "receipts": [],
                        "control_plane_audits": [],
                        "known_gaps": [],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    payload = run_matrix(tmp_path, manifest)

    assert payload["status"] == "block"
    codes = {f["code"] for f in payload["findings"]}
    assert "real-consumer-missing" in codes
    assert "real-tests-missing" in codes
    assert "real-receipt-or-audit-missing" in codes


def test_capability_matrix_write_and_check_generated_roundtrip(tmp_path: Path) -> None:
    write(tmp_path / "docs/02-Decisions/adrs/ADR-101-demo.md", "# ADR-101\n\n## Status\nAccepted\n")
    write(tmp_path / "lib/demo.py", "")
    write(tmp_path / "tests/test_demo.py", "def test_demo():\n    assert True\n")
    manifest = tmp_path / "capabilities.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "capability-coverage/v1",
                "policy": {
                    "adr_coverage": {"min": 101, "max": 101, "require_accepted_or_resolved_adr_covered": True},
                    "public_claim_allowed_levels": ["REAL", "PARTIAL", "RESOLVED"],
                    "real_requires": {"implementation": True, "consumers": True, "tests": True, "receipt_or_audit": True},
                    "generated_outputs": {"matrix_md": "docs/07-Capabilities/capabilities/MATRIX.md", "latest_json": "docs/06-Daily/reports/capability-coverage-latest.json"},
                },
                "capabilities": [
                    {
                        "id": "demo",
                        "label": "Demo",
                        "owner_adr": "ADR-101",
                        "reality_level": "REAL",
                        "public_claim": False,
                        "primitive_types": ["lib"],
                        "implementation": ["lib/demo.py"],
                        "consumers": ["lib/demo.py"],
                        "tests": ["tests/test_demo.py"],
                        "receipts": ["demo-receipt"],
                        "control_plane_audits": [],
                        "known_gaps": [],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    write_payload = run_matrix(tmp_path, manifest, "--write")
    check_payload = run_matrix(tmp_path, manifest, "--check-generated")

    assert write_payload["status"] == "pass"
    assert check_payload["status"] == "pass"
    assert (tmp_path / "docs/07-Capabilities/capabilities/MATRIX.md").exists()
    assert (tmp_path / "docs/06-Daily/reports/capability-coverage-latest.json").exists()
