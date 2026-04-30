"""Unit tests for lib/context_compressor.py (ADR-080 Tier 1 #3).

All tests use mock dispatch — no real LLM calls are made.

Coverage:
1. should_compress: False when COS_CONTEXT_COMPRESS not set
2. should_compress: False when below threshold
3. should_compress: True when above threshold with env var set
4. compress: reduces token count meaningfully
5. compress: preserves last N messages verbatim (recency bias)
6. compress: dispatch unavailable → returns uncompressed with no crash
7. compress_trajectory: summarizes event list correctly
8. compress_trajectory: dispatch unavailable → returns fallback summary without crash
9. Integration: maybe_compress_context no-op without env var
10. Integration: maybe_compress_context compresses when env var set and budget low
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

# Ensure repo root is on the path
_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import lib.context_compressor as cc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_messages(n: int, content_size: int = 500) -> List[Dict[str, Any]]:
    """Generate a simple alternating user/assistant message list."""
    msgs = [{"role": "system", "content": "You are a helpful assistant."}]
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        msgs.append({"role": role, "content": f"Message {i}: " + "x" * content_size})
    return msgs


def _token_count(messages: List[Dict[str, Any]]) -> int:
    return cc._estimate_tokens(messages)


_MOCK_SUMMARY = "## Active Task\nFoo\n\n## Goal\nBar"


# ---------------------------------------------------------------------------
# Tests: should_compress
# ---------------------------------------------------------------------------


class TestShouldCompress(unittest.TestCase):

    def test_returns_false_without_env_var(self):
        """should_compress is a no-op when COS_CONTEXT_COMPRESS is not set."""
        env = {k: v for k, v in os.environ.items() if k != "COS_CONTEXT_COMPRESS"}
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(cc.should_compress(_make_messages(50), budget=10_000))

    def test_returns_false_below_threshold(self):
        """should_compress returns False when usage is comfortably below threshold."""
        msgs = _make_messages(3, content_size=10)  # tiny messages
        with patch.dict(os.environ, {"COS_CONTEXT_COMPRESS": "1"}):
            # budget of 1_000_000 means these tiny messages will never reach 80%
            self.assertFalse(cc.should_compress(msgs, budget=1_000_000))

    def test_returns_true_above_threshold(self):
        """should_compress returns True when usage exceeds threshold_pct of budget."""
        # Create messages with known large size
        msgs = _make_messages(20, content_size=1_000)
        estimated = _token_count(msgs)
        # Set budget so that estimated > 80% of budget
        budget = int(estimated * 0.9)  # estimated is ~111% of budget
        with patch.dict(os.environ, {"COS_CONTEXT_COMPRESS": "1"}):
            self.assertTrue(cc.should_compress(msgs, budget=budget))


# ---------------------------------------------------------------------------
# Tests: compress
# ---------------------------------------------------------------------------


class TestCompress(unittest.TestCase):

    def _mock_dispatch(self, return_value=_MOCK_SUMMARY):
        """Return a context-manager patch for _dispatch_summarize."""
        return patch.object(cc, "_dispatch_summarize", return_value=return_value)

    def test_compress_reduces_token_count(self):
        """compress should produce a smaller token count than the original."""
        msgs = _make_messages(30, content_size=800)
        before = _token_count(msgs)
        with self._mock_dispatch(_MOCK_SUMMARY):
            compressed, _ = cc.compress(msgs, target_tokens=50_000)
        after = _token_count(compressed)
        self.assertLess(after, before, "compress should reduce token count")

    def test_compress_preserves_tail_messages_verbatim(self):
        """The last N messages (recency bias) must appear verbatim in output."""
        msgs = _make_messages(30, content_size=500)
        # The tail ratio defaults to 0.20 * target_tokens.
        # With 30 messages and content_size=500, a generous target_tokens ensures tail is kept.
        with self._mock_dispatch(_MOCK_SUMMARY):
            compressed, _ = cc.compress(msgs, target_tokens=200_000)

        # The very last message must be in the compressed output verbatim
        last_original = msgs[-1]["content"]
        last_compressed = compressed[-1]["content"]
        self.assertEqual(last_original, last_compressed,
                         "Last message must be preserved verbatim (recency bias)")

    def test_compress_preserves_head_messages(self):
        """System prompt and first exchange must not be touched."""
        msgs = _make_messages(30, content_size=500)
        system_content = msgs[0]["content"]
        with self._mock_dispatch(_MOCK_SUMMARY):
            compressed, _ = cc.compress(msgs, target_tokens=200_000)

        # System prompt must still be first
        self.assertEqual(compressed[0]["role"], "system")
        # System prompt content may have a compaction note appended — check it still starts with original
        self.assertIn(system_content, compressed[0]["content"])

    def test_compress_dispatch_unavailable_returns_uncompressed(self):
        """If dispatch returns None, compress returns the original messages without crashing."""
        msgs = _make_messages(20, content_size=500)
        with self._mock_dispatch(None):
            compressed, summary = cc.compress(msgs, target_tokens=10_000)

        # Should return the pruned (but otherwise intact) message list — not crash
        self.assertIsInstance(compressed, list)
        self.assertGreater(len(compressed), 0)
        # summary should be None (no new summary generated)
        self.assertIsNone(summary)

    def test_compress_too_few_messages_noop(self):
        """compress is a no-op when there aren't enough messages to summarize."""
        msgs = _make_messages(3, content_size=100)  # below protect_head + tail_min + 1
        with self._mock_dispatch(_MOCK_SUMMARY):
            compressed, _ = cc.compress(msgs, target_tokens=100)
        # Should return the same list (no-op)
        self.assertEqual(len(msgs), len(compressed))


