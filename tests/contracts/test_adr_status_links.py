"""Contract tests for ADR status literals and supersede-link symmetry.

Guards `scripts/audit_adr_status_links.py`. The point of these tests is that the
rules are proven to fire: a validator whose checks never trigger gives a false
sense of coverage, so each check is exercised against a fabricated offender as
well as against a fabricated compliant case.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts import audit_adr_status_links as audit  # noqa: E402


def _collect_in(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(audit, "ADRS", tmp_path)
    return audit.collect()


def _write(tmp_path: pathlib.Path, name: str, frontmatter: str, body: str = "") -> None:
    (tmp_path / name).write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")


def _codes(findings) -> set[str]:
    return {f["code"] for f in findings}


def test_status_case_drift_is_a_finding(tmp_path, monkeypatch) -> None:
    _write(tmp_path, "ADR-900-x.md", "adr: 900\nstatus: Accepted\nimplementation_status: Implemented\n")
    findings, _, _ = _collect_in(tmp_path, monkeypatch)
    assert "STATUS_CASE_DRIFT" in _codes(findings)
    assert len([f for f in findings if f["code"] == "STATUS_CASE_DRIFT"]) == 2


def test_canonical_lowercase_status_is_clean(tmp_path, monkeypatch) -> None:
    _write(tmp_path, "ADR-900-x.md", "adr: 900\nstatus: accepted\nimplementation_status: implemented\n")
    findings, _, _ = _collect_in(tmp_path, monkeypatch)
    assert "STATUS_CASE_DRIFT" not in _codes(findings)


def test_superseded_dead_end_is_a_finding(tmp_path, monkeypatch) -> None:
    _write(tmp_path, "ADR-900-x.md", "adr: 900\nstatus: superseded\nimplementation_status: not-applicable\nsuperseded_by: null\n")
    findings, _, _ = _collect_in(tmp_path, monkeypatch)
    assert "SUPERSEDED_DEAD_END" in _codes(findings)


def test_supersede_link_asymmetry_is_a_finding_in_both_directions(tmp_path, monkeypatch) -> None:
    # forward-only: 901 claims to supersede 900, 900 never points back
    _write(tmp_path, "ADR-900-x.md", "adr: 900\nstatus: accepted\nimplementation_status: implemented\n")
    _write(tmp_path, "ADR-901-y.md", "adr: 901\nstatus: accepted\nimplementation_status: implemented\nsupersedes: [ADR-900]\n")
    findings, _, _ = _collect_in(tmp_path, monkeypatch)
    asym = [f for f in findings if f["code"] == "SUPERSEDE_LINK_ASYMMETRY"]
    assert len(asym) == 1 and asym[0]["direction"] == "missing superseded_by"

    # backward-only: 900 says it was superseded, 901 never claims it
    _write(tmp_path, "ADR-900-x.md", "adr: 900\nstatus: superseded\nimplementation_status: not-applicable\nsuperseded_by: ADR-901\n")
    _write(tmp_path, "ADR-901-y.md", "adr: 901\nstatus: accepted\nimplementation_status: implemented\n")
    findings, _, _ = _collect_in(tmp_path, monkeypatch)
    asym = [f for f in findings if f["code"] == "SUPERSEDE_LINK_ASYMMETRY"]
    assert len(asym) == 1 and asym[0]["direction"] == "missing supersedes"


def test_symmetric_supersede_pair_is_clean(tmp_path, monkeypatch) -> None:
    _write(tmp_path, "ADR-900-x.md", "adr: 900\nstatus: superseded\nimplementation_status: not-applicable\nsuperseded_by: ADR-901\n")
    _write(tmp_path, "ADR-901-y.md", "adr: 901\nstatus: accepted\nimplementation_status: implemented\nsupersedes: [ADR-900]\n")
    findings, _, _ = _collect_in(tmp_path, monkeypatch)
    assert "SUPERSEDE_LINK_ASYMMETRY" not in _codes(findings)


def test_tombstone_authority_pointer_is_a_note_not_a_finding(tmp_path, monkeypatch) -> None:
    """A retired slot naming its current authority owes no reverse edge."""
    _write(tmp_path, "ADR-900-tombstone.md", "adr: 900\nstatus: tombstone\nimplementation_status: not-applicable\nsuperseded_by: ADR-901\n")
    _write(tmp_path, "ADR-901-y.md", "adr: 901\nstatus: accepted\nimplementation_status: implemented\n")
    findings, notes, _ = _collect_in(tmp_path, monkeypatch)
    assert "SUPERSEDE_LINK_ASYMMETRY" not in _codes(findings)
    assert "TOMBSTONE_AUTHORITY_POINTER" in _codes(notes)


def test_prose_status_contradiction_fires_across_families(tmp_path, monkeypatch) -> None:
    _write(
        tmp_path,
        "ADR-900-x.md",
        "adr: 900\nstatus: accepted\nimplementation_status: implemented\n",
        "\n## Status\n\nProposed — awaiting review.\n",
    )
    findings, _, _ = _collect_in(tmp_path, monkeypatch)
    assert "PROSE_STATUS_CONTRADICTS_FRONTMATTER" in _codes(findings)


@pytest.mark.parametrize(
    "status,prose",
    [
        ("implemented", "**Accepted — Implemented** as the posture."),
        ("implemented", "Accepted — Partially Implemented. Remaining work is tracked."),
        ("accepted", "Accepted — slices a-f implemented (2026-05-07)"),
        ("implemented", "Accepted — 2026-05-02. Related: ADR-102."),
    ],
)
def test_prose_annotations_are_not_contradictions(tmp_path, monkeypatch, status, prose) -> None:
    """Slice/date detail alongside a same-family status is annotation, not drift.

    Flattening these to a bare canonical word would normalize the field and
    destroy the information the prose was carrying.
    """
    _write(
        tmp_path,
        "ADR-900-x.md",
        f"adr: 900\nstatus: {status}\nimplementation_status: implemented\n",
        f"\n## Status\n\n{prose}\n",
    )
    findings, _, _ = _collect_in(tmp_path, monkeypatch)
    assert "PROSE_STATUS_CONTRADICTS_FRONTMATTER" not in _codes(findings)


def test_real_repository_has_no_case_drift_or_dead_ends() -> None:
    """Ratchet: the classes normalized on 2026-08-15 must not come back."""
    findings, _, records = audit.collect()
    assert len(records) >= 350
    regressions = [f for f in findings if f["code"] in {"STATUS_CASE_DRIFT", "SUPERSEDED_DEAD_END", "MISSING_FRONTMATTER"}]
    assert regressions == [], regressions
