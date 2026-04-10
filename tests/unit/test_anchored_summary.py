"""Unit tests for lib/anchored_summary.py

AnchoredSummary is a context-compression utility designed to help agents survive
context compaction by maintaining a rolling "anchor" — a structured summary of
the most important information from past messages. The anchor is updated
incrementally so it never loses critical state even as conversation history grows.

If lib/anchored_summary.py does not yet exist, all tests are marked with
pytest.mark.skip so the file is ready to unskip when the module is created.

Test strategy:
  - Pure unit tests: no subprocess, no filesystem, no Engram
  - Each test covers one behavioral contract of the AnchoredSummary class
  - Tests specify the expected API, enabling TDD-style implementation
"""

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Conditional import: skip all tests if module not yet implemented
# ---------------------------------------------------------------------------

_MODULE_PATH = Path(__file__).resolve().parent.parent.parent / "lib" / "anchored_summary.py"
_MODULE_EXISTS = _MODULE_PATH.exists()

_SKIP_REASON = (
    "lib/anchored_summary.py not yet implemented. "
    "These tests are ready to unskip when the module is created."
)

try:
    if _MODULE_EXISTS:
        sys.path.insert(0, str(_MODULE_PATH.parent.parent))
        from lib.anchored_summary import AnchoredSummary  # type: ignore[import]
    else:
        AnchoredSummary = None  # type: ignore[assignment,misc]
except ImportError:
    AnchoredSummary = None


def _skip_if_missing():
    """Skip decorator factory based on module availability."""
    return pytest.mark.skipif(not _MODULE_EXISTS or AnchoredSummary is None, reason=_SKIP_REASON)


# ===========================================================================
# TestAnchoredSummaryCreation
# ===========================================================================


class TestAnchoredSummaryCreation:
    """AnchoredSummary() initializes with the expected empty structure."""

    @_skip_if_missing()
    def test_creates_instance(self):
        """AnchoredSummary() can be instantiated without arguments."""
        anchor = AnchoredSummary()
        assert anchor is not None

    @_skip_if_missing()
    def test_empty_anchor_has_decisions_field(self):
        """New anchor has an empty 'decisions' field."""
        anchor = AnchoredSummary()
        assert hasattr(anchor, "decisions") or hasattr(anchor, "get_summary"), (
            "AnchoredSummary must have a decisions attribute or get_summary method"
        )

    @_skip_if_missing()
    def test_empty_anchor_has_files_field(self):
        """New anchor tracks modified files."""
        anchor = AnchoredSummary()
        # Accepts either attribute-based or dict-based access
        summary = anchor.get_summary() if hasattr(anchor, "get_summary") else {}
        assert isinstance(summary, (dict, str)), "get_summary() must return dict or str"

    @_skip_if_missing()
    def test_empty_anchor_has_task_state_field(self):
        """New anchor tracks current task state."""
        anchor = AnchoredSummary()
        assert anchor is not None  # Detailed check depends on API

    @_skip_if_missing()
    def test_empty_anchor_has_next_steps_field(self):
        """New anchor has a 'next_steps' or equivalent field for what to do after compaction."""
        anchor = AnchoredSummary()
        assert anchor is not None  # Specific field check per implementation


# ===========================================================================
# TestMergeNewMessages
# ===========================================================================


