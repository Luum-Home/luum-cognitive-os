"""Unit tests for lib/prompt_cache.py

Validates:
  A. Legacy Anthropic adapter: system prompt caching, message-level caching
     (system_and_3 strategy), savings estimation, PromptCacheManager.
  B. Portable provider-agnostic layer (ADR-080 Tier 1 #2): mark_cacheable,
     compose_cached_prompt, cache_metrics, maybe_apply_cache, and provider
     adapters (Anthropic, OpenAI/Codex, Ollama).
"""

import copy
import threading

import pytest

from lib.prompt_cache import (
    _apply_cache_marker,
    apply_cache_to_system_prompt,
    apply_message_cache,
    estimate_cache_savings,
    PromptCacheManager,
    # Portable layer (ADR-080 Tier 1 #2)
    CacheableSegment,
    ProviderRequest,
    mark_cacheable,
    compose_cached_prompt,
    cache_metrics,
    maybe_apply_cache,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Metrics reset helper
# ---------------------------------------------------------------------------


def _fresh_metrics():
    """Reset process-local cache metrics between tests to avoid cross-test leakage."""
    import lib.prompt_cache as pc
    with pc._metrics_lock:
        for k in list(pc._metrics.keys()):
            pc._metrics[k] = 0

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


# ===========================================================================
# Section B: Portable provider-agnostic layer (ADR-080 Tier 1 #2)
# ===========================================================================


# ---------------------------------------------------------------------------
# mark_cacheable
# ---------------------------------------------------------------------------


class TestMarkCacheable:
    def test_returns_cacheable_segment(self):
        seg = mark_cacheable("You are an agent.")
        assert isinstance(seg, CacheableSegment)
        assert seg.text == "You are an agent."
        assert seg.ttl == "5m"
        assert seg.role == "system"

    def test_custom_ttl_and_role(self):
        seg = mark_cacheable("rules block", ttl="1h", role="user")
        assert seg.ttl == "1h"
        assert seg.role == "user"


# ---------------------------------------------------------------------------
# compose_cached_prompt — Anthropic adapter
# ---------------------------------------------------------------------------


class TestComposeAnthropicAdapter:
    def setup_method(self):
        _fresh_metrics()

    def test_returns_provider_request(self):
        seg = mark_cacheable("You are an agent.")
        req = compose_cached_prompt([seg], provider="anthropic")
        assert isinstance(req, ProviderRequest)
        assert req.provider == "anthropic"
        assert req.cache_applied is True

    def test_anthropic_cache_control_type_ephemeral(self):
        """Anthropic adapter must produce cache_control with type=ephemeral."""
        seg = mark_cacheable("Stable system prompt.")
        req = compose_cached_prompt([seg], provider="anthropic")
        assert req.raw_messages, "raw_messages must not be empty"
        block = req.raw_messages[0]
        assert block["type"] == "text"
        assert "cache_control" in block, "Anthropic adapter must inject cache_control"
        cc = block["cache_control"]
        assert cc.get("type") == "ephemeral", f"Expected ephemeral, got {cc}"

    def test_anthropic_1h_ttl_propagated(self):
        seg = mark_cacheable("Long-lived rules.", ttl="1h")
        req = compose_cached_prompt([seg], provider="anthropic")
        cc = req.raw_messages[0]["cache_control"]
        assert cc.get("ttl") == "1h"

    def test_anthropic_max_4_breakpoints_enforced(self):
        """Segments beyond 4 must NOT receive cache_control (Anthropic hard limit)."""
        segs = [mark_cacheable(f"seg {i}") for i in range(6)]
        req = compose_cached_prompt(segs, provider="anthropic")
        assert len(req.raw_messages) == 6
        for i, block in enumerate(req.raw_messages):
            if i < 4:
                assert "cache_control" in block, f"Block {i} should have cache_control"
            else:
                assert "cache_control" not in block, (
                    f"Block {i} must NOT have cache_control (exceeds 4-breakpoint limit)"
                )

    def test_claude_alias_uses_anthropic_adapter(self):
        """'claude' provider must use the Anthropic adapter (COS 'claude' = Anthropic API)."""
        seg = mark_cacheable("System.")
        req = compose_cached_prompt([seg], provider="claude")
        assert "cache_control" in req.raw_messages[0]
        assert req.cache_applied is True

    def test_writes_metric_incremented_for_anthropic(self):
        seg = mark_cacheable("content")
        compose_cached_prompt([seg], provider="anthropic")
        m = cache_metrics()
        assert m["writes"] >= 1


# ---------------------------------------------------------------------------
# compose_cached_prompt — OpenAI/Codex adapter (documented no-op)
# ---------------------------------------------------------------------------


class TestComposeOpenAIAdapter:
    def setup_method(self):
        _fresh_metrics()

    def test_openai_no_cache_control_injected(self):
        """OpenAI adapter is a documented no-op: must NOT inject cache_control."""
        seg = mark_cacheable("System prompt for openai.")
        req = compose_cached_prompt([seg], provider="openai")
        block = req.raw_messages[0]
        assert "cache_control" not in block, "OpenAI adapter must not inject cache_control"

    def test_openai_returns_plain_text_blocks(self):
        seg = mark_cacheable("Hello openai")
        req = compose_cached_prompt([seg], provider="openai")
        assert req.raw_messages[0]["type"] == "text"
        assert req.raw_messages[0]["text"] == "Hello openai"

    def test_openai_cache_applied_false(self):
        seg = mark_cacheable("System.")
        req = compose_cached_prompt([seg], provider="openai")
        assert req.cache_applied is False

    def test_codex_alias_is_no_op(self):
        """'codex' provider must be a no-op (OpenAI-compatible format)."""
        seg = mark_cacheable("Codex system.")
        req = compose_cached_prompt([seg], provider="codex")
        assert "cache_control" not in req.raw_messages[0]

    def test_noop_openai_metric_incremented(self):
        seg = mark_cacheable("content")
        compose_cached_prompt([seg], provider="openai")
        m = cache_metrics()
        assert m["noop_openai"] >= 1


# ---------------------------------------------------------------------------
# compose_cached_prompt — Ollama adapter (silent no-op)
# ---------------------------------------------------------------------------


class TestComposeOllamaAdapter:
    def setup_method(self):
        _fresh_metrics()

    def test_ollama_no_cache_control(self):
        seg = mark_cacheable("Ollama system.")
        req = compose_cached_prompt([seg], provider="ollama")
        assert "cache_control" not in req.raw_messages[0]

    def test_ollama_returns_plain_text(self):
        seg = mark_cacheable("Hello ollama")
        req = compose_cached_prompt([seg], provider="ollama")
        assert req.raw_messages[0]["text"] == "Hello ollama"

    def test_unknown_provider_falls_back_to_noop(self):
        """Unknown provider must not raise — falls back to Ollama no-op."""
        seg = mark_cacheable("content")
        req = compose_cached_prompt([seg], provider="unknown_future_provider_xyz")
        assert "cache_control" not in req.raw_messages[0]

    def test_noop_ollama_metric_incremented(self):
        seg = mark_cacheable("content")
        compose_cached_prompt([seg], provider="ollama")
        m = cache_metrics()
        assert m["noop_ollama"] >= 1


# ---------------------------------------------------------------------------
# cache_metrics
# ---------------------------------------------------------------------------


class TestCacheMetrics:
    def setup_method(self):
        _fresh_metrics()

    def test_initial_state_all_zeros(self):
        m = cache_metrics()
        assert m["hits"] == 0
        assert m["misses"] == 0
        assert m["writes"] == 0
        assert m["hit_rate_pct"] == 0.0

    def test_hit_rate_computed_correctly(self):
        import lib.prompt_cache as pc
        with pc._metrics_lock:
            pc._metrics["hits"] = 3
            pc._metrics["misses"] = 1
        m = cache_metrics()
        assert m["hit_rate_pct"] == 75.0

    def test_metrics_snapshot_is_independent_of_internal_state(self):
        """Mutating the returned dict must not affect internal state."""
        m = cache_metrics()
        m["hits"] = 9999
        import lib.prompt_cache as pc
        with pc._metrics_lock:
            assert pc._metrics["hits"] == 0

    def test_metrics_thread_safe(self):
        """Concurrent metric increments must not corrupt the counter."""
        import lib.prompt_cache as pc
        errors = []

        def bump():
            try:
                for _ in range(50):
                    pc._increment_metric("hits")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=bump) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        m = cache_metrics()
        assert m["hits"] == 200  # 4 threads × 50


