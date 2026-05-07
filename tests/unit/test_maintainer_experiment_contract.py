from pathlib import Path

import pytest

from lib.maintainer_experiment import evaluate_outcome, load_schema, validate_experiment


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "manifests" / "maintainer-experiment-schema.yaml"


def _experiment():
    return {
        "schema_version": "maintainer-experiment/v1",
        "experiment_id": "exp-router-confidence-20260507",
        "proposal_id": "perf-ledger-skill-router-example",
        "target_surface": "skill-router",
        "desired_state": {"router_confidence": {"auto-rollback": 0.40}},
        "canary_scope": {"type": "fixture", "population": "router-negative-intent-fixtures"},
        "success_metrics": [{"name": "false_positive_rate", "target": "decrease"}],
        "guardrail_metrics": [{"name": "valid_invocation_recall", "threshold": ">=0.95"}],
        "rollback_threshold": {"guardrail_regression": True},
        "measurement_window": "P7D",
        "human_approval": {"required": True, "approver_role": "operator"},
        "owner": "platform-safety",
        "cooldown": "P7D",
        "outcome_action": "manual_investigation",
    }


def test_maintainer_experiment_schema_accepts_complete_contract():
    schema = load_schema(SCHEMA)

    validate_experiment(_experiment(), schema)


def test_maintainer_experiment_requires_guardrail_metric():
    schema = load_schema(SCHEMA)
    experiment = _experiment()
    experiment["guardrail_metrics"] = []

    with pytest.raises(ValueError, match="guardrail_metrics"):
        validate_experiment(experiment, schema)


def test_maintainer_experiment_requires_human_approval():
    schema = load_schema(SCHEMA)
    experiment = _experiment()
    experiment["human_approval"]["required"] = False

    with pytest.raises(ValueError, match="human_approval.required"):
        validate_experiment(experiment, schema)


def test_maintainer_outcome_fails_on_guardrail_regression():
    assert evaluate_outcome({"success_metric_improved": True, "guardrail_regressed": True}) == "failed"
    assert evaluate_outcome({"success_metric_improved": True, "guardrail_regressed": False}) == "passed"
    assert evaluate_outcome({"success_metric_improved": False, "guardrail_regressed": False}) == "inconclusive"

