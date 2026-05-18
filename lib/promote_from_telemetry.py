"""PromoteFromTelemetry primitive for ADR-201.

Converts Performance Ledger observations into bounded, human-approved maintainer
proposals. It refuses to consume streams blocked by ADR-204 signal quality.

Phase 2 adds three pattern-detection functions that operate on raw event lists
and return structured findings (not proposals) for operator review:
  - detect_skill_override_patterns
  - detect_provider_fallback_drift
  - detect_dormant_no_evidence
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import yaml

from lib.maintainer_proposals import PROPOSAL_SCHEMA_VERSION, deterministic_proposal_id, validate_proposal_schema
from lib.performance_ledger import compile_ledger, repo_root, rollup_skill_metrics, rollup_provider_metrics


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


# ---------------------------------------------------------------------------
# Phase 2 — pattern detection (skill overrides, provider drift, dormant primitives)
# ---------------------------------------------------------------------------

# Finding shape shared by all three detectors.
# {kind, subject_id, severity, evidence_window, current_value, baseline_value, suggested_action}

_OVERRIDE_DELTA_THRESHOLD = 0.15   # override_rate increase that triggers P2
_OVERRIDE_SPIKE_THRESHOLD = 0.40   # absolute override_rate that triggers P1
_TRUST_DROP_THRESHOLD = 0.10       # trust_pass_rate drop that triggers detection
_FALLBACK_DELTA_THRESHOLD = 0.10   # fallback_rate increase that triggers P2
_FALLBACK_SPIKE_THRESHOLD = 0.30   # absolute fallback_rate that triggers P1
_LATENCY_DELTA_RATIO = 0.25        # relative latency increase that triggers detection


def _partition_events_by_window(
    events: list[dict[str, Any]],
    baseline_window: tuple[datetime, datetime],
    current_window: tuple[datetime, datetime],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split events into baseline and current lists by timestamp."""
    from lib.performance_ledger import _parse_ts

    baseline_events: list[dict[str, Any]] = []
    current_events: list[dict[str, Any]] = []
    for event in events:
        ts_str = event.get("timestamp") or event.get("ts") or ""
        ts = _parse_ts(ts_str)
        if ts is None:
            continue
        if baseline_window[0] <= ts <= baseline_window[1]:
            baseline_events.append(event)
        elif current_window[0] <= ts <= current_window[1]:
            current_events.append(event)
    return baseline_events, current_events


def _group_by_subject(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group events by skill/provider subject_id."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        subject = (
            event.get("skill")
            or (event.get("payload") or {}).get("skill_name")
            or event.get("chosen_provider")
            or event.get("primitive")
            or event.get("model")
            or "unknown"
        )
        groups.setdefault(subject, []).append(event)
    return groups


