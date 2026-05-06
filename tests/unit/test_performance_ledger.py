import json
import sqlite3
from pathlib import Path

from lib.performance_ledger import compile_ledger


REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "manifests" / "reward-signal-contract.yaml"


def _write_skill(root: Path, name: str) -> None:
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")


def _write_fixture_metrics(root: Path) -> None:
    _write_skill(root, "docs-to-artifact")
    metrics = root / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "skill-feedback.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:00Z","skill":"docs-to-artifact","success":true}\n'
        '{"timestamp":"2026-05-06T00:00:01Z","skill":"matias","success":false}\n',
        encoding="utf-8",
    )
    (metrics / "trust-report.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:02Z","subject_id":"run-valid","trust_score":82,"evidence_ref":"verify-events:1"}\n'
        '{"timestamp":"2026-05-06T00:00:03Z","subject_id":"run-suspect","trust_score":75}\n',
        encoding="utf-8",
    )


def test_compile_ledger_writes_sqlite_jsonl_and_latest_report(tmp_path):
    _write_fixture_metrics(tmp_path)

    payload = compile_ledger(tmp_path, contract_path=CONTRACT, run_id="test-run")

    sqlite_path = tmp_path / ".cognitive-os" / "ledgers" / "performance-ledger.sqlite"
    jsonl_path = tmp_path / ".cognitive-os" / "metrics" / "performance-ledger.jsonl"
    latest_path = tmp_path / ".cognitive-os" / "reports" / "performance-ledger-latest.json"
    assert sqlite_path.exists()
    assert jsonl_path.exists()
    assert latest_path.exists()
    assert payload["summary"] == {"valid": 2, "suspect": 1, "corrupt": 1, "total": 4, "eligible_for_rollup": 2}
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    assert latest["run_id"] == "test-run"


def test_corrupt_and_suspect_rows_do_not_enter_rollup_eligible_counts(tmp_path):
    _write_fixture_metrics(tmp_path)

    payload = compile_ledger(tmp_path, contract_path=CONTRACT, run_id="quality-run")

    rollups = {(row["stream"], row["subject_id"]): row for row in payload["rollups"]}
    assert rollups[("skill-feedback", "docs-to-artifact")]["eligible_count"] == 1
    assert rollups[("skill-feedback", "matias")]["eligible_count"] == 0
    assert rollups[("skill-feedback", "matias")]["corrupt_count"] == 1
    assert rollups[("trust-report", "run-suspect")]["eligible_count"] == 0
    assert rollups[("trust-report", "run-suspect")]["suspect_count"] == 1


def test_sqlite_contains_only_valid_rows_as_rollup_eligible(tmp_path):
    _write_fixture_metrics(tmp_path)
    compile_ledger(tmp_path, contract_path=CONTRACT, run_id="sqlite-run")

    conn = sqlite3.connect(tmp_path / ".cognitive-os" / "ledgers" / "performance-ledger.sqlite")
    try:
        rows = conn.execute(
            "SELECT status, SUM(eligible_for_rollup) FROM signal_rows WHERE run_id = ? GROUP BY status",
            ("sqlite-run",),
        ).fetchall()
    finally:
        conn.close()

    assert dict(rows) == {"corrupt": 0, "suspect": 0, "valid": 2}


def test_recompiling_same_run_replaces_rows_not_duplicates(tmp_path):
    _write_fixture_metrics(tmp_path)
    compile_ledger(tmp_path, contract_path=CONTRACT, run_id="stable-run")
    compile_ledger(tmp_path, contract_path=CONTRACT, run_id="stable-run")

    conn = sqlite3.connect(tmp_path / ".cognitive-os" / "ledgers" / "performance-ledger.sqlite")
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM signal_rows WHERE run_id = ?",
            ("stable-run",),
        ).fetchone()[0]
    finally:
        conn.close()

    assert count == 4
