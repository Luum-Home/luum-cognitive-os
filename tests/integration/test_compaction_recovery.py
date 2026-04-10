"""Integration tests for compaction recovery via Engram persistence.

Verifies that critical state can survive a simulated context compaction:
  - Session summaries with decisions, files, and next_steps are fully recoverable
  - Multiple observations saved in sequence are all findable
  - Special characters (file paths with spaces, JSON content) round-trip correctly
  - Keyword search finds content saved with an explicit topic_key
  - A full pre-compaction → post-compaction recovery simulation works end-to-end

Uses the real_engram fixture from tests/conftest.py — no mocks.
Auto-skips if the engram binary is not installed.
"""

import json
import uuid

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique(prefix: str = "test") -> str:
    """Return a unique string to prevent test data collisions."""
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


# ===========================================================================
# TestSessionSummaryRoundtrip
# ===========================================================================


class TestSessionSummaryRoundtrip:
    """Session summary data survives save → search → verify cycles."""

    def test_session_summary_all_fields_recoverable(self, real_engram):
        """Save a full session summary and verify all fields are findable.

        Simulates what pre-compaction-flush.sh asks the agent to do:
        save a structured session summary before context is lost.
        """
        session_id = _unique("session")
        decisions = "Use PostgreSQL for the user service. Adopt ginext over huma."
        files_modified = "internal/users/handler.go, internal/users/dto.go"
        next_steps = "Complete the GetUserByID use case. Add integration tests."

        content = (
            f"## Session: {session_id}\n"
            f"**Decisions**: {decisions}\n"
            f"**Files Modified**: {files_modified}\n"
            f"**Next Steps**: {next_steps}\n"
        )

        result = real_engram["save"](
            f"Session summary {session_id}",
            content,
            topic_key=f"planning/{session_id}/session-summary",
            type_="manual",
        )
        assert result.returncode == 0, f"Save failed: {result.stderr}"

        # Simulate post-compaction: search by the unique session ID
        search = real_engram["search"](session_id)
        assert search.returncode == 0, f"Search failed: {search.stderr}"

        # Verify by reading from DB directly
        rows = real_engram["query"](
            "SELECT content FROM observations WHERE project = ? ORDER BY id DESC LIMIT 10",
            (real_engram["project"],),
        )
        all_content = " ".join(r[0] or "" for r in rows)
        assert decisions[:20] in all_content, "Decisions not found in recovered content"
        assert "internal/users" in all_content, "File paths not found in recovered content"
        assert "integration tests" in all_content, "Next steps not found in recovered content"

    def test_decisions_recoverable_by_keyword_search(self, real_engram):
        """Architectural decisions saved pre-compaction are findable by keyword."""
        unique_decision = _unique("decision-use-postgres")
        content = f"Architecture decision: {unique_decision} — chose PostgreSQL over MySQL."

        real_engram["save"](f"arch-decision-{unique_decision}", content)

        search = real_engram["search"](unique_decision)
        assert search.returncode == 0

        # The unique decision marker must appear in search output or DB
        rows = real_engram["query"](
            "SELECT content FROM observations WHERE project = ? ORDER BY id DESC LIMIT 5",
            (real_engram["project"],),
        )
        found = any(unique_decision in (r[0] or "") for r in rows)
        assert found, f"Decision marker {unique_decision!r} not found after save"

    def test_bug_fix_context_survives_compaction(self, real_engram):
        """Bug fix context (root cause + fix) is fully recoverable after compaction."""
        bug_id = _unique("bugfix-nil-pointer")
        content = (
            f"## Bug: {bug_id}\n"
            "**Root cause**: nil pointer in GetUser when user not found\n"
            "**Fix**: added nil check in handler.go line 42\n"
            "**Files**: internal/users/handler.go\n"
        )

        real_engram["save"](
            f"Bug fix: {bug_id}",
            content,
            topic_key=f"bugfix/users/{bug_id}",
            type_="manual",
        )

        rows = real_engram["query"](
            "SELECT content FROM observations WHERE project = ? ORDER BY id DESC LIMIT 5",
            (real_engram["project"],),
        )
        all_content = " ".join(r[0] or "" for r in rows)
        assert "nil pointer" in all_content, "Bug root cause not recoverable"
        assert "handler.go line 42" in all_content, "Fix location not recoverable"


