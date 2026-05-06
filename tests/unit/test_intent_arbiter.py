from __future__ import annotations

from pathlib import Path

import pytest

from lib.intent_arbiter import process_once, read_json, result_path, submit_intent

pytestmark = pytest.mark.unit


def test_adr_number_intents_are_assigned_distinct_numbers(tmp_path: Path) -> None:
    adrs = tmp_path / "docs" / "adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-001-existing.md").write_text("# ADR-001: Existing\n", encoding="utf-8")

    submit_intent(
        tmp_path,
        kind="adr-number-request",
        session_id="s1",
        intent_id="intent-a",
        context={"topic": "First feature", "filename_stem": "first-feature"},
    )
    submit_intent(
        tmp_path,
        kind="adr-number-request",
        session_id="s2",
        intent_id="intent-b",
        context={"topic": "Second feature", "filename_stem": "second-feature"},
    )

    processed = process_once(tmp_path)

    assert len(processed) == 2
    numbers = {row["decision"]["adr_number"] for row in processed}
    assert numbers == {2, 3}


def test_tombstone_intent_rejects_active_adr_number(tmp_path: Path) -> None:
    adrs = tmp_path / "docs" / "adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-007-active-decision.md").write_text("# ADR-007: Active\n", encoding="utf-8")

    submit_intent(
        tmp_path,
        kind="adr-tombstone-request",
        session_id="s1",
        intent_id="intent-tombstone",
        context={"adr_number": 7, "candidate_filename": "ADR-007-tombstone.md"},
    )

    [result] = process_once(tmp_path)

    assert result["status"] == "rejected"
    assert result["decision"]["adr_number"] == 7
    assert "active ADR file" in result["decision"]["findings"][0]["message"]


def test_tombstone_intent_requires_canonical_adr_filename_prefix(tmp_path: Path) -> None:
    submit_intent(
        tmp_path,
        kind="adr-tombstone-request",
        session_id="s1",
        intent_id="intent-bad-filename",
        context={"adr_number": 7, "candidate_filename": "ADR-007evil.md"},
    )

    [result] = process_once(tmp_path)

    assert result["status"] == "rejected"
    assert "preserve ADR number" in result["reason"]


def test_process_once_is_idempotent_for_decided_intent(tmp_path: Path) -> None:
    submit_intent(
        tmp_path,
        kind="adr-number-request",
        session_id="s1",
        intent_id="intent-idempotent",
        context={"topic": "Once"},
    )

    assert process_once(tmp_path)
    first = result_path(tmp_path, "intent-idempotent").read_text(encoding="utf-8")
    assert process_once(tmp_path) == []
    second = result_path(tmp_path, "intent-idempotent").read_text(encoding="utf-8")
    assert first == second


def test_submit_intent_does_not_overwrite_pending_intent_with_same_id(tmp_path: Path) -> None:
    first = submit_intent(
        tmp_path,
        kind="adr-number-request",
        session_id="s1",
        intent_id="intent-same",
        context={"topic": "Original"},
    )
    second = submit_intent(
        tmp_path,
        kind="adr-number-request",
        session_id="s2",
        intent_id="intent-same",
        context={"topic": "Overwrite attempt"},
    )

    stored = read_json(Path(first["intent_path"]))

    assert second["status"] == "already-submitted"
    assert stored is not None
    assert stored["session_id"] == "s1"
    assert stored["context"]["topic"] == "Original"
