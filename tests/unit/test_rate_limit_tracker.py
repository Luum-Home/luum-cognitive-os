"""Tests for lib/rate_limit_tracker.py (ADR-080 Tier 1 #4).

Tests are organized into:
  1. Per-provider parsers with realistic header fixtures
  2. record() + state() behavioral round-trip
  3. should_throttle() — threshold logic
  4. metrics() snapshot
  5. Dispatch cascade integration (mocked dispatch)
  6. Failure paths — malformed headers, missing env var
  7. JSONL persistence — atomic append
"""

from __future__ import annotations

import json
import sys
import time
from unittest.mock import MagicMock

import pytest

# ── helpers ───────────────────────────────────────────────────────────────────

def _reload_tracker():
    """Reimport the module so module-level _STATE is fresh between tests."""
    if "lib.rate_limit_tracker" in sys.modules:
        del sys.modules["lib.rate_limit_tracker"]
    import lib.rate_limit_tracker as m
    return m


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Reset process-local _STATE and env vars before each test."""
    import lib.rate_limit_tracker as tracker
    tracker.clear()
    monkeypatch.delenv("COS_RATE_TRACKER", raising=False)
    monkeypatch.delenv("COS_RATE_THROTTLE_PCT", raising=False)
    yield
    tracker.clear()


# ── Realistic header fixtures ─────────────────────────────────────────────────

ANTHROPIC_HEADERS_50PCT = {
    "anthropic-ratelimit-requests-limit": "100",
    "anthropic-ratelimit-requests-remaining": "50",
    "anthropic-ratelimit-requests-reset": "30",
    "anthropic-ratelimit-tokens-limit": "100000",
    "anthropic-ratelimit-tokens-remaining": "50000",
    "anthropic-ratelimit-tokens-reset": "30",
}

ANTHROPIC_HEADERS_90PCT = {
    "anthropic-ratelimit-requests-limit": "100",
    "anthropic-ratelimit-requests-remaining": "10",
    "anthropic-ratelimit-requests-reset": "45",
    "anthropic-ratelimit-tokens-limit": "100000",
    "anthropic-ratelimit-tokens-remaining": "5000",
    "anthropic-ratelimit-tokens-reset": "45",
    # Day bucket too
    "anthropic-ratelimit-tokens-day-limit": "1000000",
    "anthropic-ratelimit-tokens-day-remaining": "100000",
    "anthropic-ratelimit-tokens-day-reset": "3600",
}

OPENAI_HEADERS_50PCT = {
    "x-ratelimit-limit-requests": "500",
    "x-ratelimit-remaining-requests": "250",
    "x-ratelimit-reset-requests": "20",
    "x-ratelimit-limit-tokens": "90000",
    "x-ratelimit-remaining-tokens": "45000",
    "x-ratelimit-reset-tokens": "20",
    "x-ratelimit-limit-requests-1h": "10000",
    "x-ratelimit-remaining-requests-1h": "5000",
    "x-ratelimit-reset-requests-1h": "1800",
    "x-ratelimit-limit-tokens-1h": "5000000",
    "x-ratelimit-remaining-tokens-1h": "2500000",
    "x-ratelimit-reset-tokens-1h": "1800",
}

OPENAI_HEADERS_88PCT = {
    "x-ratelimit-limit-requests": "500",
    "x-ratelimit-remaining-requests": "60",        # 88% used
    "x-ratelimit-reset-requests": "15",
    "x-ratelimit-limit-tokens": "90000",
    "x-ratelimit-remaining-tokens": "70000",       # ~22% used
    "x-ratelimit-reset-tokens": "15",
    "x-ratelimit-limit-requests-1h": "10000",
    "x-ratelimit-remaining-requests-1h": "9000",
    "x-ratelimit-reset-requests-1h": "1800",
    "x-ratelimit-limit-tokens-1h": "5000000",
    "x-ratelimit-remaining-tokens-1h": "4000000",
    "x-ratelimit-reset-tokens-1h": "1800",
}

EMPTY_HEADERS: dict = {}
IRRELEVANT_HEADERS = {
    "content-type": "application/json",
    "x-request-id": "abc123",
}


# ═════════════════════════════════════════════════════════════════════════════
# 1. Per-provider parsers
# ═════════════════════════════════════════════════════════════════════════════

class TestParseAnthropic:
    def test_50pct_headers_parsed_correctly(self):
        import lib.rate_limit_tracker as m
        lowered = {k.lower(): v for k, v in ANTHROPIC_HEADERS_50PCT.items()}
        result = m._parse_anthropic_headers(lowered, time.time())

        assert result.requests_min.limit == 100
        assert result.requests_min.remaining == 50
        assert result.requests_min.usage_pct == pytest.approx(50.0)
        assert result.tokens_min.limit == 100000
        assert result.tokens_min.remaining == 50000
        assert result.provider == "anthropic"

    def test_90pct_headers_parsed_correctly(self):
        import lib.rate_limit_tracker as m
        lowered = {k.lower(): v for k, v in ANTHROPIC_HEADERS_90PCT.items()}
        result = m._parse_anthropic_headers(lowered, time.time())

        assert result.requests_min.usage_pct == pytest.approx(90.0)
        assert result.tokens_min.usage_pct == pytest.approx(95.0)
        assert result.tokens_day.limit == 1000000

    def test_has_data_true(self):
        import lib.rate_limit_tracker as m
        lowered = {k.lower(): v for k, v in ANTHROPIC_HEADERS_50PCT.items()}
        result = m._parse_anthropic_headers(lowered, time.time())
        assert result.has_data is True

    def test_provider_label(self):
        import lib.rate_limit_tracker as m
        lowered = {k.lower(): v for k, v in ANTHROPIC_HEADERS_50PCT.items()}
        result = m._parse_anthropic_headers(lowered, time.time())
        assert result.provider == "anthropic"


class TestParseOpenAI:
    def test_50pct_headers_parsed_correctly(self):
        import lib.rate_limit_tracker as m
        lowered = {k.lower(): v for k, v in OPENAI_HEADERS_50PCT.items()}
        result = m._parse_openai_headers(lowered, time.time())

        assert result.requests_min.limit == 500
        assert result.requests_min.remaining == 250
        assert result.requests_min.usage_pct == pytest.approx(50.0)
        assert result.requests_day.limit == 10000  # hour window in day slot
        assert result.tokens_day.limit == 5000000

    def test_88pct_requests_per_min(self):
        import lib.rate_limit_tracker as m
        lowered = {k.lower(): v for k, v in OPENAI_HEADERS_88PCT.items()}
        result = m._parse_openai_headers(lowered, time.time())

        # 440/500 = 88%
        assert result.requests_min.usage_pct == pytest.approx(88.0)

    def test_provider_label_passed_through(self):
        import lib.rate_limit_tracker as m
        lowered = {k.lower(): v for k, v in OPENAI_HEADERS_50PCT.items()}
        result = m._parse_openai_headers(lowered, time.time(), provider="qwen")
        assert result.provider == "qwen"


class TestParseQwen:
    def test_delegates_to_openai_parser(self):
        """Qwen uses the OpenAI header shape."""
        import lib.rate_limit_tracker as m
        lowered = {k.lower(): v for k, v in OPENAI_HEADERS_50PCT.items()}
        result = m._parse_qwen_headers(lowered, time.time())
        assert result.provider == "qwen"
        assert result.requests_min.usage_pct == pytest.approx(50.0)


class TestParseOllama:
    def test_always_empty_state(self):
        import lib.rate_limit_tracker as m
        result = m._parse_ollama_headers({}, time.time())
        assert result.has_data is False
        assert result.provider == "ollama"


# ═════════════════════════════════════════════════════════════════════════════
# 2. record() + state() behavioral round-trip
# ═════════════════════════════════════════════════════════════════════════════

class TestRecordAndState:
    def test_no_op_without_env_var(self, monkeypatch):
        import lib.rate_limit_tracker as m
        m.record("anthropic", ANTHROPIC_HEADERS_50PCT)
        s = m.state("anthropic")
        assert s.has_data is False

    def test_record_stores_state(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        m.record("anthropic", ANTHROPIC_HEADERS_50PCT)
        s = m.state("anthropic")
        assert s.has_data is True
        assert s.requests_min.usage_pct == pytest.approx(50.0)

    def test_record_openai_headers(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        m.record("openai", OPENAI_HEADERS_50PCT)
        s = m.state("openai")
        assert s.has_data is True
        assert s.requests_min.limit == 500

    def test_state_empty_when_no_data(self):
        import lib.rate_limit_tracker as m
        s = m.state("nonexistent_provider")
        assert s.has_data is False

    def test_record_empty_headers_no_crash(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        m.record("anthropic", EMPTY_HEADERS)
        assert m.state("anthropic").has_data is False

    def test_record_irrelevant_headers_no_crash(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        m.record("openai", IRRELEVANT_HEADERS)
        assert m.state("openai").has_data is False

    def test_record_overwrites_previous_state(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        m.record("anthropic", ANTHROPIC_HEADERS_50PCT)
        m.record("anthropic", ANTHROPIC_HEADERS_90PCT)
        s = m.state("anthropic")
        # Latest record wins — 90% not 50%
        assert s.requests_min.usage_pct == pytest.approx(90.0)


# ═════════════════════════════════════════════════════════════════════════════
# 3. should_throttle() — threshold logic
# ═════════════════════════════════════════════════════════════════════════════

class TestShouldThrottle:
    def test_no_op_without_env_var(self):
        import lib.rate_limit_tracker as m
        should, reason = m.should_throttle("anthropic")
        assert should is False
        assert reason == ""

    def test_false_below_threshold(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        m.record("anthropic", ANTHROPIC_HEADERS_50PCT)
        should, reason = m.should_throttle("anthropic")
        assert should is False

    def test_true_above_85pct(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        m.record("anthropic", ANTHROPIC_HEADERS_90PCT)
        should, reason = m.should_throttle("anthropic")
        assert should is True
        assert "anthropic" in reason
        assert "%" in reason

    def test_true_above_85pct_openai(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        m.record("openai", OPENAI_HEADERS_88PCT)
        should, reason = m.should_throttle("openai")
        assert should is True
        assert "openai" in reason

    def test_reason_contains_reset_info(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        m.record("anthropic", ANTHROPIC_HEADERS_90PCT)
        _, reason = m.should_throttle("anthropic")
        # Reason must mention the reset window
        assert "resets in" in reason

    def test_ollama_never_throttles(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        # Even with bogus state, ollama must return False
        should, reason = m.should_throttle("ollama")
        assert should is False

    def test_unknown_provider_no_data_false(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        should, reason = m.should_throttle("some_new_provider")
        assert should is False

    def test_custom_threshold_respected(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        monkeypatch.setenv("COS_RATE_THROTTLE_PCT", "96")
        import lib.rate_limit_tracker as m
        # ANTHROPIC_HEADERS_90PCT has worst bucket at 95% (tokens/min).
        # Threshold is 96 → 95 < 96, should NOT throttle.
        m.record("anthropic", ANTHROPIC_HEADERS_90PCT)
        should, _ = m.should_throttle("anthropic")
        assert should is False

    def test_custom_threshold_low_triggers(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        monkeypatch.setenv("COS_RATE_THROTTLE_PCT", "40")
        import lib.rate_limit_tracker as m
        # 50% consumed, threshold is 40 → should throttle
        m.record("anthropic", ANTHROPIC_HEADERS_50PCT)
        should, _ = m.should_throttle("anthropic")
        assert should is True


# ═════════════════════════════════════════════════════════════════════════════
# 4. metrics() snapshot
# ═════════════════════════════════════════════════════════════════════════════

class TestMetrics:
    def test_empty_when_no_data(self):
        import lib.rate_limit_tracker as m
        result = m.metrics()
        assert result["providers"] == {}
        assert "throttle_threshold_pct" in result
        assert "tracker_enabled" in result

    def test_snapshot_after_record(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        m.record("anthropic", ANTHROPIC_HEADERS_90PCT)
        result = m.metrics()
        assert "anthropic" in result["providers"]
        snap = result["providers"]["anthropic"]
        assert snap["worst_pct"] == pytest.approx(95.0, abs=1.0)
        assert snap["worst_label"] != ""
        # At 90%+ consumption, predicted_exhaustion should be a string
        assert snap["predicted_exhaustion"] is not None

    def test_tracker_enabled_false_without_env(self):
        import lib.rate_limit_tracker as m
        result = m.metrics()
        assert result["tracker_enabled"] is False


# ═════════════════════════════════════════════════════════════════════════════
# 5. Dispatch cascade integration
# ═════════════════════════════════════════════════════════════════════════════

class TestDispatchCascadeIntegration:
    """When provider 1 throttles, dispatch falls back to provider 2."""

    def _make_dispatch_result(self, provider: str, success: bool = True) -> dict:
        return {
            "success": success,
            "text": f"response from {provider}",
            "tokens_in": 10,
            "tokens_out": 50,
            "cost_usd": 0.001,
            "error": "" if success else "error",
            "model": "test-model",
            "provider_label": provider,
        }

    def test_throttled_provider_is_skipped(self, monkeypatch):
        """When qwen is throttled, dispatch should fall through to claude."""
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        # Pre-load qwen state at 90% so it will be throttled
        m.record("qwen", OPENAI_HEADERS_88PCT)

        # Patch should_throttle to be deterministic
        qwen_response = self._make_dispatch_result("alibaba_qwen")
        claude_response = self._make_dispatch_result("claude")

        call_order: list[str] = []

        def mock_qwen(prompt, claude_model=None, verbose=False):
            call_order.append("qwen")
            return qwen_response

        def mock_claude(prompt, claude_model, executor, timeout=600):
            call_order.append("claude")
            return claude_response

        mock_executor = MagicMock()

        import lib.dispatch as dispatch_mod
        result = dispatch_mod.dispatch(
            prompt="test",
            providers=["qwen", "claude"],
            claude_executor=mock_executor,
            _qwen_fn=mock_qwen,
            _claude_fn=mock_claude,
            _metric_sink=lambda _: None,
        )

        # With throttling active, qwen should be skipped → claude used
        assert result.provider_used == "claude"
        assert "qwen" not in call_order
        assert "claude" in call_order

    def test_non_throttled_provider_is_tried(self, monkeypatch):
        """When no throttle is active, providers are tried normally."""
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        # 50% — below threshold
        m.record("qwen", OPENAI_HEADERS_50PCT)

        call_order: list[str] = []
        qwen_response = self._make_dispatch_result("alibaba_qwen")

        def mock_qwen(prompt, claude_model=None, verbose=False):
            call_order.append("qwen")
            return qwen_response

        import lib.dispatch as dispatch_mod
        result = dispatch_mod.dispatch(
            prompt="test",
            providers=["qwen", "claude"],
            _qwen_fn=mock_qwen,
            _metric_sink=lambda _: None,
        )

        assert "qwen" in call_order
        assert result.success is True


# ═════════════════════════════════════════════════════════════════════════════
# 6. Failure paths
# ═════════════════════════════════════════════════════════════════════════════

class TestFailurePaths:
    def test_malformed_numeric_header_uses_default(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        bad_headers = {
            "anthropic-ratelimit-requests-limit": "not_a_number",
            "anthropic-ratelimit-requests-remaining": "50",
            "anthropic-ratelimit-requests-reset": "30",
        }
        # Must not crash; defaults to 0 for unparseable values
        m.record("anthropic", bad_headers)
        s = m.state("anthropic")
        # remaining=50 with limit=0 → usage_pct=0 (no data for limit)
        assert s.requests_min.usage_pct == pytest.approx(0.0)

    def test_completely_malformed_headers_no_crash(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        bad_headers = {
            "x-ratelimit-limit-requests": None,     # type: ignore
            "x-ratelimit-remaining-requests": object(),  # type: ignore
        }
        # Should not raise
        try:
            m.record("openai", bad_headers)  # type: ignore
        except Exception as exc:
            pytest.fail(f"record() raised unexpectedly: {exc}")

    def test_none_headers_no_crash(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        m.record("openai", None)  # type: ignore
        assert m.state("openai").has_data is False

    def test_safe_int_with_none(self):
        import lib.rate_limit_tracker as m
        assert m._safe_int(None) == 0
        assert m._safe_int("") == 0
        assert m._safe_int("bad") == 0

    def test_safe_float_with_none(self):
        import lib.rate_limit_tracker as m
        assert m._safe_float(None) == 0.0
        assert m._safe_float("bad") == 0.0

    def test_throttle_returns_safe_when_no_data(self, monkeypatch):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        import lib.rate_limit_tracker as m
        should, reason = m.should_throttle("nonexistent")
        assert should is False
        assert reason == ""


# ═════════════════════════════════════════════════════════════════════════════
# 7. JSONL persistence — atomic append
# ═════════════════════════════════════════════════════════════════════════════

class TestJsonlPersistence:
    def test_jsonl_written_on_record(self, monkeypatch, tmp_path):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")

        # Redirect JSONL path to tmp
        def mock_jsonl_path():
            return tmp_path / ".cognitive-os" / "runtime" / "rate-limits.jsonl"

        import lib.rate_limit_tracker as m
        monkeypatch.setattr(m, "_jsonl_path", mock_jsonl_path)

        m.record("anthropic", ANTHROPIC_HEADERS_50PCT)

        jsonl_file = mock_jsonl_path()
        assert jsonl_file.exists()
        lines = jsonl_file.read_text().strip().splitlines()
        assert len(lines) >= 1

        record_data = json.loads(lines[-1])
        assert record_data["provider"] == "anthropic"
        assert "ts" in record_data
        assert "worst_pct" in record_data

    def test_jsonl_records_are_valid_json(self, monkeypatch, tmp_path):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")

        def mock_jsonl_path():
            return tmp_path / ".cognitive-os" / "runtime" / "rate-limits.jsonl"

        import lib.rate_limit_tracker as m
        monkeypatch.setattr(m, "_jsonl_path", mock_jsonl_path)

        m.record("openai", OPENAI_HEADERS_50PCT)
        m.record("anthropic", ANTHROPIC_HEADERS_50PCT)

        lines = mock_jsonl_path().read_text().strip().splitlines()
        for line in lines:
            parsed = json.loads(line)  # must not raise
            assert "provider" in parsed

    def test_jsonl_not_written_when_tracker_disabled(self, monkeypatch, tmp_path):
        # COS_RATE_TRACKER not set (default)
        def mock_jsonl_path():
            return tmp_path / ".cognitive-os" / "runtime" / "rate-limits.jsonl"

        import lib.rate_limit_tracker as m
        monkeypatch.setattr(m, "_jsonl_path", mock_jsonl_path)

        m.record("anthropic", ANTHROPIC_HEADERS_50PCT)

        assert not mock_jsonl_path().exists()

    def test_jsonl_dir_created_if_absent(self, monkeypatch, tmp_path):
        monkeypatch.setenv("COS_RATE_TRACKER", "1")
        deep_path = tmp_path / "a" / "b" / "c" / "rate-limits.jsonl"

        import lib.rate_limit_tracker as m
        monkeypatch.setattr(m, "_jsonl_path", lambda: deep_path)

        m.record("anthropic", ANTHROPIC_HEADERS_50PCT)

        assert deep_path.exists()
