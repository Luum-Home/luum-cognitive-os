from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_adr_004_is_not_used_as_license_decision_reference() -> None:
    path = ROOT / "docs" / "business" / "open-source-design.md"
    text = path.read_text(encoding="utf-8")
    assert "### ADR-004: FSL-1.1-MIT License" not in text
    assert "ADR-004 is a tombstone/reserved slot" in text


def test_homebrew_formula_uses_cannot_represent_for_fsl() -> None:
    formula = (ROOT / "Formula" / "cognitive-os.rb").read_text(encoding="utf-8")
    assert "license :cannot_represent" in formula
    assert "license \"FSL-1.1-MIT\"" not in formula


def test_goreleaser_cask_does_not_emit_invalid_fsl_spdx_license() -> None:
    config = yaml.safe_load((ROOT / ".goreleaser.yaml").read_text(encoding="utf-8"))
    casks = config.get("homebrew_casks") or []
    assert casks, "expected homebrew_casks config"
    for cask in casks:
        assert cask.get("license") != "FSL-1.1-MIT"
        assert "FSL-1.1-MIT" in cask.get("caveats", "")
