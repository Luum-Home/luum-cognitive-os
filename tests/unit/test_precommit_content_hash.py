from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import precommit_content_hash as dedupe

pytestmark = pytest.mark.unit


def test_check_allows_empty_staged_diff() -> None:
    with patch.object(dedupe, "get_staged_patch_id", return_value=None):
        assert dedupe.check(repo_root=Path(".")) == 0


def test_check_allows_non_duplicate_patch() -> None:
    with (
        patch.object(dedupe, "get_staged_patch_id", return_value="patch-a"),
        patch.object(dedupe, "get_origin_patch_ids", return_value={"patch-b": "abc123"}),
    ):
        assert dedupe.check(repo_root=Path(".")) == 0


def test_check_warns_but_allows_duplicate_patch(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(dedupe, "get_staged_patch_id", return_value="patch-a"),
        patch.object(dedupe, "get_origin_patch_ids", return_value={"patch-a": "abcdef123456"}),
        patch.object(dedupe, "emit_collision_event") as emit,
    ):
        assert dedupe.check(mode="warn", repo_root=Path(".")) == 0

    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    emit.assert_called_once()


def test_check_blocks_duplicate_patch_in_block_mode(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(dedupe, "get_staged_patch_id", return_value="patch-a"),
        patch.object(dedupe, "get_origin_patch_ids", return_value={"patch-a": "abcdef123456"}),
        patch.object(dedupe, "emit_collision_event") as emit,
    ):
        assert dedupe.check(mode="block", repo_root=Path(".")) == 2

    captured = capsys.readouterr()
    assert "COMMIT BLOCKED" in captured.err
    emit.assert_called_once()


def test_check_off_mode_skips_all_checks() -> None:
    """COS_DEDUPE_MODE=off must short-circuit without any git calls."""
    with patch.object(dedupe, "get_staged_patch_id") as mock_staged:
        result = dedupe.check(mode="off", repo_root=Path("."))
    assert result == 0
    mock_staged.assert_not_called()


def test_collision_emits_jsonl_event(tmp_path: Path) -> None:
    """collision_detected event must be written to events.jsonl via event_bus."""
    import json

    bus_file = tmp_path / "events.jsonl"
    with (
        patch.object(dedupe, "get_staged_patch_id", return_value="pid-xyz"),
        patch.object(dedupe, "get_origin_patch_ids", return_value={"pid-xyz": "sha-abc"}),
    ):
        dedupe.check(mode="warn", repo_root=tmp_path, bus_path=bus_file)

    assert bus_file.exists(), "events.jsonl must be created on collision"
    lines = [ln for ln in bus_file.read_text().splitlines() if ln.strip()]
    assert lines, "At least one event line expected"
    event = json.loads(lines[-1])
    assert event["event_type"] == "conflict_detected"
    assert event["payload"]["staged_patch_id"] == "pid-xyz"
    assert event["payload"]["matched_commit"] == "sha-abc"
    assert event["payload"]["source"] == "pre-commit-content-hash-dedupe"

