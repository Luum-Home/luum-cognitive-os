from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAIM_PATH = ROOT / "scripts" / "claim_proof_audit.py"
BACKLOG_PATH = ROOT / "scripts" / "reduction_backlog.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


claim_proof_audit = load_module("claim_proof_audit", CLAIM_PATH)
reduction_backlog = load_module("reduction_backlog", BACKLOG_PATH)


def make_claim_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "docs" / "business").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "tests").mkdir()
    (root / "README.md").write_text(
        "# Product\n\nAutomatically prevents duplicate docs with 77% token reduction.\n\n"
        "```yaml\n- productionChanges\n# auto-executes setup\n```\n"
    )
    (root / "docs" / "README.md").write_text("# Docs\n")
    (root / "docs" / "business" / "features.md").write_text("The system always blocks unsafe writes.\n")
    (root / "scripts" / "docs_duplicate_audit.py").write_text("# duplicate docs prevention\n")
    (root / "tests" / "test_docs_duplicate_audit.py").write_text("def test_duplicate_docs(): pass\n")
    return root


def test_claim_proof_marks_claims_by_available_evidence(tmp_path: Path) -> None:
    root = make_claim_repo(tmp_path)

    rows = claim_proof_audit.audit(root)

    assert rows
    assert any(row.status in {"weak-proof", "mapped"} for row in rows)
    assert any("77%" in row.claim and row.status != "mapped" for row in rows)
    assert all("productionChanges" not in row.claim for row in rows)


def test_claim_proof_cli_writes_reports(tmp_path: Path) -> None:
    root = make_claim_repo(tmp_path)

    result = subprocess.run([sys.executable, str(CLAIM_PATH), "--project-dir", str(root)], text=True, capture_output=True)

    assert result.returncode == 0, result.stderr
    assert (root / "docs" / "reports" / "claim-proof-latest.json").exists()
    assert "Claims Needing Work" in (root / "docs" / "reports" / "claim-proof-latest.md").read_text()


def test_claim_proof_cli_fail_unmapped_blocks_unproven_claim(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("Always guarantees autonomous unicorn remediation.\n")
    (root / "docs").mkdir()
    (root / "docs" / "README.md").write_text("# Docs\n")

    result = subprocess.run(
        [sys.executable, str(CLAIM_PATH), "--project-dir", str(root), "--fail-unmapped"],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2


def test_reduction_backlog_uses_row_and_claim_audits(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    reports = root / "docs" / "reports"
    reports.mkdir(parents=True)
    (reports / "primitive-row-audit-latest.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "family": "hooks",
                        "path": "hooks/orphan.sh",
                        "status": "aspirational",
                        "severity": "high",
                        "evidence": "unregistered",
                        "next_action": "delete",
                    }
                ]
            }
        )
    )
    (reports / "claim-proof-latest.json").write_text(
        json.dumps({"rows": [{"status": "unmapped", "path": "README.md", "line": 3, "claim": "Always automatic"}]})
    )

    result = subprocess.run([sys.executable, str(BACKLOG_PATH), "--project-dir", str(root)], text=True, capture_output=True)

    assert result.returncode == 0, result.stderr
    payload = json.loads((reports / "reduction-backlog-latest.json").read_text())
    assert [item["action"] for item in payload["items"]] == ["delete-or-wire", "demote-or-prove-claim"]
    assert "Reduction Sprint Backlog" in (reports / "reduction-backlog-latest.md").read_text()
