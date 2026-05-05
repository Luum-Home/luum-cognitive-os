from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "proof-drill-evidence-record"


def test_records_and_upserts_proof_drill_evidence(tmp_path: Path) -> None:
    out = tmp_path / "proof.json"
    args = [
        str(SCRIPT),
        "--id", "demo-drill",
        "--status", "passed",
        "--scope", "os-self",
        "--command", "echo ok",
        "--exit-code", "0",
        "--artifact", "artifact/path",
        "--proves", "demo proof",
        "--does-not-prove", "everything else",
        "--out", str(out),
        "--json",
    ]
    first = subprocess.run(args, cwd=REPO, text=True, capture_output=True, check=False)
    assert first.returncode == 0, first.stderr + first.stdout
    second = subprocess.run(args, cwd=REPO, text=True, capture_output=True, check=False)
    assert second.returncode == 0, second.stderr + second.stdout

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "proof-drill-evidence.v1"
    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["id"] == "demo-drill"
    assert payload["rows"][0]["evidence_artifacts"] == ["artifact/path"]
