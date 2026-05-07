from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.behavior
def test_event_log_migration_dry_run_and_execute(project_root: Path, tmp_path: Path) -> None:
    legacy = tmp_path / ".cognitive-os" / "sessions" / "events.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(
        json.dumps({"schema_version": 1, "event_type": "session-start", "session_id": "s1", "payload": {"n": 1}}) + "\n"
        + json.dumps({"schema_version": 1, "event_type": "session-end", "session_id": "s1", "payload": {"n": 2}}) + "\n",
        encoding="utf-8",
    )

    dry = subprocess.run(
        ["python3", str(project_root / "scripts" / "migrate_event_log_to_v2.py"), "--project-dir", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert dry.returncode == 0, dry.stderr
    assert json.loads(dry.stdout)["legacy_events"] == 2

    run = subprocess.run(
        ["python3", str(project_root / "scripts" / "migrate_event_log_to_v2.py"), "--project-dir", str(tmp_path), "--execute", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert run.returncode == 0, run.stderr
    payload = json.loads(run.stdout)
    assert payload["migrated"] == 2
    assert (tmp_path / ".cognitive-os" / "sessions" / "s1.events.jsonl").is_file()