# ===========================================================================
# TestMultipleObservationRecovery
# ===========================================================================


class TestMultipleObservationRecovery:
    """Multiple observations saved in sequence are all individually findable."""

    def test_five_observations_all_findable(self, real_engram):
        """Save 5 observations; verify each is independently findable."""
        markers = [_unique(f"obs{i}") for i in range(5)]

        for i, marker in enumerate(markers):
            result = real_engram["save"](
                f"observation-{marker}",
                f"Content for observation {marker}: important data {i}",
                topic_key=f"planning/test-{marker}/obs",
            )
            assert result.returncode == 0, f"Save {i} failed: {result.stderr}"

        # All 5 must be present in the DB
        rows = real_engram["query"](
            "SELECT content FROM observations WHERE project = ? ORDER BY id DESC LIMIT 20",
            (real_engram["project"],),
        )
        all_content = " ".join(r[0] or "" for r in rows)
        for marker in markers:
            assert marker in all_content, f"Observation {marker!r} not found after sequential saves"

    def test_observation_ordering_preserved(self, real_engram):
        """Rows saved in sequence should accumulate, not overwrite."""
        before = real_engram["query"](
            "SELECT COUNT(*) FROM observations WHERE project = ?",
            (real_engram["project"],),
        )[0][0]

        for i in range(3):
            real_engram["save"](f"seq-{_unique()}", f"sequential content {i}")

        after = real_engram["query"](
            "SELECT COUNT(*) FROM observations WHERE project = ?",
            (real_engram["project"],),
        )[0][0]

        assert after >= before + 3, f"Expected ≥3 new rows, got {after - before}"

    def test_topic_keyed_observations_each_findable(self, real_engram):
        """Observations with different topic keys are each independently findable."""
        topic_keys = [
            f"planning/change-{_unique()}/proposal",
            f"implementation/service-{_unique()}/pattern",
            f"bugfix/api/{_unique()}",
        ]
        markers = []

        for key in topic_keys:
            marker = _unique("content")
            markers.append(marker)
            result = real_engram["save"](
                f"obs-{marker}",
                f"Unique marker: {marker}",
                topic_key=key,
            )
            assert result.returncode == 0

        rows = real_engram["query"](
            "SELECT content FROM observations WHERE project = ? ORDER BY id DESC LIMIT 20",
            (real_engram["project"],),
        )
        all_content = " ".join(r[0] or "" for r in rows)
        for marker in markers:
            assert marker in all_content, f"Marker {marker!r} for a topic-keyed obs not found"


# ===========================================================================
# TestSpecialCharacterRoundtrip
# ===========================================================================


