"""PromoteFromTelemetry primitive for ADR-201.

Converts Performance Ledger observations into bounded, human-approved maintainer
proposals. It refuses to consume streams blocked by ADR-204 signal quality.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.maintainer_proposals import PROPOSAL_SCHEMA_VERSION, deterministic_proposal_id, validate_proposal_schema
from lib.performance_ledger import compile_ledger, repo_root


PROMOTION_SCHEMA_VERSION = "promote-from-telemetry/v1"


def utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@dataclass(frozen=True)
class PromotionPolicy:
    corrupt_row_threshold: int = 1
    min_self_confidence: float = 0.62
    cooldown_after_apply: str = "P7D"
    post_change_measurement_window: str = "P7D"


def _severity(corrupt_count: int, total_count: int) -> str:
    if corrupt_count >= 25 or (total_count and corrupt_count / total_count >= 0.5):
        return "P1"
    if corrupt_count >= 5:
        return "P2"
    return "P3"


def _source_refs(rollup: dict[str, Any]) -> list[str]:
    stream = str(rollup.get("stream") or "unknown")
    subject = str(rollup.get("subject_id") or "stream")
    return [f"performance-ledger:{stream}:{subject}"]


def build_signal_quality_proposal(rollup: dict[str, Any], *, day_window: str, policy: PromotionPolicy) -> dict[str, Any]:
    stream = str(rollup.get("stream") or "unknown")
    subject = str(rollup.get("subject_id") or "stream")
    corrupt_count = int(rollup.get("corrupt_count") or 0)
    total_count = int(rollup.get("total_count") or 0)
    degradation_pattern = f"corrupt-reward-signal-rows:{stream}:{subject}"
    proposal_id = deterministic_proposal_id("reward-signal-quality", degradation_pattern, day_window)
    proposal = {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "proposal_id": proposal_id,
        "severity": _severity(corrupt_count, total_count),
        "self_confidence": policy.min_self_confidence,
        "surface": "reward-signal-quality",
        "harness_scope": "harness-agnostic",
        "source_metric_streams": [stream],
        "source_event_refs": _source_refs(rollup),
        "affected_primitive": f"reward-signal:{stream}",
        "degradation_pattern": degradation_pattern,
        "candidate_action": (
            "Tighten the reward-signal contract or producer normalization so corrupt rows are quarantined "
            "before router, maintainer, or skill lifecycle consumers read them."
        ),
        "allowed_write_paths": [
            "manifests/reward-signal-contract.yaml",
            "lib/reward_signal_quality.py",
            "tests/unit/test_reward_signal_quality.py",
        ],
        "blocked_write_paths": [".env", "secrets/**", ".git/config"],
        "tests_required": [
            "python3 -m pytest tests/unit/test_reward_signal_quality.py -q",
            "python3 -m pytest tests/unit/test_performance_ledger.py -q",
        ],
        "rollback_plan": "Revert the reward-signal contract/validator change and re-run the Performance Ledger compile smoke.",
        "cooldown_after_apply": policy.cooldown_after_apply,
        "related_proposals": [],
        "experiment_design": {
            "type": "before_after",
            "canary_scope": "local Performance Ledger compile",
            "success_metric": "corrupt_ratio for the affected stream decreases without reducing valid eligible rows",
            "minimum_observation_window": policy.post_change_measurement_window,
        },
        "expected_impact_metric": "lower_corrupt_ratio_without_lower_valid_rollup",
        "post_change_measurement_window": policy.post_change_measurement_window,
        "human_approval_required": True,
        "outcome_on_regression": "quarantine_pattern_and_open_manual_investigation",
    }
    validate_proposal_schema(proposal)
    return proposal


def promote_from_ledger_report(ledger_report: dict[str, Any], *, day_window: str | None = None, policy: PromotionPolicy | None = None) -> dict[str, Any]:
    active_policy = policy or PromotionPolicy()
    window = day_window or utc_day()
    consumption = ledger_report.get("consumption_policy") or {}
    if not bool(consumption.get("can_consume_all", False)):
        return {
            "schema_version": PROMOTION_SCHEMA_VERSION,
            "status": "blocked_by_signal_quality",
            "day_window": window,
            "ledger_run_id": ledger_report.get("run_id"),
            "blocked_streams": list(consumption.get("blocked_streams") or []),
            "proposals": [],
            "proposal_count": 0,
            "reason": "ADR-204 consumption policy blocked one or more streams; maintainer proposals are suppressed until signal quality is repaired.",
        }

    proposals: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rollup in ledger_report.get("rollups", []) or []:
        corrupt_count = int(rollup.get("corrupt_count") or 0)
        if corrupt_count < active_policy.corrupt_row_threshold:
            continue
        proposal = build_signal_quality_proposal(rollup, day_window=window, policy=active_policy)
        if proposal["proposal_id"] in seen:
            continue
        seen.add(proposal["proposal_id"])
        proposals.append(proposal)

    return {
        "schema_version": PROMOTION_SCHEMA_VERSION,
        "status": "ok",
        "day_window": window,
        "ledger_run_id": ledger_report.get("run_id"),
        "blocked_streams": [],
        "proposals": proposals,
        "proposal_count": len(proposals),
        "reason": "proposals_generated" if proposals else "no_promotable_degradation_detected",
    }


def promote_from_telemetry(
    project_dir: Path | None = None,
    *,
    contract_path: Path | None = None,
    streams: list[str] | None = None,
    limit: int | None = None,
    run_id: str | None = None,
    day_window: str | None = None,
    write_ledger: bool = True,
) -> dict[str, Any]:
    project = (project_dir or repo_root()).resolve()
    ledger = compile_ledger(
        project,
        contract_path=contract_path,
        streams=streams,
        limit=limit,
        run_id=run_id,
        write=write_ledger,
    )
    result = promote_from_ledger_report(ledger, day_window=day_window)
    result["project_dir"] = str(project)
    result["ledger_summary"] = ledger.get("summary", {})
    result["consumption_policy"] = ledger.get("consumption_policy", {})
    return result
