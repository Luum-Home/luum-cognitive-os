"""Unit tests for lib/evolve_skill_review.py (ADR-262 spike)."""

from __future__ import annotations

import json
from pathlib import Path


from lib.evolve_skill_review import (
    EvolveSkillReview,
    _parse_llm_response,
    _read_session_turns,
    _validate_proposal_dict,
)
from lib.evolve_task_queue import EvolveTaskQueue


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_PROPOSAL = {
    "kind": "skill_new",
    "title": "Automate multi-service rollback",
    "rationale": "Observed in 3 turns: operator manually triggers rollback for each service. A skill would reduce friction.",
    "draft": "# Automate multi-service rollback\n\nUsage: ...\n\nAcceptance criteria:\n- [ ] Triggers rollback for all services",
    "confidence": 0.85,
}

LOW_CONFIDENCE_PROPOSAL = {
    "kind": "skill_new",
    "title": "One-off debug helper",
    "rationale": "Used once in session.",
    "draft": "# Debug helper",
    "confidence": 0.50,
}


def make_mock_dispatch(response_proposals: list[dict]):
    """Return a dispatch function that returns the given proposals as JSON."""
    def _dispatch(prompt: str) -> str:
        return json.dumps(response_proposals)
    return _dispatch


def make_queue(tmp_path: Path) -> EvolveTaskQueue:
    return EvolveTaskQueue(db_path=tmp_path / "test.db")


# ---------------------------------------------------------------------------
# Smoke test: valid JSON from dispatch → queue gets filled
# ---------------------------------------------------------------------------

class TestSmokeTest:
    def test_dispatch_mocked_valid_json_enqueues_proposals(self, tmp_path: Path) -> None:
        """With dispatch mocked to return valid JSON, queue should receive proposals."""
        queue = make_queue(tmp_path)

        # Create minimal session turn log
        turns_dir = tmp_path / "session" / "turns"
        turns_dir.mkdir(parents=True)
        (turns_dir / "turn-001.json").write_text(
            json.dumps({"tool": "Agent", "output": "Deployed service A. Deployed service B."})
        )

        review = EvolveSkillReview(
            queue=queue,
            config={"enabled": True, "cadence_turns": 1, "confidence_threshold": 0.72},
            _dispatch_fn=make_mock_dispatch([VALID_PROPOSAL]),
        )
        count = review.run(session_dir=tmp_path / "session")

        assert count == 1
        pending = queue.list_pending()
        assert len(pending) == 1
        assert pending[0].title == VALID_PROPOSAL["title"]
        assert pending[0].kind == "skill_new"

    def test_multiple_valid_proposals_all_enqueued(self, tmp_path: Path) -> None:
        queue = make_queue(tmp_path)
        turns_dir = tmp_path / "session" / "turns"
        turns_dir.mkdir(parents=True)
        (turns_dir / "turn-001.json").write_text(json.dumps({"output": "work done"}))

        proposals = [
            VALID_PROPOSAL,
            {
                "kind": "skill_patch",
                "title": "improve-deploy: add health check step",
                "rationale": "Observed deploy skill missing health check validation.",
                "draft": "Add step: wait for health endpoint 200 before marking deploy complete.",
                "confidence": 0.78,
            },
        ]

        review = EvolveSkillReview(
            queue=queue,
            config={"enabled": True, "cadence_turns": 1, "confidence_threshold": 0.72},
            _dispatch_fn=make_mock_dispatch(proposals),
        )
        count = review.run(session_dir=tmp_path / "session")

        assert count == 2

    def test_dispatch_returns_empty_array_no_proposals(self, tmp_path: Path) -> None:
        queue = make_queue(tmp_path)
        turns_dir = tmp_path / "session" / "turns"
        turns_dir.mkdir(parents=True)
        (turns_dir / "turn-001.json").write_text(json.dumps({"output": "nothing special"}))

        review = EvolveSkillReview(
            queue=queue,
            config={"confidence_threshold": 0.72},
            _dispatch_fn=make_mock_dispatch([]),
        )
        count = review.run(session_dir=tmp_path / "session")
        assert count == 0
        assert queue.list_pending() == []


# ---------------------------------------------------------------------------
# Confidence filter
# ---------------------------------------------------------------------------

class TestConfidenceFilter:
    def test_low_confidence_proposals_discarded(self, tmp_path: Path) -> None:
        queue = make_queue(tmp_path)
        turns_dir = tmp_path / "session" / "turns"
        turns_dir.mkdir(parents=True)
        (turns_dir / "turn-001.json").write_text(json.dumps({"output": "work"}))

        proposals = [
            VALID_PROPOSAL,          # confidence 0.85 → passes
            LOW_CONFIDENCE_PROPOSAL,  # confidence 0.50 → filtered
        ]

        review = EvolveSkillReview(
            queue=queue,
            config={"confidence_threshold": 0.72},
            _dispatch_fn=make_mock_dispatch(proposals),
        )
        count = review.run(session_dir=tmp_path / "session")

        assert count == 1
        pending = queue.list_pending()
        assert len(pending) == 1
        assert pending[0].title == VALID_PROPOSAL["title"]

    def test_exactly_at_threshold_passes(self, tmp_path: Path) -> None:
        queue = make_queue(tmp_path)
        turns_dir = tmp_path / "session" / "turns"
        turns_dir.mkdir(parents=True)
        (turns_dir / "turn-001.json").write_text(json.dumps({"output": "work"}))

        at_threshold = dict(VALID_PROPOSAL, title="At threshold", confidence=0.72)

        review = EvolveSkillReview(
            queue=queue,
            config={"confidence_threshold": 0.72},
            _dispatch_fn=make_mock_dispatch([at_threshold]),
        )
        count = review.run(session_dir=tmp_path / "session")
        assert count == 1

    def test_below_threshold_by_epsilon_filtered(self, tmp_path: Path) -> None:
        queue = make_queue(tmp_path)
        turns_dir = tmp_path / "session" / "turns"
        turns_dir.mkdir(parents=True)
        (turns_dir / "turn-001.json").write_text(json.dumps({"output": "work"}))

        below = dict(VALID_PROPOSAL, title="Below threshold", confidence=0.719)

        review = EvolveSkillReview(
            queue=queue,
            config={"confidence_threshold": 0.72},
            _dispatch_fn=make_mock_dispatch([below]),
        )
        count = review.run(session_dir=tmp_path / "session")
        assert count == 0


