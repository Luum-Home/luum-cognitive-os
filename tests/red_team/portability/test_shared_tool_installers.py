"""Portability proof for shared optional tool installer primitives."""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
INSTALLERS = [
    "scripts/install-aguara.sh",
    "scripts/install-credibility-tools.sh",
    "scripts/install-garak.sh",
    "scripts/install-mcp-scan.sh",
    "scripts/install-promptfoo.sh",
    "scripts/install-syft-grype.sh",
    "scripts/install-tob-skills.sh",
    "scripts/install-trivy.sh",
]


def test_shared_installers_are_manual_optional_and_not_checkout_bound() -> None:
    for rel in INSTALLERS:
        text = (REPO / rel).read_text(encoding="utf-8")
        assert "SCOPE: both" in "\n".join(text.splitlines()[:4])
        assert "/Users/" not in text
        assert "matias" not in text.lower()
        assert any(token in text.lower() for token in ("install", "manual-trigger", "optional", "next steps")), rel
