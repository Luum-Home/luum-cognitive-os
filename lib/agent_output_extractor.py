"""
Agent Output Extractor — parse Claude Code agent JSONL output files.

Each line in an agent output file is a JSON object representing one event
in the conversation transcript. This module extracts the useful content
(assistant text responses) from those files.

JSONL format overview:
  - type == "user"      → user prompt or tool result
  - type == "assistant" → assistant message (text + tool_use in message.content[])
  - type == "system"    → system events (e.g. compact_boundary)

Within an assistant message, message.content is an array of blocks:
  - {"type": "text", "text": "..."}          → actual text response
  - {"type": "tool_use", "name": "...", ...} → tool invocation
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any


def _iter_lines(output_path: str):
    """Yield parsed JSON objects from a JSONL file, skipping malformed lines."""
    try:
        with open(output_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return
    except OSError:
        return


def _is_compaction_boundary(obj: dict) -> bool:
    """Return True for compact_boundary system events."""
    return obj.get("type") == "system" and obj.get("subtype") == "compact_boundary"


def _extract_text_blocks(obj: dict) -> list[str]:
    """Return all text block strings from a single assistant event."""
    if obj.get("type") != "assistant":
        return []
    content = obj.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return []
    return [
        block["text"]
        for block in content
        if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
    ]


def extract_assistant_text(output_path: str) -> str:
    """Extract all assistant text messages from an agent JSONL output file.

    Returns concatenated assistant text, most recent last.
    Compaction boundaries are noted as separators.
    Returns empty string if the file doesn't exist or has no assistant text.
    """
    if not output_path or not os.path.exists(output_path):
        return ""

    segments: list[str] = []
    after_compaction = False

    for obj in _iter_lines(output_path):
        if _is_compaction_boundary(obj):
            after_compaction = True
            continue

        texts = _extract_text_blocks(obj)
        if texts:
            if after_compaction and segments:
                segments.append("[--- compaction boundary ---]")
                after_compaction = False
            segments.extend(texts)

    return "\n\n".join(segments)


def extract_last_response(output_path: str) -> str:
    """Extract only the final assistant text message.

    Returns the last text block from the last assistant event that has text.
    Returns empty string if the file doesn't exist or has no assistant text.
    """
    if not output_path or not os.path.exists(output_path):
        return ""

    last_texts: list[str] = []

    for obj in _iter_lines(output_path):
        texts = _extract_text_blocks(obj)
        if texts:
            last_texts = texts  # keep overwriting — we want the last one

    return "\n\n".join(last_texts)


def extract_tool_results(output_path: str) -> list[dict]:
    """Extract tool call results from an agent JSONL output file.

    Returns a list of dicts with keys:
      - tool_name (str): name of the tool invoked
      - tool_id (str): tool use ID for correlating requests/results
      - success (bool | None): True/False/None if not determinable
      - summary (str): truncated content summary
    """
    if not output_path or not os.path.exists(output_path):
        return []

    results: list[dict] = []

    # First pass: collect tool_use events from assistant messages
    tool_uses: dict[str, str] = {}  # tool_id -> tool_name
    for obj in _iter_lines(output_path):
        if obj.get("type") != "assistant":
            continue
        content = obj.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tid = block.get("id", "")
                name = block.get("name", "unknown")
                if tid:
                    tool_uses[tid] = name

    # Second pass: collect tool_result blocks from user messages
    for obj in _iter_lines(output_path):
        if obj.get("type") != "user":
            continue
        content = obj.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_result":
                continue
            tool_id = block.get("tool_use_id", "")
            tool_name = tool_uses.get(tool_id, "unknown")
            is_error = block.get("is_error", False)
            raw_content = block.get("content", "")
            # content may be a string or list of blocks
            if isinstance(raw_content, list):
                text_parts = [
                    b.get("text", "") for b in raw_content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                summary_text = " ".join(text_parts)
            else:
                summary_text = str(raw_content)

            results.append({
                "tool_name": tool_name,
                "tool_id": tool_id,
                "success": not is_error,
                "summary": summary_text[:300] + ("..." if len(summary_text) > 300 else ""),
            })

    return results


def summarize_agent_output(output_path: str) -> dict[str, Any]:
    """Return a structured summary of an agent output file.

    Returns a dict with:
      - text (str): all assistant text concatenated
      - tool_calls (int): number of tool invocations
      - duration_ms (int): elapsed time from first to last event (0 if unavailable)
      - tokens (int): total output tokens across all assistant messages
    """
    if not output_path or not os.path.exists(output_path):
        return {"text": "", "tool_calls": 0, "duration_ms": 0, "tokens": 0}

    text_segments: list[str] = []
    tool_call_count = 0
    total_output_tokens = 0
    first_ts: datetime | None = None
    last_ts: datetime | None = None

    for obj in _iter_lines(output_path):
        # Parse timestamp
        ts_str = obj.get("timestamp")
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
            except ValueError:
                pass

        if obj.get("type") != "assistant":
            continue

        message = obj.get("message", {})
        content = message.get("content", [])
        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and block.get("text"):
                text_segments.append(block["text"])
            elif block.get("type") == "tool_use":
                tool_call_count += 1

        # Sum output tokens
        usage = message.get("usage", {})
        total_output_tokens += usage.get("output_tokens", 0)

    duration_ms = 0
    if first_ts and last_ts:
        duration_ms = int((last_ts - first_ts).total_seconds() * 1000)

    return {
        "text": "\n\n".join(text_segments),
        "tool_calls": tool_call_count,
        "duration_ms": duration_ms,
        "tokens": total_output_tokens,
    }
