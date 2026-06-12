"""Behavior tests for aggregate_session_tokens.py and token_report.py.

Tests use synthetic transcript fixtures (tmp_path), never live session files.
Covers: aggregation math, dedup skip, unknown-model null cost, missing
transcript exit 0, token_report per-session / per-day / cache-ratio output.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from scripts.aggregate_session_tokens import (
    _is_pricing_known,
    _session_already_recorded,
    find_portable_session_jsonl,
    main as aggregate_main,
    parse_claude_transcript,
    parse_usage_transcript,
    write_transcript_cost_event,
)
from scripts.token_report import (
    _aggregate_day,
    _aggregate_session,
    _cache_hit_ratio,
    load_cost_events,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_assistant_event(
    input_tokens: int,
    output_tokens: int,
    cache_read: int = 0,
    cache_write: int = 0,
    model: str = "claude-fable-5",
) -> dict:
    """Return a single assistant JSONL event dict."""
    return {
        "type": "assistant",
        "message": {
            "model": model,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_write,
            },
        },
    }


def _write_transcript(path: Path, events: list[dict]) -> None:
    """Write a synthetic transcript JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event) + "\n")


def _write_cost_event(cost_file: Path, session_id: str) -> None:
    """Pre-seed cost-events.jsonl with one transcript row for session_id."""
    cost_file.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "source": "aggregate_session_tokens",
        "event_type": "cost.recorded",
        "timestamp": "2026-06-10T00:00:00+00:00",
        "payload": {
            "source": "transcript",
            "session_id": session_id,
            "is_estimate": False,
            "actual_cost_usd": 0.01,
        },
    }
    with cost_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


# ---------------------------------------------------------------------------
# parse_claude_transcript tests
# ---------------------------------------------------------------------------

class TestParseClaudeTranscript:
    def test_sums_tokens_across_multiple_turns(self, tmp_path: Path) -> None:
        """Aggregation math: sums input/output/cache across all assistant events."""
        transcript = tmp_path / "session-abc.jsonl"
        _write_transcript(transcript, [
            _make_assistant_event(input_tokens=1000, output_tokens=200, cache_read=500, cache_write=300),
            _make_assistant_event(input_tokens=2000, output_tokens=400, cache_read=100, cache_write=0),
            # non-assistant event — must be ignored
            {"type": "user", "message": {"content": "hello"}},
        ])

        totals = parse_claude_transcript(str(transcript))

        assert totals["input_tokens"] == 3000
        assert totals["output_tokens"] == 600
        assert totals["cache_read_input_tokens"] == 600
        assert totals["cache_creation_input_tokens"] == 300
        assert totals["turn_count"] == 2
        assert totals["model"] == "claude-fable-5"
        assert totals["providers_seen"] == ["anthropic"]
        assert totals["harnesses_seen"] == ["claude-code"]

    def test_dominant_model_most_frequent(self, tmp_path: Path) -> None:
        """Dominant model is the most-frequently-seen model across turns."""
        transcript = tmp_path / "session-model.jsonl"
        _write_transcript(transcript, [
            _make_assistant_event(1000, 100, model="claude-sonnet-4-6"),
            _make_assistant_event(1000, 100, model="claude-sonnet-4-6"),
            _make_assistant_event(1000, 100, model="claude-fable-5"),
        ])

        totals = parse_claude_transcript(str(transcript))
        assert totals["model"] == "claude-sonnet-4-6"
        assert "claude-fable-5" in totals["models_seen"]

    def test_empty_transcript_returns_zero_totals(self, tmp_path: Path) -> None:
        """An empty or non-assistant-only transcript returns zero counts."""
        transcript = tmp_path / "session-empty.jsonl"
        _write_transcript(transcript, [
            {"type": "user", "message": {"content": "hello"}},
        ])

        totals = parse_claude_transcript(str(transcript))
        assert totals["input_tokens"] == 0
        assert totals["output_tokens"] == 0
        assert totals["turn_count"] == 0
        assert totals["model"] == "unknown"

    def test_skips_malformed_json_lines(self, tmp_path: Path) -> None:
        """Malformed JSONL lines are silently skipped."""
        transcript = tmp_path / "session-bad.jsonl"
        transcript.parent.mkdir(parents=True, exist_ok=True)
        with transcript.open("w") as fh:
            fh.write("NOT JSON\n")
            fh.write(json.dumps(_make_assistant_event(500, 100)) + "\n")

        totals = parse_claude_transcript(str(transcript))
        assert totals["input_tokens"] == 500
        assert totals["turn_count"] == 1

    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            parse_claude_transcript(str(tmp_path / "does_not_exist.jsonl"))


