"""Unit tests for lib/evolve_task_queue.py (ADR-262 spike)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.evolve_task_queue import (
    QUEUE_CAP,
    EvolveProposal,
    EvolveTaskQueue,
    compute_fingerprint,
)


def _make_proposal(
    title: str = "Test Skill",
    kind: str = "skill_new",
    confidence: float = 0.80,
    draft: str = "# Test\nDoes things.",
    rationale: str = "Reusable pattern",
) -> EvolveProposal:
    return EvolveProposal(
        kind=kind,
        title=title,
        rationale=rationale,
        draft=draft,
        confidence=confidence,
    )


@pytest.fixture
def queue(tmp_path: Path) -> EvolveTaskQueue:
    """Return an in-memory queue backed by a temp SQLite file."""
    db_file = tmp_path / "test-evolve.db"
    return EvolveTaskQueue(db_path=db_file)


# ---------------------------------------------------------------------------
# enqueue + list_pending
# ---------------------------------------------------------------------------

class TestEnqueue:
    def test_enqueue_returns_id_and_list_shows_it(self, queue: EvolveTaskQueue) -> None:
        proposal = _make_proposal(title="Orchestrate multi-step deploys")
        pid = queue.enqueue(proposal)
        assert pid is not None
        assert len(pid) > 8  # UUID

        pending = queue.list_pending()
        assert len(pending) == 1
        assert pending[0].title == "Orchestrate multi-step deploys"
        assert pending[0].status == "pending"

    def test_list_pending_ordered_by_confidence_desc(self, queue: EvolveTaskQueue) -> None:
        queue.enqueue(_make_proposal(title="Low confidence", confidence=0.73))
        queue.enqueue(_make_proposal(title="High confidence", confidence=0.95))
        queue.enqueue(_make_proposal(title="Mid confidence", confidence=0.82))

        pending = queue.list_pending()
        confidences = [p.confidence for p in pending]
        assert confidences == sorted(confidences, reverse=True)

    def test_enqueue_sets_created_at(self, queue: EvolveTaskQueue) -> None:
        pid = queue.enqueue(_make_proposal())
        assert pid is not None
        proposal = queue.get(pid)
        assert proposal is not None
        assert proposal.created_at  # ISO-8601 string


# ---------------------------------------------------------------------------
# Deduplication by fingerprint
# ---------------------------------------------------------------------------

class TestDedup:
    def test_duplicate_fingerprint_returns_none(self, queue: EvolveTaskQueue) -> None:
        p1 = _make_proposal(title="Reuse me", draft="# Draft\nStep 1. Step 2.")
        p2 = _make_proposal(title="Reuse me", draft="# Draft\nStep 1. Step 2.")
        # Same content → same fingerprint
        assert p1.fingerprint == p2.fingerprint

        pid1 = queue.enqueue(p1)
        pid2 = queue.enqueue(p2)

        assert pid1 is not None
        assert pid2 is None  # duplicate rejected

    def test_duplicate_count_is_one_row(self, queue: EvolveTaskQueue) -> None:
        p = _make_proposal(title="Unique skill", draft="Unique draft content here.")
        queue.enqueue(p)
        queue.enqueue(p)  # second enqueue silently ignored

        pending = queue.list_pending()
        assert len(pending) == 1

    def test_different_content_different_fingerprint(self, queue: EvolveTaskQueue) -> None:
        p1 = _make_proposal(title="Skill A", draft="Draft A content.")
        p2 = _make_proposal(title="Skill B", draft="Draft B content.")
        assert p1.fingerprint != p2.fingerprint

        pid1 = queue.enqueue(p1)
        pid2 = queue.enqueue(p2)
        assert pid1 is not None
        assert pid2 is not None


# ---------------------------------------------------------------------------
# Queue cap
# ---------------------------------------------------------------------------

class TestQueueCap:
    def test_51st_enqueue_returns_none_and_logs(
        self, queue: EvolveTaskQueue, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Enqueue 50 proposals (fills cap), then 51st must return None."""
        with caplog.at_level("WARNING", logger="lib.evolve_task_queue"):
            for i in range(QUEUE_CAP):
                p = _make_proposal(
                    title=f"Skill {i}",
                    draft=f"Unique draft content for skill number {i}.",
                )
                result = queue.enqueue(p)
                assert result is not None, f"Enqueue {i} failed before cap"

            # 51st — different content to avoid fingerprint dedup masking the cap
            overflow = _make_proposal(
                title="Overflow proposal",
                draft="This is the overflow proposal that should be rejected by the cap.",
            )
            result = queue.enqueue(overflow)

        assert result is None
        assert queue.pending_count() == QUEUE_CAP
        assert any("capacity" in record.message.lower() for record in caplog.records)


# ---------------------------------------------------------------------------
# approve
# ---------------------------------------------------------------------------

