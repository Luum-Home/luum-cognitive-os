"""ADR-209 Maintainer experiment contract validation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


SCHEMA_VERSION = "maintainer-experiment-schema/v1"
EXPERIMENT_VERSION = "maintainer-experiment/v1"


def load_schema(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported maintainer experiment schema: {payload.get('schema_version')}")
    return payload


def validate_experiment(experiment: dict[str, Any], schema: dict[str, Any]) -> None:
    missing = sorted(set(schema.get("required_fields", [])) - set(experiment))
    if missing:
        raise ValueError(f"maintainer experiment missing required fields: {', '.join(missing)}")
    if experiment.get("schema_version") != EXPERIMENT_VERSION:
        raise ValueError("unsupported maintainer experiment schema_version")

    contracts = schema.get("field_contracts", {}) or {}
    for field_name, contract in contracts.items():
        if field_name not in experiment:
            continue
        if "enum" in contract and experiment[field_name] not in contract["enum"]:
            raise ValueError(f"{field_name} must be one of: {', '.join(contract['enum'])}")
        if "min_items" in contract:
            value = experiment[field_name]
            if not isinstance(value, list) or len(value) < int(contract["min_items"]):
                raise ValueError(f"{field_name} must contain at least {contract['min_items']} item(s)")
        if "required_fields" in contract:
            value = experiment[field_name]
            if not isinstance(value, dict):
                raise ValueError(f"{field_name} must be an object")
            nested_missing = sorted(set(contract["required_fields"]) - set(value))
            if nested_missing:
                raise ValueError(f"{field_name} missing required fields: {', '.join(nested_missing)}")

    policy = schema.get("policy", {}) or {}
    if policy.get("require_guardrail_for_every_success_metric"):
        if len(experiment.get("guardrail_metrics", [])) < 1:
            raise ValueError("at least one guardrail metric is required")
    approval = experiment.get("human_approval", {})
    if approval.get("required") is not True:
        raise ValueError("human_approval.required must be true for executable maintainer experiments")


def evaluate_outcome(measurement: dict[str, Any]) -> str:
    """Deterministic pass/fail/inconclusive evaluator for canary outcomes."""
    if bool(measurement.get("guardrail_regressed")):
        return "failed"
    if bool(measurement.get("success_metric_improved")):
        return "passed"
    return "inconclusive"

