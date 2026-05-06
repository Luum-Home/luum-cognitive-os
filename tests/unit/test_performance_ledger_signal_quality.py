from pathlib import Path

from lib.performance_ledger import compile_ledger


REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "manifests" / "reward-signal-contract.yaml"


def test_performance_ledger_preserves_adr_204_quality_counts(tmp_path):
    skill_dir = tmp_path / "skills" / "known-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: known-skill\n---\n", encoding="utf-8")
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "skill-feedback.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:00Z","skill":"known-skill","success":true}\n'
        '{"timestamp":"2026-05-06T00:00:01Z","skill":"unknown-human","success":false}\n',
        encoding="utf-8",
    )
    (metrics / "trust-report.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:02Z","subject_id":"default-score","trust_score":75}\n',
        encoding="utf-8",
    )

    payload = compile_ledger(tmp_path, contract_path=CONTRACT, run_id="quality-counts")

    assert payload["streams"]["skill-feedback"] == {
        "valid": 1,
        "suspect": 0,
        "corrupt": 1,
        "total": 2,
        "eligible_for_rollup": 1,
    }
    assert payload["streams"]["trust-report"] == {
        "valid": 0,
        "suspect": 1,
        "corrupt": 0,
        "total": 1,
        "eligible_for_rollup": 0,
    }
    assert payload["summary"]["eligible_for_rollup"] == 1
