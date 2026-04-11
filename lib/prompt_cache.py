"""Prompt caching adapter for Anthropic models.

Adapts the ``system_and_3`` caching strategy from hermes-agent (MIT) to
provide a simple API for Cognitive OS sub-agent prompt composition.

The key idea: Anthropic allows up to 4 ``cache_control: ephemeral``
breakpoints per request.  By marking stable content (system prompt, rules,
preamble) as cacheable, repeated identical prefixes are served from cache
at ~10% of the normal input token cost -- yielding ~75% cost reduction on
multi-turn conversations that share the same system prompt.

Usage::

    from lib.prompt_cache import apply_cache_to_system_prompt

    cached = apply_cache_to_system_prompt("You are a sub-agent...")
    # Returns structured content block with cache_control marker.

For full message-level caching (system + last 3 messages), use
``apply_message_cache``.
"""

import copy
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Low-level helpers (adapted from hermes-agent prompt_caching.py, MIT)
# ---------------------------------------------------------------------------


def _apply_cache_marker(
    msg: Dict[str, Any],
    cache_marker: Dict[str, str],
    native_anthropic: bool = False,
) -> None:
    """Add ``cache_control`` to a single message dict.

    Handles the three content shapes Anthropic accepts:
      - ``None`` / empty string  -> top-level marker
      - plain string             -> wrapped into ``[{"type":"text", ...}]``
      - list of content blocks   -> marker on the **last** block
    """
    role = msg.get("role", "")
    content = msg.get("content")

    if role == "tool":
        if native_anthropic:
            msg["cache_control"] = cache_marker
        return

    if content is None or content == "":
        msg["cache_control"] = cache_marker
        return

    if isinstance(content, str):
        msg["content"] = [
            {"type": "text", "text": content, "cache_control": cache_marker}
        ]
        return

    if isinstance(content, list) and content:
        last = content[-1]
        if isinstance(last, dict):
            last["cache_control"] = cache_marker


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def apply_cache_to_system_prompt(
    system_prompt: str,
    cache_ttl: str = "5m",
) -> List[Dict[str, Any]]:
    """Wrap a system prompt string in an Anthropic-cacheable content block.

    Returns a list with a single text block carrying ``cache_control``.
    This is the format expected by Anthropic's Messages API for the
    ``system`` parameter when you want to enable prompt caching.

    Args:
        system_prompt: The full system prompt text (rules + preamble + task).
        cache_ttl: Cache time-to-live.  ``"5m"`` (default) or ``"1h"``.

    Returns:
        A list of content blocks suitable for the ``system`` parameter::

            [{"type": "text", "text": "...", "cache_control": {"type": "ephemeral"}}]
    """
    marker: Dict[str, str] = {"type": "ephemeral"}
    if cache_ttl == "1h":
        marker["ttl"] = "1h"

    return [{"type": "text", "text": system_prompt, "cache_control": marker}]


def apply_message_cache(
    messages: List[Dict[str, Any]],
    cache_ttl: str = "5m",
    native_anthropic: bool = False,
) -> List[Dict[str, Any]]:
    """Apply the ``system_and_3`` caching strategy to a message list.

    Places up to 4 ``cache_control`` breakpoints:
      1. System message (if present) -- stable across turns.
      2-4. Last 3 non-system messages -- rolling window.

    Args:
        messages: List of message dicts (``{"role": ..., "content": ...}``).
        cache_ttl: ``"5m"`` (default) or ``"1h"``.
        native_anthropic: ``True`` when calling Anthropic directly (not via
            OpenRouter or LiteLLM).

    Returns:
        Deep copy of *messages* with ``cache_control`` breakpoints injected.
        The original list is never mutated.
    """
    msgs = copy.deepcopy(messages)
    if not msgs:
        return msgs

    marker: Dict[str, str] = {"type": "ephemeral"}
    if cache_ttl == "1h":
        marker["ttl"] = "1h"

    breakpoints_used = 0

    # 1. Cache the system prompt (most stable content).
    if msgs[0].get("role") == "system":
        _apply_cache_marker(msgs[0], marker, native_anthropic=native_anthropic)
        breakpoints_used += 1

    # 2-4. Cache the last 3 non-system messages.
    remaining = 4 - breakpoints_used
    non_sys = [i for i, m in enumerate(msgs) if m.get("role") != "system"]
    for idx in non_sys[-remaining:]:
        _apply_cache_marker(msgs[idx], marker, native_anthropic=native_anthropic)

    return msgs


def estimate_cache_savings(
    system_prompt_tokens: int,
    avg_turns: int = 5,
) -> Dict[str, Any]:
    """Estimate cost savings from prompt caching.

    Cached input tokens cost ~10% of uncached tokens on Anthropic.  The
    system prompt is cached on every turn after the first, so savings
    scale with conversation length.

    Args:
        system_prompt_tokens: Approximate token count of the system prompt.
        avg_turns: Average number of turns in a conversation.

    Returns:
        Dict with ``cached_tokens``, ``savings_pct``, and ``description``.
    """
    if avg_turns <= 1:
        return {
            "cached_tokens": 0,
            "savings_pct": 0,
            "description": "No savings on single-turn conversations.",
        }

    # Turns 2..N read the system prompt from cache at 10% cost.
    cached_reads = avg_turns - 1
    tokens_saved = system_prompt_tokens * cached_reads * 0.9  # 90% saving

    total_without_cache = system_prompt_tokens * avg_turns
    savings_pct = int((tokens_saved / total_without_cache) * 100) if total_without_cache else 0

    return {
        "cached_tokens": int(tokens_saved),
        "savings_pct": savings_pct,
        "description": (
            f"System prompt ({system_prompt_tokens:,} tokens) cached across "
            f"{cached_reads} turns. ~{savings_pct}% input cost reduction."
        ),
    }


