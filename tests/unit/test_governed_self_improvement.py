"""Unit tests for governed self-improvement drafts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.governed_self_improvement import (
    create_improvement_draft,
    promote_improvement_draft,
    suggest_improvement_signals,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_repeated_errors_create_signal(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / ".cognitive-os" / "metrics" / "error-learning.jsonl",
        [
            {"type": "TEST_FAILURE", "service": "auth", "command": "pytest"},
            {"type": "TEST_FAILURE", "service": "auth", "command": "pytest"},
            {"type": "TEST_FAILURE", "service": "auth", "command": "pytest"},
        ],
    )

    signals = suggest_improvement_signals(tmp_path)

    assert [(signal.signal_type, signal.slug, signal.priority) for signal in signals] == [
        ("repeated_error", "repair-test-failure-auth", "P0")
    ]
    assert len(signals[0].evidence) == 3


def test_skill_failures_and_successful_workflows_create_signals(tmp_path: Path) -> None:
    metrics = tmp_path / ".cognitive-os" / "metrics"
    _write_jsonl(
        metrics / "skill-archive.jsonl",
        [
            {"skill_name": "sdd-apply", "success": False},
            {"skill_name": "sdd-apply", "success": False},
        ],
    )
    _write_jsonl(
        metrics / "session-learnings.jsonl",
        [{"task": "release validation", "steps": 7, "success": True}],
    )

    signals = suggest_improvement_signals(tmp_path)

    assert {signal.signal_type for signal in signals} == {
        "skill_failure",
        "successful_multistep_workflow",
    }
    assert {signal.slug for signal in signals} == {
        "improve-sdd-apply",
        "reuse-release-validation",
    }


def test_draft_writes_canonical_improvement_artifacts(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / ".cognitive-os" / "metrics" / "error-learning.jsonl",
        [
            {"type": "BUILD_ERROR", "service": "api"},
            {"type": "BUILD_ERROR", "service": "api"},
            {"type": "BUILD_ERROR", "service": "api"},
        ],
    )
    signal = suggest_improvement_signals(tmp_path)[0]

    draft = create_improvement_draft(tmp_path, signal)

    assert draft.status == "draft"
    assert draft.approvals_required is True
    assert draft.draft_dir == ".cognitive-os/improvements/drafts/repair-build-error-api"
    skill = tmp_path / draft.skill_path
    metadata = tmp_path / draft.draft_dir / "improvement.json"
    assert skill.exists()
    assert metadata.exists()
    assert "governed-improvement: true" in skill.read_text(encoding="utf-8")
    assert json.loads(metadata.read_text(encoding="utf-8"))["status"] == "draft"


def test_promotion_requires_approval_and_stays_canonical(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / ".cognitive-os" / "metrics" / "error-learning.jsonl",
        [
            {"type": "TEST_FAILURE", "service": "billing"},
            {"type": "TEST_FAILURE", "service": "billing"},
            {"type": "TEST_FAILURE", "service": "billing"},
        ],
    )
    draft = create_improvement_draft(tmp_path, suggest_improvement_signals(tmp_path)[0])

    with pytest.raises(PermissionError):
        promote_improvement_draft(tmp_path, draft.draft_id)

    promotion = promote_improvement_draft(tmp_path, draft.draft_id, approved_by="test-reviewer")

    assert promotion["target"] == ".cognitive-os/skills/cos/repair-test-failure-billing/SKILL.md"
    assert (tmp_path / promotion["target"]).exists()
    assert not (tmp_path / "skills" / "repair-test-failure-billing" / "SKILL.md").exists()