# ---------------------------------------------------------------------------
# Empty turn log
# ---------------------------------------------------------------------------

class TestEmptyTurnLog:
    def test_missing_turns_dir_returns_zero_no_error(self, tmp_path: Path) -> None:
        """If the session directory exists but has no turns/, return 0 without crash."""
        queue = make_queue(tmp_path)
        session_dir = tmp_path / "empty-session"
        session_dir.mkdir()
        # No turns/ subdirectory

        dispatch_called = []

        def _dispatch(prompt: str) -> str:
            dispatch_called.append(prompt)
            return "[]"

        review = EvolveSkillReview(
            queue=queue,
            config={"confidence_threshold": 0.72},
            _dispatch_fn=_dispatch,
        )
        count = review.run(session_dir=session_dir)

        assert count == 0
        assert not dispatch_called, "LLM must not be called if there are no turns"

    def test_empty_turns_dir_returns_zero(self, tmp_path: Path) -> None:
        """turns/ exists but has no files — should return 0."""
        queue = make_queue(tmp_path)
        session_dir = tmp_path / "session"
        (session_dir / "turns").mkdir(parents=True)

        dispatch_called = []

        def _dispatch(prompt: str) -> str:
            dispatch_called.append(prompt)
            return "[]"

        review = EvolveSkillReview(
            queue=queue,
            config={"confidence_threshold": 0.72},
            _dispatch_fn=_dispatch,
        )
        count = review.run(session_dir=session_dir)

        assert count == 0
        assert not dispatch_called

    def test_nonexistent_session_dir_returns_zero(self, tmp_path: Path) -> None:
        queue = make_queue(tmp_path)
        review = EvolveSkillReview(
            queue=queue,
            config={"confidence_threshold": 0.72},
            _dispatch_fn=make_mock_dispatch([VALID_PROPOSAL]),
        )
        count = review.run(session_dir=tmp_path / "does-not-exist")
        assert count == 0


# ---------------------------------------------------------------------------
# _read_session_turns
# ---------------------------------------------------------------------------

class TestReadSessionTurns:
    def test_reads_last_n_files(self, tmp_path: Path) -> None:
        turns_dir = tmp_path / "turns"
        turns_dir.mkdir()
        for i in range(5):
            (turns_dir / f"turn-00{i}.json").write_text(json.dumps({"i": i}))

        turns = _read_session_turns(tmp_path, last_n=3)
        assert len(turns) == 3
        # Should be the last 3 lexicographically (turn-002, 003, 004)
        assert turns[-1]["i"] == 4

    def test_skips_invalid_json_file(self, tmp_path: Path) -> None:
        turns_dir = tmp_path / "turns"
        turns_dir.mkdir()
        (turns_dir / "turn-001.json").write_text("not json {{{")
        (turns_dir / "turn-002.json").write_text(json.dumps({"ok": True}))

        turns = _read_session_turns(tmp_path, last_n=10)
        assert len(turns) == 1
        assert turns[0]["ok"] is True


# ---------------------------------------------------------------------------
# _parse_llm_response
# ---------------------------------------------------------------------------

class TestParseLlmResponse:
    def test_parses_plain_json_array(self) -> None:
        data = [VALID_PROPOSAL]
        result = _parse_llm_response(json.dumps(data))
        assert len(result) == 1

    def test_parses_json_in_markdown_fence(self) -> None:
        text = "```json\n" + json.dumps([VALID_PROPOSAL]) + "\n```"
        result = _parse_llm_response(text)
        assert len(result) == 1

    def test_returns_empty_list_for_non_array(self) -> None:
        result = _parse_llm_response(json.dumps({"key": "value"}))
        assert result == []

    def test_returns_empty_list_for_empty_string(self) -> None:
        assert _parse_llm_response("") == []

    def test_returns_empty_array_for_empty_json_array(self) -> None:
        assert _parse_llm_response("[]") == []


# ---------------------------------------------------------------------------
# _validate_proposal_dict
# ---------------------------------------------------------------------------

class TestValidateProposalDict:
    def test_valid_proposal_passes(self) -> None:
        assert _validate_proposal_dict(VALID_PROPOSAL, 0.72) is True

    def test_missing_field_fails(self) -> None:
        incomplete = {k: v for k, v in VALID_PROPOSAL.items() if k != "rationale"}
        assert _validate_proposal_dict(incomplete, 0.72) is False

    def test_invalid_kind_fails(self) -> None:
        bad = dict(VALID_PROPOSAL, kind="unknown_kind")
        assert _validate_proposal_dict(bad, 0.72) is False

    def test_low_confidence_fails(self) -> None:
        low = dict(VALID_PROPOSAL, confidence=0.50)
        assert _validate_proposal_dict(low, 0.72) is False

    def test_non_dict_fails(self) -> None:
        assert _validate_proposal_dict("not a dict", 0.72) is False
        assert _validate_proposal_dict(None, 0.72) is False
