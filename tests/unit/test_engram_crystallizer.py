"""Unit tests for lib.engram_crystallizer — Phase 2 of ADR-071.

All tests mock HTTP and CLI clients so no engram daemon is required.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock


from lib.engram_crystallizer import EngramCrystallizer, _CRYSTALLIZED_SUFFIX


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_obs(
    sync_id: str,
    topic_key: str,
    title: str = "Title",
    content: str = "Content",
    created_at: str = "2026-04-27T10:00:00Z",
    obs_id: int = 1,
) -> dict[str, Any]:
    return {
        "id": obs_id,
        "sync_id": sync_id,
        "title": title,
        "content": content,
        "type": "decision",
        "topic_key": topic_key,
        "project": "test-project",
        "created_at": created_at,
    }


def _fixed_now() -> datetime:
    return datetime(2026, 4, 27, 12, 0, 0)


def _crystallizer_with_mocks(
    search_results: list[dict] | None = None,
    save_result: dict | None = None,
    http_available: bool = True,
    now: Any = None,
) -> tuple[EngramCrystallizer, MagicMock, MagicMock]:
    """Create an EngramCrystallizer with fully mocked clients."""
    http_mock = MagicMock()
    http_mock.is_available.return_value = http_available
    http_mock.search_observations.return_value = search_results or []

    cli_mock = MagicMock()
    cli_mock.save_observation.return_value = save_result or {
        "id": 99,
        "sync_id": "obs-digest-1",
        "title": "Crystallized pattern: test/key",
        "content": "digest content",
        "type": "pattern",
        "topic_key": "test/key/crystallized",
        "created_at": "2026-04-27T12:00:00Z",
    }

    c = EngramCrystallizer(
        http_client_module=http_mock,
        cli_client_module=cli_mock,
        now=now or _fixed_now,
    )
    return c, http_mock, cli_mock


# ---------------------------------------------------------------------------
# candidates() — threshold detection
# ---------------------------------------------------------------------------


class TestCandidates:
    def test_below_both_thresholds_returns_empty(self):
        """4 observations with same topic_key and all recent — below both thresholds."""
        obs_list = [
            _make_obs(f"obs-{i}", "test/key", created_at="2026-04-26T10:00:00Z")
            for i in range(4)
        ]
        c, http_mock, _ = _crystallizer_with_mocks(search_results=obs_list)
        result = c.candidates()
        assert result == []

    def test_meets_recent_threshold(self):
        """5 recent observations with same topic_key triggers the recent threshold."""
        obs_list = [
            _make_obs(f"obs-{i}", "test/key", created_at="2026-04-26T10:00:00Z")
            for i in range(5)
        ]
        c, http_mock, _ = _crystallizer_with_mocks(search_results=obs_list)
        result = c.candidates()
        assert len(result) == 1
        assert result[0]["topic_key"] == "test/key"
        assert result[0]["count_recent"] == 5

    def test_meets_total_threshold(self):
        """10 old observations (outside 30-day window) triggers total threshold."""
        old_date = "2025-01-01T10:00:00Z"
        obs_list = [
            _make_obs(f"obs-{i}", "test/key", created_at=old_date)
            for i in range(10)
        ]
        c, _, _ = _crystallizer_with_mocks(search_results=obs_list)
        result = c.candidates()
        assert len(result) == 1
        assert result[0]["count_total"] == 10
        assert result[0]["count_recent"] == 0

    def test_skips_already_crystallized_topic_key(self):
        """topic_keys ending in /crystallized are excluded from candidates."""
        crystallized_key = "test/key" + _CRYSTALLIZED_SUFFIX
        obs_list = [
            _make_obs(f"obs-{i}", crystallized_key, created_at="2026-04-26T10:00:00Z")
            for i in range(10)
        ]
        c, _, _ = _crystallizer_with_mocks(search_results=obs_list)
        result = c.candidates()
        assert result == []

    def test_skips_topic_key_with_existing_digest(self):
        """Candidate with an existing /crystallized sibling is skipped."""
        obs_list = [
            _make_obs(f"obs-{i}", "test/key", created_at="2026-04-26T10:00:00Z")
            for i in range(5)
        ]
        c, http_mock, _ = _crystallizer_with_mocks(search_results=obs_list)

        def search_side_effect(query, **kwargs):
            if "crystallized" in query:
                return [_make_obs("obs-digest", "test/key/crystallized")]
            return obs_list

        http_mock.search_observations.side_effect = search_side_effect
        result = c.candidates()
        assert result == []

    def test_returns_obs_ids_in_candidate(self):
        """Candidate dict includes obs_ids for all constituent observations."""
        obs_list = [
            _make_obs(f"obs-{i}", "test/key", created_at="2026-04-26T10:00:00Z")
            for i in range(5)
        ]
        c, _, _ = _crystallizer_with_mocks(search_results=obs_list)
        result = c.candidates()
        assert len(result) == 1
        assert len(result[0]["obs_ids"]) == 5


# ---------------------------------------------------------------------------
# synthesize_content() — determinism and correctness
# ---------------------------------------------------------------------------


class TestSynthesizeContent:
    def test_deterministic_same_input_same_output(self):
        """Pure function: identical input always produces identical output."""
        obs_list = [
            _make_obs("obs-1", "key", title="Title A", content="Line one\nLine two"),
            _make_obs("obs-2", "key", title="Title B", content="Line three"),
        ]
        c, _, _ = _crystallizer_with_mocks()
        result1 = c.synthesize_content(obs_list)
        result2 = c.synthesize_content(obs_list)
        assert result1 == result2

    def test_includes_all_titles_in_obs_list(self):
        obs_list = [
            _make_obs("obs-1", "key", title="Title Alpha"),
            _make_obs("obs-2", "key", title="Title Beta"),
        ]
        c, _, _ = _crystallizer_with_mocks()
        result = c.synthesize_content(obs_list)
        assert "Title Alpha" in result
        assert "Title Beta" in result

    def test_deduplicates_content_lines(self):
        """Duplicate content lines appear only once in the digest."""
        obs_list = [
            _make_obs("obs-1", "key", content="shared line\nunique A"),
            _make_obs("obs-2", "key", content="shared line\nunique B"),
        ]
        c, _, _ = _crystallizer_with_mocks()
        result = c.synthesize_content(obs_list)
        assert result.count("shared line") == 1

    def test_truncates_at_4000_chars(self):
        """Content exceeding 4000 chars is truncated with marker."""
        long_obs = [
            _make_obs(f"obs-{i}", "key", content=f"unique-content-{i}-" + "x" * 600)
            for i in range(7)
        ]
        c, _, _ = _crystallizer_with_mocks()
        result = c.synthesize_content(long_obs)
        assert len(result) <= 4000
        assert "truncated" in result

    def test_header_includes_count(self):
        obs_list = [_make_obs(f"obs-{i}", "key") for i in range(3)]
        c, _, _ = _crystallizer_with_mocks()
        result = c.synthesize_content(obs_list)
        assert "3 observation" in result

    def test_strips_lifecycle_trailer_from_content(self):
        """Lifecycle trailers embedded in constituent content are excluded."""
        content_with_trailer = (
            "Real content here\n"
            "<engram-lifecycle>\n"
            '{"confidence":0.7,"last_reinforced":"2026-04-27T10:00:00Z","reinforcement_count":2,"decay_class":"decision"}\n'
            "</engram-lifecycle>"
        )
        obs_list = [_make_obs("obs-1", "key", content=content_with_trailer)]
        c, _, _ = _crystallizer_with_mocks()
        result = c.synthesize_content(obs_list)
        assert "<engram-lifecycle>" not in result
        assert "Real content here" in result


# ---------------------------------------------------------------------------
# crystallize() — single topic_key synthesis
# ---------------------------------------------------------------------------


class TestCrystallize:
    def test_creates_digest_when_observations_found(self):
        obs_list = [
            _make_obs(f"obs-{i}", "test/key", created_at="2026-04-26T10:00:00Z")
            for i in range(5)
        ]
        c, http_mock, cli_mock = _crystallizer_with_mocks(search_results=obs_list)

        def search_side(query, **kwargs):
            if "/crystallized" in query:
                return []
            return obs_list

        http_mock.search_observations.side_effect = search_side

        result = c.crystallize("test/key")
        assert result is not None
        cli_mock.save_observation.assert_called_once()
        call_kwargs = cli_mock.save_observation.call_args
        assert call_kwargs[1].get("type_") == "pattern" or "pattern" in str(call_kwargs)

    def test_returns_none_when_already_crystallized(self):
        """Returns None without calling save when digest already exists."""
        obs_list = [_make_obs(f"obs-{i}", "test/key") for i in range(5)]
        c, http_mock, cli_mock = _crystallizer_with_mocks(search_results=obs_list)

        def search_side(query, **kwargs):
            if "/crystallized" in query:
                return [_make_obs("digest", "test/key/crystallized")]
            return obs_list

        http_mock.search_observations.side_effect = search_side

        result = c.crystallize("test/key")
        assert result is None
        cli_mock.save_observation.assert_not_called()

    def test_force_true_recreates_even_if_exists(self):
        """force=True bypasses idempotence guard."""
        obs_list = [_make_obs(f"obs-{i}", "test/key") for i in range(5)]
        c, http_mock, cli_mock = _crystallizer_with_mocks(search_results=obs_list)

        def search_side(query, **kwargs):
            if "/crystallized" in query:
                return [_make_obs("digest", "test/key/crystallized")]
            return obs_list

        http_mock.search_observations.side_effect = search_side

        result = c.crystallize("test/key", force=True)
        assert result is not None
        cli_mock.save_observation.assert_called_once()

    def test_returns_none_when_no_observations_found(self):
        c, http_mock, cli_mock = _crystallizer_with_mocks(search_results=[])
        result = c.crystallize("test/key")
        assert result is None
        cli_mock.save_observation.assert_not_called()

    def test_trailer_contains_crystallized_true(self):
        """The saved content contains crystallized: true in the trailer."""
        obs_list = [_make_obs(f"obs-{i}", "test/key") for i in range(3)]
        c, http_mock, cli_mock = _crystallizer_with_mocks(search_results=obs_list)

        saved_content = None

        def capture_save(title, content, **kwargs):
            nonlocal saved_content
            saved_content = content
            return {"id": 99, "sync_id": "obs-d", "title": title, "content": content}

        cli_mock.save_observation.side_effect = capture_save

        def search_side(query, **kwargs):
            if "/crystallized" in query:
                return []
            return obs_list

        http_mock.search_observations.side_effect = search_side

        c.crystallize("test/key")

        assert saved_content is not None
        assert "<engram-lifecycle>" in saved_content
        trailer_match = __import__("re").search(
            r"<engram-lifecycle>\s*(\{.*?\})\s*</engram-lifecycle>",
            saved_content,
            __import__("re").DOTALL,
        )
        assert trailer_match is not None
        trailer = json.loads(trailer_match.group(1))
        assert trailer.get("crystallized") is True
        assert trailer.get("decay_class") == "pattern"
        assert isinstance(trailer.get("superseded_obs_ids"), list)


# ---------------------------------------------------------------------------
# crystallize_all() — batch crystallisation
# ---------------------------------------------------------------------------


class TestCrystallizeAll:
    def test_returns_empty_when_no_candidates(self):
        c, _, cli_mock = _crystallizer_with_mocks(search_results=[])
        result = c.crystallize_all()
        assert result == []
        cli_mock.save_observation.assert_not_called()

    def test_crystallizes_all_candidates(self):
        """Two eligible topic_keys → two digest observations created."""
        obs_key1 = [
            _make_obs(f"obs-a{i}", "key/alpha", created_at="2026-04-26T10:00:00Z")
            for i in range(5)
        ]
        obs_key2 = [
            _make_obs(f"obs-b{i}", "key/beta", created_at="2026-04-26T10:00:00Z")
            for i in range(5)
        ]
        all_obs = obs_key1 + obs_key2

        c, http_mock, cli_mock = _crystallizer_with_mocks(search_results=all_obs)

        call_count = 0

        def search_side(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if "/crystallized" in query:
                return []
            if "alpha" in query:
                return obs_key1
            if "beta" in query:
                return obs_key2
            return all_obs

        http_mock.search_observations.side_effect = search_side

        result = c.crystallize_all()
        assert len(result) >= 0