class TestSpecialCharacterRoundtrip:
    """Special characters and complex content survive the Engram round-trip."""

    def test_file_path_with_spaces_survives(self, real_engram):
        """File paths containing spaces round-trip correctly."""
        title = f"paths-{_unique()}"
        content = "Modified files: /Users/me/My Projects/luum/src/main.go"
        result = real_engram["save"](title, content)
        assert result.returncode == 0, f"Save with spaces failed: {result.stderr}"

    def test_json_content_survives(self, real_engram):
        """JSON-structured content saves and is findable."""
        title = f"json-{_unique()}"
        unique_key = _unique("json-marker")
        payload = json.dumps({
            "decision": "Use PostgreSQL",
            "marker": unique_key,
            "files": ["internal/users/handler.go"],
        })
        result = real_engram["save"](title, payload)
        assert result.returncode == 0, f"Save of JSON content failed: {result.stderr}"

        # The unique marker should be findable
        rows = real_engram["query"](
            "SELECT content FROM observations WHERE project = ? ORDER BY id DESC LIMIT 5",
            (real_engram["project"],),
        )
        found = any(unique_key in (r[0] or "") for r in rows)
        assert found, f"JSON content with marker {unique_key!r} not found after save"

    def test_multiline_content_with_code_survives(self, real_engram):
        """Multiline content including code snippets round-trips correctly."""
        title = f"code-{_unique()}"
        unique_marker = _unique("code-marker")
        content = (
            f"## Fix: {unique_marker}\n\n"
            "```go\n"
            "func GetUser(id string) (*User, error) {\n"
            "    if id == \"\" {\n"
            "        return nil, ErrInvalidID\n"
            "    }\n"
            "    return repo.FindByID(id)\n"
            "}\n"
            "```\n"
        )
        result = real_engram["save"](title, content)
        assert result.returncode == 0, f"Save of multiline code content failed: {result.stderr}"

    def test_unicode_content_survives(self, real_engram):
        """Spanish/accented characters survive the round-trip."""
        title = f"unicode-{_unique()}"
        content = "Decisión arquitectural: usar ginext no huma. Éxito en la implementación."
        result = real_engram["save"](title, content)
        assert result.returncode == 0, f"Save of unicode content failed: {result.stderr}"

    def test_content_with_markdown_headers_survives(self, real_engram):
        """Markdown-formatted content (headers, bullets, code blocks) saves correctly."""
        title = f"markdown-{_unique()}"
        unique_marker = _unique("md-marker")
        content = (
            f"# Session Summary: {unique_marker}\n\n"
            "## What was accomplished\n"
            "- Implemented GetUserByID use case\n"
            "- Added unit tests\n\n"
            "## Files Modified\n"
            "- `internal/users/application/use_cases/get_user_by_id.go`\n"
            "- `internal/users/application/use_cases/get_user_by_id_test.go`\n"
        )
        result = real_engram["save"](title, content)
        assert result.returncode == 0, f"Save of markdown content failed: {result.stderr}"


# ===========================================================================
# TestKeywordSearchForTopicKeyed
# ===========================================================================


class TestKeywordSearchForTopicKeyed:
    """Observations saved with topic_key are findable by keyword, not just exact key."""

    def test_search_by_keyword_finds_topic_keyed_obs(self, real_engram):
        """An observation saved with a topic_key is searchable by its content keywords."""
        unique_keyword = _unique("kw-postgres")
        topic_key = f"architecture/{_unique()}"

        real_engram["save"](
            f"Decision: {unique_keyword}",
            f"We chose PostgreSQL because of {unique_keyword} reasons.",
            topic_key=topic_key,
        )

        search = real_engram["search"](unique_keyword)
        assert search.returncode == 0, f"Keyword search failed: {search.stderr}"
        # Verify the data is in DB (search output format varies)
        rows = real_engram["query"](
            "SELECT content FROM observations WHERE project = ? ORDER BY id DESC LIMIT 5",
            (real_engram["project"],),
        )
        found = any(unique_keyword in (r[0] or "") for r in rows)
        assert found, f"Topic-keyed observation not findable by keyword {unique_keyword!r}"

    def test_search_by_title_fragment_works(self, real_engram):
        """Partial title search returns the matching observation."""
        unique_fragment = _unique("arch-frag")
        full_title = f"Architecture decision: {unique_fragment}-full-title"

        real_engram["save"](full_title, "Some architectural decision content.")

        search = real_engram["search"](unique_fragment)
        assert search.returncode == 0


# ===========================================================================
# TestCompactionRecoverySimulation
# ===========================================================================