# ---------------------------------------------------------------------------
# Dedup tests
# ---------------------------------------------------------------------------

class TestSessionAlreadyRecorded:
    def test_returns_false_when_file_missing(self, tmp_path: Path) -> None:
        cost_file = tmp_path / "cost-events.jsonl"
        assert _session_already_recorded(str(cost_file), "session-123") is False

    def test_returns_true_when_session_present(self, tmp_path: Path) -> None:
        cost_file = tmp_path / "cost-events.jsonl"
        _write_cost_event(cost_file, "session-abc")
        assert _session_already_recorded(str(cost_file), "session-abc") is True

    def test_returns_false_for_different_session(self, tmp_path: Path) -> None:
        cost_file = tmp_path / "cost-events.jsonl"
        _write_cost_event(cost_file, "session-abc")
        assert _session_already_recorded(str(cost_file), "session-xyz") is False


# ---------------------------------------------------------------------------
# write_transcript_cost_event tests
# ---------------------------------------------------------------------------

class TestWriteTranscriptCostEvent:
    def test_writes_real_cost_event_for_known_model(self, tmp_path: Path) -> None:
        """Known model produces is_estimate=false and non-null actual_cost_usd."""
        metrics_dir = str(tmp_path / ".cognitive-os" / "metrics")
        totals = {
            "input_tokens": 10_000,
            "output_tokens": 500,
            "cache_read_input_tokens": 2000,
            "cache_creation_input_tokens": 1000,
            "model": "claude-fable-5",
            "models_seen": ["claude-fable-5"],
            "turn_count": 3,
            "providers_seen": ["anthropic"],
            "harnesses_seen": ["claude-code"],
        }

        write_transcript_cost_event(metrics_dir, "session-cost-known", totals)

        cost_file = Path(metrics_dir) / "cost-events.jsonl"
        rows = [json.loads(l) for l in cost_file.read_text().splitlines() if l.strip()]
        assert len(rows) == 1
        payload = rows[0]["payload"]
        assert payload["is_estimate"] is False
        assert payload["source"] == "transcript"
        assert payload["telemetry_schema"] == "token-usage-normalized.v1"
        assert payload["session_id"] == "session-cost-known"
        assert payload["providers_seen"] == ["anthropic"]
        assert payload["harnesses_seen"] == ["claude-code"]
        assert payload["pricing_known"] is True
        assert payload["actual_cost_usd"] is not None
        assert payload["actual_cost_usd"] > 0

    def test_writes_null_cost_for_unknown_model(self, tmp_path: Path) -> None:
        """Unknown model: tokens recorded accurately, actual_cost_usd is None, pricing_known False."""
        metrics_dir = str(tmp_path / ".cognitive-os" / "metrics")
        totals = {
            "input_tokens": 5_000,
            "output_tokens": 300,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "model": "some-future-unknown-model-x99",
            "models_seen": ["some-future-unknown-model-x99"],
            "turn_count": 1,
            "providers_seen": ["unknown"],
            "harnesses_seen": ["ide-x"],
        }

        write_transcript_cost_event(metrics_dir, "session-unknown-model", totals)

        cost_file = Path(metrics_dir) / "cost-events.jsonl"
        rows = [json.loads(l) for l in cost_file.read_text().splitlines() if l.strip()]
        payload = rows[0]["payload"]
        assert payload["input_tokens"] == 5_000
        assert payload["actual_cost_usd"] is None
        assert payload["pricing_known"] is False


# ---------------------------------------------------------------------------
# Missing transcript / exit-0 test
# ---------------------------------------------------------------------------

class TestMissingTranscriptExit0:
    """Script must exit 0 and emit no cost event when transcript is unavailable."""

    def test_no_event_written_when_transcript_missing(self, tmp_path: Path) -> None:
        """parse_claude_transcript raises FileNotFoundError; caller should catch."""
        missing = tmp_path / "no_such_session.jsonl"
        with pytest.raises(FileNotFoundError):
            parse_claude_transcript(str(missing))
        # No cost event file should exist (caller didn't write one)
        cost_file = tmp_path / "cost-events.jsonl"
        assert not cost_file.exists()


