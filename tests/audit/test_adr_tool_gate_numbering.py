"""Regression tests for ADR-214/ADR-216 tool-gate numbering.

ADR-214 is a tombstone from a parallel-session collision. The accepted Tool
Discovery Pre-Use Gate lives at ADR-216. Agents must not keep citing
"ADR-214 tool gate" as if it were canonical.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.audit

REPO_ROOT = Path(__file__).resolve().parents[2]
ADR_214 = REPO_ROOT / "docs" / "adrs" / "ADR-214-tombstone.md"
ADR_216 = REPO_ROOT / "docs" / "adrs" / "ADR-216-tool-discovery-pre-use-gate.md"

SEARCH_ROOTS = [
    REPO_ROOT / "docs",
    REPO_ROOT / "manifests",
    REPO_ROOT / "scripts",
    REPO_ROOT / "tests",
]


def _tracked_text_files() -> list[Path]:
    files: list[Path] = []
    self_file = Path(__file__).resolve()
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.resolve() == self_file:
                continue
            if any(part == "__pycache__" for part in path.parts):
                continue
            if path.suffix in {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf"}:
                continue
            files.append(path)
    return files


def test_tool_discovery_gate_canonical_adr_is_216() -> None:
    assert ADR_214.exists()
    assert ADR_216.exists()

    tombstone = ADR_214.read_text(encoding="utf-8")
    canonical = ADR_216.read_text(encoding="utf-8")

    assert "status: tombstone" in tombstone
    assert "ADR-216 — Tool Discovery Pre-Use Gate" in canonical
    assert "ADR-216 — Tool Discovery Pre-Use Gate" in tombstone


def test_no_non_tombstone_reference_claims_adr_214_tool_gate() -> None:
    offenders: list[str] = []
    bad_phrases = [
        "ADR-214 tool gate",
        "ADR-214 Tool Gate",
        "ADR-214 Tool Discovery",
        "ADR-214-tool-discovery",
        "ADR-214-tool-gate",
    ]
    for path in _tracked_text_files():
        if path == ADR_214:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for phrase in bad_phrases:
            if phrase in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {phrase}")

    assert not offenders, (
        "ADR-214 is a tombstone; cite ADR-216 for Tool Discovery Pre-Use Gate:\n"
        + "\n".join(offenders)
    )
