"""
Unit tests for lib/skill_synthesizer.py

All tests use synthetic JSONL data (tmp_path fixture).
No network, no external services, no real metrics directory.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from lib.skill_synthesizer import (
    find_recurring_sequences,
    propose_skill_draft,
    auto_promote_eligible,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(delta_hours: int = 0) -> str:
    dt = datetime.now(timezone.utc) + timedelta(hours=delta_hours)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def _make_seq_record(
    tools: list[str],
    session_id: str,
    delta_hours: int = -1,
    success: bool = True,
) -> list[dict]:
    """Build one sequence of tool records for a session."""
    ts = _ts(delta_hours)
    return [
        {
            "timestamp": ts,
            "session_id": session_id,
            "task_id": f"task-{session_id}",
            "tool": t,
            "args_hash": "abcdef01",
            "success": success,
        }
        for t in tools
    ]


# ---------------------------------------------------------------------------
# find_recurring_sequences — basic
# ---------------------------------------------------------------------------

class TestFindRecurringSequences:
    def test_three_sessions_same_sequence_returns_result(self, tmp_path: Path) -> None:
        """Pattern appearing in 3 sessions with min_occurrences=3 → returned."""
        jsonl = tmp_path / "tool-sequences.jsonl"
        records = []
        for i in range(3):
            records.extend(_make_seq_record(["Read", "Edit", "Bash"], f"sess-{i}"))
        _write_jsonl(jsonl, records)

        result = find_recurring_sequences(jsonl, min_length=3, min_occurrences=3, window_days=7)

        assert len(result) >= 1
        sigs = {r["signature"] for r in result}
        assert "Read->Edit->Bash" in sigs

    def test_two_sessions_below_threshold_returns_empty(self, tmp_path: Path) -> None:
        """Pattern in only 2 sessions with min_occurrences=3 → not returned."""
        jsonl = tmp_path / "tool-sequences.jsonl"
        records = []
        for i in range(2):
            records.extend(_make_seq_record(["Read", "Edit", "Bash"], f"sess-{i}"))
        _write_jsonl(jsonl, records)

        result = find_recurring_sequences(jsonl, min_length=3, min_occurrences=3, window_days=7)
        sigs = {r["signature"] for r in result}
        assert "Read->Edit->Bash" not in sigs

    def test_failed_tools_not_counted(self, tmp_path: Path) -> None:
        """Failed tool calls must not contribute to recurring sequence counts."""
        jsonl = tmp_path / "tool-sequences.jsonl"
        # 5 sessions but all tools have success=False
        records = []
        for i in range(5):
            records.extend(_make_seq_record(["Bash", "Edit", "Read"], f"sess-{i}", success=False))
        _write_jsonl(jsonl, records)

        result = find_recurring_sequences(jsonl, min_length=3, min_occurrences=3, window_days=7)
        assert result == []

    def test_old_records_excluded_by_window(self, tmp_path: Path) -> None:
        """Records older than window_days must not be counted."""
        jsonl = tmp_path / "tool-sequences.jsonl"
        records = []
        for i in range(5):
            # 8 days old — outside 7-day window
            records.extend(_make_seq_record(["Read", "Write", "Bash"], f"sess-{i}", delta_hours=-192))
        _write_jsonl(jsonl, records)

        result = find_recurring_sequences(jsonl, min_length=3, min_occurrences=3, window_days=7)
        assert result == []

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "nonexistent.jsonl"
        assert find_recurring_sequences(jsonl) == []

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "tool-sequences.jsonl"
        _write_jsonl(jsonl, [])
        assert find_recurring_sequences(jsonl) == []

    def test_result_sorted_by_occurrences_desc(self, tmp_path: Path) -> None:
        """Results sorted highest-occurrence first."""
        jsonl = tmp_path / "tool-sequences.jsonl"
        records = []
        # Sequence A: 5 sessions
        for i in range(5):
            records.extend(_make_seq_record(["Read", "Edit", "Bash"], f"a-{i}"))
        # Sequence B: 3 sessions
        for i in range(3):
            records.extend(_make_seq_record(["Write", "Edit", "Bash"], f"b-{i}"))
        _write_jsonl(jsonl, records)

        result = find_recurring_sequences(jsonl, min_length=3, min_occurrences=3, window_days=7)
        occurrences = [r["occurrences"] for r in result]
        assert occurrences == sorted(occurrences, reverse=True)

    def test_sequence_record_has_expected_fields(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "tool-sequences.jsonl"
        records = []
        for i in range(3):
            records.extend(_make_seq_record(["Read", "Edit", "Bash"], f"sess-{i}"))
        _write_jsonl(jsonl, records)

        result = find_recurring_sequences(jsonl, min_length=3, min_occurrences=3, window_days=7)
        assert result

        rec = next(r for r in result if r["signature"] == "Read->Edit->Bash")
        assert "signature" in rec
        assert "tools" in rec
        assert "length" in rec
        assert "occurrences" in rec
        assert "sessions" in rec
        assert "session_count" in rec
        assert rec["length"] == 3
        assert rec["session_count"] == 3

    def test_min_length_filters_short_sequences(self, tmp_path: Path) -> None:
        """Sequences shorter than min_length must not appear."""
        jsonl = tmp_path / "tool-sequences.jsonl"
        # Each session has only 2 tools — below min_length=3
        records = []
        for i in range(5):
            records.extend(_make_seq_record(["Read", "Bash"], f"sess-{i}"))
        _write_jsonl(jsonl, records)

        result = find_recurring_sequences(jsonl, min_length=3, min_occurrences=3, window_days=7)
        # No 3-gram can be formed from a 2-element session
        assert all(r["length"] >= 3 for r in result)


# ---------------------------------------------------------------------------
# propose_skill_draft — draft creation and idempotency
# ---------------------------------------------------------------------------

class TestProposeSkillDraft:
    def _make_seq(self, tools: list[str], occurrences: int = 5) -> dict:
        return {
            "signature": "->".join(tools),
            "tools": tools,
            "length": len(tools),
            "occurrences": occurrences,
            "sessions": [f"sess-{i}" for i in range(min(occurrences, 3))],
            "session_count": min(occurrences, 3),
        }

    def test_creates_skill_md(self, tmp_path: Path) -> None:
        seq = self._make_seq(["Read", "Edit", "Bash"])
        draft_dir = tmp_path / "experimental"
        path = propose_skill_draft(seq, draft_dir)

        assert path.exists()
        assert path.name == "SKILL.md"
        content = path.read_text()
        assert "version: \"0.1.0-experimental\"" in content
        assert "tier: experimental" in content
        assert "auto-generated" in content

    def test_idempotent_on_repeated_calls(self, tmp_path: Path) -> None:
        """Calling twice with same sequence must not overwrite or raise."""
        seq = self._make_seq(["Read", "Write", "Bash"])
        draft_dir = tmp_path / "experimental"
        path1 = propose_skill_draft(seq, draft_dir)
        mtime1 = path1.stat().st_mtime

        path2 = propose_skill_draft(seq, draft_dir)
        mtime2 = path2.stat().st_mtime

        assert path1 == path2
        assert mtime1 == mtime2  # file not touched

    def test_different_sequences_produce_different_dirs(self, tmp_path: Path) -> None:
        draft_dir = tmp_path / "experimental"
        path_a = propose_skill_draft(self._make_seq(["Read", "Edit", "Bash"]), draft_dir)
        path_b = propose_skill_draft(self._make_seq(["Write", "Bash", "Edit"]), draft_dir)
        assert path_a != path_b

    def test_frontmatter_fields_present(self, tmp_path: Path) -> None:
        seq = self._make_seq(["Bash", "Read", "Edit"])
        path = propose_skill_draft(seq, tmp_path / "exp")
        content = path.read_text()

        for field in ("name:", "description:", "version:", "platforms:", "tier:", "tags:"):
            assert field in content, f"Missing frontmatter field: {field}"

    def test_empty_tools_raises_value_error(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="tools"):
            propose_skill_draft({"tools": [], "signature": ""}, tmp_path)

    def test_synthesis_signature_in_content(self, tmp_path: Path) -> None:
        seq = self._make_seq(["Read", "Edit", "Bash"])
        path = propose_skill_draft(seq, tmp_path / "exp")
        content = path.read_text()
        assert "Read->Edit->Bash" in content


# ---------------------------------------------------------------------------
# auto_promote_eligible — threshold filtering
# ---------------------------------------------------------------------------

class TestAutoPromoteEligible:
    def _make_experimental_skill(self, exp_dir: Path, name: str) -> Path:
        skill_dir = exp_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(f"---\nname: {name}\n---\n# {name}\n")
        return skill_file

    def _make_feedback(self, path: Path, skill: str, successes: int, failures: int = 0) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        records = (
            [{"timestamp": ts, "skill": skill, "success": True}] * successes
            + [{"timestamp": ts, "skill": skill, "success": False}] * failures
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")

    def test_skill_above_threshold_returned(self, tmp_path: Path) -> None:
        exp_dir = tmp_path / "experimental"
        fb = tmp_path / "skill-feedback.jsonl"
        self._make_experimental_skill(exp_dir, "auto-read-edit-bash-abc123")
        self._make_feedback(fb, "auto-read-edit-bash-abc123", successes=5)

        result = auto_promote_eligible(exp_dir, fb, threshold=5)
        names = [p.parent.name for p in result]
        assert "auto-read-edit-bash-abc123" in names

    def test_skill_below_threshold_not_returned(self, tmp_path: Path) -> None:
        exp_dir = tmp_path / "experimental"
        fb = tmp_path / "skill-feedback.jsonl"
        self._make_experimental_skill(exp_dir, "auto-write-bash-xyz456")
        self._make_feedback(fb, "auto-write-bash-xyz456", successes=4)

        result = auto_promote_eligible(exp_dir, fb, threshold=5)
        names = [p.parent.name for p in result]
        assert "auto-write-bash-xyz456" not in names

    def test_missing_experimental_dir_returns_empty(self, tmp_path: Path) -> None:
        fb = tmp_path / "feedback.jsonl"
        _write_jsonl(fb, [])
        result = auto_promote_eligible(tmp_path / "nonexistent", fb, threshold=5)
        assert result == []

    def test_failures_do_not_count_toward_threshold(self, tmp_path: Path) -> None:
        """Only successes count — failures should not inflate the count."""
        exp_dir = tmp_path / "experimental"
        fb = tmp_path / "skill-feedback.jsonl"
        self._make_experimental_skill(exp_dir, "auto-flaky-skill-aa1122")
        self._make_feedback(fb, "auto-flaky-skill-aa1122", successes=2, failures=10)

        result = auto_promote_eligible(exp_dir, fb, threshold=5)
        names = [p.parent.name for p in result]
        assert "auto-flaky-skill-aa1122" not in names

    def test_returns_skill_md_paths(self, tmp_path: Path) -> None:
        """Returned paths must point to SKILL.md files, not directories."""
        exp_dir = tmp_path / "experimental"
        fb = tmp_path / "skill-feedback.jsonl"
        self._make_experimental_skill(exp_dir, "auto-eligible-skill-cc3344")
        self._make_feedback(fb, "auto-eligible-skill-cc3344", successes=10)

        result = auto_promote_eligible(exp_dir, fb, threshold=5)
        for p in result:
            assert p.name == "SKILL.md"

    def test_missing_feedback_file_returns_empty(self, tmp_path: Path) -> None:
        exp_dir = tmp_path / "experimental"
        fb = tmp_path / "nonexistent-feedback.jsonl"
        self._make_experimental_skill(exp_dir, "auto-some-skill-dd5566")
        # No feedback file — no skill reaches threshold
        result = auto_promote_eligible(exp_dir, fb, threshold=5)
        assert result == []

    def test_multiple_skills_independent_thresholds(self, tmp_path: Path) -> None:
        """Each skill is evaluated independently."""
        exp_dir = tmp_path / "experimental"
        fb = tmp_path / "skill-feedback.jsonl"
        self._make_experimental_skill(exp_dir, "auto-skill-a-ee7788")
        self._make_experimental_skill(exp_dir, "auto-skill-b-ff9900")
        self._make_feedback(fb, "auto-skill-a-ee7788", successes=6)
        self._make_feedback(fb, "auto-skill-b-ff9900", successes=2)

        result = auto_promote_eligible(exp_dir, fb, threshold=5)
        names = [p.parent.name for p in result]
        assert "auto-skill-a-ee7788" in names
        assert "auto-skill-b-ff9900" not in names
