"""Unit tests for lib/prompt_cache.py

Validates Anthropic prompt caching adapter: system prompt caching,
message-level caching (system_and_3 strategy), and savings estimation.
Also tests PromptCacheManager for ClaudeExecutor integration.
"""

import copy
import pytest

from lib.prompt_cache import (
    _apply_cache_marker,
    apply_cache_to_system_prompt,
    apply_message_cache,
    estimate_cache_savings,
    PromptCacheManager,
)

pytestmark = pytest.mark.unit

MARKER = {"type": "ephemeral"}


# ---------------------------------------------------------------------------
# _apply_cache_marker
# ---------------------------------------------------------------------------


class TestApplyCacheMarker:
    def test_string_content_wrapped_in_list(self):
        msg = {"role": "user", "content": "Hello"}
        _apply_cache_marker(msg, MARKER)
        assert isinstance(msg["content"], list)
        assert len(msg["content"]) == 1
        assert msg["content"][0]["type"] == "text"
        assert msg["content"][0]["text"] == "Hello"
        assert msg["content"][0]["cache_control"] == MARKER

    def test_none_content_gets_top_level_marker(self):
        msg = {"role": "assistant", "content": None}
        _apply_cache_marker(msg, MARKER)
        assert msg["cache_control"] == MARKER

    def test_empty_string_content_gets_top_level_marker(self):
        msg = {"role": "assistant", "content": ""}
        _apply_cache_marker(msg, MARKER)
        assert msg["cache_control"] == MARKER
        assert msg["content"] == ""

    def test_list_content_last_item_gets_marker(self):
        msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": "First"},
                {"type": "text", "text": "Second"},
            ],
        }
        _apply_cache_marker(msg, MARKER)
        assert "cache_control" not in msg["content"][0]
        assert msg["content"][1]["cache_control"] == MARKER

    def test_empty_list_no_crash(self):
        msg = {"role": "user", "content": []}
        _apply_cache_marker(msg, MARKER)  # should not raise

    def test_tool_message_native_anthropic(self):
        msg = {"role": "tool", "content": "result"}
        _apply_cache_marker(msg, MARKER, native_anthropic=True)
        assert msg["cache_control"] == MARKER

    def test_tool_message_non_native_skips(self):
        msg = {"role": "tool", "content": "result"}
        _apply_cache_marker(msg, MARKER, native_anthropic=False)
        assert "cache_control" not in msg


# ---------------------------------------------------------------------------
# apply_cache_to_system_prompt
# ---------------------------------------------------------------------------


class TestApplyCacheToSystemPrompt:
    def test_returns_list_with_one_block(self):
        result = apply_cache_to_system_prompt("You are helpful.")
        assert isinstance(result, list)
        assert len(result) == 1

    def test_block_has_correct_structure(self):
        result = apply_cache_to_system_prompt("System prompt text")
        block = result[0]
        assert block["type"] == "text"
        assert block["text"] == "System prompt text"
        assert block["cache_control"]["type"] == "ephemeral"

    def test_default_ttl_is_5m(self):
        result = apply_cache_to_system_prompt("test")
        assert "ttl" not in result[0]["cache_control"]

    def test_1h_ttl(self):
        result = apply_cache_to_system_prompt("test", cache_ttl="1h")
        assert result[0]["cache_control"]["ttl"] == "1h"

    def test_preserves_full_prompt_text(self):
        long_prompt = "A" * 10000
        result = apply_cache_to_system_prompt(long_prompt)
        assert result[0]["text"] == long_prompt

    def test_empty_prompt(self):
        result = apply_cache_to_system_prompt("")
        assert result[0]["text"] == ""
        assert result[0]["cache_control"]["type"] == "ephemeral"


# ---------------------------------------------------------------------------
# apply_message_cache
# ---------------------------------------------------------------------------


