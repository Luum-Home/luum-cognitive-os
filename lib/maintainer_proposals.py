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
