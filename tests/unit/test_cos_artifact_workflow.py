from __future__ import annotations

import json
from pathlib import Path

from scripts import cos_artifact_workflow


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_artifact_ingest_dedupes_and_reports_signals(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    first = artifacts / "evidence.md"
    second = artifacts / "copy.md"
    first.write_text("# Claim\nverified but warning present\n", encoding="utf-8")
    second.write_text(first.read_text(encoding="utf-8"), encoding="utf-8")

    rc = cos_artifact_workflow.main([
        "artifact-ingest",
        "--project-dir",
        str(tmp_path),
        "--artifact-dir",
        str(artifacts),
        "--json",
    ])
    assert rc == 0
    ledger = read_json(tmp_path / ".cognitive-os/artifacts/ledger.json")
    assert len(ledger["artifacts"]) == 2
    duplicate_groups = [paths for paths in ledger["fingerprints"].values() if len(paths) == 2]
    assert duplicate_groups

    report = cos_artifact_workflow.artifact_report(tmp_path)
    assert report["artifact_count"] == 2
    assert report["duplicate_count"] == 1
    assert report["signal_counts"]["claim-text"] == 2


def test_artifact_watch_only_updates_changed_files(tmp_path: Path) -> None:
    artifacts = tmp_path / "watch"
    artifacts.mkdir()
    item = artifacts / "log.txt"
    item.write_text("first\n", encoding="utf-8")

    assert cos_artifact_workflow.main(["artifact-watch", "--project-dir", str(tmp_path), "--artifact-dir", str(artifacts), "--max-cycles", "1", "--json"]) == 0
    first = read_json(tmp_path / ".cognitive-os/artifacts/ledger.json")["artifacts"]["watch/log.txt"]["fingerprint"]
    assert cos_artifact_workflow.main(["artifact-watch", "--project-dir", str(tmp_path), "--artifact-dir", str(artifacts), "--max-cycles", "1", "--json"]) == 0
    item.write_text("second\n", encoding="utf-8")
    assert cos_artifact_workflow.main(["artifact-watch", "--project-dir", str(tmp_path), "--artifact-dir", str(artifacts), "--max-cycles", "1", "--json"]) == 0
    second = read_json(tmp_path / ".cognitive-os/artifacts/ledger.json")["artifacts"]["watch/log.txt"]["fingerprint"]
    assert first != second


def test_work_graph_persists_tasks_and_blocks_duplicates(tmp_path: Path) -> None:
    assert cos_artifact_workflow.main(["work-graph", "add", "--project-dir", str(tmp_path), "--graph-id", "g", "--task-id", "T1", "--title", "Implement ledger", "--priority", "5", "--json"]) == 0
    assert cos_artifact_workflow.main(["work-graph", "add", "--project-dir", str(tmp_path), "--graph-id", "g", "--task-id", "T2", "--title", "Implement ledger", "--priority", "1", "--json"]) == 2
    assert cos_artifact_workflow.main(["work-graph", "update", "--project-dir", str(tmp_path), "--graph-id", "g", "--task-id", "T1", "--status", "done", "--evidence", "unit passed", "--json"]) == 0
    graph = read_json(tmp_path / ".cognitive-os/work-graphs/g/state.json")
    assert graph["tasks"]["T1"]["status"] == "done"
    assert len(graph["tasks"]) == 1


def test_refutation_review_records_fresh_review_on_unsupported_claim(tmp_path: Path) -> None:
    rc = cos_artifact_workflow.main([
        "refutation-review",
        "--project-dir",
        str(tmp_path),
        "--process-id",
        "p",
        "--claim-id",
        "C1",
        "--claim",
        "all tests pass",
        "--verification-command",
        "python3 -c 'raise SystemExit(1)'",
        "--json",
    ])
    assert rc == 2
    review = (tmp_path / ".cognitive-os/process-loops/p/review-findings.jsonl").read_text(encoding="utf-8")
    assert "refutation-C1" in review
    refutations = (tmp_path / ".cognitive-os/process-loops/p/refutation-review.jsonl").read_text(encoding="utf-8")
    assert "verification command did not pass" in refutations


def test_refutation_review_supports_claim_with_evidence_and_verification(tmp_path: Path) -> None:
    rc = cos_artifact_workflow.main([
        "refutation-review",
        "--project-dir",
        str(tmp_path),
        "--process-id",
        "p",
        "--claim-id",
        "C2",
        "--claim",
        "unit lane passed",
        "--evidence",
        "pytest output",
        "--verification-command",
        "python3 -c 'raise SystemExit(0)'",
        "--json",
    ])
    assert rc == 0
    row = json.loads((tmp_path / ".cognitive-os/process-loops/p/refutation-review.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert row["verdict"] == "supported"
    assert row["confidence"] >= 75


def test_second_pass_advisor_triggers_by_signals_and_records_receipt(tmp_path: Path) -> None:
    rc = cos_artifact_workflow.main([
        "second-pass-advisor",
        "--project-dir",
        str(tmp_path),
        "--process-id",
        "p",
        "--advisor-id",
        "local",
        "--signal",
        "large-diff",
        "--command",
        "python3 -c 'print(\"reviewed\")'",
        "--json",
    ])
    assert rc == 0
    row = json.loads((tmp_path / ".cognitive-os/process-loops/p/advisor-receipts.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert row["triggered"] is True
    assert row["read_only_required"] is True
    assert row["result"]["passed"] is True
    assert "reviewed" in row["result"]["stdout_tail"]


def test_second_pass_advisor_skips_below_signal_threshold(tmp_path: Path) -> None:
    rc = cos_artifact_workflow.main([
        "second-pass-advisor",
        "--project-dir",
        str(tmp_path),
        "--process-id",
        "p",
        "--advisor-id",
        "local",
        "--min-signals",
        "2",
        "--signal",
        "one",
        "--command",
        "python3 -c 'raise SystemExit(1)'",
        "--json",
    ])
    assert rc == 0
    row = json.loads((tmp_path / ".cognitive-os/process-loops/p/advisor-receipts.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert row["triggered"] is False
    assert row["result"] is None