class TestApplyMessageCache:
    def test_empty_messages(self):
        assert apply_message_cache([]) == []

    def test_returns_deep_copy(self):
        msgs = [{"role": "user", "content": "Hello"}]
        result = apply_message_cache(msgs)
        assert result is not msgs
        assert result[0] is not msgs[0]

    def test_original_unmodified(self):
        msgs = [{"role": "user", "content": "Hello"}]
        original = copy.deepcopy(msgs)
        apply_message_cache(msgs)
        assert msgs == original

    def test_system_message_gets_marker(self):
        msgs = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hi"},
        ]
        result = apply_message_cache(msgs)
        sys_content = result[0]["content"]
        assert isinstance(sys_content, list)
        assert sys_content[0]["cache_control"]["type"] == "ephemeral"

    def test_max_4_breakpoints(self):
        msgs = [{"role": "system", "content": "System"}] + [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg{i}"}
            for i in range(10)
        ]
        result = apply_message_cache(msgs)
        count = 0
        for msg in result:
            content = msg.get("content")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "cache_control" in item:
                        count += 1
            elif "cache_control" in msg:
                count += 1
        assert count <= 4

    def test_no_system_message(self):
        msgs = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        result = apply_message_cache(msgs)
        assert len(result) == 2

    def test_1h_ttl_propagated(self):
        msgs = [{"role": "system", "content": "System prompt"}]
        result = apply_message_cache(msgs, cache_ttl="1h")
        sys_content = result[0]["content"]
        assert isinstance(sys_content, list)
        assert sys_content[0]["cache_control"]["ttl"] == "1h"

    def test_native_anthropic_flag(self):
        msgs = [
            {"role": "system", "content": "System"},
            {"role": "tool", "content": "result"},
        ]
        result = apply_message_cache(msgs, native_anthropic=True)
        assert result[1].get("cache_control", {}).get("type") == "ephemeral"

    def test_last_3_non_system_get_markers(self):
        msgs = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "msg2"},
            {"role": "user", "content": "msg3"},
            {"role": "assistant", "content": "msg4"},
        ]
        result = apply_message_cache(msgs)
        # msg1 (index 1) should NOT have marker -- only last 3 non-system
        content_1 = result[1]["content"]
        if isinstance(content_1, str):
            pass  # no marker applied (still a string = no wrapping)
        else:
            assert "cache_control" not in content_1[0]


# ---------------------------------------------------------------------------
# estimate_cache_savings
# ---------------------------------------------------------------------------


class TestEstimateCacheSavings:
    def test_single_turn_no_savings(self):
        result = estimate_cache_savings(5000, avg_turns=1)
        assert result["cached_tokens"] == 0
        assert result["savings_pct"] == 0

    def test_multi_turn_has_savings(self):
        result = estimate_cache_savings(5000, avg_turns=5)
        assert result["cached_tokens"] > 0
        assert result["savings_pct"] > 0

    def test_savings_increase_with_turns(self):
        r5 = estimate_cache_savings(5000, avg_turns=5)
        r10 = estimate_cache_savings(5000, avg_turns=10)
        assert r10["cached_tokens"] > r5["cached_tokens"]

    def test_savings_increase_with_prompt_size(self):
        small = estimate_cache_savings(1000, avg_turns=5)
        large = estimate_cache_savings(10000, avg_turns=5)
        assert large["cached_tokens"] > small["cached_tokens"]

    def test_returns_expected_keys(self):
        result = estimate_cache_savings(5000)
        assert "cached_tokens" in result
        assert "savings_pct" in result
        assert "description" in result

    def test_description_is_string(self):
        result = estimate_cache_savings(5000, avg_turns=5)
        assert isinstance(result["description"], str)
        assert len(result["description"]) > 0

    def test_zero_tokens_no_crash(self):
        result = estimate_cache_savings(0, avg_turns=5)
        assert result["cached_tokens"] == 0


# ---------------------------------------------------------------------------
# PromptCacheManager
# ---------------------------------------------------------------------------