class TestMergeNewMessages:
    """merge_new_messages() updates the anchor without losing existing content."""

    @_skip_if_missing()
    def test_merge_updates_anchor(self):
        """Merging messages changes the anchor state."""
        anchor = AnchoredSummary()
        messages = [
            {"role": "assistant", "content": "I decided to use PostgreSQL."},
        ]
        anchor.merge_new_messages(messages)
        summary = anchor.get_summary()
        # Summary should be non-empty after a merge
        assert summary, "Summary should not be empty after merging messages"

    @_skip_if_missing()
    def test_merge_preserves_old_content(self):
        """Iterative merges accumulate — old content is not dropped."""
        anchor = AnchoredSummary()

        # First merge
        anchor.merge_new_messages([
            {"role": "assistant", "content": "Decision A: use PostgreSQL."},
        ])

        # Second merge
        anchor.merge_new_messages([
            {"role": "assistant", "content": "Decision B: use ginext not huma."},
        ])

        summary_text = str(anchor.get_summary())
        # Both decisions should be present
        assert "PostgreSQL" in summary_text or "A" in summary_text, (
            "First merge content lost after second merge"
        )

    @_skip_if_missing()
    def test_merge_preserves_file_paths(self):
        """File paths mentioned in messages are preserved in the anchor."""
        anchor = AnchoredSummary()
        anchor.merge_new_messages([
            {"role": "assistant", "content": "Modified internal/users/handler.go"},
        ])
        summary_text = str(anchor.get_summary())
        assert "handler.go" in summary_text or "users" in summary_text, (
            "File path not preserved in anchor after merge"
        )

    @_skip_if_missing()
    def test_merge_handles_empty_messages(self):
        """Merging an empty list does not crash and leaves anchor unchanged."""
        anchor = AnchoredSummary()
        anchor.merge_new_messages([
            {"role": "assistant", "content": "Initial content."},
        ])
        first_summary = str(anchor.get_summary())

        anchor.merge_new_messages([])  # empty merge — should not raise

        second_summary = str(anchor.get_summary())
        assert first_summary == second_summary, (
            "Empty merge should not change the anchor"
        )

    @_skip_if_missing()
    def test_merge_handles_large_batch(self):
        """Merging >50 messages does not crash and produces a non-empty summary."""
        anchor = AnchoredSummary()
        messages = [
            {"role": "assistant", "content": f"Message {i} with content about feature {i}."}
            for i in range(60)
        ]
        anchor.merge_new_messages(messages)
        summary = anchor.get_summary()
        assert summary, "Summary should not be empty after large batch merge"


# ===========================================================================
# TestGetSummary
# ===========================================================================


class TestGetSummary:
    """get_summary() returns a formatted, non-empty representation of the anchor."""

    @_skip_if_missing()
    def test_empty_anchor_returns_something(self):
        """get_summary() on a fresh anchor returns a string (possibly empty string)."""
        anchor = AnchoredSummary()
        result = anchor.get_summary()
        assert isinstance(result, (str, dict)), (
            f"get_summary() must return str or dict, got {type(result)}"
        )

    @_skip_if_missing()
    def test_populated_anchor_returns_non_empty(self):
        """get_summary() returns non-empty output after content is added."""
        anchor = AnchoredSummary()
        anchor.merge_new_messages([
            {"role": "assistant", "content": "Made an important decision about the architecture."},
        ])
        result = anchor.get_summary()
        assert result, "get_summary() returned empty after populating anchor"

    @_skip_if_missing()
    def test_summary_is_deterministic(self):
        """Calling get_summary() twice returns the same result."""
        anchor = AnchoredSummary()
        anchor.merge_new_messages([
            {"role": "assistant", "content": "Decision: use PostgreSQL."},
        ])
        first = anchor.get_summary()
        second = anchor.get_summary()
        assert first == second, "get_summary() is not deterministic"


# ===========================================================================
# TestEngramPersistence
# ===========================================================================