def detect_skill_override_patterns(
    events: list[dict[str, Any]],
    baseline_window: tuple[datetime, datetime],
    current_window: tuple[datetime, datetime],
) -> list[dict[str, Any]]:
    """Detect skills whose override_rate increased substantially window-over-window
    or whose trust_pass_rate dropped.

    Returns a list of findings with shape:
      {kind, subject_id, severity, evidence_window, current_value, baseline_value, suggested_action}
    """
    baseline_events, current_events = _partition_events_by_window(events, baseline_window, current_window)
    baseline_groups = _group_by_subject(baseline_events)
    current_groups = _group_by_subject(current_events)

    all_subjects = set(baseline_groups) | set(current_groups)
    findings: list[dict[str, Any]] = []

    for subject in sorted(all_subjects):
        b_rollup = rollup_skill_metrics(baseline_groups.get(subject, []))
        c_rollup = rollup_skill_metrics(current_groups.get(subject, []))

        if not b_rollup or not c_rollup:
            continue

        b_metrics = b_rollup.get("metrics", {})
        c_metrics = c_rollup.get("metrics", {})

        b_override = float(b_metrics.get("override_rate") or 0.0)
        c_override = float(c_metrics.get("override_rate") or 0.0)
        delta_override = c_override - b_override

        # Determine severity for override drift
        if c_override >= _OVERRIDE_SPIKE_THRESHOLD:
            sev = "P1"
        elif delta_override >= _OVERRIDE_DELTA_THRESHOLD:
            sev = "P2"
        else:
            sev = None

        if sev:
            findings.append({
                "kind": "skill_override_rate_increase",
                "subject_id": subject,
                "severity": sev,
                "evidence_window": {
                    "baseline_start": baseline_window[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "baseline_end": baseline_window[1].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "current_start": current_window[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "current_end": current_window[1].strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
                "current_value": c_override,
                "baseline_value": b_override,
                "suggested_action": (
                    f"Investigate why skill '{subject}' is being bypassed more frequently. "
                    "Review routing rules, trust gate configuration, or skill output quality."
                ),
            })

        # Check trust_pass_rate drop (only when both windows have data)
        b_trust = b_metrics.get("trust_pass_rate")
        c_trust = c_metrics.get("trust_pass_rate")
        if b_trust is not None and c_trust is not None:
            delta_trust = float(b_trust) - float(c_trust)
            if delta_trust >= _TRUST_DROP_THRESHOLD:
                findings.append({
                    "kind": "skill_trust_pass_rate_drop",
                    "subject_id": subject,
                    "severity": "P2" if delta_trust >= 0.20 else "P3",
                    "evidence_window": {
                        "baseline_start": baseline_window[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "baseline_end": baseline_window[1].strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "current_start": current_window[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "current_end": current_window[1].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    },
                    "current_value": float(c_trust),
                    "baseline_value": float(b_trust),
                    "suggested_action": (
                        f"Skill '{subject}' trust_pass_rate dropped by {delta_trust:.2f}. "
                        "Review trust gate thresholds or skill output reliability."
                    ),
                })

    return findings


def detect_provider_fallback_drift(
    events: list[dict[str, Any]],
    baseline_window: tuple[datetime, datetime],
    current_window: tuple[datetime, datetime],
) -> list[dict[str, Any]]:
    """Detect providers whose fallback_rate grew sustainably or latency degraded.

    Returns a list of findings with shape:
      {kind, subject_id, severity, evidence_window, current_value, baseline_value, suggested_action}
    """
    baseline_events, current_events = _partition_events_by_window(events, baseline_window, current_window)
    baseline_groups = _group_by_subject(baseline_events)
    current_groups = _group_by_subject(current_events)

    all_subjects = set(baseline_groups) | set(current_groups)
    findings: list[dict[str, Any]] = []

    for subject in sorted(all_subjects):
        b_rollup = rollup_provider_metrics(baseline_groups.get(subject, []))
        c_rollup = rollup_provider_metrics(current_groups.get(subject, []))

        if not b_rollup or not c_rollup:
            continue

        b_metrics = b_rollup.get("metrics", {})
        c_metrics = c_rollup.get("metrics", {})

        b_fallback = float(b_metrics.get("fallback_rate") or 0.0)
        c_fallback = float(c_metrics.get("fallback_rate") or 0.0)
        delta_fallback = c_fallback - b_fallback

        # Severity: spike or sustained drift
        if c_fallback >= _FALLBACK_SPIKE_THRESHOLD:
            sev = "P1"
        elif delta_fallback >= _FALLBACK_DELTA_THRESHOLD:
            sev = "P2"
        else:
            sev = None

        if sev:
            findings.append({
                "kind": "provider_fallback_rate_increase",
                "subject_id": subject,
                "severity": sev,
                "evidence_window": {
                    "baseline_start": baseline_window[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "baseline_end": baseline_window[1].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "current_start": current_window[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "current_end": current_window[1].strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
                "current_value": c_fallback,
                "baseline_value": b_fallback,
                "suggested_action": (
                    f"Provider '{subject}' fallback rate increased by {delta_fallback:.2f}. "
                    "Check provider health, quota limits, and routing configuration."
                ),
            })

        # Check latency degradation when both windows have data
        b_lat = b_metrics.get("latency_ms_avg")
        c_lat = c_metrics.get("latency_ms_avg")
        if b_lat is not None and c_lat is not None and float(b_lat) > 0:
            lat_ratio = (float(c_lat) - float(b_lat)) / float(b_lat)
            if lat_ratio >= _LATENCY_DELTA_RATIO:
                findings.append({
                    "kind": "provider_latency_degradation",
                    "subject_id": subject,
                    "severity": "P1" if lat_ratio >= 0.50 else "P2",
                    "evidence_window": {
                        "baseline_start": baseline_window[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "baseline_end": baseline_window[1].strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "current_start": current_window[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "current_end": current_window[1].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    },
                    "current_value": float(c_lat),
                    "baseline_value": float(b_lat),
                    "suggested_action": (
                        f"Provider '{subject}' average latency increased by {lat_ratio*100:.0f}%. "
                        "Investigate provider capacity, network conditions, or model size changes."
                    ),
                })

    return findings


def detect_dormant_no_evidence(
    primitives_yaml_path: Path,
    events: list[dict[str, Any]],
    window_days: int = 30,
) -> list[dict[str, Any]]:
    """Detect primitives in lifecycle.yaml whose subject_id has no event activity
    in the last ``window_days`` days.

    A primitive is flagged as dormant when:
      - It exists in the lifecycle YAML under ``primitives[].id``
      - Zero events reference its id in the last window_days days

    Returns a list of findings with shape:
      {kind, subject_id, severity, evidence_window, current_value, baseline_value, suggested_action}
    """
    from lib.performance_ledger import _parse_ts

    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    window_label = {
        "start": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": window_days,
    }

    # Parse lifecycle yaml
    try:
        raw = yaml.safe_load(primitives_yaml_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []

    primitives_list = raw.get("primitives") or []

    # Collect all subject IDs seen in events within the window
    active_ids: set[str] = set()
    for event in events:
        ts_str = event.get("timestamp") or event.get("ts") or ""
        ts = _parse_ts(ts_str)
        if ts is None or ts < cutoff:
            continue
        # Collect any field that could be a primitive subject reference
        for field in ("primitive_id", "primitive", "subject_id", "id"):
            val = event.get(field)
            if val and isinstance(val, str):
                active_ids.add(val)

    findings: list[dict[str, Any]] = []
    for prim in primitives_list:
        prim_id = prim.get("id") or prim.get("subject_id") or ""
        if not prim_id:
            continue
        if prim_id in active_ids:
            continue

        lifecycle_state = prim.get("lifecycle_state") or prim.get("maturity") or "unknown"
        # Only flag dormant/aspirational states (not 'active' primitives with no telemetry
        # because they may be triggered rarely but correctly)
        if lifecycle_state in ("active",):
            sev = "P3"
        elif lifecycle_state in ("advisory", "aspirational", "dormant"):
            sev = "P2"
        else:
            sev = "P3"

        findings.append({
            "kind": "primitive_dormant_no_evidence",
            "subject_id": prim_id,
            "severity": sev,
            "evidence_window": window_label,
            "current_value": 0,         # events seen in window
            "baseline_value": None,     # no baseline comparison applicable
            "suggested_action": (
                f"Primitive '{prim_id}' (lifecycle_state={lifecycle_state}) has no evidence "
                f"in the last {window_days} days. Consider retiring, demoting to aspirational, "
                "or adding an evidence_commands test to verify it fires."
            ),
        })

    return findings


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