# ---------------------------------------------------------------------------
# Tests: compress_trajectory
# ---------------------------------------------------------------------------


class TestCompressTrajectory(unittest.TestCase):

    def _make_trajectory(self, n: int = 10) -> list:
        events = []
        for i in range(n):
            events.append({
                "event_type": "tool_use" if i % 2 else "agent_start",
                "agent_id": "agent-001",
                "ts": 1_700_000_000.0 + i,
                "tool_name": f"tool_{i}",
            })
        return events

    def test_compress_trajectory_returns_dict(self):
        """compress_trajectory must return a dict with expected keys."""
        trajectory = self._make_trajectory(10)
        with patch.object(cc, "_dispatch_summarize", return_value="Agent ran 10 tools."):
            result = cc.compress_trajectory(trajectory)

        self.assertIn("type", result)
        self.assertIn("summary", result)
        self.assertIn("event_count", result)
        self.assertIn("ts", result)
        self.assertEqual(result["event_count"], 10)
        self.assertIn("Agent ran 10 tools.", result["summary"])

    def test_compress_trajectory_dispatch_unavailable_fallback(self):
        """If dispatch is unavailable, compress_trajectory returns a fallback dict — no crash."""
        trajectory = self._make_trajectory(5)
        with patch.object(cc, "_dispatch_summarize", return_value=None):
            result = cc.compress_trajectory(trajectory)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["event_count"], 5)
        self.assertIn("unavailable", result["summary"].lower())

    def test_compress_trajectory_empty(self):
        """compress_trajectory handles empty trajectory gracefully."""
        result = cc.compress_trajectory([])
        self.assertEqual(result["event_count"], 0)
        self.assertIn("Empty", result["summary"])


# ---------------------------------------------------------------------------
# Tests: maybe_compress_context (harness adapter integration)
# ---------------------------------------------------------------------------


class TestMaybeCompressContext(unittest.TestCase):

    def test_noop_without_env_var(self):
        """maybe_compress_context is a no-op when COS_CONTEXT_COMPRESS is not set."""
        from lib.harness_adapter.base import maybe_compress_context

        msgs = _make_messages(30, content_size=500)
        env = {k: v for k, v in os.environ.items() if k != "COS_CONTEXT_COMPRESS"}
        with patch.dict(os.environ, env, clear=True):
            result_msgs, result_summary = maybe_compress_context(msgs, budget=1_000)

        self.assertEqual(result_msgs, msgs)
        self.assertIsNone(result_summary)

    def test_compresses_when_env_set_and_budget_low(self):
        """maybe_compress_context compresses when env var is set and budget is low."""
        from lib.harness_adapter.base import maybe_compress_context

        msgs = _make_messages(30, content_size=800)
        estimated = _token_count(msgs)
        budget = int(estimated * 0.9)  # estimated ~111% of budget → above 80% threshold

        with patch.dict(os.environ, {"COS_CONTEXT_COMPRESS": "1"}):
            with patch.object(cc, "_dispatch_summarize", return_value=_MOCK_SUMMARY):
                result_msgs, result_summary = maybe_compress_context(msgs, budget=budget)

        # Compression must have occurred — fewer tokens or fewer messages
        after_tokens = _token_count(result_msgs)
        before_tokens = _token_count(msgs)
        self.assertLess(after_tokens, before_tokens,
                        "maybe_compress_context should reduce token count when triggered")


if __name__ == "__main__":
    unittest.main()
