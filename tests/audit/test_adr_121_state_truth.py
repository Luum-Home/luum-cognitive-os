"""Audit ADR-121 Wave 5 residual-state truth in backlog docs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.audit

REPO = Path(__file__).resolve().parents[2]
ADR = REPO / "docs" / "02-Decisions" / "adrs" / "ADR-121-foundation-hardening-program.md"
PLAN = REPO / ".cognitive-os" / "plans" / "architecture" / "foundation-hardening-program.md"
POST_SESSION_BACKLOG = REPO / "docs" / "06-Daily" / "reports" / "post-session-backlog-2026-05-20.md"
PARTIAL_BACKLOG_JSON = REPO / "docs" / "06-Daily" / "reports" / "adr-partial-backlog-latest.json"

EXPECTED_RESIDUAL = (
    "program ADR is partial: Phase 1/2/4/5 acceptance is closed; "
    "residuals are Phase 6 ADR-118 swarm scenarios; Phase 3 domain/registry "
    "ownership inventory has an initial executable slice"
)
STALE_SUMMARIES = (
    "ADR-121 phases 3-6",
    "remaining phases stay open",
)


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    _empty, frontmatter, _body = text.split("---", 2)
    return yaml.safe_load(frontmatter)


def test_adr_121_partial_metadata_names_narrow_wave5_residuals() -> None:
    metadata = _frontmatter(ADR)

    assert metadata["implementation_status"] == "partial"
    assert metadata["classification_basis"] == EXPECTED_RESIDUAL
    assert metadata["partial_remaining"] == EXPECTED_RESIDUAL


def test_wave5_backlog_does_not_reintroduce_broad_adr_121_phase_range() -> None:
    docs = [ADR, PLAN, POST_SESSION_BACKLOG]
    offenders: list[str] = []
    for path in docs:
        text = path.read_text(encoding="utf-8")
        for stale in STALE_SUMMARIES:
            if stale in text:
                offenders.append(f"{path.relative_to(REPO)} contains {stale!r}")

    assert not offenders, "ADR-121 residuals must stay narrowed: " + "; ".join(offenders)


def test_generated_partial_backlog_matches_adr_121_metadata() -> None:
    payload = json.loads(PARTIAL_BACKLOG_JSON.read_text(encoding="utf-8"))
    rows = [item for item in payload["items"] if item["adr"] == "ADR-121"]

    assert len(rows) == 1
    row = rows[0]
    assert row["classification_basis"] == EXPECTED_RESIDUAL
    assert row["partial_remaining"] == EXPECTED_RESIDUAL
    assert row["remaining"] == EXPECTED_RESIDUAL
