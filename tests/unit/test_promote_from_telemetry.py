from pathlib import Path

from lib.promote_from_telemetry import promote_from_telemetry

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "manifests" / "reward-signal-contract.yaml"


def _write_skill(root: Path, name: str) -> None:
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")


def _contract_with_threshold(tmp_path: Path, threshold: str) -> Path:
    path = tmp_path / "reward-signal-contract.yaml"
    path.write_text(CONTRACT.read_text(encoding="utf-8").replace("corrupt_ratio_block_threshold: 0.25", f"corrupt_ratio_block_threshold: {threshold}"), encoding="utf-8")
    return path


def test_promote_from_telemetry_refuses_blocked_signal_quality(tmp_path):
    _write_skill(tmp_path, "docs-to-artifact")
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "skill-feedback.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:00Z","skill":"docs-to-artifact","success":true}\n'
        '{"timestamp":"2026-05-06T00:00:01Z","skill":"matias","success":false}\n',
        encoding="utf-8",
    )

    payload = promote_from_telemetry(tmp_path, contract_path=CONTRACT, streams=["skill-feedback"], run_id="blocked", write_ledger=False)

    assert payload["status"] == "blocked_by_signal_quality"
    assert payload["proposal_count"] == 0
    assert payload["blocked_streams"] == ["skill-feedback"]


def test_promote_from_telemetry_generates_deduped_schema_valid_quality_proposal(tmp_path):
    _write_skill(tmp_path, "docs-to-artifact")
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "skill-feedback.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:00Z","skill":"docs-to-artifact","success":true}\n'
        '{"timestamp":"2026-05-06T00:00:01Z","skill":"docs-to-artifact","success":false}\n'
        '{"timestamp":"2026-05-06T00:00:02Z","skill":"matias","success":false}\n',
        encoding="utf-8",
    )
    contract = _contract_with_threshold(tmp_path, "0.34")

    payload = promote_from_telemetry(
        tmp_path,
        contract_path=contract,
        streams=["skill-feedback"],
        run_id="allowed",
        day_window="2026-05-06",
        write_ledger=False,
    )

    assert payload["status"] == "ok"
    assert payload["proposal_count"] == 1
    proposal = payload["proposals"][0]
    assert proposal["schema_version"] == "maintainer-proposal/v1"
    assert proposal["severity"] in {"P1", "P2", "P3"}
    assert proposal["human_approval_required"] is True
    assert proposal["experiment_design"]["type"] == "before_after"
    assert proposal["proposal_id"].startswith("perf-ledger-reward-signal-quality-")


def test_promote_from_telemetry_quarantines_regressed_post_change_outcome(tmp_path):
    from lib.maintainer_impact import append_post_change_impact_event, build_post_change_impact_event, default_post_change_ledger_path

    event = build_post_change_impact_event(
        proposal_id="proposal-regressed",
        work_id="work-maintainer-loop-regression",
        surface="skill-router",
        degradation_pattern="skill-override-rate-increase:scout",
        before_metrics={"override_rate": 0.10},
        after_metrics={"override_rate": 0.30},
        source_rollup_ref="performance-ledger:skill-feedback:scout",
        operator_decision="applied",
        outcome="regressed",
    )
    append_post_change_impact_event(default_post_change_ledger_path(tmp_path), event)
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    (metrics / "skill-feedback.jsonl").write_text("", encoding="utf-8")

    payload = promote_from_telemetry(
        tmp_path,
        contract_path=CONTRACT,
        streams=["skill-feedback"],
        run_id="regression-fixture",
        day_window="2026-05-20",
        write_ledger=False,
    )

    assert payload["outcome_quarantine_count"] == 1
    report = payload["outcome_quarantine_reports"][0]
    assert report["quarantine_state"] == "quarantined_until_manual_resolution"
    assert report["manual_investigation_required"] is True
    assert report["rollback_approval_required"] is True
    assert report["work_id"] == "work-maintainer-loop-regression"


def test_promote_from_telemetry_proposes_for_repeated_capability_mismatches(tmp_path):
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "subagent-preflight.jsonl").write_text(
        '{"timestamp":"2026-05-20T00:00:00Z","classification":"capability_contract_mismatch","agent_type":"Explore","prompt_requires_write":true,"write_capability":false,"safe_alternatives":["general-purpose"]}\n'
        '{"timestamp":"2026-05-20T00:01:00Z","classification":"capability_contract_mismatch","agent_type":"Explore","prompt_requires_write":true,"write_capability":false,"safe_alternatives":["general-purpose"]}\n',
        encoding="utf-8",
    )
    (metrics / "skill-feedback.jsonl").write_text("", encoding="utf-8")

    payload = promote_from_telemetry(
        tmp_path,
        contract_path=CONTRACT,
        streams=["skill-feedback"],
        run_id="capability-mismatch-fixture",
        day_window="2026-05-20",
        write_ledger=False,
    )

    proposals = [p for p in payload["proposals"] if p["surface"] == "subagent-capability-contract"]
    assert payload["capability_mismatch_proposal_count"] == 1
    assert proposals
    assert proposals[0]["affected_primitive"] == "subagent:Explore"
    assert "manifests/subagent-capabilities.yaml" in proposals[0]["allowed_write_paths"]
