"""Unit tests for portable token usage normalization."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cos_lib.token_usage import normalize_usage_record, summarize_usage_jsonl

pytestmark = pytest.mark.unit


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def test_normalizes_claude_message_usage() -> None:
    item = normalize_usage_record(
        {
            "type": "assistant",
            "message": {
                "model": "claude-sonnet-4-6",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "cache_read_input_tokens": 40,
                    "cache_creation_input_tokens": 5,
                },
            },
        },
        default_harness="claude-code",
    )

    assert item is not None
    assert item.input_tokens == 100
    assert item.output_tokens == 20
    assert item.cache_read_input_tokens == 40
    assert item.cache_creation_input_tokens == 5
    assert item.provider == "anthropic"
    assert item.harness == "claude-code"
    assert item.raw_usage_shape == "anthropic-compatible"


def test_normalizes_openai_prompt_usage_with_cached_tokens() -> None:
    item = normalize_usage_record(
        {
            "provider": "openai",
            "model": "gpt-5.1",
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 200,
                "prompt_tokens_details": {"cached_tokens": 256},
            },
        },
        default_harness="codex",
    )

    assert item is not None
    assert item.input_tokens == 1000
    assert item.output_tokens == 200
    assert item.cache_read_input_tokens == 256
    assert item.provider == "openai"
    assert item.harness == "codex"
    assert item.raw_usage_shape == "openai-compatible"


def test_normalizes_camel_case_sdk_usage_with_payload_harness() -> None:
    item = normalize_usage_record(
        {
            "payload": {"provider": "anthropic", "harness": "opencode", "model": "claude-haiku-4"},
            "usage": {
                "inputTokens": 500,
                "outputTokens": 100,
                "cachedInputTokens": 50,
                "cacheCreationInputTokens": 10,
            },
        },
        default_harness="unknown",
    )

    assert item is not None
    assert item.input_tokens == 500
    assert item.output_tokens == 100
    assert item.cache_read_input_tokens == 50
    assert item.cache_creation_input_tokens == 10
    assert item.provider == "anthropic"
    assert item.harness == "opencode"


def test_total_only_usage_is_preserved_for_budget_math() -> None:
    item = normalize_usage_record(
        {"model": "unknown-local-model", "usage": {"totalTokens": 1234}},
        default_harness="ide-x",
    )

    assert item is not None
    assert item.input_tokens == 1234
    assert item.output_tokens == 0
    assert item.provider == "unknown"
    assert item.raw_usage_shape == "generic-total-only"


def test_summarize_usage_jsonl_skips_bad_lines_and_aggregates_provenance(tmp_path: Path) -> None:
    transcript = tmp_path / "mixed.jsonl"
    transcript.write_text(
        "not-json\n"
        + json.dumps({
            "provider": "openai",
            "harness": "codex",
            "model": "gpt-5.1",
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
        })
        + "\n"
        + json.dumps({
            "harness": "claude-code",
            "message": {
                "model": "claude-sonnet-4-6",
                "usage": {"input_tokens": 200, "output_tokens": 40, "cache_read_input_tokens": 25},
            },
        })
        + "\n",
        encoding="utf-8",
    )

    summary = summarize_usage_jsonl(transcript, default_harness="fallback")

    assert summary.input_tokens == 300
    assert summary.output_tokens == 60
    assert summary.cache_read_input_tokens == 25
    assert summary.turn_count == 2
    assert summary.providers_seen == ["anthropic", "openai"]
    assert summary.harnesses_seen == ["claude-code", "codex"]
    assert summary.models_seen == ["claude-sonnet-4-6", "gpt-5.1"]
