from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.cos_governance_roi import build_report, log_catch, phase_allows_block


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
    assert report["friction"]["weighted_block_events"] == 1.0
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


def test_governance_roi_reads_catch_ledger_and_ratio_policy(tmp_path: Path) -> None:
    metrics = tmp_path / ".cognitive-os" / "metrics"
    write_jsonl(
        metrics / "hook-timing.jsonl",
        [
            {"timestamp": "2026-05-02T00:00:00Z", "hook": "guard-a", "exit_code": 2},
            {"timestamp": "2026-05-02T00:01:00Z", "hook": "guard-a", "exit_code": 2},
            {"timestamp": "2026-05-02T00:02:00Z", "hook": "guard-b", "exit_code": 2},
            {"timestamp": "2026-05-02T00:03:00Z", "hook": "guard-b", "exit_code": 2},
        ],
    )
    write_jsonl(
        metrics / "governance-catches.jsonl",
        [
            {"timestamp": "2026-05-02T00:04:00Z", "hook": "guard-a", "verdict": "confirmed_valid_block"},
            {"timestamp": "2026-05-02T00:05:00Z", "hook": "guard-a", "verdict": "silent_loss_prevented"},
            {"timestamp": "2026-05-02T00:06:00Z", "hook": "guard-c", "verdict": "false_positive_override"},
        ],
    )
    (tmp_path / "cognitive-os.yaml").write_text("project:\n  phase: reconstruction\n", encoding="utf-8")

    report = build_report(tmp_path, window_hours=0)

    assert report["catch_ledger"]["confirmed_valid_blocks"] == 2
    assert report["catch_ledger"]["confirmed_weight"] == 2.0
    assert report["catch_ledger"]["false_positive_overrides"] == 1
    assert report["catch_ledger"]["silent_loss_prevented"] == 1
    assert report["friction_vs_catch"]["ratio"] == 2.0
    assert report["friction_vs_catch"]["status"] == "paying"
    assert report["phase_policy"]["phase"] == "reconstruction"
    assert report["phase_policy"]["strictness"] == "minimal-blocking"


def test_governance_roi_flags_cut_band_when_blocks_outpace_confirmed_catches(tmp_path: Path) -> None:
    metrics = tmp_path / ".cognitive-os" / "metrics"
    write_jsonl(
        metrics / "hook-timing.jsonl",
        [{"timestamp": "2026-05-02T00:00:00Z", "hook": "guard-a", "exit_code": 2} for _ in range(12)],
    )
    write_jsonl(
        metrics / "governance-catches.jsonl",
        [
            {"timestamp": "2026-05-02T00:01:00Z", "hook": "guard-a", "verdict": "confirmed_valid_block"},
            {"timestamp": "2026-05-02T00:02:00Z", "hook": "guard-a", "verdict": "confirmed_valid_block"},
        ],
    )

    report = build_report(tmp_path, window_hours=0)

    assert report["friction_vs_catch"]["ratio"] == 6.0
    assert report["friction_vs_catch"]["status"] == "cut"
    assert any("exceeds 5x" in item for item in report["recommendations"])


def test_governance_catch_log_normalizes_verdict_and_severity(tmp_path: Path) -> None:
    row = log_catch(
        tmp_path,
        hook="destructive-git-blocker",
        verdict="confirmed-valid-block",
        reason="prevented destructive checkout",
    )

    assert row["verdict"] == "confirmed_valid_block"
    assert row["severity"] == "critical"
    assert row["severity_weight"] == 3.0

    report = build_report(tmp_path, window_hours=0)
    assert report["catch_ledger"]["confirmed_valid_blocks"] == 1
    assert report["catch_ledger"]["confirmed_weight"] == 3.0


def test_phase_policy_adapter_defaults_unknown_categories_to_advisory() -> None:
    assert phase_allows_block("reconstruction", "destructive-git")["allowed_to_block"] is True
    result = phase_allows_block("reconstruction", "style")
    assert result["allowed_to_block"] is False
    assert result["decision"] == "advisory"
    unknown = phase_allows_block("reconstruction", "new-noisy-process-gate")
    assert unknown["allowed_to_block"] is False
    assert "not explicitly allowed" in unknown["reason"]


def test_cos_dispatches_governance_catch_log(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            "bash",
            str(repo / "scripts" / "cos"),
            "governance",
            "catch",
            "log",
            "--project-dir",
            str(tmp_path),
            "--hook",
            "dispatch-gate",
            "--verdict",
            "false-positive-override",
            "--reason",
            "operator continued manually",
            "--json",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["hook"] == "dispatch-gate"
    assert payload["verdict"] == "false_positive_override"


def test_cos_dispatches_governance_catch_pending(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    write_jsonl(
        tmp_path / ".cognitive-os" / "metrics" / "governance-catch-prompts.jsonl",
        [
            {
                "timestamp": "2026-05-20T00:00:00Z",
                "hook": "dispatch-gate",
                "event": "PreToolUse",
                "default": "skip",
            }
        ],
    )

    result = subprocess.run(
        [
            "bash",
            str(repo / "scripts" / "cos"),
            "governance",
            "catch",
            "pending",
            "--project-dir",
            str(tmp_path),
            "--json",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["pending"][0]["hook"] == "dispatch-gate"


def test_cos_dispatches_governance_policy(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            "bash",
            str(repo / "scripts" / "cos"),
            "governance",
            "policy",
            "--project-dir",
            str(tmp_path),
            "--phase",
            "reconstruction",
            "--category",
            "style",
            "--json",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["decision"] == "advisory"
    assert payload["allowed_to_block"] is False
