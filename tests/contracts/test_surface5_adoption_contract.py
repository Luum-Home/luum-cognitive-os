from __future__ import annotations

from pathlib import Path

import pytest

from lib.surface5_adoption_contract import REQUIRED_PROOF_SECTIONS, check_surface5_adoption_contract

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
ADR = REPO / "docs" / "adrs" / "ADR-187-surface-5-adoption-proof-contract.md"


def test_surface5_adoption_contract_requires_source_level_proof() -> None:
    text = ADR.read_text(encoding="utf-8")
    result = check_surface5_adoption_contract(text)
    assert result.ok is True
    assert result.missing == []
    assert result.otel_phoenix_are_observability is True


def test_contract_validator_reports_missing_proof_sections() -> None:
    result = check_surface5_adoption_contract("OTel and Phoenix are not the adoption proof")
    assert result.ok is False
    assert result.missing == REQUIRED_PROOF_SECTIONS
    assert result.otel_phoenix_are_observability is True
