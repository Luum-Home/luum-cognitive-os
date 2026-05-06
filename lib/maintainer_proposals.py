"""Maintainer proposal helpers for ADR-201.

This module contains deterministic identifiers and small schema helpers shared by
future `PromoteFromTelemetry` and Maintainer runner slices.
"""
from __future__ import annotations

import hashlib
import re


PROPOSAL_SCHEMA_VERSION = "maintainer-proposal/v1"


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "unknown"


def deterministic_proposal_id(surface: str, degradation_pattern: str, day_window: str) -> str:
    """Return a stable proposal id for duplicate suppression.

    ADR-201 defines the identity as a hash of surface + degradation pattern +
    day window. The human-readable prefix keeps review queues debuggable while
    the hash prevents accidental collisions between similarly named surfaces.
    """
    material = "\0".join([surface.strip(), degradation_pattern.strip(), day_window.strip()])
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"perf-ledger-{_slug(surface)}-{_slug(degradation_pattern)}-{_slug(day_window)}-{digest}"


REQUIRED_PROPOSAL_FIELDS = {
    "schema_version",
    "proposal_id",
    "severity",
    "self_confidence",
    "surface",
    "harness_scope",
    "source_metric_streams",
    "source_event_refs",
    "affected_primitive",
    "degradation_pattern",
    "candidate_action",
    "allowed_write_paths",
    "blocked_write_paths",
    "tests_required",
    "rollback_plan",
    "cooldown_after_apply",
    "related_proposals",
    "experiment_design",
    "expected_impact_metric",
    "post_change_measurement_window",
    "human_approval_required",
    "outcome_on_regression",
}


def validate_proposal_schema(proposal: dict) -> None:
    missing = sorted(REQUIRED_PROPOSAL_FIELDS - set(proposal))
    if missing:
        raise ValueError(f"maintainer proposal missing required fields: {', '.join(missing)}")
    if proposal.get("schema_version") != PROPOSAL_SCHEMA_VERSION:
        raise ValueError("unsupported maintainer proposal schema_version")
    if proposal.get("severity") not in {"P0", "P1", "P2", "P3"}:
        raise ValueError("maintainer proposal severity must be P0/P1/P2/P3")
    confidence = float(proposal.get("self_confidence"))
    if confidence < 0 or confidence > 1:
        raise ValueError("maintainer proposal self_confidence must be between 0 and 1")
    if not isinstance(proposal.get("experiment_design"), dict):
        raise ValueError("maintainer proposal experiment_design must be an object")
