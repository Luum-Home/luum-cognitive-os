from __future__ import annotations

from pathlib import Path

import pytest

import scripts.audit_adrs as audit_adrs
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


def test_synthetic_adr_graph_emits_scope_creep_chain_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs = tmp_path / "docs" / "adrs"
    docs.mkdir(parents=True)
    for number, extends in (
        (1, "[ADR-002]"),
        (2, "[ADR-003]"),
        (3, "[ADR-004]"),
        (4, "[]"),
    ):
        (docs / f"ADR-{number:03d}-example.md").write_text(
            "\n".join(
                [
                    "---",
                    f"adr: {number}",
                    "title: Example",
                    "status: accepted",
                    f"extends: {extends}",
                    "---",
                    f"# ADR-{number:03d}",
                ]
            ),
            encoding="utf-8",
        )
    monkeypatch.setattr(audit_adrs, "REPO_ROOT", tmp_path)

    findings = analyze_relationship_graph(sorted(docs.glob("ADR-*.md")))
    chain_findings = [f for f in findings if f["code"] == CODE_ADR_RELATION_CHAIN_LONG]
    assert chain_findings
    assert chain_findings[0]["chain"] == ["ADR-001", "ADR-002", "ADR-003", "ADR-004"]


def test_existing_adr_graph_has_no_scope_creep_chain_warning_or_cycle() -> None:
    findings = analyze_relationship_graph(_collect_adr_files())
    codes = {finding["code"] for finding in findings}
    assert CODE_ADR_RELATION_CYCLE not in codes
    assert CODE_ADR_RELATION_CHAIN_LONG not in codes
