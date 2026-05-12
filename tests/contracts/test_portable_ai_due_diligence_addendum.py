"""ADR-258 due-diligence addendum must keep standards boundaries explicit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.portable_ai_overlay import build_overlay

REPORT = REPO_ROOT / "docs" / "reports" / "portable-ai-primitive-standards-due-diligence-2026-05-09.md"
ADR = REPO_ROOT / "docs" / "adrs" / "ADR-258-portable-ai-overlay-for-agentic-primitives.md"

REQUIRED_CLASSIFICATIONS = [
    ".ai` / VERSA / dotAIslash",
    "`AGENTS.md`",
    "`SKILL.md` / Agent Skills",
    "MCP",
    "ACP",
    "A2A",
    "COS primitive registry",
    "Consumer `.ai` overlay",
]


def test_due_diligence_report_classifies_standards_and_protocols() -> None:
    text = REPORT.read_text(encoding="utf-8")
    assert "## Due-diligence addendum: standard classification" in text
    for token in REQUIRED_CLASSIFICATIONS:
        assert token in text
    assert "COS canonical internal registry != consumer `.ai` overlay" in text
    assert "MCP" in text and "not a primitive registry" in text
    assert "ACP" in text and "not a primitive source of truth" in text
    assert "A2A" in text and "not IDE primitive projection" in text


def test_adr_258_records_canonical_registry_vs_overlay_invariant() -> None:
    text = ADR.read_text(encoding="utf-8")
    assert "## Due-diligence addendum" in text
    assert "COS canonical internal registry != consumer .ai overlay" in text
    assert "Internal canonical registry" in text or "Internal canonical sources remain" in text
    assert "Generated consumer export" in text
    assert "not allowed to invent primitive behavior" in text


def test_overlay_generator_preserves_due_diligence_boundary_in_output() -> None:
    files = build_overlay(REPO_ROOT)
    context = json.loads(files["context.json"])
    assert context["status"] == "generated-portable-overlay"
    assert "manifests/primitive-contracts.yaml" in context["canonical_source_of_truth"]
    assert ("generated" in context["policy"] and "overlay" in context["policy"])
    primitive_rows = [json.loads(body) for path, body in files.items() if path.startswith("primitives/") and path.endswith(".json")]
    assert primitive_rows
    assert {row["canonical_source_kind"] for row in primitive_rows} == {"cos-internal"}
    assert {row["overlay_role"] for row in primitive_rows} == {"generated-reference"}
