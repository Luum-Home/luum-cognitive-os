from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import cos_agent_flicker_report as flicker

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def materialize_control_files(project: Path) -> None:
    for definition in flicker._control_definitions():
        for rel in [*definition["artifacts"], *definition["docs"], *definition["tests"]]:
            path = project / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n", encoding="utf-8")
    (project / ".cognitive-os" / "cos-runner-hooks.json").parent.mkdir(parents=True, exist_ok=True)
    hook_names = sorted({hook for definition in flicker._control_definitions() for hook in definition.get("hooks", [])})
    (project / ".cognitive-os" / "cos-runner-hooks.json").write_text(
        json.dumps({"hooks": hook_names}),
        encoding="utf-8",
    )


def append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_complete_fixture_reports_pass_without_runtime_signals(tmp_path: Path) -> None:
    materialize_control_files(tmp_path)

    report = flicker.build_report(tmp_path)

    assert report["schema_version"] == flicker.SCHEMA_VERSION
    assert report["status"] == "pass"
    assert report["summary"]["control_count"] == 10
    assert report["summary"]["static_fail"] == 0
    assert report["runtime_signals"] == []


def test_missing_doc_or_test_marks_static_failure(tmp_path: Path) -> None:
    materialize_control_files(tmp_path)
    (tmp_path / "docs/04-Concepts/architecture/goal-loop.md").unlink()

    report = flicker.build_report(tmp_path)

    assert report["status"] == "fail"
    goal = next(item for item in report["controls"] if item["control_id"] == "deterministic-goal-loop")
    assert goal["status"] == "fail"
    assert "docs/04-Concepts/architecture/goal-loop.md" in goal["missing_docs"]


def test_runtime_signals_warn_from_local_metrics(tmp_path: Path) -> None:
    materialize_control_files(tmp_path)
    append_jsonl(
        tmp_path / ".cognitive-os" / "rate-limit-queue.jsonl",
        [
            {"action": "queued", "action_id": "a", "item": {"queue_id": "a", "retry_count": 2, "eligible_at": 1}},
            {"action": "queued", "action_id": "b", "item": {"queue_id": "b", "retry_count": 0, "eligible_at": 1}},
        ],
    )
    append_jsonl(tmp_path / ".cognitive-os" / "metrics" / "claim-enforcer.jsonl", [{"status": "block", "ok": False}])

    report = flicker.build_report(tmp_path)

    assert report["status"] == "warn"
    signal_ids = {item["signal_id"] for item in report["runtime_signals"]}
    assert "rate-limit-queue" in signal_ids
    assert "claim-enforcer-blocks" in signal_ids


def test_cli_json_executes() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "cos_agent_flicker_report.py"), "--project-dir", str(ROOT), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode in {0, 2}
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == flicker.SCHEMA_VERSION
    assert payload["summary"]["control_count"] == 10


def test_wrapper_executes_text() -> None:
    proc = subprocess.run(
        [str(ROOT / "scripts" / "cos-agent-flicker-report"), "--project-dir", str(ROOT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode in {0, 2}
    assert "Agent Flicker Control:" in proc.stdout