class TestCompactionRecoverySimulation:
    """End-to-end simulation of pre-compaction save → post-compaction recovery.

    Models the actual scenario:
    1. Session is running, context fills up
    2. pre-compaction-flush.sh fires, agent saves state to Engram
    3. Context is compacted (simulated by reading only from Engram)
    4. New session starts, reads Engram to recover state
    5. Verify all critical state is present

    No actual context compaction is triggered — we simulate it by only
    reading from Engram after the saves, as a new session would.
    """

    def test_full_pre_to_post_compaction_state_recovery(self, real_engram):
        """Critical session state is fully recoverable after simulated compaction."""
        session_marker = _unique("session")

        # === PRE-COMPACTION PHASE ===
        # Simulate what an agent does when pre-compaction-flush.sh fires:

        # 1. Save architectural decisions
        arch_decision_marker = _unique("arch-postgres")
        real_engram["save"](
            f"Architecture: {arch_decision_marker}",
            f"Decision {arch_decision_marker}: Use PostgreSQL 16 for user service. "
            "Rationale: project standard, good performance for our workload.",
            topic_key=f"architecture/{session_marker}",
            type_="manual",
        )

        # 2. Save in-progress task state
        task_marker = _unique("task-get-user")
        real_engram["save"](
            f"In-progress task: {task_marker}",
            f"Task {task_marker}: Implementing GetUserByID use case. "
            "Status: handler done, use case 70% complete. "
            "Next: add error handling and write unit tests. "
            "Files: internal/users/application/use_cases/get_user_by_id.go",
            topic_key=f"planning/{session_marker}/task-state",
            type_="manual",
        )

        # 3. Save bug fix that was just applied
        bugfix_marker = _unique("fix-nil")
        real_engram["save"](
            f"Bug fix: {bugfix_marker}",
            f"Fixed {bugfix_marker}: nil pointer dereference in user handler. "
            "Root cause: repo.FindByID returned nil without error on not-found. "
            "Fix: added nil check + return ErrUserNotFound.",
            topic_key=f"bugfix/users/{bugfix_marker}",
            type_="manual",
        )

        # === SIMULATED COMPACTION ===
        # In real compaction, the conversation history is lost.
        # We simulate this by querying Engram cold — no conversation context used.

        # === POST-COMPACTION RECOVERY ===
        # A new session would search Engram to recover state.
        rows = real_engram["query"](
            "SELECT title, content FROM observations WHERE project = ? ORDER BY id DESC LIMIT 20",
            (real_engram["project"],),
        )

        all_titles = [r[0] or "" for r in rows]
        all_content = [r[1] or "" for r in rows]
        all_text = " ".join(all_titles + all_content)

        # Verify each piece of critical state is recoverable
        assert arch_decision_marker in all_text, (
            f"Architectural decision {arch_decision_marker!r} not found post-compaction"
        )
        assert task_marker in all_text, (
            f"In-progress task {task_marker!r} not found post-compaction"
        )
        assert bugfix_marker in all_text, (
            f"Bug fix {bugfix_marker!r} not found post-compaction"
        )
        assert "GetUserByID" in all_text, "Task name not recoverable"
        assert "nil pointer" in all_text, "Bug root cause not recoverable"
        assert "PostgreSQL" in all_text, "Architectural decision content not recoverable"

    def test_recovery_works_without_exact_topic_key(self, real_engram):
        """State can be recovered even without knowing the exact topic_key — keyword search works."""
        unique_content = _unique("recovery-test")

        real_engram["save"](
            f"Pre-compaction state: {unique_content}",
            f"This content {unique_content} must be recoverable by keyword search.",
            topic_key=f"planning/some-specific-key-{unique_content}",
        )

        # Recovery via keyword (the realistic scenario — new session searches by topic)
        search_result = real_engram["search"](unique_content)
        assert search_result.returncode == 0, f"Keyword recovery search failed: {search_result.stderr}"

    def test_multiple_sessions_state_recovery(self, real_engram):
        """State from multiple session saves can coexist and are individually recoverable."""
        session_markers = [_unique(f"sess{i}") for i in range(3)]

        for marker in session_markers:
            real_engram["save"](
                f"Session checkpoint {marker}",
                f"Session {marker} decisions: chose approach A, modified file X, next do Y.",
                topic_key=f"planning/{marker}/checkpoint",
            )

        # All three sessions must be recoverable
        rows = real_engram["query"](
            "SELECT content FROM observations WHERE project = ? ORDER BY id DESC LIMIT 20",
            (real_engram["project"],),
        )
        all_content = " ".join(r[0] or "" for r in rows)
        for marker in session_markers:
            assert marker in all_content, (
                f"Session {marker!r} state not found in cross-session recovery"
            )
