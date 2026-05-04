from __future__ import annotations

import gzip
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_engram_cloud_enroll_dry_run_writes_sync_audit_without_token_value(tmp_path: Path) -> None:
    runtime = tmp_path / ".cognitive-os" / "runtime"
    proc = subprocess.run(
        [
            str(ROOT / "scripts" / "cos-engram-cloud-enroll"),
            "--project",
            "demo-project",
            "--server",
            "http://127.0.0.1:8080",
            "--dry-run",
            "--json",
        ],
        cwd=ROOT,
        env={
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
            "COGNITIVE_OS_RUNTIME_DIR": str(runtime),
            "ENGRAM_CLOUD_TOKEN": "secret-token-value",
        },
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["project_scope"] == "demo-project"
    assert payload["token_present"] == "true"
    assert "secret-token-value" not in proc.stdout
    audit = (runtime / "agent-audit-trail.jsonl").read_text(encoding="utf-8")
    assert "secret-token-value" not in audit
    row = json.loads(audit.splitlines()[0])
    assert row["audit_class"] == "sync"
    assert row["engram_project_scope"] == "demo-project"


def test_audit_archive_dry_run_preserves_source_and_reports_eligible_rows(tmp_path: Path) -> None:
    audit = tmp_path / "agent-audit-trail.jsonl"
    old = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat().replace("+00:00", "Z")
    new = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    audit.write_text(
        json.dumps({"timestamp": old, "event": "old", "audit_class": "change_management"}) + "\n"
        + json.dumps({"timestamp": new, "event": "new", "audit_class": "change_management"}) + "\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            str(ROOT / "scripts" / "cos-audit-archive"),
            "--audit-file",
            str(audit),
            "--archive-dir",
            str(tmp_path / "archive"),
            "--retention-days",
            "90",
            "--dry-run",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["eligible_rows"] == 1
    assert payload["source_preserved"] is True
    assert audit.read_text(encoding="utf-8").count("\n") == 2


def test_audit_archive_writes_gzip_copy_without_deleting_source(tmp_path: Path) -> None:
    audit = tmp_path / "agent-audit-trail.jsonl"
    old = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat().replace("+00:00", "Z")
    audit.write_text(json.dumps({"timestamp": old, "event": "old", "audit_class": "privacy"}) + "\n", encoding="utf-8")

    proc = subprocess.run(
        [
            str(ROOT / "scripts" / "cos-audit-archive"),
            "--audit-file",
            str(audit),
            "--archive-dir",
            str(tmp_path / "archive"),
            "--retention-days",
            "90",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    archive_path = Path(payload["archive_path"])
    assert archive_path.exists()
    assert audit.exists()
    with gzip.open(archive_path, "rt", encoding="utf-8") as handle:
        rows = handle.read()
    assert '"event": "old"' in rows
