# SCOPE: os-only
"""Tests for lib/research_quality_advisor.py (ADR-175).

Three guarantees verified against the 2026-05-05 audit reports:

(a) The 3 sonnet audits score lower than the 3 opus audits.
(b) The user-driven rebuttal scores >= 60.
(c) Asymmetric-row detection catches the "Command Groups was asserted
    without verification" pattern (one-sided file:line).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.research_quality_advisor import (
    ResearchQualityAdvisor,
    score_file,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "docs" / "reports"


SONNET_AUDITS = [
    REPORTS / "openharness-deep-audit-2026-05-05.md",
    REPORTS / "openspace-deep-audit-2026-05-05.md",
    REPORTS / "cli-anything-deep-audit-2026-05-05.md",
]

OPUS_AUDITS = [
    REPORTS / "openharness-opus-deep-audit-2026-05-05.md",
    REPORTS / "openspace-opus-deep-audit-2026-05-05.md",
    REPORTS / "cli-anything-opus-deep-audit-2026-05-05.md",
]

REBUTTAL = REPORTS / "cos-side-deep-rebuttal-2026-05-05.md"


def _avg(reports):
    return sum(score_file(p).overall_score for p in reports) / len(reports)


def test_sonnet_avg_below_opus_avg():
    """Opus audits should score higher overall than the original sonnet audits."""
    sonnet_avg = _avg(SONNET_AUDITS)
    opus_avg = _avg(OPUS_AUDITS)
    # Opus audits use confidence markers + explicit numerical commands +
    # falsifiability sections — they MUST out-score sonnet.
    assert opus_avg > sonnet_avg, (
        f"Expected opus avg > sonnet avg, got opus={opus_avg:.1f} sonnet={sonnet_avg:.1f}"
    )


def test_rebuttal_at_least_60():
    """The rebuttal report introduced symmetric depth; should score >= 60."""
    if not REBUTTAL.exists():
        pytest.skip("rebuttal report missing")
    report = score_file(REBUTTAL)
    assert report.overall_score >= 60, (
        f"Rebuttal scored {report.overall_score:.1f}, expected >= 60. "
        f"Findings: {[d.findings for d in report.dimensions]}"
    )


def test_detects_asymmetric_row():
    """A row with file:line on one side and hand-wavy prose on the other
    must be counted as asymmetric (the 2026-05-05 bug)."""
    sample = """# Test
| Dimension | COS | External | Verdict |
|---|---|---|---|
| Hook surface | scripts/_lib/settings-driver-claude-code.sh:119-425 wires 10 events | several events roughly | IGUAL |
| MCP | mcp-server/cos_mcp.py:1-780 publisher with 8 tools | various tools approximately | IGUAL |
"""
    report = ResearchQualityAdvisor().score(sample)
    assert report.total_rows >= 2
    assert report.asymmetric_rows >= 1, (
        f"Expected asymmetric rows >= 1, got {report.asymmetric_rows}"
    )
    sym = next(d for d in report.dimensions if d.name == "symmetric_citation")
    assert sym.score < 80


def test_high_quality_synthetic_scores_high():
    sample = """# Synthetic high-quality report

## Methodology

Numbers were extracted with the captured commands below.

```bash
grep -c CanonicalEvent lib/harness_adapter/base.py
# 11
```

## Per-dimension

| Dimension | A side | B side | Verdict |
|---|---|---|---|
| Events | a/file.py:23-100 has 11 events | b/file.py:5-50 has 10 events | IGUAL |
| Providers | a/file.py:1-65 lists 7 providers | b/file.py:5-200 lists 22 providers | B MEJOR |

## Verdict

**Confidence: HIGH.** Evidence is symmetric and reproducible.

## Uncertainties

- Heuristic regex may miss cases where evidence is semantically present.
- Threshold 70 chosen by convention.
"""
    report = ResearchQualityAdvisor().score(sample)
    assert report.overall_score >= 70, report.to_jsonable()
    assert report.asymmetric_rows == 0


def test_to_jsonable_shape():
    report = ResearchQualityAdvisor().score("# Empty")
    blob = report.to_jsonable()
    assert "overall_score" in blob
    assert "dimensions" in blob
    assert len(blob["dimensions"]) == 4
    weights = sum(d["weight"] for d in blob["dimensions"])
    assert abs(weights - 1.0) < 1e-6


def test_governance_audit_mode_scores_policy_reports_without_command_overfit():
    sample = """# Governance boundary audit

## Context

This ADR governance review evaluates policy, boundary, risk, consequence, and alternative fit.

| Decision area | Evidence | Governance reading | Confidence |
|---|---|---|---|
| Boundary | docs/02-Decisions/adrs/ADR-170-operator-cli-as-primary-ui-surface.md:1-40 defines the prior UI decision | docs/02-Decisions/adrs/ADR-172-multi-surface-ui-architecture.md:1-70 changes the accepted positioning | Confidence: HIGH |
| Risk | docs/02-Decisions/adrs/ADR-125-governance-tools-value-boundary.md:20-55 names false-positive governance cost | docs/02-Decisions/adrs/ADR-188-orchestrator-skill-invocation-gate.md:1-80 requires guardrails | Confidence: MEDIUM |

## Verdict

Confidence: HIGH. The recommendation is to keep this as a governance decision, not a mechanical implementation audit.

## Alternatives rejected

- Treating this as a grep-only implementation check would miss decision intent.
- Creating ADR 999 immediately would increase scope creep.

## Uncertainties

- The policy may change if the release boundary changes.
- The numeric ADR references above are identifiers, not measured counts.
"""
    report = ResearchQualityAdvisor().score(sample)
    assert report.audit_mode == "governance"
    assert report.overall_score >= 70, report.to_jsonable()
    weights = {d.name: d.weight for d in report.dimensions}
    assert weights["falsifiable_claim"] > weights["numerical_specificity"]


def test_mechanical_mode_still_penalizes_uncited_implementation_claims():
    sample = """# Mechanical hook audit

## Summary

Confidence: HIGH. This implementation is complete and robust.

| Surface | COS | External | Verdict |
|---|---|---|---|
| Hooks | many hooks approximately do the same thing | several scripts probably implement it | IGUAL |
| Tests | lots of tests exist | some tests exist | IGUAL |

## Uncertainties

- Could be wrong if grep missed files.
"""
    report = ResearchQualityAdvisor(audit_mode="mechanical").score(sample)
    assert report.audit_mode == "mechanical"
    assert report.overall_score < 70, report.to_jsonable()
