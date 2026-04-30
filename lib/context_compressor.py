"""Portable multi-turn context compression for harness-agnostic COS use (ADR-080 Tier 1 #3).

Ported from Hermes (.claude/plugins/hermes-agent/agent/context_compressor.py),
MIT-licensed. Attribution: the Hermes project. See .cognitive-os/adoption-registry.yaml.

Design decisions made during port (2026-04-30, Session A):
- Provider coupling: Hermes uses its own ``call_llm`` (OpenAI-compatible).
  This port routes through COS's lib/dispatch.py (qwen→claude cascade, ADR-049).
  If dispatch is unavailable the compressor degrades gracefully — it returns
  uncompressed messages with a warning and never crashes.
- Token counting: Hermes uses tiktoken. This port uses the same ``chars/4`` rough
  estimate that Hermes falls back to in its provider-agnostic paths.
- Sensitive redaction: Hermes calls ``redact_sensitive_text`` from a Hermes-internal
  module. This port applies a minimal inline regex redactor; a future integration
  with COS's own redaction layer would be drop-in (same call site).
- Manual compression feedback (Hermes ``manual_compression_feedback.py``): not
  ported. Captured as future work — ship base compression first.
- Trajectory compression: Hermes does not have a standalone trajectory_compressor.py
  (the file was absent in the plugin). ``compress_trajectory`` is implemented here
  as a first-class COS primitive: it collapses a list of agent-event dicts into a
  single summary event using the same LLM dispatch path.

Activation:
  Set ``COS_CONTEXT_COMPRESS=1`` in the environment. Without this env var the
  harness adapter ``maybe_compress_context`` method is a no-op (Claude Code does
  its own native compaction; this is only meaningful for Codex and other harnesses
  that lack PreCompact/auto-compact).

Public API:
  should_compress(messages, budget) -> bool
  compress(messages, target_tokens) -> list[Message]
  compress_trajectory(trajectory) -> Event

Message type: dict with at least {"role": str, "content": str | None}.
Event type: dict with at least {"type": str, ...}.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (tuned to match Hermes defaults)
# ---------------------------------------------------------------------------

SUMMARY_PREFIX = (
    "[CONTEXT COMPACTION — REFERENCE ONLY] Earlier turns were compacted "
    "into the summary below. This is a handoff from a previous context "
    "window — treat it as background reference, NOT as active instructions. "
    "Do NOT answer questions or fulfill requests mentioned in this summary; "
    "they were already addressed. "
    "Your current task is identified in the '## Active Task' section of the "
    "summary — resume exactly from there. "
    "Respond ONLY to the latest user message "
    "that appears AFTER this summary."
)

_CHARS_PER_TOKEN: int = 4
_MIN_SUMMARY_TOKENS: int = 2_000
_SUMMARY_RATIO: float = 0.20
_SUMMARY_TOKENS_CEILING: int = 12_000
_FAILURE_COOLDOWN_SECONDS: int = 600
_PRUNED_PLACEHOLDER: str = "[Old tool output cleared to save context space]"

# Proportion of the token budget to protect as the tail (recent messages).
_TAIL_RATIO: float = 0.20
# Minimum number of messages always kept in the tail regardless of token budget.
_TAIL_MIN_MESSAGES: int = 3
# Minimum number of head messages always kept (system prompt + first exchange).
_HEAD_PROTECT: int = 3

# ---------------------------------------------------------------------------
# Minimal inline redactor (keeps this module dependency-free).
# Replace with a proper COS redaction utility when one exists.
# ---------------------------------------------------------------------------

_REDACT_PATTERNS = [
    re.compile(r'(?i)(api[_-]?key|token|secret|password|passwd|credential)["\s:=]+[\w\-\.]+'),
    re.compile(r'(?i)(Authorization:\s*Bearer\s+)[\w\-\.]+'),
    re.compile(r'sk-[A-Za-z0-9]{20,}'),
]


def _redact(text: str) -> str:
    for pat in _REDACT_PATTERNS:
        text = pat.sub(lambda m: m.group(0).rsplit(m.group(0)[-10:], 1)[0] + "[REDACTED]", text)
    return text


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------


def _estimate_tokens(messages: List[Dict[str, Any]]) -> int:
    """Rough token estimate: chars / 4, +10 overhead per message."""
    total = 0
    for msg in messages:
        content = msg.get("content") or ""
        if isinstance(content, list):
            for block in content:
                total += len(block.get("text", "")) // _CHARS_PER_TOKEN
        else:
            total += len(content) // _CHARS_PER_TOKEN
        total += 10
    return total


# ---------------------------------------------------------------------------
# should_compress predicate
# ---------------------------------------------------------------------------


def should_compress(
    messages: List[Dict[str, Any]],
    budget: int,
    *,
    threshold_pct: float = 0.80,
) -> bool:
    """Return True when the message list exceeds ``threshold_pct`` of ``budget``.

    Args:
        messages: conversation message list.
        budget: full context window in tokens (e.g. 200_000 for claude-sonnet).
        threshold_pct: compress when usage exceeds this fraction of budget.
            Default 0.80 matches the ``COS_CONTEXT_COMPRESS`` activation intent
            (compress when < 20% remaining).

    Returns False immediately if ``COS_CONTEXT_COMPRESS`` is not set, so this
    is always safe to call — it becomes a no-op in Claude Code or other harnesses
    that manage compaction natively.
    """
    if os.environ.get("COS_CONTEXT_COMPRESS", "").strip() != "1":
        return False
    current_tokens = _estimate_tokens(messages)
    threshold = int(budget * threshold_pct)
    return current_tokens >= threshold


# ---------------------------------------------------------------------------
# Tool result pruning (cheap pre-pass, no LLM call)
# ---------------------------------------------------------------------------


def _prune_tool_results(
    messages: List[Dict[str, Any]],
    tail_count: int = _TAIL_MIN_MESSAGES,
) -> Tuple[List[Dict[str, Any]], int]:
    """Replace old tool results outside the protected tail with 1-line summaries.

    Mirrors Hermes ``_prune_old_tool_results`` but simplified for the COS port:
    uses a fixed tail count (no token-budget boundary) and a generic summary line.
    Deduplicates identical tool results (same MD5 → keep newest, prune older).

    Returns (pruned_messages, prune_count).
    """
    if not messages:
        return messages, 0

    result = [m.copy() for m in messages]
    prune_boundary = max(0, len(result) - tail_count)
    pruned = 0

    # Deduplicate identical tool results (keep newest).
    seen_hashes: Dict[str, int] = {}  # hash -> most-recent index
    for i in range(len(result) - 1, -1, -1):
        msg = result[i]
        if msg.get("role") != "tool":
            continue
        content = msg.get("content") or ""
        if isinstance(content, list) or len(content) < 200:
            continue
        h = hashlib.md5(content.encode("utf-8", errors="replace")).hexdigest()[:12]
        if h in seen_hashes:
            result[i] = {**msg, "content": "[Duplicate tool output — see more recent call]"}
            pruned += 1
        else:
            seen_hashes[h] = i

    # Replace substantial old tool results with a 1-line summary.
    for i in range(prune_boundary):
        msg = result[i]
        if msg.get("role") != "tool":
            continue
        content = msg.get("content", "")
        if isinstance(content, list):
            continue
        if not content or content == _PRUNED_PLACEHOLDER:
            continue
        if content.startswith("[Duplicate") or content.startswith("[Old tool"):
            continue
        if len(content) > 200:
            cid = msg.get("tool_call_id", "")
            result[i] = {**msg, "content": f"[tool:{cid}] output pruned ({len(content):,} chars)"}
            pruned += 1

    return result, pruned


# ---------------------------------------------------------------------------
# LLM dispatch (goes through COS cascade, not direct provider)
# ---------------------------------------------------------------------------


def _dispatch_summarize(prompt: str) -> Optional[str]:
    """Call the COS LLM dispatch cascade (qwen→claude per ADR-049).

    Returns the summary text or None if dispatch is unavailable or fails.
    Never raises — callers must handle None gracefully.
    """
    try:
        from lib.dispatch import dispatch as cos_dispatch
    except ImportError:
        logger.warning(
            "context_compressor: lib.dispatch not importable — "
            "returning uncompressed (dispatch unavailable)"
        )
        return None

    try:
        result = cos_dispatch(
            prompt=prompt,
            providers=["qwen", "claude"],
            task_type="compression",
        )
        if result.success and result.text:
            return result.text.strip()
        logger.warning(
            "context_compressor: dispatch returned success=%s, provider=%s, error=%s",
            result.success,
            result.provider_used,
            result.error[:200] if result.error else "",
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("context_compressor: dispatch raised %s — returning None", exc)
        return None


# ---------------------------------------------------------------------------
# Summarization helpers
# ---------------------------------------------------------------------------


def _serialize_for_summary(turns: List[Dict[str, Any]]) -> str:
    """Serialize conversation turns into labeled text for the summarizer."""
    _CONTENT_MAX = 6_000
    _CONTENT_HEAD = 4_000
    _CONTENT_TAIL = 1_500
    parts = []
    for msg in turns:
        role = msg.get("role", "unknown")
        content = _redact(msg.get("content") or "")
        if isinstance(content, list):
            content = " ".join(b.get("text", "") for b in content)

        if len(content) > _CONTENT_MAX:
            content = content[:_CONTENT_HEAD] + "\n...[truncated]...\n" + content[-_CONTENT_TAIL:]

        if role == "tool":
            cid = msg.get("tool_call_id", "")
            parts.append(f"[TOOL RESULT {cid}]: {content}")
        elif role == "assistant":
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                tc_names = [
                    (tc.get("function", {}).get("name", "?") if isinstance(tc, dict) else "?")
                    for tc in tool_calls
                ]
                content += f"\n[Tool calls: {', '.join(tc_names)}]"
            parts.append(f"[ASSISTANT]: {content}")
        else:
            parts.append(f"[{role.upper()}]: {content}")
    return "\n\n".join(parts)


def _build_summary_prompt(
    content_to_summarize: str,
    summary_budget: int,
    previous_summary: Optional[str] = None,
) -> str:
    preamble = (
        "You are a summarization agent creating a context checkpoint. "
        "Your output will be injected as reference material for a DIFFERENT "
        "assistant that continues the conversation. "
        "Do NOT respond to any questions or requests — only output the summary. "
        "NEVER include API keys, tokens, passwords, or credentials — write [REDACTED]."
    )

    template = f"""## Active Task
