from lib.maintainer_proposals import deterministic_proposal_id


def test_deterministic_proposal_id_is_stable():
    first = deterministic_proposal_id(
        "skill-router",
        "recovery_skill_suggested_in_meta_discussion",
        "2026-05-06",
    )
    second = deterministic_proposal_id(
        "skill-router",
        "recovery_skill_suggested_in_meta_discussion",
        "2026-05-06",
    )

    assert first == second
    assert first.startswith("perf-ledger-skill-router-recovery-skill-suggested-in-meta-discussion-2026-05-06-")


def test_deterministic_proposal_id_changes_by_day_window():
    first = deterministic_proposal_id("skill-router", "same-pattern", "2026-05-06")
    second = deterministic_proposal_id("skill-router", "same-pattern", "2026-05-07")

    assert first != second

from lib.maintainer_proposals import PROPOSAL_SCHEMA_VERSION, validate_proposal_schema


def _schema_proposal():
    return {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "proposal_id": "perf-ledger-example",
        "severity": "P2",
        "self_confidence": 0.7,
        "surface": "reward-signal-quality",
        "harness_scope": "harness-agnostic",
        "source_metric_streams": ["skill-feedback"],
        "source_event_refs": ["performance-ledger:skill-feedback:matias"],
        "affected_primitive": "reward-signal:skill-feedback",
        "degradation_pattern": "corrupt-reward-signal-rows:skill-feedback:matias",
        "candidate_action": "Tighten validator contract.",
        "allowed_write_paths": ["lib/reward_signal_quality.py"],
        "blocked_write_paths": [".env", "secrets/**"],
        "tests_required": ["python3 -m pytest tests/unit/test_reward_signal_quality.py -q"],
        "rollback_plan": "Revert validator change.",
        "cooldown_after_apply": "P7D",
        "related_proposals": [],
        "experiment_design": {"type": "before_after"},
        "expected_impact_metric": "lower_corrupt_ratio",
        "post_change_measurement_window": "P7D",
        "human_approval_required": True,
        "outcome_on_regression": "quarantine_pattern_and_open_manual_investigation",
    }


def test_full_maintainer_proposal_schema_accepts_required_service_mode_fields():
    proposal = _schema_proposal()

    validate_proposal_schema(proposal)

    assert proposal["severity"] == "P2"
    assert proposal["experiment_design"]["type"] == "before_after"


def test_full_maintainer_proposal_schema_rejects_missing_severity():
    proposal = _schema_proposal()
    proposal.pop("severity")

    try:
        validate_proposal_schema(proposal)
    except ValueError as exc:
        assert "severity" in str(exc)
    else:
        raise AssertionError("expected schema validation failure")
