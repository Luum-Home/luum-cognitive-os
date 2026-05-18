"""Tests for lib/taximeter.py — ADR-325 Phase 2 taximeter ledger."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.taximeter import (
    cost_by_provider,
    cost_by_session,
    tick,
    total_cost,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def ledger(tmp_path: Path) -> str:
    """Temporary ledger file path."""
    return str(tmp_path / "taximeter.jsonl")


# ---------------------------------------------------------------------------
# tick() — schema and write behaviour
# ---------------------------------------------------------------------------

class TestTick:
    def test_tick_returns_dict_with_required_fields(self, ledger: str) -> None:
        record = tick(
            session_id="s1",
            provider="claude",
            model="claude-sonnet-4-6",
            prompt_tokens=100,
            completion_tokens=50,
            cost_usd=0.001,
            ledger_path=ledger,
        )
        assert record["session_id"] == "s1"
        assert record["provider"] == "claude"
        assert record["model"] == "claude-sonnet-4-6"
        assert record["prompt_tokens"] == 100
        assert record["completion_tokens"] == 50
        assert record["cost_usd"] == pytest.approx(0.001, rel=1e-5)
        assert record["kind"] == "dispatch"
        assert record["latency_ms"] is None
        assert "ts" in record

    def test_tick_appends_to_jsonl(self, ledger: str) -> None:
        tick(session_id="s1", provider="claude", model="sonnet",
             prompt_tokens=10, completion_tokens=5, cost_usd=0.0001,
             ledger_path=ledger)
        tick(session_id="s2", provider="qwen", model="qwen3",
             prompt_tokens=20, completion_tokens=8, cost_usd=0.00002,
             ledger_path=ledger)

        lines = Path(ledger).read_text().strip().splitlines()
        assert len(lines) == 2
        first = json.loads(lines[0])
        second = json.loads(lines[1])
        assert first["session_id"] == "s1"
        assert second["provider"] == "qwen"

    def test_tick_latency_ms_stored(self, ledger: str) -> None:
        record = tick(
            session_id="s1", provider="claude", model="sonnet",
            prompt_tokens=10, completion_tokens=5, cost_usd=0.0001,
            latency_ms=250, ledger_path=ledger,
        )
        assert record["latency_ms"] == 250

    def test_tick_custom_kind(self, ledger: str) -> None:
        record = tick(
            session_id="s1", provider="claude", model="haiku",
            prompt_tokens=5, completion_tokens=2, cost_usd=0.00001,
            kind="preflight", ledger_path=ledger,
        )
        assert record["kind"] == "preflight"

    def test_tick_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = str(tmp_path / "a" / "b" / "taximeter.jsonl")
        tick(session_id="s1", provider="x", model="m",
             prompt_tokens=1, completion_tokens=1, cost_usd=0.0,
             ledger_path=nested)
        assert Path(nested).exists()

    def test_tick_graceful_on_unwritable_path(self) -> None:
        """tick() must not raise even if the ledger path is unwritable."""
        record = tick(
            session_id="s1", provider="claude", model="sonnet",
            prompt_tokens=10, completion_tokens=5, cost_usd=0.0001,
            ledger_path="/dev/null/impossible/path/taximeter.jsonl",
        )
        # Should still return the record dict
        assert record["session_id"] == "s1"


# ---------------------------------------------------------------------------
# total_cost()
# ---------------------------------------------------------------------------

class TestTotalCost:
    def test_empty_ledger_returns_zero(self, ledger: str) -> None:
        assert total_cost(ledger_path=ledger) == 0.0

    def test_sums_all_ticks(self, ledger: str) -> None:
        tick(session_id="s1", provider="claude", model="sonnet",
             prompt_tokens=10, completion_tokens=5, cost_usd=0.001,
             ledger_path=ledger)
        tick(session_id="s2", provider="qwen", model="qwen3",
             prompt_tokens=20, completion_tokens=8, cost_usd=0.002,
             ledger_path=ledger)
        assert total_cost(window="all", ledger_path=ledger) == pytest.approx(0.003, rel=1e-5)

    def test_window_today(self, ledger: str) -> None:
        tick(session_id="s1", provider="claude", model="sonnet",
             prompt_tokens=10, completion_tokens=5, cost_usd=0.005,
             ledger_path=ledger)
        result = total_cost(window="today", ledger_path=ledger)
        assert result == pytest.approx(0.005, rel=1e-5)

    def test_window_hour(self, ledger: str) -> None:
        tick(session_id="s1", provider="claude", model="sonnet",
             prompt_tokens=10, completion_tokens=5, cost_usd=0.003,
             ledger_path=ledger)
        result = total_cost(window="hour", ledger_path=ledger)
        assert result == pytest.approx(0.003, rel=1e-5)

    def test_window_session_filters_by_session_id(self, ledger: str) -> None:
        tick(session_id="abc", provider="claude", model="sonnet",
             prompt_tokens=10, completion_tokens=5, cost_usd=0.001,
             ledger_path=ledger)
        tick(session_id="xyz", provider="claude", model="sonnet",
             prompt_tokens=10, completion_tokens=5, cost_usd=0.009,
             ledger_path=ledger)
        result = total_cost(window="session:abc", ledger_path=ledger)
        assert result == pytest.approx(0.001, rel=1e-5)

    def test_unknown_window_falls_back_to_all(self, ledger: str) -> None:
        tick(session_id="s1", provider="claude", model="sonnet",
             prompt_tokens=10, completion_tokens=5, cost_usd=0.007,
             ledger_path=ledger)
        result = total_cost(window="bogus_window", ledger_path=ledger)
        assert result == pytest.approx(0.007, rel=1e-5)

    def test_nonexistent_ledger_returns_zero(self, tmp_path: Path) -> None:
        assert total_cost(ledger_path=str(tmp_path / "missing.jsonl")) == 0.0


# ---------------------------------------------------------------------------
# cost_by_provider()
# ---------------------------------------------------------------------------

class TestCostByProvider:
    def test_empty_ledger_returns_empty_dict(self, ledger: str) -> None:
        assert cost_by_provider(ledger_path=ledger) == {}

    def test_groups_by_provider(self, ledger: str) -> None:
        tick(session_id="s1", provider="claude", model="sonnet",
             prompt_tokens=10, completion_tokens=5, cost_usd=0.001,
             ledger_path=ledger)
        tick(session_id="s1", provider="qwen", model="qwen3",
             prompt_tokens=20, completion_tokens=8, cost_usd=0.002,
             ledger_path=ledger)
        tick(session_id="s1", provider="claude", model="haiku",
             prompt_tokens=5, completion_tokens=2, cost_usd=0.0003,
             ledger_path=ledger)

        result = cost_by_provider(ledger_path=ledger)
        assert set(result.keys()) == {"claude", "qwen"}
        assert result["claude"] == pytest.approx(0.0013, rel=1e-4)
        assert result["qwen"] == pytest.approx(0.002, rel=1e-5)

    def test_respects_window_session(self, ledger: str) -> None:
        tick(session_id="A", provider="claude", model="sonnet",
             prompt_tokens=10, completion_tokens=5, cost_usd=0.001,
             ledger_path=ledger)
        tick(session_id="B", provider="qwen", model="qwen3",
             prompt_tokens=5, completion_tokens=3, cost_usd=0.009,
             ledger_path=ledger)
        result = cost_by_provider(window="session:A", ledger_path=ledger)
        assert list(result.keys()) == ["claude"]
        assert "qwen" not in result


# ---------------------------------------------------------------------------
# cost_by_session()
# ---------------------------------------------------------------------------

class TestCostBySession:
    def test_returns_zero_for_unknown_session(self, ledger: str) -> None:
        tick(session_id="real", provider="claude", model="sonnet",
             prompt_tokens=10, completion_tokens=5, cost_usd=0.005,
             ledger_path=ledger)
        assert cost_by_session("ghost", ledger_path=ledger) == 0.0

    def test_sums_only_matching_session(self, ledger: str) -> None:
        tick(session_id="sess-1", provider="claude", model="sonnet",
             prompt_tokens=10, completion_tokens=5, cost_usd=0.001,
             ledger_path=ledger)
        tick(session_id="sess-1", provider="qwen", model="qwen3",
             prompt_tokens=20, completion_tokens=8, cost_usd=0.002,
             ledger_path=ledger)
        tick(session_id="sess-2", provider="claude", model="opus",
             prompt_tokens=50, completion_tokens=20, cost_usd=0.05,
             ledger_path=ledger)

        assert cost_by_session("sess-1", ledger_path=ledger) == pytest.approx(0.003, rel=1e-5)
        assert cost_by_session("sess-2", ledger_path=ledger) == pytest.approx(0.05, rel=1e-5)

    def test_empty_ledger_returns_zero(self, ledger: str) -> None:
        assert cost_by_session("any", ledger_path=ledger) == 0.0


# ---------------------------------------------------------------------------
# Robustness — malformed lines ignored
# ---------------------------------------------------------------------------

class TestRobustness:
    def test_malformed_jsonl_lines_are_skipped(self, ledger: str) -> None:
        Path(ledger).parent.mkdir(parents=True, exist_ok=True)
        with open(ledger, "w") as fh:
            fh.write('{"ts":"2026-01-01T00:00:00+00:00","session_id":"s1","provider":"claude","model":"sonnet","prompt_tokens":10,"completion_tokens":5,"cost_usd":0.001,"latency_ms":null,"kind":"dispatch"}\n')
            fh.write("NOT_JSON_AT_ALL\n")
            fh.write('{"ts":"2026-01-01T01:00:00+00:00","session_id":"s1","provider":"claude","model":"sonnet","prompt_tokens":10,"completion_tokens":5,"cost_usd":0.002,"latency_ms":null,"kind":"dispatch"}\n')

        result = total_cost(window="all", ledger_path=ledger)
        assert result == pytest.approx(0.003, rel=1e-5)