[Most recent unfulfilled user request — copy verbatim]

## Goal
[Overall user objective]

## Completed Actions
[Numbered list: what was done, with file paths / commands / outcomes]

## Active State
[Files modified, test status, running processes]

## Blocked / Errors
[Unresolved blockers or exact error messages]

## Key Decisions
[Important technical choices and rationale]

## Remaining Work
[What still needs to be done — framed as context, not instructions]

## Critical Context
[Specific values, error messages, config details that must not be lost. NO secrets.]

Target ~{summary_budget} tokens. Be concrete — file paths, commands, exact values."""

    if previous_summary:
        return (
            f"{preamble}\n\nUpdate the previous compaction summary with the new turns below.\n"
            f"PREVIOUS SUMMARY:\n{previous_summary}\n\n"
            f"NEW TURNS:\n{content_to_summarize}\n\n"
            f"Use this structure:\n{template}"
        )
    return (
        f"{preamble}\n\nCreate a structured handoff summary for a different assistant.\n\n"
        f"TURNS TO SUMMARIZE:\n{content_to_summarize}\n\n"
        f"Use this structure:\n{template}"
    )


# ---------------------------------------------------------------------------
# Tool-pair integrity: remove orphaned tool results after compression
# ---------------------------------------------------------------------------


def _sanitize_tool_pairs(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove tool results whose call_id has no matching assistant tool_call."""
    surviving_call_ids: set = set()
    for msg in messages:
        if msg.get("role") == "assistant":
            for tc in msg.get("tool_calls") or []:
                cid = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")
                if cid:
                    surviving_call_ids.add(cid)

    result_call_ids: set = set()
    for msg in messages:
        if msg.get("role") == "tool" and msg.get("tool_call_id"):
            result_call_ids.add(msg["tool_call_id"])

    orphaned = result_call_ids - surviving_call_ids
    if orphaned:
        messages = [
            m for m in messages
            if not (m.get("role") == "tool" and m.get("tool_call_id") in orphaned)
        ]
        logger.debug("context_compressor: removed %d orphaned tool result(s)", len(orphaned))

    # Add stub results for orphaned calls
    missing = surviving_call_ids - result_call_ids
    if missing:
        patched: List[Dict[str, Any]] = []
        for msg in messages:
            patched.append(msg)
            if msg.get("role") == "assistant":
                for tc in msg.get("tool_calls") or []:
                    cid = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")
                    if cid in missing:
                        patched.append({
                            "role": "tool",
                            "content": "[Result from earlier conversation — see context summary]",
                            "tool_call_id": cid,
                        })
        messages = patched
        logger.debug("context_compressor: added %d stub tool result(s)", len(missing))

    return messages


