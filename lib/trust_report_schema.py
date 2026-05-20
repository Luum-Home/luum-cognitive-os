# SCOPE: os-only
"""trust_report_schema.py — ADR-038 Wave 3 Pydantic v2 TrustReport model.

Defines the canonical structured schema for the TRUST_REPORT block emitted
by sub-agents at the end of every completion (see templates/agent-preamble.md
and rules/trust-score.md for the authoritative policy).

Usage:
    from lib.trust_report_schema import TrustReport, build_trust_report

    report = TrustReport(
        score=82,
        status="MEDIUM",
        evidence_count=4,
        uncertainty_count=2,
        verified=["All unit tests pass", "Lint clean"],
        unsure=["Coverage not measured", "Concurrent behaviour untested"],
        human_should_check=["Run integration tests"],
    )

    # Or build from the raw header fields + section lists:
    report = build_trust_report(
        score=82,
        verified=[...],
        unsure=[...],
        human_should_check=[...],
    )

Status band policy (rules/trust-score.md):
    HIGH     90-100
    MEDIUM   70-89
    LOW      50-69
    CRITICAL  0-49

Design note: the model-validator enforces band consistency so that a report
with SCORE=95 STATUS=LOW is rejected at construction time. This lets
downstream consumers trust the status field without re-computing it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Status band boundaries — single source of truth, used by schema + parser.
# ---------------------------------------------------------------------------
_BAND_TABLE: list[tuple[int, str]] = [
    (90, "HIGH"),
    (70, "MEDIUM"),
    (50, "LOW"),
    (0, "CRITICAL"),
]


def score_to_status(score: int) -> Literal["HIGH", "MEDIUM", "LOW", "CRITICAL"]:
    """Return the canonical status label for a numeric trust score.

    Boundaries (inclusive lower, exclusive upper) match rules/trust-score.md:
        HIGH     90-100
        MEDIUM   70-89
        LOW      50-69
        CRITICAL  0-49
    """
    for threshold, label in _BAND_TABLE:
        if score >= threshold:
            return label  # type: ignore[return-value]
    return "CRITICAL"  # unreachable; satisfies type checker


# ---------------------------------------------------------------------------
# Pydantic v2 model
# ---------------------------------------------------------------------------

class TrustReport(BaseModel):
    """Structured representation of an agent TRUST_REPORT block.

    Fields mirror the machine-parseable header plus the three human-readable
    sections (WHAT I VERIFIED / UNSURE ABOUT / HUMAN SHOULD CHECK).

    Constraints enforced at construction:
    - score must be 0-100 inclusive
    - uncertainty_count must be >= 1 (agents MUST list at least one doubt)
    - status must be consistent with score's band
    - evidence_count must be >= 0
    """

    score: int
    status: Literal["HIGH", "MEDIUM", "LOW", "CRITICAL"]
    evidence_count: int
    uncertainty_count: int
    verified: list[str]
    unsure: list[str]
    human_should_check: list[str]

    # ------------------------------------------------------------------
    # Field-level validators
    # ------------------------------------------------------------------

    @field_validator("score")
    @classmethod
    def score_in_range(cls, v: int) -> int:
        if not (0 <= v <= 100):
            raise ValueError(
                f"RANGE_ERROR: score={v} is outside the allowed range 0-100. "
                "Adjust the score to a value between 0 and 100 inclusive."
            )
        return v

    @field_validator("evidence_count")
    @classmethod
    def evidence_count_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(
                f"RANGE_ERROR: evidence_count={v} must be >= 0. "
                "Evidence count cannot be negative."
            )
        return v

    @field_validator("uncertainty_count")
    @classmethod
    def uncertainty_count_at_least_one(cls, v: int) -> int:
        if v < 1:
            raise ValueError(
                "MISSING_UNCERTAINTY: uncertainty_count must be >= 1. "
                "Per rules/trust-score.md, '100%% confident' is a RED FLAG — "
                "every agent MUST list at least one honest doubt. "
                "Add at least one item to the UNSURE ABOUT section."
            )
        return v

    # ------------------------------------------------------------------
    # Cross-field validator: score ↔ status band consistency
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def status_matches_score_band(self) -> "TrustReport":
        expected = score_to_status(self.score)
        if self.status != expected:
            raise ValueError(
                f"BAND_MISMATCH: score={self.score} belongs to band {expected!r} "
                f"but status={self.status!r} was given. "
                f"Fix status to {expected!r} or adjust the score. "
                f"Bands: HIGH 90-100, MEDIUM 70-89, LOW 50-69, CRITICAL 0-49."
            )
        return self

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def header_line(self) -> str:
        """Return the machine-parseable TRUST_REPORT: header string."""
        return (
            f"TRUST_REPORT: SCORE={self.score} STATUS={self.status} "
            f"EVIDENCE={self.evidence_count} UNCERTAINTIES={self.uncertainty_count}"
        )

    def as_text(self) -> str:
        """Render a full human-readable Trust Report block."""
        verified_lines = "\n".join(f"  - {item}" for item in self.verified) or "  (none)"
        unsure_lines = "\n".join(f"  - {item}" for item in self.unsure) or "  (none)"
        check_lines = "\n".join(f"  - {item}" for item in self.human_should_check) or "  (none)"
        return (
            f"{self.header_line()}\n"
            "---\n"
            f"Score: {self.score}/100\n"
            "\n"
            "WHAT I VERIFIED:\n"
            f"{verified_lines}\n"
            "\n"
            "UNSURE ABOUT:\n"
            f"{unsure_lines}\n"
            "\n"
            "HUMAN SHOULD CHECK:\n"
            f"{check_lines}\n"
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_trust_report(
    score: int,
    verified: list[str],
    unsure: list[str],
    human_should_check: list[str],
    *,
    evidence_count: int | None = None,
    uncertainty_count: int | None = None,
) -> TrustReport:
    """Construct a TrustReport, auto-deriving status and counts when omitted.

    Args:
        score: Numeric trust score (0-100).
        verified: List of verified items (WHAT I VERIFIED section).
        unsure: List of uncertainty items (UNSURE ABOUT section).
        human_should_check: List of items for human review.
        evidence_count: If omitted, defaults to len(verified).
        uncertainty_count: If omitted, defaults to len(unsure).

    Returns:
        Validated TrustReport instance.

    Raises:
        pydantic.ValidationError: If any field violates constraints.
    """
    return TrustReport(
        score=score,
        status=score_to_status(score),
        evidence_count=evidence_count if evidence_count is not None else len(verified),
        uncertainty_count=uncertainty_count if uncertainty_count is not None else len(unsure),
        verified=verified,
        unsure=unsure,
        human_should_check=human_should_check,
    )
