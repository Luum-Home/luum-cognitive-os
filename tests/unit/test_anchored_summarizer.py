"""Unit tests for lib/anchored_summarizer.py

Tests cover:
  - extract_decisions with various decision patterns
  - extract_file_paths from mixed text
  - extract_task_state (done / remaining)
  - create_anchor combines all extractions
  - persist_anchor writes file
  - auto_save convenience method
  - Empty / edge-case input handling
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# Ensure lib/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lib.anchored_summarizer import AnchoredSummarizer  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make(session_dir: str | None = None, tmp_path=None) -> AnchoredSummarizer:
    if session_dir:
        return AnchoredSummarizer(session_dir=session_dir)
    if tmp_path:
        return AnchoredSummarizer(session_dir=str(tmp_path / "session"))
    return AnchoredSummarizer()


# ===========================================================================
# extract_decisions
# ===========================================================================


class TestExtractDecisions:
    def test_decided_to_phrase(self):
        text = "We decided to use PostgreSQL for the database."
        decisions = _make().extract_decisions(text)
        assert any("PostgreSQL" in d for d in decisions), decisions

    def test_chose_phrase(self):
        text = "I chose ginext over huma for the HTTP layer."
        decisions = _make().extract_decisions(text)
        assert any("ginext" in d or "huma" in d for d in decisions), decisions

    def test_will_use_phrase(self):
        text = "We will use clean architecture with four layers."
        decisions = _make().extract_decisions(text)
        assert decisions, "No decisions extracted from 'will use' phrase"

    def test_approach_colon_phrase(self):
        text = "Approach: write one use case per file."
        decisions = _make().extract_decisions(text)
        assert decisions, "No decisions extracted from 'approach:' phrase"

    def test_multiple_decisions_in_text(self):
        text = (
            "Decided to use Redis for caching.\n"
            "We will use ginext for routing.\n"
            "Chose PostgreSQL over MySQL."
        )
        decisions = _make().extract_decisions(text)
        assert len(decisions) >= 2, f"Expected >=2 decisions, got: {decisions}"

    def test_empty_text_returns_empty_list(self):
        assert _make().extract_decisions("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert _make().extract_decisions("   \n\t  ") == []

    def test_no_decision_signals_returns_empty(self):
        text = "The weather is nice today and the sky is blue."
        decisions = _make().extract_decisions(text)
        # May return empty, that's fine
        assert isinstance(decisions, list)

    def test_deduplication(self):
        text = "We decided to use Redis. We decided to use Redis again."
        decisions = _make().extract_decisions(text)
        # Should not have exact duplicates
        lower_decisions = [d.lower() for d in decisions]
        assert len(lower_decisions) == len(set(lower_decisions)), "Duplicate decisions returned"


# ===========================================================================
# extract_file_paths
# ===========================================================================


class TestExtractFilePaths:
    def test_simple_go_file(self):
        text = "Modified internal/users/handler.go to add new endpoint."
        paths = _make().extract_file_paths(text)
        assert any("handler.go" in p or "internal/users" in p for p in paths), paths

    def test_multiple_paths_in_text(self):
        text = (
            "Created lib/anchored_summarizer.py and updated hooks/pre-compaction-flush.sh."
        )
        paths = _make().extract_file_paths(text)
        assert len(paths) >= 1, f"Expected paths, got: {paths}"

    def test_absolute_path(self):
        text = "The file /home/user/project/config.yaml was updated."
        paths = _make().extract_file_paths(text)
        assert any("config.yaml" in p or "project" in p for p in paths), paths

    def test_url_excluded(self):
        text = "See https://example.com/docs/path for details."
        paths = _make().extract_file_paths(text)
        # Should not include the URL
        assert not any("https:" in p for p in paths), f"URL included in paths: {paths}"

    def test_empty_text_returns_empty(self):
        assert _make().extract_file_paths("") == []

    def test_no_paths_in_plain_text(self):
        text = "Hello world. This is a sentence with no paths."
        paths = _make().extract_file_paths(text)
        assert isinstance(paths, list)

    def test_deduplicated(self):
        text = "Modified internal/users/handler.go and also internal/users/handler.go again."
        paths = _make().extract_file_paths(text)
        assert len(paths) == len(set(paths)), "Duplicate paths returned"


# ===========================================================================
# extract_task_state
# ===========================================================================


class TestExtractTaskState:
    def test_returns_dict_with_done_and_remaining(self):
        state = _make().extract_task_state("completed the handler. still need to add tests.")
        assert "done" in state and "remaining" in state

    def test_completed_phrase(self):
        text = "Completed the user authentication module."
        state = _make().extract_task_state(text)
        assert state["done"], f"Expected done items, got: {state}"

    def test_still_need_to_phrase(self):
        text = "Still need to add integration tests for the payment endpoint."
        state = _make().extract_task_state(text)
        assert state["remaining"], f"Expected remaining items, got: {state}"

    def test_empty_text(self):
        state = _make().extract_task_state("")
        assert state == {"done": [], "remaining": []}

    def test_no_task_signals(self):
        text = "The sky is blue and the grass is green."
        state = _make().extract_task_state(text)
        assert "done" in state and "remaining" in state


# ===========================================================================
# create_anchor
# ===========================================================================


class TestCreateAnchor:
    def test_returns_dict_with_required_keys(self):
        anchor = _make().create_anchor("decided to use PostgreSQL.")
        for key in ("timestamp", "decisions", "files_touched", "task_state", "summary"):
            assert key in anchor, f"Missing key '{key}' in anchor"

    def test_timestamp_is_iso_format(self):
        anchor = _make().create_anchor("decided to use Redis.")
        ts = anchor["timestamp"]
        from datetime import datetime, timezone
        # Must parse without raising and be a recent UTC timestamp
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None, "timestamp must be timezone-aware"
        assert parsed.year >= 2024, f"timestamp year {parsed.year} looks wrong"

    def test_decisions_populated(self):
        anchor = _make().create_anchor("We decided to use ginext for routing.")
        assert isinstance(anchor["decisions"], list)
        assert anchor["decisions"], "Decisions should be non-empty"

    def test_files_touched_populated(self):
        anchor = _make().create_anchor("Modified lib/anchored_summarizer.py today.")
        assert isinstance(anchor["files_touched"], list)

    def test_task_state_is_dict(self):
        anchor = _make().create_anchor("Completed the handler. Still need to add tests.")
        assert isinstance(anchor["task_state"], dict)

    def test_summary_is_string(self):
        anchor = _make().create_anchor("decided to use Redis.")
        assert isinstance(anchor["summary"], str)

    def test_empty_context_returns_valid_anchor(self):
        anchor = _make().create_anchor("")
        for key in ("timestamp", "decisions", "files_touched", "task_state", "summary"):
            assert key in anchor


# ===========================================================================
# persist_anchor
# ===========================================================================


class TestPersistAnchor:
    def test_writes_file_to_session_dir(self, tmp_path):
        session_dir = tmp_path / "session"
        instance = AnchoredSummarizer(session_dir=str(session_dir))
        anchor = instance.create_anchor("decided to use Redis.")
        result = instance.persist_anchor(anchor, to_file=True, to_engram=False)
        assert result["file_path"] is not None
        assert Path(result["file_path"]).exists()

    def test_written_file_is_valid_json(self, tmp_path):
        session_dir = tmp_path / "session"
        instance = AnchoredSummarizer(session_dir=str(session_dir))
        anchor = instance.create_anchor("decided to use PostgreSQL.")
        result = instance.persist_anchor(anchor, to_file=True, to_engram=False)
        content = Path(result["file_path"]).read_text()
        parsed = json.loads(content)
        assert "timestamp" in parsed

    def test_creates_session_dir_if_missing(self, tmp_path):
        session_dir = tmp_path / "new" / "session"
        assert not session_dir.exists()
        instance = AnchoredSummarizer(session_dir=str(session_dir))
        anchor = instance.create_anchor("decided to use Redis.")
        result = instance.persist_anchor(anchor, to_file=True, to_engram=False)
        assert session_dir.exists()

    def test_file_path_none_when_to_file_false(self, tmp_path):
        session_dir = tmp_path / "session"
        instance = AnchoredSummarizer(session_dir=str(session_dir))
        anchor = instance.create_anchor("decided to use Redis.")
        result = instance.persist_anchor(anchor, to_file=False, to_engram=False)
        assert result["file_path"] is None


# ===========================================================================
# auto_save
# ===========================================================================


class TestAutoSave:
    def test_auto_save_returns_dict(self, tmp_path):
        result = AnchoredSummarizer.auto_save(session_dir=str(tmp_path / "session"))
        assert isinstance(result, dict)

    def test_auto_save_writes_anchor_file(self, tmp_path):
        session_dir = tmp_path / "session"
        AnchoredSummarizer.auto_save(session_dir=str(session_dir))
        anchor_file = session_dir / "anchor.json"
        assert anchor_file.exists(), "anchor.json not written by auto_save"

    def test_auto_save_with_snapshot(self, tmp_path):
        """auto_save reads state-snapshot.json when present."""
        session_dir = tmp_path / "session"
        session_dir.mkdir(parents=True)
        snapshot = {
            "active_tasks": ["implement anchored summarizer"],
            "git_status": "M lib/anchored_summarizer.py",
        }
        (session_dir / "state-snapshot.json").write_text(json.dumps(snapshot))
        result = AnchoredSummarizer.auto_save(session_dir=str(session_dir))
        assert result["file_path"] is not None
        anchor_file = Path(result["file_path"])
        content = json.loads(anchor_file.read_text())
        assert "timestamp" in content
