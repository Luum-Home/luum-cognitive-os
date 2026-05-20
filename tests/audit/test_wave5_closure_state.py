"""Audit Wave 5 structural ADR closure contracts.

The Wave 5 ADRs have executable slices, but none is formally closed yet. This
file prevents stale backlog prose from turning those slices into false closure.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.audit

REPO = Path(__file__).resolve().parents[2]
ADR_DIR = REPO / "docs" / "02-Decisions" / "adrs"
PARTIAL_BACKLOG_MD = REPO / "docs" / "06-Daily" / "reports" / "adr-partial-backlog-latest.md"
PARTIAL_BACKLOG_JSON = REPO / "docs" / "06-Daily" / "reports" / "adr-partial-backlog-latest.json"
POST_SESSION_BACKLOG = REPO / "docs" / "06-Daily" / "reports" / "post-session-backlog-2026-05-20.md"

EXPECTED_RESIDUALS = {
    "ADR-121": (
        "program ADR is partial: Phase 1/2/4/5 acceptance is closed; "
        "residuals are Phase 6 ADR-118 swarm scenarios; Phase 3 domain/registry "
        "ownership inventory has an initial executable slice"
    ),
    "ADR-291": (
        "phase-2-in-progress: 13 functional operations are live "
        "(health/version/agent options, 8 file-backed JSON session lifecycle/event "
        "endpoints, and 2 local sync query endpoints); remaining scope is 10 typed "
        "JSON 501 stubs, 3 SSE stub operations, full in-process agent-runner "
        "execution, models/runtime settings, CSRF, rate limiting, workspace/search, "
        "sharing, abort, and JSON-to-SQLite migration."
    ),
    "ADR-325": (
        "partial ADR-325 implementation: manifest/audit/preflight/language-token "
        "rule and Phase 2 taximeter exist; Phase 3 has context-budget and "
        "subagent-budget resource-ledger emission plus token-budget ledger reads. "
        "Remaining scope is provider actual-cost ingestion, ledger "
        "normalization/deduplication, preflight threshold enforcement, local "
        "fallback routing, and CI ratchets."
    ),
}

ADR_PATHS = {
    "ADR-121": ADR_DIR / "ADR-121-foundation-hardening-program.md",
    "ADR-291": ADR_DIR / "ADR-291-agent-runtime-web-service.md",
    "ADR-325": ADR_DIR / "ADR-325-ai-resource-economy-and-degradation.md",
}

CLOSURE_GATE_MARKERS = {
    "ADR-121": "ADR-118 swarm scenarios covering",
    "ADR-291": "Formal closure requires replacing the remaining 10 JSON",
    "ADR-325": "Formal closure requires\nprovider actual-cost ingestion",
}

STALE_PHRASES = (
    "ADR-121 phases 3-6",
    "11 functional operations are live",
    "12 typed JSON 501 stubs",
    "sync agent queries",
    "subagent-budget ledger integration",
    "initial context-budget resource-ledger emission",
)


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    _prefix, raw_frontmatter, _body = text.split("---", 2)
    return yaml.safe_load(raw_frontmatter)


def _partial_backlog_rows() -> dict[str, dict[str, object]]:
    payload = json.loads(PARTIAL_BACKLOG_JSON.read_text(encoding="utf-8"))
    return {item["adr"]: item for item in payload["items"] if item["adr"] in EXPECTED_RESIDUALS}


def test_wave5_adrs_remain_partial_until_formal_blockers_are_closed() -> None:
    for adr, path in ADR_PATHS.items():
        metadata = _frontmatter(path)
        assert metadata["implementation_status"] == "partial", adr
        assert metadata["partial_remaining"] == EXPECTED_RESIDUALS[adr], adr


def test_wave5_generated_backlog_matches_adr_residual_contracts() -> None:
    rows = _partial_backlog_rows()

    assert set(rows) == set(EXPECTED_RESIDUALS)
    for adr, expected in EXPECTED_RESIDUALS.items():
        row = rows[adr]
        assert row["implementation_status"] == "partial"
        assert row["classification_basis"] == expected
        assert row["partial_remaining"] == expected
        assert row["remaining"] == expected


def test_wave5_closure_gates_are_explicit_in_adr_docs() -> None:
    for adr, marker in CLOSURE_GATE_MARKERS.items():
        text = ADR_PATHS[adr].read_text(encoding="utf-8")
        assert "## Wave 5 closure gate" in text, adr
        assert marker in text, adr
        assert "is **not closed**" in text, adr


def test_wave5_backlog_no_longer_contains_stale_residual_phrases() -> None:
    docs = [*ADR_PATHS.values(), PARTIAL_BACKLOG_MD, PARTIAL_BACKLOG_JSON, POST_SESSION_BACKLOG]
    offenders: list[str] = []
    for path in docs:
        text = path.read_text(encoding="utf-8")
        for phrase in STALE_PHRASES:
            if phrase in text:
                offenders.append(f"{path.relative_to(REPO)} contains {phrase!r}")

    assert not offenders, "Wave 5 closure state drifted stale: " + "; ".join(offenders)


def test_op_stability_phase3_is_closed_before_wave5_exit_criteria_continue() -> None:
    text = POST_SESSION_BACKLOG.read_text(encoding="utf-8")

    assert "Op Stability Phase 3 — adaptive profiles resolver | DONE in continuation" in text
    assert "Wave 5 backlog:" in text