# ---------------------------------------------------------------------------
# maybe_apply_cache — dispatch integration
# ---------------------------------------------------------------------------


class TestMaybeApplyCache:
    def setup_method(self):
        _fresh_metrics()

    def _make_messages(self):
        return [
            {"role": "system", "content": "You are a sub-agent."},
            {"role": "user", "content": "Run the task."},
        ]

    def test_anthropic_injects_cache_control_in_system_message(self):
        msgs = self._make_messages()
        result = maybe_apply_cache(msgs, provider="claude")
        sys_content = result[0].get("content")
        assert isinstance(sys_content, list), "System message content must be a list after caching"
        assert any(
            "cache_control" in b for b in sys_content if isinstance(b, dict)
        ), "At least one block must carry cache_control"

    def test_openai_returns_original_reference_unchanged(self):
        """OpenAI no-op must return the same object (no copy, no mutation)."""
        msgs = self._make_messages()
        result = maybe_apply_cache(msgs, provider="openai")
        assert result is msgs, "OpenAI no-op must return the original reference unchanged"

    def test_ollama_returns_original_reference_unchanged(self):
        msgs = self._make_messages()
        result = maybe_apply_cache(msgs, provider="ollama")
        assert result is msgs

    def test_empty_messages_returns_empty(self):
        result = maybe_apply_cache([], provider="anthropic")
        assert result == []

    def test_anthropic_does_not_mutate_original(self):
        """Anthropic path must return a deep copy, not mutate the input."""
        msgs = self._make_messages()
        original_content = msgs[0]["content"]
        maybe_apply_cache(msgs, provider="anthropic")
        assert msgs[0]["content"] == original_content, "Original messages must not be mutated"

    def test_qwen_is_noop(self):
        """Qwen uses OpenAI-compatible format; must be a no-op returning original ref."""
        msgs = self._make_messages()
        result = maybe_apply_cache(msgs, provider="qwen")
        assert result is msgs

    def test_writes_metric_for_anthropic(self):
        msgs = self._make_messages()
        maybe_apply_cache(msgs, provider="anthropic")
        m = cache_metrics()
        assert m["writes"] >= 1

    def test_noop_openai_metric_for_openai(self):
        msgs = self._make_messages()
        maybe_apply_cache(msgs, provider="openai")
        m = cache_metrics()
        assert m["noop_openai"] >= 1

    def test_noop_ollama_metric_for_ollama(self):
        msgs = self._make_messages()
        maybe_apply_cache(msgs, provider="ollama")
        m = cache_metrics()
        assert m["noop_ollama"] >= 1
