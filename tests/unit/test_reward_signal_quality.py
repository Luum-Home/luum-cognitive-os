from pathlib import Path

from lib.reward_signal_quality import audit_stream, known_skill_ids, load_contract, repair_streams, summarize, validate_row


REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "manifests" / "reward-signal-contract.yaml"


def test_skill_matias_is_corrupt_and_not_rollup_eligible():
    contract = load_contract(CONTRACT)
    cfg = contract["streams"]["skill-feedback"]

    result = validate_row(
        "skill-feedback",
        {"timestamp": "2026-05-06T00:00:00Z", "skill": "matias", "success": False},
        cfg,
        known_subjects={"docs-to-artifact", "repo-map"},
    )

    assert result.status == "corrupt"
    assert result.eligible_for_rollup is False
    assert "unknown_skill_id" in result.reasons


def test_known_skill_feedback_row_is_valid():
    contract = load_contract(CONTRACT)
    cfg = contract["streams"]["skill-feedback"]

    result = validate_row(
        "skill-feedback",
        {"timestamp": "2026-05-06T00:00:00Z", "skill": "docs-to-artifact", "success": True},
        cfg,
        known_subjects={"docs-to-artifact"},
    )

    assert result.status == "valid"
    assert result.eligible_for_rollup is True
    assert result.reasons == []


def test_default_trust_score_without_evidence_is_suspect():
    contract = load_contract(CONTRACT)
    cfg = contract["streams"]["trust-report"]

    result = validate_row(
        "trust-report",
        {"timestamp": "2026-05-06T00:00:00Z", "subject_id": "run-1", "trust_score": 75},
        cfg,
    )

    assert result.status == "suspect"
    assert result.eligible_for_rollup is False
    assert "default_trust_score_without_evidence" in result.reasons


def test_default_trust_score_with_evidence_is_valid():
    contract = load_contract(CONTRACT)
    cfg = contract["streams"]["trust-report"]

    result = validate_row(
        "trust-report",
        {
            "timestamp": "2026-05-06T00:00:00Z",
            "subject_id": "run-1",
            "trust_score": 75,
            "evidence_ref": ".cognitive-os/metrics/verify-events.jsonl:12",
        },
        cfg,
    )

    assert result.status == "valid"
    assert result.eligible_for_rollup is True


def test_impossible_numeric_values_are_corrupt():
    contract = load_contract(CONTRACT)
    cfg = contract["streams"]["skill-metrics"]

    result = validate_row(
        "skill-metrics",
        {
            "timestamp": "2026-05-06T00:00:00Z",
            "skill": "docs-to-artifact",
            "success": True,
            "tokens": -1,
            "duration_ms": -20,
        },
        cfg,
        known_subjects={"docs-to-artifact"},
    )

    assert result.status == "corrupt"
    assert result.eligible_for_rollup is False
    assert "numeric_below_min:tokens" in result.reasons
    assert "numeric_below_min:duration_ms" in result.reasons


def test_audit_stream_quarantines_fixture_rows(tmp_path):
    contract = load_contract(CONTRACT)
    skill_dir = tmp_path / "skills" / "docs-to-artifact"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: docs-to-artifact\n---\n", encoding="utf-8")
    metrics_dir = tmp_path / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)
    (metrics_dir / "skill-feedback.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:00Z","skill":"docs-to-artifact","success":true}\n'
        '{"timestamp":"2026-05-06T00:00:01Z","skill":"matias","success":false}\n',
        encoding="utf-8",
    )

    results = audit_stream(tmp_path, contract, "skill-feedback")
    summary = summarize(results)

    assert summary == {"valid": 1, "suspect": 0, "corrupt": 1, "total": 2, "eligible_for_rollup": 1}


def test_known_skill_ids_reads_skill_directories():
    contract = load_contract(CONTRACT)

    ids = known_skill_ids(REPO, contract)

    assert "docs-to-artifact" in ids


def test_repair_streams_archives_quarantined_rows_and_rewrites_valid_only(tmp_path):
    skill_dir = tmp_path / "skills" / "known"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: known\n---\n", encoding="utf-8")
    metrics_dir = tmp_path / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)
    stream = metrics_dir / "skill-feedback.jsonl"
    stream.write_text(
        '{"timestamp":"2026-05-06T00:00:00Z","skill":"known","success":true}\n'
        '{"timestamp":"2026-05-06T00:01:00Z","skill":"matias","success":false}\n',
        encoding="utf-8",
    )
    contract = {
        "schema_version": "reward-signal-contract/v1",
        "known_subject_sources": {"skills_dirs": ["skills"]},
        "streams": {
            "skill-feedback": {
                "path": ".cognitive-os/metrics/skill-feedback.jsonl",
                "subject_type": "skill",
                "subject_field": "skill",
                "outcome_field": "success",
                "required_fields": ["timestamp", "skill", "success"],
                "known_subject_source": "skills_dirs",
            }
        },
    }

    payload = repair_streams(tmp_path, contract, ["skill-feedback"], execute=True)

    assert payload["summary"] == {"kept_rows": 1, "quarantined_rows": 1}
    rewritten = stream.read_text(encoding="utf-8")
    assert rewritten.count("\n") == 1
    assert '"skill":"known"' in rewritten
    assert '"skill":"matias"' not in rewritten
    archive = Path(payload["streams"][0]["archive_path"])
    assert archive.exists()
    assert '"skill":"matias"' in archive.read_text(encoding="utf-8")
