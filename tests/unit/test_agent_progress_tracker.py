"""Tests for lib/agent_progress_tracker.py"""

import pytest
from lib.agent_progress_tracker import AgentProgressTracker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tracker():
    return AgentProgressTracker("Fix auth bug in lib/auth.py")


@pytest.fixture
def tracker_custom():
    return AgentProgressTracker("Implement JWT refresh token flow", project="my-project")


# ---------------------------------------------------------------------------
# should_save
# ---------------------------------------------------------------------------

class TestShouldSave:
    def test_should_save_every_10(self, tracker):
        assert tracker.should_save(10) is True
        assert tracker.should_save(20) is True
        assert tracker.should_save(30) is True

    def test_should_save_never_at_zero(self, tracker):
        assert tracker.should_save(0) is False

    def test_should_not_save_between_intervals(self, tracker):
        for n in range(1, 10):
            assert tracker.should_save(n) is False
        for n in range(11, 20):
            assert tracker.should_save(n) is False

    def test_should_save_at_100(self, tracker):
        assert tracker.should_save(100) is True


# ---------------------------------------------------------------------------
# generate_topic_key
# ---------------------------------------------------------------------------

class TestGenerateTopicKey:
    def test_uses_agent_progress_prefix(self, tracker):
        key = tracker.generate_topic_key()
        assert key.startswith("agent-progress/")

    def test_slugifies_correctly(self, tracker):
        key = tracker.generate_topic_key()
        # "Fix auth bug in lib/auth.py" -> first 5 words after stripping non-alnum chars:
        # "Fix auth bug in libauthpy" (slash and dot removed, words joined)
        assert key == "agent-progress/fix-auth-bug-in-libauthpy"

    def test_generate_topic_key_long_description(self):
        t = AgentProgressTracker("one two three four five six seven eight")
        key = t.generate_topic_key()
        # Only first 5 words
        assert key == "agent-progress/one-two-three-four-five"

    def test_generate_topic_key_special_chars(self):
        t = AgentProgressTracker("Fix: the 'bug' in auth!")
        key = t.generate_topic_key()
        # Special chars stripped, words: Fix the bug in auth
        assert key == "agent-progress/fix-the-bug-in-auth"

    def test_topic_key_is_stable(self, tracker):
        """Same instance returns same key on multiple calls."""
        assert tracker.generate_topic_key() == tracker.generate_topic_key()

    def test_topic_key_lowercase(self):
        t = AgentProgressTracker("UPPERCASE Task Description Here Now")
        key = t.generate_topic_key()
        assert key == key.lower()


# ---------------------------------------------------------------------------
# format_progress_save
# ---------------------------------------------------------------------------

class TestFormatProgressSave:
    def test_format_progress_save_structure(self, tracker):
        result = tracker.format_progress_save(10)
        assert "title" in result
        assert "content" in result
        assert "type" in result
        assert "topic_key" in result
        assert "project" in result

    def test_format_progress_save_title(self, tracker):
        result = tracker.format_progress_save(10)
        assert "Progress:" in result["title"]
        assert "step 1" in result["title"]

    def test_format_progress_save_step_increments(self, tracker):
        r10 = tracker.format_progress_save(10)
        r20 = tracker.format_progress_save(20)
        assert "step 1" in r10["title"]
        assert "step 2" in r20["title"]

    def test_format_progress_save_content_includes_task(self, tracker):
        result = tracker.format_progress_save(10)
        assert "Fix auth bug in lib/auth.py" in result["content"]

    def test_format_progress_save_content_includes_findings(self, tracker):
        result = tracker.format_progress_save(10, findings=["Found the bug", "JWT is misconfigured"])
        assert "Found the bug" in result["content"]
        assert "JWT is misconfigured" in result["content"]

    def test_format_progress_save_content_includes_files(self, tracker):
        result = tracker.format_progress_save(
            10,
            files_created=["lib/new.py"],
            files_modified=["lib/auth.py"],
        )
        assert "lib/new.py" in result["content"]
        assert "lib/auth.py" in result["content"]

    def test_format_progress_save_default_status(self, tracker):
        result = tracker.format_progress_save(10)
        assert "in_progress" in result["content"]

    def test_format_progress_save_topic_key_matches_generate(self, tracker):
        result = tracker.format_progress_save(10)
        assert result["topic_key"] == tracker.generate_topic_key()

    def test_format_progress_save_project(self, tracker_custom):
        result = tracker_custom.format_progress_save(10)
        assert result["project"] == "my-project"

    def test_format_progress_save_type_is_discovery(self, tracker):
        result = tracker.format_progress_save(10)
        assert result["type"] == "discovery"


# ---------------------------------------------------------------------------
# format_final_save
# ---------------------------------------------------------------------------

class TestFormatFinalSave:
    def test_format_final_save_status_completed(self, tracker):
        result = tracker.format_final_save()
        assert "completed" in result["content"]

    def test_format_final_save_overwrites_topic_key(self, tracker):
        """Same topic_key as progress so mem_save upserts."""
        progress = tracker.format_progress_save(10)
        final = tracker.format_final_save()
        assert progress["topic_key"] == final["topic_key"]

    def test_format_final_save_title_says_completed(self, tracker):
        result = tracker.format_final_save()
        assert "Completed:" in result["title"]

    def test_format_final_save_includes_result_summary(self, tracker):
        result = tracker.format_final_save(result_summary="All 5 tests pass")
        assert "All 5 tests pass" in result["content"]

    def test_format_final_save_includes_files(self, tracker):
        result = tracker.format_final_save(
            files_created=["lib/auth_v2.py"],
            files_modified=["tests/test_auth.py"],
        )
        assert "lib/auth_v2.py" in result["content"]
        assert "tests/test_auth.py" in result["content"]


# ---------------------------------------------------------------------------
# Edge cases — empty/None inputs
# ---------------------------------------------------------------------------

class TestEmptyInputs:
    def test_empty_lists_handled(self, tracker):
        """None/empty lists should not crash."""
        result = tracker.format_progress_save(10, files_created=None, files_modified=[], findings=None)
        assert result is not None
        assert "none" in result["content"]

    def test_empty_findings_list(self, tracker):
        result = tracker.format_progress_save(10, findings=[])
        assert "none" in result["content"]

    def test_final_save_no_args(self, tracker):
        result = tracker.format_final_save()
        assert result is not None
        assert result["topic_key"].startswith("agent-progress/")

    def test_empty_task_description(self):
        t = AgentProgressTracker("")
        key = t.generate_topic_key()
        assert key == "agent-progress/unknown"
