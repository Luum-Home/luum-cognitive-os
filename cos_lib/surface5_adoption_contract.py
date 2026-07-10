# SCOPE: both
"""Validator for ADR-187 Surface 5 adoption proof packs."""
from __future__ import annotations

from dataclasses import dataclass

REQUIRED_PROOF_SECTIONS = [
    "Candidate identity",
    "Source-level reading",
    "COS fit matrix",
    "Integration boundary",
    "Reversibility plan",
    "Security/licensing proof",
    "Performance/context proof",
    "Falsifiable claim",
]


@dataclass(frozen=True)
class Surface5ContractCheck:
    ok: bool
    missing: list[str]
    otel_phoenix_are_observability: bool


def check_surface5_adoption_contract(text: str) -> Surface5ContractCheck:
    """Validate that a Surface 5 adoption contract carries the minimum proof pack."""
    missing = [section for section in REQUIRED_PROOF_SECTIONS if section not in text]
    observability = all(term in text for term in ["OTel", "Phoenix", "not the", "adoption proof"])
    return Surface5ContractCheck(ok=not missing and observability, missing=missing, otel_phoenix_are_observability=observability)