# ---------------------------------------------------------------------------
# PromptCacheManager — high-level class for ClaudeExecutor integration
# ---------------------------------------------------------------------------

# Sonnet pricing (per 1M tokens)
_INPUT_PRICE_PER_M = 3.00
_CACHE_WRITE_PRICE_PER_M = 3.75   # 1.25× input
_CACHE_READ_PRICE_PER_M = 0.30    # 0.10× input
_CHARS_PER_TOKEN = 4
_TASK_MARKER = "## Task"


class PromptCacheManager:
    """Manages prompt cache breakpoints for the Anthropic API.

    A helper intended for use with ClaudeExecutor when
    ORCHESTRATOR_MODE=executor.  Marks stable sections (preamble, rules,
    project context) with ``cache_control: {type: ephemeral}`` so that
    repeated sub-agent launches read from the cache at 0.10× input cost.
    """

    CACHEABLE_SECTIONS = [
        "system_prompt",
        "rules_context",
        "project_context",
    ]

    def add_cache_breakpoints(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add ``cache_control`` to the first stable system/user message.

        Strategy:
        - First message with role ``"system"`` or the first ``"user"``
          message whose content contains preamble text → marked cacheable.
        - All other messages → untouched.

        Returns a new list; original dicts are not mutated.
        """
        if not messages:
            return []

        result: List[Dict[str, Any]] = []
        marked = False

        for msg in messages:
            role = msg.get("role", "")
            if not marked and role in ("system", "user"):
                msg = dict(msg)
                content = msg.get("content", "")
                if isinstance(content, str):
                    cacheable, _ = self._split_at_marker(content)
                    if cacheable:
                        msg["cache_control"] = {"type": "ephemeral"}
                        marked = True
                elif isinstance(content, list):
                    new_blocks: List[Any] = []
                    for block in content:
                        if (
                            not marked
                            and isinstance(block, dict)
                            and block.get("type") == "text"
                        ):
                            block = dict(block)
                            block["cache_control"] = {"type": "ephemeral"}
                            marked = True
                        new_blocks.append(block)
                    msg["content"] = new_blocks
            result.append(msg)

        return result

    def estimate_cache_savings(
        self,
        cached_tokens: int,
        total_invocations: int,
    ) -> Dict[str, float]:
        """Estimate USD cost savings from caching across *total_invocations*.

        First invocation pays the cache-write premium (1.25×).
        Subsequent invocations pay the cache-read discount (0.10×).

        Returns:
            without_cache_usd, with_cache_usd, savings_pct,
            cache_write_cost, cache_read_cost
        """
        if total_invocations < 1:
            total_invocations = 1

        without_cache = (
            (cached_tokens / 1_000_000) * _INPUT_PRICE_PER_M * total_invocations
        )
        write_cost = (cached_tokens / 1_000_000) * _CACHE_WRITE_PRICE_PER_M
        reads = max(0, total_invocations - 1)
        read_cost = (cached_tokens / 1_000_000) * _CACHE_READ_PRICE_PER_M * reads
        with_cache = write_cost + read_cost
        savings_pct = (
            (without_cache - with_cache) / without_cache * 100 if without_cache else 0.0
        )

        return {
            "without_cache_usd": round(without_cache, 6),
            "with_cache_usd": round(with_cache, 6),
            "savings_pct": round(savings_pct, 1),
            "cache_write_cost": round(write_cost, 6),
            "cache_read_cost": round(read_cost, 6),
        }

    def split_prompt_sections(self, full_prompt: str) -> Dict[str, Any]:
        """Split a full agent prompt at the ``## Task`` marker.

        Returns:
            cacheable        – text before the task marker
            non_cacheable    – ``## Task`` section and everything after
            cacheable_tokens – rough token count of the cacheable section
        """
        cacheable, non_cacheable = self._split_at_marker(full_prompt)
        token_estimate = max(1, len(cacheable) // _CHARS_PER_TOKEN)
        return {
            "cacheable": cacheable,
            "non_cacheable": non_cacheable,
            "cacheable_tokens": token_estimate,
        }

    def format_cache_report(self, invocations: int, cached_tokens: int) -> str:
        """One-line cache savings report for session summaries."""
        est = self.estimate_cache_savings(cached_tokens, invocations)
        saved = est["without_cache_usd"] - est["with_cache_usd"]
        return (
            "Cache: {inv} invocations × {tok} tokens → "
            "{pct:.0f}% saved (${saved:.4f} of ${total:.4f})".format(
                inv=invocations,
                tok=cached_tokens,
                pct=est["savings_pct"],
                saved=saved,
                total=est["without_cache_usd"],
            )
        )

    @staticmethod
    def _split_at_marker(text: str) -> "tuple[str, str]":
        idx = text.find(_TASK_MARKER)
        if idx == -1:
            return text, ""
        return text[:idx], text[idx:]
