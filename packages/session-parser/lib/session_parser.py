# SCOPE: both
# scope: both
"""Session Parser -- reads Claude Code JSONL session files for real metrics.

Extracts token counts, tool usage timings, subagent activity, and model
information from Claude Code's native session storage.

Inspired by claude-esp (phiat/claude-esp) session parsing approach.

Usage:
    from lib.session_parser import parse_session, list_sessions, get_session_metrics

    sessions = list_sessions()  # All recent sessions
    metrics = get_session_metrics(session_id)  # Detailed metrics for one session
    events = parse_session(session_path)  # Raw parsed events
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def get_sessions_dir() -> Path:
    """Return the Claude Code projects directory (~/.claude/projects/)."""
    return Path.home() / ".claude" / "projects"


def list_sessions(
    project_filter: str | None = None,
    since_hours: float | None = None,
) -> list[dict]:
    """Scan all session JSONL files and return metadata.

    Args:
        project_filter: Only include sessions whose path contains this string.
        since_hours: Only include sessions modified within the last N hours.

    Returns:
        List of dicts with: session_id, path, project, last_modified, size_bytes.
    """
    projects_dir = get_sessions_dir()
    if not projects_dir.exists():
        logger.info("Claude projects dir not found: %s", projects_dir)
        return []

    cutoff = None
    if since_hours is not None:
        cutoff = time.time() - (since_hours * 3600)

    sessions: list[dict] = []
    for jsonl_file in projects_dir.rglob("*.jsonl"):
        # Skip subagent files
        if jsonl_file.name.startswith("agent-"):
            continue
        # Skip files inside subagents directories
        if "subagents" in jsonl_file.parts:
            continue

        if project_filter and project_filter not in str(jsonl_file):
            continue

        try:
            stat = jsonl_file.stat()
        except OSError:
            continue

        if cutoff and stat.st_mtime < cutoff:
            continue

        # Extract session ID from filename (UUID.jsonl)
        session_id = jsonl_file.stem

        # Derive project from parent directory name
        project_dir_name = jsonl_file.parent.name

        sessions.append({
            "session_id": session_id,
            "path": jsonl_file,
            "project": project_dir_name,
            "last_modified": datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat(),
            "size_bytes": stat.st_size,
        })

    # Sort by last_modified descending (most recent first)
    sessions.sort(key=lambda s: s["last_modified"], reverse=True)
    return sessions


def parse_session(path: Path) -> list[dict]:
    """Parse a Claude Code JSONL session file into structured events.

    Reads line by line, extracting user messages, assistant messages (with
    token usage), tool_use, tool_result, thinking blocks, and agent progress.
    Skips queue-operation entries and malformed lines.

    Args:
        path: Path to the .jsonl session file.

    Returns:
        List of event dicts, each with at minimum: type, timestamp.
    """
    events: list[dict] = []
    try:
        with open(path) as f:
            for line_num, raw_line in enumerate(f, start=1):
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError:
                    logger.debug("Skipping malformed JSON at %s:%d", path, line_num)
                    continue

                entry_type = entry.get("type", "")
                timestamp = entry.get("timestamp", "")

                # Skip queue operations and other meta entries
                if entry_type == "queue-operation":
                    continue

                if entry_type in ("user", "assistant"):
                    _parse_message_entry(entry, entry_type, timestamp, events)
                elif entry_type == "progress":
                    _parse_progress_entry(entry, timestamp, events)

    except (OSError, IOError) as exc:
        logger.warning("Failed to read session file %s: %s", path, exc)

    return events


def _parse_message_entry(
    entry: dict,
    entry_type: str,
    timestamp: str,
    events: list[dict],
) -> None:
    """Extract message events (user/assistant) from a JSONL entry."""
    message = entry.get("message", {})
    if not isinstance(message, dict):
        return

    role = message.get("role", entry_type)
    model = message.get("model", "")
    usage = message.get("usage", {})
    content = message.get("content", "")

    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_creation = usage.get("cache_creation_input_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)

    # Parse content blocks for tool_use, tool_result, thinking
    content_types: list[str] = []
    tool_uses: list[dict] = []
    tool_results: list[dict] = []
    has_thinking = False
    content_summary = ""

    if isinstance(content, str):
        content_types = ["text"]
        content_summary = content[:200]
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type", "")
            content_types.append(block_type)

            if block_type == "tool_use":
                tool_uses.append({
                    "type": "tool_use",
                    "timestamp": timestamp,
                    "name": block.get("name", ""),
                    "tool_use_id": block.get("id", ""),
                    "input_summary": _summarize_tool_input(block.get("input", {})),
                })
            elif block_type == "tool_result":
                tool_results.append({
                    "type": "tool_result",
                    "timestamp": timestamp,
                    "tool_use_id": block.get("tool_use_id", ""),
                    "is_error": block.get("is_error", False),
                })
            elif block_type == "thinking":
                has_thinking = True
            elif block_type == "text":
                text = block.get("text", "")
                if not content_summary:
                    content_summary = text[:200]

    event: dict[str, Any] = {
        "type": "message",
        "timestamp": timestamp,
        "role": role,
        "content_types": content_types,
        "content_summary": content_summary,
    }

    if model:
        event["model"] = model
    if input_tokens:
        event["input_tokens"] = input_tokens
    if output_tokens:
        event["output_tokens"] = output_tokens
    if cache_creation:
        event["cache_creation_tokens"] = cache_creation
    if cache_read:
        event["cache_read_tokens"] = cache_read
    if has_thinking:
        event["has_thinking"] = True

    events.append(event)

    # Add tool_use and tool_result as separate events for easier analysis
    events.extend(tool_uses)
    events.extend(tool_results)


def _parse_progress_entry(
    entry: dict,
    timestamp: str,
    events: list[dict],
) -> None:
    """Extract progress events (hooks, agent activity) from a JSONL entry."""
    data = entry.get("data", {})
    if not isinstance(data, dict):
        return

    data_type = data.get("type", "")

    if data_type == "agent_progress":
        events.append({
            "type": "agent_progress",
            "timestamp": timestamp,
            "agent_id": data.get("agentId", ""),
            "message": data.get("message", ""),
        })
    elif data_type == "hook_progress":
        events.append({
            "type": "hook_progress",
            "timestamp": timestamp,
            "hook_name": data.get("hookName", ""),
            "hook_event": data.get("hookEvent", ""),
        })


def _summarize_tool_input(tool_input: Any) -> str:
    """Create a short summary of tool input for logging."""
    if isinstance(tool_input, dict):
        # Common patterns
        if "file_path" in tool_input:
            return f"file: {tool_input['file_path']}"
        if "command" in tool_input:
            cmd = tool_input["command"]
            return f"cmd: {cmd[:100]}" if isinstance(cmd, str) else "cmd: ..."
        if "pattern" in tool_input:
            return f"pattern: {tool_input['pattern']}"
        if "query" in tool_input:
            return f"query: {tool_input['query'][:80]}"
        # Fallback: show keys
        return f"keys: {','.join(sorted(tool_input.keys())[:5])}"
    if isinstance(tool_input, str):
        return tool_input[:100]
    return ""


def discover_subagents(session_dir: Path) -> list[dict]:
    """Discover subagent JSONL files in a session directory.

    Looks for files matching ``subagents/agent-*.jsonl`` and reads
    companion ``.meta.json`` files for agent metadata.

    Args:
        session_dir: Path to the session directory (not the .jsonl file).
                     For a session ``abc123.jsonl``, this is the ``abc123/``
                     directory that sits alongside it.

    Returns:
        List of dicts with: agent_id, path, type, label, message_count.
    """
    subagents_dir = session_dir / "subagents"
    if not subagents_dir.is_dir():
        return []

    agents: list[dict] = []
    for agent_file in sorted(subagents_dir.glob("agent-*.jsonl")):
        # Extract agent ID from filename: agent-<id>.jsonl
        agent_id = agent_file.stem.replace("agent-", "", 1)

        # Count messages
        message_count = 0
        try:
            with open(agent_file) as f:
                for line in f:
                    if line.strip():
                        message_count += 1
        except (OSError, IOError):
            pass

        # Read meta.json if present
        meta_file = agent_file.with_suffix(".meta.json")
        agent_type = ""
        label = ""
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                agent_type = meta.get("agentType", meta.get("type", ""))
                label = meta.get("description", meta.get("label", ""))
            except (json.JSONDecodeError, OSError):
                pass

        agents.append({
            "agent_id": agent_id,
            "path": agent_file,
            "type": agent_type,
            "label": label,
            "message_count": message_count,
        })

    return agents


def get_session_metrics(session_id_or_path: str | Path) -> dict:
    """Calculate aggregate metrics for a session.

    Accepts either a session ID (will search for the file) or a direct
    path to the ``.jsonl`` file.

    Returns:
        Dict with: total_input_tokens, total_output_tokens,
        cache_creation_tokens, cache_read_tokens, tool_uses (list),
        tool_use_count, models_used, subagent_count, duration_minutes,
        message_count, thinking_count, session_id.
    """
    path = _resolve_session_path(session_id_or_path)
    if path is None:
        return _empty_metrics()

    events = parse_session(path)
    if not events:
        return _empty_metrics()

    total_input = 0
    total_output = 0
    total_cache_creation = 0
    total_cache_read = 0
    models: set[str] = set()
    message_count = 0
    thinking_count = 0
    tool_counter: dict[str, int] = {}
    agent_ids: set[str] = set()
    timestamps: list[str] = []

    for event in events:
        ts = event.get("timestamp", "")
        if ts:
            timestamps.append(ts)

        etype = event.get("type", "")

        if etype == "message":
            message_count += 1
            total_input += event.get("input_tokens", 0)
            total_output += event.get("output_tokens", 0)
            total_cache_creation += event.get("cache_creation_tokens", 0)
            total_cache_read += event.get("cache_read_tokens", 0)
            if event.get("model"):
                models.add(event["model"])
            if event.get("has_thinking"):
                thinking_count += 1

        elif etype == "tool_use":
            name = event.get("name", "unknown")
            tool_counter[name] = tool_counter.get(name, 0) + 1

        elif etype == "agent_progress":
            aid = event.get("agent_id", "")
            if aid:
                agent_ids.add(aid)

    # Calculate duration using actual earliest and latest timestamps
    duration_minutes = 0.0
    if len(timestamps) >= 2:
        try:
            def _parse_ts(ts: str):
                # Python <3.11 fromisoformat does not accept 'Z' suffix
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))

            parsed_ts = sorted(
                _parse_ts(ts) for ts in timestamps if ts
            )
            if len(parsed_ts) >= 2:
                duration_minutes = round(
                    (parsed_ts[-1] - parsed_ts[0]).total_seconds() / 60.0, 1
                )
        except (ValueError, TypeError):
            pass

    # Also discover subagents from the session directory
    subagent_count = len(agent_ids)
    session_dir = path.with_suffix("")
    if session_dir.is_dir():
        discovered = discover_subagents(session_dir)
        # Merge: use the larger count
        subagent_count = max(subagent_count, len(discovered))

    # Build tool_uses summary
    tool_uses = [
        {"tool": name, "count": count}
        for name, count in sorted(tool_counter.items(), key=lambda x: -x[1])
    ]

    session_id = path.stem

    return {
        "session_id": session_id,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "cache_creation_tokens": total_cache_creation,
        "cache_read_tokens": total_cache_read,
        "tool_uses": tool_uses,
        "tool_use_count": sum(tool_counter.values()),
        "models_used": sorted(models),
        "subagent_count": subagent_count,
        "duration_minutes": duration_minutes,
        "message_count": message_count,
        "thinking_count": thinking_count,
    }


def format_session_report(metrics: dict) -> str:
    """Format session metrics into a human-readable report.

    Args:
        metrics: Dict returned by get_session_metrics.

    Returns:
        Multi-line string report.
    """
    total_tokens = metrics["total_input_tokens"] + metrics["total_output_tokens"]
    lines = [
        "SESSION METRICS REPORT",
        f"  Session:          {metrics.get('session_id', 'unknown')}",
        f"  Duration:         {metrics['duration_minutes']} minutes",
        f"  Messages:         {metrics['message_count']}",
        "",
        "TOKENS",
        f"  Input tokens:     {metrics['total_input_tokens']:,}",
        f"  Output tokens:    {metrics['total_output_tokens']:,}",
        f"  Total tokens:     {total_tokens:,}",
        f"  Cache creation:   {metrics['cache_creation_tokens']:,}",
        f"  Cache read:       {metrics['cache_read_tokens']:,}",
        "",
        "TOOL USAGE",
        f"  Total tool uses:  {metrics['tool_use_count']}",
    ]
    for tool_info in metrics["tool_uses"][:10]:
        lines.append(f"    {tool_info['tool']}: {tool_info['count']}")

    lines.extend([
        "",
        "MODELS",
        f"  Models used:      {', '.join(metrics['models_used']) or 'none detected'}",
        "",
        "AGENTS",
        f"  Subagents:        {metrics['subagent_count']}",
        f"  Thinking blocks:  {metrics['thinking_count']}",
    ])

    return "\n".join(lines)


def _resolve_session_path(session_id_or_path: str | Path) -> Path | None:
    """Resolve a session ID or path to a concrete .jsonl file path."""
    p = Path(session_id_or_path)
    if p.is_file():
        return p

    # Try as a session ID: search in projects dir
    projects_dir = get_sessions_dir()
    if not projects_dir.exists():
        return None

    # Search for matching JSONL file by name
    session_name = f"{session_id_or_path}.jsonl"
    for match in projects_dir.rglob("*.jsonl"):
        if match.name == session_name and "subagents" not in match.parts:
            return match

    return None


def _empty_metrics() -> dict:
    """Return an empty metrics dict with all expected keys."""
    return {
        "session_id": "",
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "tool_uses": [],
        "tool_use_count": 0,
        "models_used": [],
        "subagent_count": 0,
        "duration_minutes": 0.0,
        "message_count": 0,
        "thinking_count": 0,
    }