# ---------------------------------------------------------------------------
# Main compress entry point
# ---------------------------------------------------------------------------


def compress(
    messages: List[Dict[str, Any]],
    target_tokens: int,
    *,
    protect_head: int = _HEAD_PROTECT,
    protect_tail_ratio: float = _TAIL_RATIO,
    previous_summary: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Compress conversation messages by summarizing the middle turns.

    Recency bias: the tail (most recent ``protect_tail_ratio`` of ``target_tokens``)
    is always preserved verbatim. Head messages (system prompt + first exchange)
    are also protected. Middle turns are summarized via LLM dispatch.

    If dispatch is unavailable the original messages are returned unmodified with
    a warning logged — no crash, no data loss.

    Args:
        messages: full message list.
        target_tokens: token budget for the compressed result.
        protect_head: number of head messages always kept verbatim.
        protect_tail_ratio: fraction of target_tokens to protect as the tail.
        previous_summary: prior summary for iterative update (second+ compaction).

    Returns:
        (compressed_messages, new_summary_text)
        new_summary_text is None if dispatch failed (messages returned uncompressed).
    """
    n = len(messages)
    min_compress = protect_head + _TAIL_MIN_MESSAGES + 1
    if n <= min_compress:
        logger.debug("context_compressor: too few messages (%d) to compress", n)
        return messages, previous_summary

    # Phase 1: cheap prune pass
    tail_count = max(_TAIL_MIN_MESSAGES, int(n * protect_tail_ratio))
    messages, pruned = _prune_tool_results(messages, tail_count=tail_count)
    if pruned:
        logger.info("context_compressor: pruned %d tool result(s)", pruned)

    # Phase 2: boundaries
    compress_start = protect_head
    # Slide forward past orphaned tool results at the head boundary
    while compress_start < n and messages[compress_start].get("role") == "tool":
        compress_start += 1

    tail_token_budget = int(target_tokens * protect_tail_ratio)
    compress_end = _find_tail_boundary(messages, compress_start, tail_token_budget)

    if compress_start >= compress_end:
        logger.debug("context_compressor: nothing to compress after boundary resolution")
        return messages, previous_summary

    turns_to_summarize = messages[compress_start:compress_end]

    # Phase 3: summarize
    content_tokens = _estimate_tokens(turns_to_summarize)
    summary_budget = max(
        _MIN_SUMMARY_TOKENS,
        min(int(content_tokens * _SUMMARY_RATIO), _SUMMARY_TOKENS_CEILING),
    )
    serialized = _serialize_for_summary(turns_to_summarize)
    prompt = _build_summary_prompt(serialized, summary_budget, previous_summary)

    summary_text = _dispatch_summarize(prompt)

    if summary_text is None:
        logger.warning(
            "context_compressor: dispatch unavailable — returning uncompressed messages"
        )
        return messages, previous_summary

    # Apply SUMMARY_PREFIX framing
    summary_message = f"{SUMMARY_PREFIX}\n{summary_text}"

    # Phase 4: assemble result
    compressed: List[Dict[str, Any]] = []
    for i in range(compress_start):
        msg = messages[i].copy()
        if i == 0 and msg.get("role") == "system":
            note = "[Note: Earlier conversation turns have been compacted into a summary below.]"
            existing = msg.get("content") or ""
            if note not in existing:
                msg["content"] = existing + "\n\n" + note
        compressed.append(msg)

    # Choose summary role to avoid role-alternation issues
    last_head_role = messages[compress_start - 1].get("role", "user") if compress_start > 0 else "user"
    first_tail_role = messages[compress_end].get("role", "user") if compress_end < n else "user"
    if last_head_role in ("assistant", "tool"):
        summary_role = "user"
    else:
        summary_role = "assistant"
    if summary_role == first_tail_role:
        flipped = "assistant" if summary_role == "user" else "user"
        if flipped != last_head_role:
            summary_role = flipped

    compressed.append({"role": summary_role, "content": summary_message})

    for i in range(compress_end, n):
        compressed.append(messages[i].copy())

    compressed = _sanitize_tool_pairs(compressed)

    before_tokens = _estimate_tokens(messages)
    after_tokens = _estimate_tokens(compressed)
    savings = before_tokens - after_tokens
    logger.info(
        "context_compressor: %d → %d messages (~%d tokens saved, %.0f%%)",
        n, len(compressed), savings,
        (savings / before_tokens * 100) if before_tokens else 0,
    )

    return compressed, summary_text


def _find_tail_boundary(
    messages: List[Dict[str, Any]],
    head_end: int,
    tail_token_budget: int,
) -> int:
    """Walk backward from end accumulating tokens until budget is reached.

    Returns the index where the protected tail starts.
    Ensures the result is always > head_end.
    """
    n = len(messages)
    accumulated = 0
    cut_idx = n

    for i in range(n - 1, head_end - 1, -1):
        msg = messages[i]
        content = msg.get("content") or ""
        tokens = len(content) // _CHARS_PER_TOKEN + 10
        if accumulated + tokens > tail_token_budget and (n - i) >= _TAIL_MIN_MESSAGES:
            break
        accumulated += tokens
        cut_idx = i

    return max(cut_idx, head_end + 1)


# ---------------------------------------------------------------------------
# compress_trajectory
# ---------------------------------------------------------------------------


def compress_trajectory(
    trajectory: List[Dict[str, Any]],
    *,
    label: str = "trajectory_summary",
) -> Dict[str, Any]:
    """Summarize a list of agent-event dicts into a single summary event.

    Trajectory events are COS canonical events (AgentStart, ToolUse, AgentEnd, …)
    serialized as dicts. The compressed result is a single dict with:
        {"type": label, "summary": <text>, "event_count": <n>, "ts": <epoch>}

    If dispatch is unavailable returns a minimal summary without LLM text.

    Args:
        trajectory: list of canonical event dicts.
        label: event_type string for the returned summary event.

    Returns:
        dict representing the compacted trajectory event.
    """
    n = len(trajectory)
    if n == 0:
        return {"type": label, "summary": "Empty trajectory.", "event_count": 0, "ts": time.time()}

    serialized = json.dumps(trajectory, indent=None, default=str)
    if len(serialized) > 8_000:
        serialized = serialized[:8_000] + "...[truncated]"

    prompt = (
        "You are summarizing an AI agent execution trajectory for a context handoff. "
        "Produce a concise (≤300 word) plain-text summary covering: what the agent did, "
        "key tool calls and their outcomes, final status, and any errors. "
        "Do not include credentials or secrets.\n\n"
        f"TRAJECTORY ({n} events):\n{serialized}"
    )

    summary_text = _dispatch_summarize(prompt)
    if summary_text is None:
        summary_text = (
            f"Trajectory contained {n} events. "
            "LLM summarization was unavailable — inspect raw events for details."
        )
        logger.warning("context_compressor: trajectory dispatch failed — using fallback summary")

    return {
        "type": label,
        "summary": summary_text,
        "event_count": n,
        "ts": time.time(),
    }