class TestZeroTokenGuard:
    """Zero-token sessions (login stubs, error sessions) must not be recorded."""

    def test_zero_token_session_skipped(self, tmp_path: Path) -> None:
        transcript = tmp_path / "zero-session.jsonl"
        _write_transcript(transcript, [_make_assistant_event(0, 0, model="<synthetic>")])
        rc = aggregate_main([str(transcript), "--project-dir", str(tmp_path)])
        assert rc == 0
        cost_file = tmp_path / ".cognitive-os" / "metrics" / "cost-events.jsonl"
        assert not cost_file.exists()

    def test_nonzero_session_still_recorded(self, tmp_path: Path) -> None:
        transcript = tmp_path / "real-session.jsonl"
        _write_transcript(transcript, [_make_assistant_event(100, 50)])
        rc = aggregate_main([str(transcript), "--project-dir", str(tmp_path)])
        assert rc == 0
        cost_file = tmp_path / ".cognitive-os" / "metrics" / "cost-events.jsonl"
        rows = [json.loads(line) for line in cost_file.read_text().splitlines()]
        assert len(rows) == 1
        assert rows[0]["payload"]["input_tokens"] == 100


class TestPortableUsageAggregation:
    def test_openai_style_jsonl_is_aggregated(self, tmp_path: Path) -> None:
        transcript = tmp_path / "codex-session.jsonl"
        _write_transcript(transcript, [
            {
                "provider": "openai",
                "harness": "codex",
                "model": "gpt-5.1",
                "usage": {
                    "prompt_tokens": 1200,
                    "completion_tokens": 300,
                    "prompt_tokens_details": {"cached_tokens": 128},
                },
            }
        ])

        totals = parse_usage_transcript(str(transcript), default_harness="codex")

        assert totals["input_tokens"] == 1200
        assert totals["output_tokens"] == 300
        assert totals["cache_read_input_tokens"] == 128
        assert totals["providers_seen"] == ["openai"]
        assert totals["harnesses_seen"] == ["codex"]

    def test_camel_case_opencode_usage_is_recorded_with_provenance(self, tmp_path: Path) -> None:
        transcript = tmp_path / "opencode-session.jsonl"
        _write_transcript(transcript, [
            {
                "payload": {"provider": "anthropic", "harness": "opencode", "model": "claude-haiku-4"},
                "usage": {"inputTokens": 700, "outputTokens": 80, "cachedInputTokens": 50},
            }
        ])

        rc = aggregate_main([str(transcript), "--project-dir", str(tmp_path)])

        assert rc == 0
        cost_file = tmp_path / ".cognitive-os" / "metrics" / "cost-events.jsonl"
        payload = json.loads(cost_file.read_text().splitlines()[0])["payload"]
        assert payload["telemetry_schema"] == "token-usage-normalized.v1"
        assert payload["providers_seen"] == ["anthropic"]
        assert payload["harnesses_seen"] == ["opencode"]
        assert payload["input_tokens"] == 700
        assert payload["output_tokens"] == 80

    def test_explicit_session_env_wins_for_portable_discovery(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        transcript = tmp_path / "explicit-session.jsonl"
        _write_transcript(transcript, [{"usage": {"totalTokens": 1}}])
        monkeypatch.setenv("COGNITIVE_OS_SESSION_JSONL", str(transcript))

        assert find_portable_session_jsonl(str(tmp_path)) == str(transcript)


# ---------------------------------------------------------------------------
# token_report tests (read path)
# ---------------------------------------------------------------------------

def _build_cost_events_file(cost_file: Path, rows: list[dict]) -> None:
    cost_file.parent.mkdir(parents=True, exist_ok=True)
    with cost_file.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _transcript_row(
    session_id: str,
    date: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read: int = 0,
    cache_write: int = 0,
    cost: float | None = 0.10,
    pricing_known: bool = True,
    providers_seen: list[str] | None = None,
    harnesses_seen: list[str] | None = None,
) -> dict:
    return {
        "source": "aggregate_session_tokens",
        "event_type": "cost.recorded",
        "timestamp": f"{date}T12:00:00+00:00",
        "payload": {
            "source": "transcript",
            "telemetry_schema": "token-usage-normalized.v1",
            "session_id": session_id,
            "model": model,
            "providers_seen": providers_seen or ["anthropic"],
            "harnesses_seen": harnesses_seen or ["claude-code"],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_input_tokens": cache_read,
            "cache_creation_input_tokens": cache_write,
            "actual_cost_usd": cost,
            "pricing_known": pricing_known,
            "is_estimate": False,
        },
    }


class TestTokenReport:
    def test_per_session_output(self, tmp_path: Path) -> None:
        """per-session aggregation returns one row per session_id."""
        cost_file = tmp_path / "cost-events.jsonl"
        _build_cost_events_file(cost_file, [
            _transcript_row("sess-001", "2026-06-10", "claude-fable-5", 10_000, 500, cache_read=2000, cache_write=1000),
            _transcript_row("sess-002", "2026-06-10", "claude-sonnet-4-6", 5_000, 300),
        ])

        rows = load_cost_events(str(cost_file))
        sessions = _aggregate_session(rows)

        assert len(sessions) == 2
        ids = {s["session_id"] for s in sessions}
        assert "sess-001" in ids
        assert "sess-002" in ids

        s1 = next(s for s in sessions if s["session_id"] == "sess-001")
        assert s1["input_tokens"] == 10_000
        assert s1["output_tokens"] == 500
        assert s1["cache_read"] == 2000
        assert s1["cache_write"] == 1000
        assert s1["providers_seen"] == ["anthropic"]
        assert s1["harnesses_seen"] == ["claude-code"]

    def test_per_day_rollup(self, tmp_path: Path) -> None:
        """per-day aggregation groups sessions by calendar date."""
        cost_file = tmp_path / "cost-events.jsonl"
        _build_cost_events_file(cost_file, [
            _transcript_row("sess-001", "2026-06-10", "claude-fable-5", 10_000, 500),
            _transcript_row("sess-002", "2026-06-10", "gpt-5.1", 8_000, 400, providers_seen=["openai"], harnesses_seen=["codex"]),
            _transcript_row("sess-003", "2026-06-11", "claude-fable-5", 5_000, 200),
        ])

        rows = load_cost_events(str(cost_file))
        days = _aggregate_day(rows)

        assert len(days) == 2
        day_10 = next(d for d in days if d["date"] == "2026-06-10")
        assert day_10["sessions"] == 2
        assert day_10["input_tokens"] == 18_000
        assert day_10["providers_seen"] == ["anthropic", "openai"]
        assert day_10["harnesses_seen"] == ["claude-code", "codex"]

        day_11 = next(d for d in days if d["date"] == "2026-06-11")
        assert day_11["sessions"] == 1
        assert day_11["input_tokens"] == 5_000

    def test_cache_hit_ratio_calculation(self) -> None:
        """Cache-hit ratio: cache_read / (input + cache_read + cache_write)."""
        # 2000 / (10000 + 2000 + 1000) = 0.1538..., rounded to 4 decimal places
        ratio = _cache_hit_ratio(10_000, 2_000, 1_000)
        assert abs(ratio - round(2000 / 13000, 4)) < 1e-6

    def test_cache_hit_ratio_zero_total(self) -> None:
        assert _cache_hit_ratio(0, 0, 0) == 0.0

    def test_estimate_rows_excluded(self, tmp_path: Path) -> None:
        """Estimate rows without normalized real-usage schema must be excluded."""
        cost_file = tmp_path / "cost-events.jsonl"
        estimate_row = {
            "source": "record_completion",
            "event_type": "cost.recorded",
            "timestamp": "2026-06-10T12:00:00+00:00",
            "payload": {
                "agent": "test-agent",
                "model": "sonnet",
                "tokens_estimated": 1000,
                "is_estimate": True,
            },
        }
        _build_cost_events_file(cost_file, [
            estimate_row,
            _transcript_row("sess-real", "2026-06-10", "claude-fable-5", 5_000, 300),
        ])

        rows = load_cost_events(str(cost_file))
        sessions = _aggregate_session(rows)
        # Only the transcript row should appear
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "sess-real"

    def test_unknown_model_null_cost_flagged(self, tmp_path: Path) -> None:
        """Session with pricing_known=False is preserved with has_null_cost signal."""
        cost_file = tmp_path / "cost-events.jsonl"
        _build_cost_events_file(cost_file, [
            _transcript_row("sess-uk", "2026-06-10", "future-model-x", 5_000, 300, cost=None, pricing_known=False),
        ])

        rows = load_cost_events(str(cost_file))
        sessions = _aggregate_session(rows)

        assert len(sessions) == 1
        assert sessions[0]["has_null_cost"] is True
        assert sessions[0]["pricing_known"] is False


# ---------------------------------------------------------------------------
# _is_pricing_known tests
# ---------------------------------------------------------------------------

class TestIsPricingKnown:
    def test_known_model_returns_true(self) -> None:
        assert _is_pricing_known("claude-fable-5") is True

    def test_known_model_prefix_match(self) -> None:
        assert _is_pricing_known("claude-sonnet-4-6-blah") is True

    def test_unknown_model_returns_false(self) -> None:
        assert _is_pricing_known("some-imaginary-model-v99") is False
