from __future__ import annotations

from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]


@pytest.mark.contract
def test_publication_safety_contract_files_exist() -> None:
    for rel in [
        "lib/publication_safety.py",
        "scripts/cos-publication-safety",
        "hooks/publication-safety.sh",
        "manifests/publication-safety.yaml",
        "docs/04-Concepts/architecture/publication-safety-receipt-v0.md",
        "docs/02-Decisions/adrs/ADR-333-publication-safety-primitive.md",
    ]:
        assert (REPO / rel).exists(), rel


@pytest.mark.contract
def test_publication_safety_docs_use_agentic_primitive_not_component() -> None:
    docs = [
        REPO / "docs/04-Concepts/architecture/publication-safety-receipt-v0.md",
        REPO / "docs/02-Decisions/adrs/ADR-333-publication-safety-primitive.md",
    ]
    for path in docs:
        text = path.read_text(encoding="utf-8").lower()
        assert "os component" not in text
        assert "primitive" in text


@pytest.mark.contract
def test_publication_safety_core_does_not_hardcode_harness_paths() -> None:
    text = "\n".join(
        (REPO / rel).read_text(encoding="utf-8")
        for rel in [
            "lib/publication_safety.py",
            "scripts/cos-publication-safety",
            "hooks/publication-safety.sh",
            "manifests/publication-safety.yaml",
        ]
    )
    forbidden = [
        "luum-agent-harness",
        "scripts/pre-publication-gate",
        "public-readiness-audit.py",
        "history-publication-readiness-audit",
        "env-variables-check.py",
    ]
    for token in forbidden:
        assert token not in text


@pytest.mark.contract
def test_publication_safety_registered_in_cognitive_os_config() -> None:
    text = (REPO / "cognitive-os.yaml").read_text(encoding="utf-8")
    assert "publication-safety:" in text
    assert "hooks/publication-safety.sh" in text
