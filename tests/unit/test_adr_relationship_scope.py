from __future__ import annotations

from pathlib import Path

import pytest

from scripts.audit_adrs import (
    CODE_ADR_RELATION_CHAIN_LONG,
    CODE_ADR_RELATION_CYCLE,
    _collect_adr_files,
    _relationship_refs,
    analyze_relationship_graph,
)

pytestmark = pytest.mark.unit


def test_relationship_refs_parse_frontmatter_and_prose() -> None:
    refs = _relationship_refs(
        Path("docs/adrs/ADR-999-example.md"),
        {"extends": ["ADR-172"], "supersedes": ["ADR-170"], "replaces": []},
        "This also replaces ADR-043 and extends ADR-173.",
    )
    assert refs == {43, 170, 172, 173}


def test_existing_adr_graph_emits_scope_creep_chain_warning_not_cycle() -> None:
    findings = analyze_relationship_graph(_collect_adr_files())
    codes = {finding["code"] for finding in findings}
    assert CODE_ADR_RELATION_CYCLE not in codes
    assert CODE_ADR_RELATION_CHAIN_LONG in codes
    chain_findings = [f for f in findings if f["code"] == CODE_ADR_RELATION_CHAIN_LONG]
    assert any(f["chain"] == ["ADR-187", "ADR-173", "ADR-172", "ADR-170"] for f in chain_findings)
