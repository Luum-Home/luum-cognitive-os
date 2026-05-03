from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.cos_governance_roi import build_report


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_governance_roi_counts_friction_and_wip_restore(tmp_path: Path) -> None:
    metrics = tmp_path / ".cognitive-os" / "metrics"
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)
    write_jsonl(
        metrics / "hook-timing.jsonl",
        [
            {"timestamp": "2026-05-02T00:00:00Z", "hook": "agent-prelaunch", "exit_code": 2, "body_duration_ms": 120000},
            {"timestamp": "2026-05-02T00:01:00Z", "hook": "secret-detector", "exit_code": 0, "body_duration_ms": 30000},
        ],
    )
    write_jsonl(
        metrics / "agent-snapshots.jsonl",
        [
            {"timestamp": "2026-05-02T00:02:00Z", "event": "agent_snapshot_restore", "action": "restored"},
        ],
    )
    report = build_report(tmp_path, window_hours=0)

    assert report["friction"]["blocking_events"] == 1
    assert report["friction"]["body_time_minutes"] == 2.5
    assert report["benefits"]["wip_restore_events"] == 1
    assert report["roi"]["benefit_minutes_estimate"] > report["roi"]["friction_minutes_estimate"]
    assert report["roi"]["status"] == "positive"


def test_governance_roi_flags_discovery_overload_and_residue(tmp_path: Path) -> None:
    (tmp_path / ".cognitive-os" / "runtime").mkdir(parents=True)
    (tmp_path / ".cognitive-os" / "runtime" / "pre-agent-snapshot-x.json").write_text("{}\n", encoding="utf-8")
    for idx in range(80):
        skill = tmp_path / "skills" / f"skill-{idx}" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: x\ndescription: x\n---\n", encoding="utf-8")

    report = build_report(tmp_path, window_hours=0)

    assert report["benefits"]["orphan_marker_count"] == 1
    assert report["discovery"]["discovery_overload"] is True
    assert any("distribution tiers" in item for item in report["recommendations"])
    assert report["roi"]["status"] == "negative"


def test_cos_dispatches_governance_roi_json(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["bash", str(repo / "scripts" / "cos"), "governance", "roi", "--project-dir", str(tmp_path), "--json"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["project"] == str(tmp_path.resolve())
    assert "roi" in payload