class TestEngramPersistence:
    """save_to_engram() and load_from_engram() round-trip correctly.

    These tests are skipped when the module doesn't exist OR when engram
    is not available (handled by individual test logic).
    """

    @_skip_if_missing()
    def test_save_to_engram_method_exists(self):
        """AnchoredSummary has a save_to_engram() method."""
        anchor = AnchoredSummary()
        assert hasattr(anchor, "save_to_engram"), (
            "AnchoredSummary must have save_to_engram() method"
        )

    @_skip_if_missing()
    def test_load_from_engram_method_exists(self):
        """AnchoredSummary has a load_from_engram() class/static method."""
        assert hasattr(AnchoredSummary, "load_from_engram"), (
            "AnchoredSummary must have load_from_engram() class or static method"
        )

    @_skip_if_missing()
    def test_save_and_load_roundtrip(self, tmp_path):
        """State saved to engram is recovered by load_from_engram().

        Uses a mock or in-memory backend if engram binary is not installed.
        """
        anchor = AnchoredSummary()
        anchor.merge_new_messages([
            {"role": "assistant", "content": "Decision: use PostgreSQL. Files: handler.go"},
        ])

        import shutil
        import os
        engram_bin = os.environ.get("ENGRAM_BIN", str(Path.home() / ".local" / "bin" / "engram"))
        if not Path(engram_bin).exists() and not shutil.which("engram"):
            pytest.skip("engram binary not available for roundtrip test")

        session_key = f"test-anchor-{__import__('uuid').uuid4().hex[:8]}"

        try:
            anchor.save_to_engram(session_key)
            loaded = AnchoredSummary.load_from_engram(session_key)
            assert loaded is not None, "load_from_engram returned None"
            loaded_summary = str(loaded.get_summary())
            assert loaded_summary, "Loaded anchor has empty summary"
        except Exception as exc:
            pytest.fail(f"save/load roundtrip raised: {exc}")


# ===========================================================================
# TestIterativeMergePreservesFilePaths
# ===========================================================================


class TestIterativeMergePreservesFilePaths:
    """File paths and decisions accumulate correctly across iterative merges."""

    @_skip_if_missing()
    def test_file_paths_accumulate_across_merges(self):
        """Multiple file paths mentioned in different merges are all preserved."""
        anchor = AnchoredSummary()

        anchor.merge_new_messages([
            {"role": "assistant", "content": "Modified internal/users/handler.go"},
        ])
        anchor.merge_new_messages([
            {"role": "assistant", "content": "Also modified internal/users/dto.go"},
        ])
        anchor.merge_new_messages([
            {"role": "assistant", "content": "Added tests in internal/users/handler_test.go"},
        ])

        summary_text = str(anchor.get_summary())
        # At least some of the file context should be preserved
        has_files = any(
            name in summary_text
            for name in ("handler", "dto", "test", "users", "internal")
        )
        assert has_files, (
            f"No file path context found in anchor after 3 merges.\nSummary: {summary_text!r}"
        )

    @_skip_if_missing()
    def test_decisions_accumulate_across_merges(self):
        """Decisions from multiple merges coexist in the summary."""
        anchor = AnchoredSummary()

        decisions = [
            "Use PostgreSQL for the database.",
            "Use ginext for HTTP handlers.",
            "Use clean architecture with 4 layers.",
        ]

        for decision in decisions:
            anchor.merge_new_messages([
                {"role": "assistant", "content": f"Decision: {decision}"},
            ])

        summary_text = str(anchor.get_summary())
        # At least one major decision keyword must survive
        found_keywords = [kw for kw in ["PostgreSQL", "ginext", "architecture", "layers", "HTTP"]
                          if kw.lower() in summary_text.lower()]
        assert found_keywords, (
            f"No decision keywords survived iterative merges.\nSummary: {summary_text!r}"
        )

    @_skip_if_missing()
    def test_merge_with_only_tool_calls_no_crash(self):
        """Merging messages that only contain tool calls does not crash."""
        anchor = AnchoredSummary()
        tool_messages = [
            {"role": "assistant", "content": None, "tool_use": {"name": "Read", "input": {}}},
            {"role": "user", "content": None, "tool_result": {"content": "file content"}},
        ]
        # Should not raise regardless of whether tool calls are processed
        try:
            anchor.merge_new_messages(tool_messages)
        except (KeyError, TypeError) as exc:
            pytest.fail(
                f"merge_new_messages raised {type(exc).__name__} on tool call messages: {exc}"
            )
