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


def test_control_plane_writes_latest_report_metrics_and_remediation_queue(tmp_path: Path) -> None:
    audit = tmp_path / "audit.py"
    write(audit, """import json
print(json.dumps({'schema_version':'demo/v1','findings':[{'severity':'block','code':'demo-block','message':'broken','path':'x'}]}))
""")
    manifest = tmp_path / "control.yaml"
    write(manifest, f"""schema_version: control-plane-audits/v1
lanes:
  hook-fast:
    max_seconds: 5
    audits: [demo]
audits:
  demo:
    adr: ADR-999
    command: [python3, {audit.as_posix()}]
    expected_schema: demo/v1
    mutates: false
""")

    payload = run_control(tmp_path, manifest)

    assert payload["status"] == "block"
    latest = tmp_path / ".cognitive-os" / "reports" / "control-plane" / "latest.json"
    queue = tmp_path / ".cognitive-os" / "tasks" / "control-plane-remediation.jsonl"
    metrics = tmp_path / ".cognitive-os" / "metrics" / "control-plane-audit.jsonl"
    state = tmp_path / ".cognitive-os" / "runtime" / "control-plane-audit" / "findings-state.json"
    assert latest.exists()
    assert queue.exists()
    assert metrics.exists()
    assert state.exists()
    latest_payload = json.loads(latest.read_text(encoding="utf-8"))
    assert latest_payload["findings_enriched"][0]["adr"] == "ADR-999"
    metric_payload = json.loads(metrics.read_text(encoding="utf-8").splitlines()[-1])
    assert metric_payload["findings_by_adr"] == {"ADR-999": 1}
    queue_payload = json.loads(queue.read_text(encoding="utf-8").splitlines()[-1])
    assert queue_payload["event"] == "proposed"
    assert queue_payload["status"] == "queued"


def test_control_plane_marks_time_to_remediate_when_finding_disappears(tmp_path: Path) -> None:
    flag = tmp_path / "flag"
    flag.write_text("bad", encoding="utf-8")
    audit = tmp_path / "audit.py"
    write(audit, f"""import json, pathlib
findings=[]
if pathlib.Path({str(flag)!r}).exists():
    findings.append({{'severity':'block','code':'demo-block','message':'broken','path':'x'}})
print(json.dumps({{'schema_version':'demo/v1','findings':findings}}))
""")
    manifest = tmp_path / "control.yaml"
    write(manifest, f"""schema_version: control-plane-audits/v1
lanes:
  hook-fast:
    max_seconds: 5
    audits: [demo]
audits:
  demo:
    adr: ADR-999
    command: [python3, {audit.as_posix()}]
    expected_schema: demo/v1
    mutates: false
""")
    first = run_control(tmp_path, manifest)
    assert first["status"] == "block"
    flag.unlink()

    second = run_control(tmp_path, manifest)

    assert second["status"] == "pass"
    metric_payload = json.loads((tmp_path / ".cognitive-os" / "metrics" / "control-plane-audit.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert metric_payload["resolved_findings"] == 1
    assert metric_payload["time_to_remediate"][0]["time_to_remediate_seconds"] >= 0


def test_control_plane_applies_only_manifest_declared_safe_fix(tmp_path: Path) -> None:
    flag = tmp_path / "flag"
    flag.write_text("bad", encoding="utf-8")
    audit = tmp_path / "audit.py"
    fix = tmp_path / "fix.py"
    write(audit, f"""import json, pathlib
findings=[]
if pathlib.Path({str(flag)!r}).exists():
    findings.append({{'severity':'warn','code':'stale-generated-report','message':'stale report','path':'report'}})
print(json.dumps({{'schema_version':'demo/v1','findings':findings}}))
""")
    write(fix, f"""from pathlib import Path
Path({str(flag)!r}).unlink(missing_ok=True)
""")
    manifest = tmp_path / "control.yaml"
    write(manifest, f"""schema_version: control-plane-audits/v1
remediation:
  safe_classes: [stale-generated-report]
  safe_fixes:
    refresh-demo:
      finding_code: stale-generated-report
      safe_class: stale-generated-report
      command: [python3, {fix.as_posix()}]
lanes:
  hook-fast:
    max_seconds: 5
    audits: [demo]
audits:
  demo:
    adr: ADR-999
    command: [python3, {audit.as_posix()}]
    expected_schema: demo/v1
    mutates: false
""")
    proc = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(tmp_path), "--manifest", str(manifest), "--lane", "hook-fast", "--json", "--apply-safe-fixes"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout, proc.stderr
    payload = json.loads(proc.stdout)

    assert proc.returncode == 0
    assert payload["status"] == "pass"
    assert not flag.exists()
    assert payload["safe_fixes"][0]["measurement"]["reduced"] is True
