from __future__ import annotations

import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "cos-control-plane-audit"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_control(root: Path, manifest: Path, lane: str = "hook-fast") -> dict:
    proc = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(root), "--manifest", str(manifest), "--lane", lane, "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout, proc.stderr
    payload = json.loads(proc.stdout)
    payload["returncode"] = proc.returncode
    return payload


def test_control_plane_audit_aggregates_json_audit_results(tmp_path: Path) -> None:
    audit = tmp_path / "audit.py"
    write(audit, """import json
print(json.dumps({'schema_version':'demo/v1','findings':[{'severity':'warn','code':'demo'}]}))
""")
    manifest = tmp_path / "control.yaml"
    write(manifest, f"""schema_version: control-plane-audits/v1
lanes:
  hook-fast:
    max_seconds: 5
    audits: [demo]
audits:
  demo:
    adr: ADR-X
    command: [python3, {audit.as_posix()}]
    expected_schema: demo/v1
    mutates: false
""")
    payload = run_control(tmp_path, manifest)
    assert payload["status"] == "warn"
    assert payload["summary"]["warn"] == 1
    assert payload["returncode"] == 0


def test_control_plane_audit_blocks_mutating_audit_specs(tmp_path: Path) -> None:
    manifest = tmp_path / "control.yaml"
    write(manifest, """schema_version: control-plane-audits/v1
lanes:
  hook-fast:
    max_seconds: 5
    audits: [bad]
audits:
  bad:
    adr: ADR-X
    command: [python3, -c, 'print(1)']
    expected_schema: demo/v1
    mutates: true
""")
    payload = run_control(tmp_path, manifest)
    assert payload["status"] == "block"
    assert any(f["code"] == "mutating-audit-not-allowed" for a in payload["audits"] for f in a["findings"])


def test_control_plane_audit_blocks_schema_mismatch(tmp_path: Path) -> None:
    audit = tmp_path / "audit.py"
    write(audit, """import json
print(json.dumps({'schema_version':'wrong/v1','findings':[]}))
""")
    manifest = tmp_path / "control.yaml"
    write(manifest, f"""schema_version: control-plane-audits/v1
lanes:
  hook-fast:
    max_seconds: 5
    audits: [demo]
audits:
  demo:
    adr: ADR-X
    command: [python3, {audit.as_posix()}]
    expected_schema: demo/v1
    mutates: false
""")
    payload = run_control(tmp_path, manifest)
    assert payload["status"] == "block"
    assert any(f["code"] == "audit-schema-mismatch" for a in payload["audits"] for f in a["findings"])
