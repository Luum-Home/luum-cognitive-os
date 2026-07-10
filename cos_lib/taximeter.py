# SCOPE: os-only
"""Taximeter — ADR-325 cost-accounting and resource ledgers.

Append-only JSONL ledger at .cognitive-os/metrics/taximeter.jsonl.
Each tick records one AI-consuming work unit.

Schema (all fields required unless noted):
  ts             ISO-8601 UTC timestamp
  session_id     str
  provider       str  (e.g. "claude", "qwen", "openai")
  model          str  (e.g. "claude-sonnet-4-6", "sonnet")
  prompt_tokens  int
  completion_tokens int
  cost_usd       float  (computed or provided)
  latency_ms     int | None  (optional)
  kind           str  (e.g. "dispatch", "tool", "preflight")

ADR-325 resource ledger:
  .cognitive-os/metrics/ai-resource-ledger.jsonl stores the broader resource
  economy event shape used by hooks that do not know provider price data yet.
  Those rows use tokens_in/tokens_out, estimated/actual cost, retry_count,
  tool_calls, reasoning_effort, agent_id, and task_id.

Query API:
  total_cost(window)             -> float
  cost_by_provider(window)       -> dict[str, float]
  cost_by_session(session_id)    -> float

window: "all" | "today" | "hour" | "session:<id>"
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_LEDGER = ".cognitive-os/metrics/taximeter.jsonl"
DEFAULT_RESOURCE_LEDGER = ".cognitive-os/metrics/ai-resource-ledger.jsonl"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _load_ticks(ledger_path: str) -> List[dict]:
    path = Path(ledger_path)
    if not path.exists():
        return []
    ticks: List[dict] = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ticks.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return ticks


def _filter_window(ticks: List[dict], window: str) -> List[dict]:
    """Filter ticks by time window string.

    Supported values:
      all            — no filtering
      today          — UTC calendar day
      hour           — last 60 minutes
      session:<id>   — by session_id field
    """
    if window == "all":
        return ticks

    if window == "today":
        target_date = _now_utc().date()
        out = []
        for t in ticks:
            ts = _parse_ts(t.get("ts", ""))
            if ts and ts.astimezone(timezone.utc).date() == target_date:
                out.append(t)
        return out

    if window == "hour":
        cutoff = _now_utc() - timedelta(hours=1)
        out = []
        for t in ticks:
            ts = _parse_ts(t.get("ts", ""))
            if ts and ts.astimezone(timezone.utc) >= cutoff:
                out.append(t)
        return out

    if window.startswith("session:"):
        session_id = window[len("session:"):]
        return [t for t in ticks if t.get("session_id") == session_id]

    # Unknown window — return all as safe fallback
    return ticks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def tick(
    session_id: str,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
    kind: str = "dispatch",
    latency_ms: Optional[int] = None,
    ledger_path: str = DEFAULT_LEDGER,
) -> dict:
    """Append one cost event to the taximeter ledger.

    Args:
        session_id:        Caller session identifier.
        provider:          Provider name (e.g. "claude", "qwen").
        model:             Model name (e.g. "claude-sonnet-4-6").
        prompt_tokens:     Number of input/prompt tokens consumed.
        completion_tokens: Number of output/completion tokens generated.
        cost_usd:          Actual or estimated cost in USD.
        kind:              Event kind tag (default "dispatch").
        latency_ms:        Round-trip latency in milliseconds (optional).
        ledger_path:       Path to the JSONL ledger file.

    Returns:
        The recorded tick dict (for testing / inline use).
    """
    record: dict = {
        "ts": _now_utc().isoformat(),
        "session_id": session_id,
        "provider": provider,
        "model": model,
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
        "cost_usd": round(float(cost_usd), 6),
        "latency_ms": int(latency_ms) if latency_ms is not None else None,
        "kind": kind,
    }

    path = Path(ledger_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        pass  # Graceful degradation — do not crash callers on write failure

    return record


def resource_tick(
    session_id: str,
    agent_id: str = "",
    task_id: str = "",
    model: str = "unknown",
    tokens_in: int = 0,
    tokens_out: int = 0,
    estimated_cost_usd: float = 0.0,
    actual_cost_usd: float = 0.0,
    retry_count: int = 0,
    tool_calls: int = 0,
    reasoning_effort: str = "unknown",
    kind: str = "resource",
    source: str = "unknown",
    provider: str = "unknown",
    ledger_path: str = DEFAULT_RESOURCE_LEDGER,
) -> dict:
    """Append one ADR-325 resource economy event to the resource ledger.

    This is the hook-friendly ledger shape from ADR-325. Hooks often know
    estimated tokens or tool calls before provider billing exists, so this row
    is intentionally usable with zero costs while preserving the fields needed
    for later provider ingestion and ratchets.

    Args:
        session_id: Session identifier.
        agent_id: Agent/subagent identifier, if known.
        task_id: Task identifier, if known.
        model: Model name or "unknown" for hook-only estimates.
        tokens_in: Input/context token estimate or provider-reported value.
        tokens_out: Output/completion token estimate or provider-reported value.
        estimated_cost_usd: Estimated USD cost.
        actual_cost_usd: Provider-reported USD cost when available.
        retry_count: Retry count associated with this work unit.
        tool_calls: Tool calls represented by this event.
        reasoning_effort: Low/medium/high/none/unknown effort label.
        kind: Event kind tag.
        source: Hook/script/library emitting the event.
        provider: Provider name, if known.
        ledger_path: Path to the JSONL resource ledger.

    Returns:
        The recorded resource event dict.
    """
    record: dict = {
        "schema_version": 1,
        "ts": _now_utc().isoformat(),
        "session_id": str(session_id or "unknown"),
        "agent_id": str(agent_id or ""),
        "task_id": str(task_id or ""),
        "provider": str(provider or "unknown"),
        "model": str(model or "unknown"),
        "tokens_in": max(0, int(tokens_in)),
        "tokens_out": max(0, int(tokens_out)),
        "estimated_cost_usd": round(float(estimated_cost_usd), 6),
        "actual_cost_usd": round(float(actual_cost_usd), 6),
        "retry_count": max(0, int(retry_count)),
        "tool_calls": max(0, int(tool_calls)),
        "reasoning_effort": str(reasoning_effort or "unknown"),
        "kind": str(kind or "resource"),
        "source": str(source or "unknown"),
    }

    path = Path(ledger_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError:
        pass

    return record


def total_cost(
    window: str = "all",
    ledger_path: str = DEFAULT_LEDGER,
) -> float:
    """Return total cost (USD) across all ticks matching the window.

    Args:
        window:       "all" | "today" | "hour" | "session:<id>"
        ledger_path:  Path to the JSONL ledger file.

    Returns:
        Sum of cost_usd for matching ticks.
    """
    ticks = _filter_window(_load_ticks(ledger_path), window)
    return round(sum(float(t.get("cost_usd", 0.0)) for t in ticks), 6)


def cost_by_provider(
    window: str = "all",
    ledger_path: str = DEFAULT_LEDGER,
) -> Dict[str, float]:
    """Return cost (USD) grouped by provider for the given window.

    Args:
        window:       "all" | "today" | "hour" | "session:<id>"
        ledger_path:  Path to the JSONL ledger file.

    Returns:
        dict mapping provider -> total cost_usd.
    """
    ticks = _filter_window(_load_ticks(ledger_path), window)
    breakdown: Dict[str, float] = {}
    for t in ticks:
        provider = str(t.get("provider", "unknown") or "unknown")
        cost = float(t.get("cost_usd", 0.0))
        breakdown[provider] = round(breakdown.get(provider, 0.0) + cost, 6)
    return breakdown


def cost_by_session(
    session_id: str,
    ledger_path: str = DEFAULT_LEDGER,
) -> float:
    """Return total cost (USD) for a specific session.

    Args:
        session_id:   Session identifier to filter on.
        ledger_path:  Path to the JSONL ledger file.

    Returns:
        Sum of cost_usd for ticks matching session_id.
    """
    return total_cost(window=f"session:{session_id}", ledger_path=ledger_path)
