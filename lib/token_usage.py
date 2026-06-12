# SCOPE: both
"""Portable token-usage normalization across agent harnesses and providers.

The OS has multiple token optimization mechanisms, but real usage telemetry
must not be coupled to one transcript shape.  This module normalizes usage from
provider/harness records into one internal schema that can be written to the
existing ``cost-events.jsonl`` stream without losing source provenance.

Supported shapes are intentionally conservative:

- Claude Code transcript records: ``type=assistant`` + ``message.usage``.
- OpenAI Responses/Chat style objects: ``usage.prompt_tokens``,
  ``usage.completion_tokens`` and ``usage.prompt_tokens_details.cached_tokens``.
- Generic Codex/OpenCode/IDE JSONL records that expose a ``usage`` object with
  either snake_case or camelCase token fields.

Unknown fields are ignored; unknown pricing remains a downstream concern.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Iterable


@dataclass
class NormalizedUsage:
    """Canonical real-token usage for one model/provider turn."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    model: str = "unknown"
    provider: str = "unknown"
    harness: str = "unknown"
    source: str = "usage"
    raw_usage_shape: str = "unknown"

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_input_tokens
            + self.cache_creation_input_tokens
        )


@dataclass
class UsageSummary:
    """Aggregated token usage for a transcript/session."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    turn_count: int = 0
    model: str = "unknown"
    models_seen: list[str] = field(default_factory=list)
    providers_seen: list[str] = field(default_factory=list)
    harnesses_seen: list[str] = field(default_factory=list)
    source_kind: str = "usage"
    parser_version: str = "token-usage-normalizer.v1"

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_input_tokens
            + self.cache_creation_input_tokens
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "model": self.model,
            "turn_count": self.turn_count,
            "models_seen": self.models_seen,
            "providers_seen": self.providers_seen,
            "harnesses_seen": self.harnesses_seen,
            "source_kind": self.source_kind,
            "parser_version": self.parser_version,
        }


def _int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _nested(data: dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _detect_provider(model: str, explicit: str | None = None) -> str:
    if explicit:
        return str(explicit)
    lower = model.lower()
    if lower.startswith("claude") or "sonnet" in lower or "opus" in lower or "haiku" in lower:
        return "anthropic"
    if lower.startswith("gpt") or lower.startswith("o") or "openai" in lower:
        return "openai"
    return "unknown"


def normalize_usage_record(record: dict[str, Any], *, default_harness: str = "unknown") -> NormalizedUsage | None:
    """Normalize one JSON object that may contain provider usage.

    Returns ``None`` if no usage object is present or all token counts are zero.
    """
    message = record.get("message") if isinstance(record.get("message"), dict) else {}
    response = record.get("response") if isinstance(record.get("response"), dict) else {}

    usage = (
        record.get("usage")
        or message.get("usage")
        or response.get("usage")
        or _nested(record, "payload", "usage")
        or _nested(record, "data", "usage")
    )
    if not isinstance(usage, dict):
        return None

    model = str(
        record.get("model")
        or message.get("model")
        or response.get("model")
        or _nested(record, "payload", "model")
        or _nested(record, "data", "model")
        or "unknown"
    )
    provider = _detect_provider(model, record.get("provider") or _nested(record, "payload", "provider"))
    harness = str(record.get("harness") or _nested(record, "payload", "harness") or default_harness)

    # Anthropic / Claude-style usage.
    input_tokens = _int(usage.get("input_tokens") or usage.get("inputTokens"))
    output_tokens = _int(usage.get("output_tokens") or usage.get("outputTokens"))
    cache_read = _int(
        usage.get("cache_read_input_tokens")
        or usage.get("cacheReadInputTokens")
        or usage.get("cached_input_tokens")
        or usage.get("cachedInputTokens")
    )
    cache_write = _int(
        usage.get("cache_creation_input_tokens")
        or usage.get("cacheCreationInputTokens")
        or usage.get("cache_write_input_tokens")
        or usage.get("cacheWriteInputTokens")
    )
    shape = "anthropic-compatible"

    # OpenAI Responses/Chat-style usage.
    if input_tokens == 0 and ("prompt_tokens" in usage or "promptTokens" in usage):
        input_tokens = _int(usage.get("prompt_tokens") or usage.get("promptTokens"))
        output_tokens = _int(usage.get("completion_tokens") or usage.get("completionTokens") or usage.get("output_tokens"))
        prompt_details = usage.get("prompt_tokens_details") or usage.get("promptTokensDetails") or {}
        if isinstance(prompt_details, dict):
            cache_read = _int(prompt_details.get("cached_tokens") or prompt_details.get("cachedTokens"))
        shape = "openai-compatible"

    # Some SDKs expose totalTokens but omit input/output. Keep as input so budget
    # gates can still reason about consumed tokens without inventing output.
    if input_tokens == 0 and output_tokens == 0 and "totalTokens" in usage:
        input_tokens = _int(usage.get("totalTokens"))
        shape = "generic-total-only"
    if input_tokens == 0 and output_tokens == 0 and "total_tokens" in usage:
        input_tokens = _int(usage.get("total_tokens"))
        shape = "generic-total-only"

    normalized = NormalizedUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=cache_read,
        cache_creation_input_tokens=cache_write,
        model=model,
        provider=provider,
        harness=harness,
        source=str(record.get("type") or record.get("event_type") or "usage"),
        raw_usage_shape=shape,
    )
    if normalized.total_tokens <= 0:
        return None
    return normalized


def summarize_usage(records: Iterable[dict[str, Any]], *, default_harness: str = "unknown") -> UsageSummary:
    """Aggregate normalized usage records into one session summary."""
    totals = UsageSummary()
    model_counts: dict[str, int] = {}
    providers: set[str] = set()
    harnesses: set[str] = set()

    for record in records:
        item = normalize_usage_record(record, default_harness=default_harness)
        if item is None:
            continue
        totals.input_tokens += item.input_tokens
        totals.output_tokens += item.output_tokens
        totals.cache_read_input_tokens += item.cache_read_input_tokens
        totals.cache_creation_input_tokens += item.cache_creation_input_tokens
        totals.turn_count += 1
        if item.model:
            model_counts[item.model] = model_counts.get(item.model, 0) + 1
        providers.add(item.provider)
        harnesses.add(item.harness)

    if model_counts:
        totals.model = max(model_counts, key=lambda model: model_counts[model])
        totals.models_seen = sorted(model_counts)
    totals.providers_seen = sorted(providers)
    totals.harnesses_seen = sorted(harnesses)
    return totals


def load_jsonl_records(path: str | Path) -> list[dict[str, Any]]:
    """Load JSONL records, skipping malformed lines."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Transcript not found: {path}")
    records: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                records.append(row)
    return records


def summarize_usage_jsonl(path: str | Path, *, default_harness: str = "unknown") -> UsageSummary:
    """Load a JSONL transcript/session file and summarize any usage records."""
    return summarize_usage(load_jsonl_records(path), default_harness=default_harness)