class TestApprove:
    def test_approve_changes_status_to_approved(self, queue: EvolveTaskQueue) -> None:
        pid = queue.enqueue(_make_proposal(title="Approval target"))
        assert pid is not None

        ok = queue.approve(pid, reviewer="test-operator")
        assert ok is True

        proposal = queue.get(pid)
        assert proposal is not None
        assert proposal.status == "approved"
        assert proposal.reviewer == "test-operator"
        assert proposal.reviewed_at is not None

    def test_approve_nonexistent_returns_false(self, queue: EvolveTaskQueue) -> None:
        ok = queue.approve("nonexistent-id")
        assert ok is False

    def test_approve_already_approved_returns_false(self, queue: EvolveTaskQueue) -> None:
        pid = queue.enqueue(_make_proposal())
        assert pid is not None
        queue.approve(pid)
        # Second approve: already not pending → returns False
        ok = queue.approve(pid)
        assert ok is False

    def test_approve_does_not_promote(self, queue: EvolveTaskQueue) -> None:
        """Approval must NOT auto-promote. Human action is required."""
        pid = queue.enqueue(_make_proposal())
        assert pid is not None
        queue.approve(pid)
        proposal = queue.get(pid)
        assert proposal is not None
        assert proposal.status == "approved"
        assert proposal.status != "promoted"


# ---------------------------------------------------------------------------
# reject
# ---------------------------------------------------------------------------

class TestReject:
    def test_reject_stores_reason(self, queue: EvolveTaskQueue) -> None:
        pid = queue.enqueue(_make_proposal(title="Reject me"))
        assert pid is not None

        ok = queue.reject(pid, reason="Too session-specific", reviewer="test-operator")
        assert ok is True

        proposal = queue.get(pid)
        assert proposal is not None
        assert proposal.status == "rejected"
        assert proposal.reject_reason == "Too session-specific"
        assert proposal.reviewer == "test-operator"
        assert proposal.reviewed_at is not None

    def test_reject_removes_from_pending_list(self, queue: EvolveTaskQueue) -> None:
        pid = queue.enqueue(_make_proposal(title="Will be rejected"))
        assert pid is not None
        queue.reject(pid, reason="Noise")

        pending = queue.list_pending()
        pending_ids = [p.proposal_id for p in pending]
        assert pid not in pending_ids

    def test_reject_nonexistent_returns_false(self, queue: EvolveTaskQueue) -> None:
        ok = queue.reject("nonexistent", reason="N/A")
        assert ok is False


# ---------------------------------------------------------------------------
# mark_promoted
# ---------------------------------------------------------------------------

class TestMarkPromoted:
    def test_mark_promoted_requires_approved_first(self, queue: EvolveTaskQueue) -> None:
        pid = queue.enqueue(_make_proposal())
        assert pid is not None
        # Cannot promote from pending
        ok = queue.mark_promoted(pid)
        assert ok is False

    def test_mark_promoted_after_approve(self, queue: EvolveTaskQueue) -> None:
        pid = queue.enqueue(_make_proposal(title="Promote me"))
        assert pid is not None
        queue.approve(pid)
        ok = queue.mark_promoted(pid)
        assert ok is True

        proposal = queue.get(pid)
        assert proposal is not None
        assert proposal.status == "promoted"

    def test_mark_promoted_returns_false_for_nonexistent(self, queue: EvolveTaskQueue) -> None:
        ok = queue.mark_promoted("does-not-exist")
        assert ok is False


# ---------------------------------------------------------------------------
# compute_fingerprint
# ---------------------------------------------------------------------------

class TestComputeFingerprint:
    def test_same_content_same_fingerprint(self) -> None:
        fp1 = compute_fingerprint("skill_new", "Title", "Draft content")
        fp2 = compute_fingerprint("skill_new", "Title", "Draft content")
        assert fp1 == fp2

    def test_whitespace_normalized(self) -> None:
        fp1 = compute_fingerprint("skill_new", "  Title  ", "Draft content\n\n")
        fp2 = compute_fingerprint("skill_new", "Title", "Draft content")
        assert fp1 == fp2

    def test_different_kind_different_fingerprint(self) -> None:
        fp1 = compute_fingerprint("skill_new", "T", "D")
        fp2 = compute_fingerprint("skill_patch", "T", "D")
        assert fp1 != fp2

    def test_fingerprint_is_sha256_hex(self) -> None:
        fp = compute_fingerprint("skill_new", "t", "d")
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)


# ---------------------------------------------------------------------------
# EvolveProposal validation
# ---------------------------------------------------------------------------

class TestEvolveProposal:
    def test_invalid_kind_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid kind"):
            EvolveProposal(
                kind="invalid_kind",
                title="T",
                rationale="R",
                draft="D",
                confidence=0.8,
            )

    def test_fingerprint_auto_computed(self) -> None:
        p = EvolveProposal(kind="skill_new", title="T", rationale="R", draft="D", confidence=0.8)
        expected = compute_fingerprint("skill_new", "T", "D")
        assert p.fingerprint == expected

    def test_explicit_fingerprint_preserved(self) -> None:
        p = EvolveProposal(
            kind="skill_new",
            title="T",
            rationale="R",
            draft="D",
            confidence=0.8,
            fingerprint="custom-fp",
        )
        assert p.fingerprint == "custom-fp"
