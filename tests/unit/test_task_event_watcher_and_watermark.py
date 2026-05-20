from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.cos_task_claims import claim_task, claims_path, watermark_landed_claims
from scripts.cos_task_event_watcher import summarize_events


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _init_repo(repo: Path) -> None:
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-m", "seed")


def test_event_watcher_reports_claim_completion_and_conflict(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    rows = [
        {"ts": "2026-05-20T00:00:00Z", "session": "s1", "event": "claim", "payload": {"task_id": "t1", "expected_files": ["a.py"]}},
        {"ts": "2026-05-20T00:01:00Z", "session": "s2", "event": "conflict", "payload": {"task_id": "t1", "held_by": "s1"}},
        {"ts": "2026-05-20T00:02:00Z", "session": "s1", "event": "complete", "payload": {"task_id": "t1"}},
    ]
    events.write_text("\n".join(json.dumps(row) for row in rows) + "\nnot-json\n", encoding="utf-8")

    projection = summarize_events(events)

    assert projection.current_claims == {}
    assert "t1" in projection.completions
    assert len(projection.conflicts) == 1
    assert projection.skipped_lines == 1


def test_watermark_marks_claim_completed_when_outputs_landed_in_main(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "landed.py").write_text("print('landed')\n", encoding="utf-8")
    _git(tmp_path, "add", "scripts/landed.py")
    _git(tmp_path, "commit", "-m", "feat: landed output")

    ok, claim = claim_task(
        tmp_path,
        {"id": "task-landed", "description": "landed output"},
        session="worker-1",
        expected_files=["scripts/landed.py"],
    )
    assert ok, claim

    result = watermark_landed_claims(tmp_path, ref="main", session="watcher")

    assert result["count"] == 1
    data = json.loads(claims_path(tmp_path).read_text(encoding="utf-8"))
    stored = data["claims"][0]
    assert stored["status"] == "completed-by-watermark"
    assert stored["watermark_evidence"]["matched_paths"] == ["scripts/landed.py"]
