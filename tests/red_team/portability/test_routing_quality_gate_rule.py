# SCOPE: os-only
"""Portability proof for rules/routing-quality-gate.md."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "rules/routing-quality-gate.md"


def test_routing_quality_gate_rule_loads_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: routing guidance must be consumer-neutral markdown."""
    target = tmp_path / "rules" / ARTIFACT.name
    target.parent.mkdir(parents=True)
    target.write_text(ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")

    text = target.read_text(encoding="utf-8")

    assert "SCOPE: os-only" in text
    assert "scripts/cos-routing-max-gate" in text
    assert str(REPO_ROOT) not in text
