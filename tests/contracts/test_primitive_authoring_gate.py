from __future__ import annotations

import json
from pathlib import Path

from scripts.portable_ai_overlay import build_overlay


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = REPO_ROOT / "skills" / "primitive-authoring" / "SKILL.md"


def _skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_primitive_authoring_gate_names_portable_standards_boundary() -> None:
    text = _skill_text()

    required_terms = [
        "COS canonical internal registry != consumer .ai overlay",
        "AGENTS.md",
        "SKILL.md",
        "VERSA / dotAIslash",
        "MCP, ACP, and A2A",
        "not equivalent to a portable primitive contract",
    ]

    for term in required_terms:
        assert term in text


def test_primitive_authoring_gate_requires_overlay_adapter_and_evidence_proof() -> None:
    text = _skill_text()

    required_terms = [
        "portable_contract",
        "primitive-contract-registry",
        "primitive-lifecycle-derived",
        "scripts/cos-portable-ai-overlay --check",
        "scripts/cos-adapters verify --json",
        "scripts/cos-observe-primitives --json",
        "host-plugin-lifecycle-capable",
        "Do not move canonical primitives physically into `.ai/`",
    ]

    for term in required_terms:
        assert term in text


def test_primitive_authoring_gate_matches_generated_overlay_contract_shape() -> None:
    overlay_files = build_overlay(REPO_ROOT)
    primitive_payloads = []

    for path, body in overlay_files.items():
        if path.startswith("primitives/") and path.endswith(".json"):
            primitive_payloads.append(json.loads(body))

    assert primitive_payloads, "expected generated primitive overlay rows"
    assert all("portable_contract" in payload for payload in primitive_payloads)

    sources = {payload["portable_contract"]["source"] for payload in primitive_payloads}
    assert "primitive-contract-registry" in sources
    assert "primitive-lifecycle-derived" in sources

    text = _skill_text()
    assert "primitive-contract-registry" in text
    assert "primitive-lifecycle-derived" in text