class TestPromptCacheManager:
    def setup_method(self):
        self.mgr = PromptCacheManager()

    # --- add_cache_breakpoints ---

    def test_add_cache_breakpoints_adds_marker(self):
        msgs = [{"role": "system", "content": "You are a helpful agent."}]
        result = self.mgr.add_cache_breakpoints(msgs)
        assert result[0].get("cache_control") == {"type": "ephemeral"} or (
            isinstance(result[0]["content"], list)
            and result[0]["content"][0].get("cache_control") == {"type": "ephemeral"}
        )

    def test_cache_breakpoints_only_on_system(self):
        """Task-specific messages (after the preamble) must not get cache markers."""
        preamble = "You are a helpful agent.\n"
        msgs = [
            {"role": "system", "content": preamble},
            {"role": "user", "content": "## Task\nDo the work."},
        ]
        result = self.mgr.add_cache_breakpoints(msgs)
        # Second message (the task) must NOT have cache_control
        task_msg = result[1]
        assert "cache_control" not in task_msg
        content = task_msg.get("content", "")
        if isinstance(content, list):
            for block in content:
                assert "cache_control" not in block

    def test_empty_messages(self):
        assert self.mgr.add_cache_breakpoints([]) == []

    def test_original_not_mutated(self):
        msgs = [{"role": "system", "content": "Preamble"}]
        original = copy.deepcopy(msgs)
        self.mgr.add_cache_breakpoints(msgs)
        assert msgs == original

    # --- estimate_cache_savings ---

    def test_estimate_savings_positive(self):
        """Multiple invocations must yield positive savings."""
        result = self.mgr.estimate_cache_savings(cached_tokens=5000, total_invocations=10)
        assert result["savings_pct"] > 0
        assert result["with_cache_usd"] < result["without_cache_usd"]

    def test_estimate_savings_single(self):
        """Single invocation has no reads — write overhead may exceed savings."""
        result = self.mgr.estimate_cache_savings(cached_tokens=5000, total_invocations=1)
        # write cost (1.25×) > read savings (0) → with_cache >= without_cache
        assert result["cache_read_cost"] == 0.0

    def test_estimate_savings_above_50pct_for_many_invocations(self):
        """5+ invocations must yield >50% savings as required by acceptance criteria."""
        result = self.mgr.estimate_cache_savings(cached_tokens=5000, total_invocations=5)
        assert result["savings_pct"] > 50

    def test_pricing_correctness(self):
        """write = 1.25× input, read = 0.10× input."""
        tokens = 1_000_000  # exactly 1M for easy maths
        result = self.mgr.estimate_cache_savings(cached_tokens=tokens, total_invocations=2)
        # write: $3.75, read: $0.30 (1 read) → total $4.05
        assert abs(result["cache_write_cost"] - 3.75) < 0.01
        assert abs(result["cache_read_cost"] - 0.30) < 0.01

    def test_returns_all_keys(self):
        result = self.mgr.estimate_cache_savings(5000, 5)
        for key in ("without_cache_usd", "with_cache_usd", "savings_pct",
                    "cache_write_cost", "cache_read_cost"):
            assert key in result

    # --- split_prompt_sections ---

    def test_split_sections_with_task_marker(self):
        prompt = "Preamble rules.\n\n## Task\nDo something.\n"
        result = self.mgr.split_prompt_sections(prompt)
        assert "Preamble" in result["cacheable"]
        assert "## Task" in result["non_cacheable"]
        assert "## Task" not in result["cacheable"]

    def test_split_sections_no_marker(self):
        prompt = "Just rules, no task section."
        result = self.mgr.split_prompt_sections(prompt)
        assert result["cacheable"] == prompt
        assert result["non_cacheable"] == ""

    def test_cacheable_tokens_estimate(self):
        prompt = "A" * 400 + "\n\n## Task\nwork"
        result = self.mgr.split_prompt_sections(prompt)
        # 400 chars / 4 = 100 tokens roughly
        assert 80 <= result["cacheable_tokens"] <= 120

    # --- format_cache_report ---

    def test_format_cache_report(self):
        report = self.mgr.format_cache_report(invocations=10, cached_tokens=5000)
        assert "%" in report
        assert "$" in report
        assert "10" in report

    def test_format_cache_report_contains_savings(self):
        report = self.mgr.format_cache_report(invocations=10, cached_tokens=5000)
        # savings should be non-zero for 10 invocations
        assert "0%" not in report or "saved" in report
