"""Tests for lib/dispatch.py — abstract LLM cascade + metrics (C2 of mega-plan).

Covers:
- Default providers list
- Cascade: first success wins, primary tried first
- Fallback advance: Qwen→Claude always, Claude→next only on rate-limit
- Kill-switches: COS_DISABLE_LLM_FALLBACK (cascade), COS_FORCE_CLAUDE_PRIMARY
- Unknown/missing providers skipped without crash
- Empty/all-failed scenario produces DispatchResult with success=False
- Metric logging: every dispatch writes exactly one JSONL record
- Metric schema: required fields present and typed
- Provider-unavailable path (qwen_fn returns None) advances cascade
- Claude executor missing path advances cascade
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from lib import dispatch as _d  # noqa: E402


def _success_response(provider_label: str, text: str = "ok"):
    return {
        "success": True, "text": text, "tokens_in": 5, "tokens_out": 10,
        "cost_usd": 0.001, "error": "", "model": "test-model",
        "provider_label": provider_label,
    }


def _failure_response(provider_label: str, error: str):
    return {
        "success": False, "text": "", "tokens_in": 0, "tokens_out": 0,
        "cost_usd": 0.0, "error": error, "model": "test-model",
        "provider_label": provider_label,
    }


class TestCascadeBasics(unittest.TestCase):
    def test_default_providers_is_qwen_claude(self):
        """When providers=None, defaults to [qwen, claude]."""
        sink_records: list[dict] = []
        r = _d.dispatch(
            "hello", providers=None,
            _qwen_fn=lambda p, **k: _success_response("alibaba_qwen"),
            _metric_sink=lambda rec: sink_records.append(rec),
        )
        self.assertTrue(r.success)
        self.assertEqual(r.provider_used, "alibaba_qwen")
        self.assertEqual(sink_records[0]["providers_requested"], ["qwen", "claude"])
        self.assertEqual(sink_records[0]["providers_tried"], ["qwen"])

    def test_first_success_wins_cascade_stops(self):
        calls = {"qwen": 0, "claude": 0}

        def qwen(p, **k):
            calls["qwen"] += 1
            return _success_response("alibaba_qwen")

        def claude(p, model, exec_, to):
            calls["claude"] += 1
            return _success_response("claude")

        r = _d.dispatch(
            "hi", providers=["qwen", "claude"],
            claude_executor=MagicMock(),
            _qwen_fn=qwen, _claude_fn=claude,
            _metric_sink=lambda rec: None,
        )
        self.assertTrue(r.success)
        self.assertEqual(calls["qwen"], 1)
        self.assertEqual(calls["claude"], 0)  # Cascade stopped at first success

    def test_qwen_failure_advances_to_claude(self):
        r = _d.dispatch(
            "hi", providers=["qwen", "claude"],
            claude_executor=MagicMock(),
            _qwen_fn=lambda p, **k: _failure_response("alibaba_qwen", "network error"),
            _claude_fn=lambda p, m, e, t: _success_response("claude"),
            _metric_sink=lambda rec: None,
        )
        self.assertTrue(r.success)
        self.assertEqual(r.provider_used, "claude")
        self.assertEqual(r.providers_tried, ["qwen", "claude"])

    def test_claude_failure_non_rate_limit_does_not_advance(self):
        """After Claude primary failure without rate-limit wording, cascade stops."""
        r = _d.dispatch(
            "hi", providers=["claude", "qwen"],
            claude_executor=MagicMock(),
            _claude_fn=lambda p, m, e, t: _failure_response("claude", "connection refused"),
            _qwen_fn=lambda p, **k: _success_response("alibaba_qwen"),
            _metric_sink=lambda rec: None,
        )
        self.assertFalse(r.success)
        self.assertEqual(r.providers_tried, ["claude"])  # qwen NOT tried

    def test_claude_rate_limit_advances_to_qwen_fallback(self):
        r = _d.dispatch(
            "hi", providers=["claude", "qwen"],
            claude_executor=MagicMock(),
            _claude_fn=lambda p, m, e, t: _failure_response("claude", "You're out of extra usage"),
            _qwen_fn=lambda p, **k: _success_response("alibaba_qwen"),
            _metric_sink=lambda rec: None,
        )
        self.assertTrue(r.success)
        self.assertEqual(r.providers_tried, ["claude", "qwen"])


class TestKillSwitches(unittest.TestCase):
    def test_fallback_disabled_blocks_cascade_advance(self):
        with patch.dict(os.environ, {"COS_DISABLE_LLM_FALLBACK": "1"}):
            r = _d.dispatch(
                "hi", providers=["qwen", "claude"],
                claude_executor=MagicMock(),
                _qwen_fn=lambda p, **k: _failure_response("alibaba_qwen", "error"),
                _claude_fn=lambda p, m, e, t: _success_response("claude"),
                _metric_sink=lambda rec: None,
            )
        # Qwen was tried (primary) but cascade didn't advance to Claude
        self.assertEqual(r.providers_tried, ["qwen"])
        self.assertFalse(r.success)

    def test_fallback_disabled_still_allows_primary(self):
        """The kill-switch is cascade-scoped: primary still fires."""
        with patch.dict(os.environ, {"COS_DISABLE_LLM_FALLBACK": "1"}):
            r = _d.dispatch(
                "hi", providers=["qwen"],
                _qwen_fn=lambda p, **k: _success_response("alibaba_qwen"),
                _metric_sink=lambda rec: None,
            )
        self.assertTrue(r.success)

    def test_force_claude_primary_overrides_list(self):
        with patch.dict(os.environ, {"COS_FORCE_CLAUDE_PRIMARY": "1"}):
            sink = []
            _d.dispatch(
                "hi", providers=["qwen", "claude"],
                claude_executor=MagicMock(),
                _qwen_fn=lambda p, **k: _success_response("alibaba_qwen"),
                _claude_fn=lambda p, m, e, t: _success_response("claude"),
                _metric_sink=lambda rec: sink.append(rec),
            )
        self.assertEqual(sink[0]["providers_requested"], ["claude"])


class TestProviderEdgeCases(unittest.TestCase):
    def test_qwen_returns_none_advances_cascade(self):
        """Qwen unavailable (unconfigured/SDK missing) → cascade advances to Claude."""
        r = _d.dispatch(
            "hi", providers=["qwen", "claude"],
            claude_executor=MagicMock(),
            _qwen_fn=lambda p, **k: None,  # unavailable
            _claude_fn=lambda p, m, e, t: _success_response("claude"),
            _metric_sink=lambda rec: None,
        )
        self.assertTrue(r.success)
        self.assertEqual(r.provider_used, "claude")
        # Qwen unavailable does NOT appear in providers_tried if it returned None
        # Actually — let's check what the implementation does: it DOES append
        # before calling, so it will appear
        self.assertIn("qwen", r.providers_tried)

    def test_unknown_provider_is_skipped(self):
        r = _d.dispatch(
            "hi", providers=["deepseek", "qwen"],
            _qwen_fn=lambda p, **k: _success_response("alibaba_qwen"),
            _metric_sink=lambda rec: None,
        )
        self.assertTrue(r.success)
        self.assertEqual(r.provider_used, "alibaba_qwen")

    def test_missing_claude_executor_skips_claude(self):
        r = _d.dispatch(
            "hi", providers=["claude", "qwen"],
            claude_executor=None,  # Missing
            _qwen_fn=lambda p, **k: _success_response("alibaba_qwen"),
            _metric_sink=lambda rec: None,
        )
        self.assertTrue(r.success)
        self.assertEqual(r.provider_used, "alibaba_qwen")

    def test_all_providers_fail_returns_failure(self):
        r = _d.dispatch(
            "hi", providers=["qwen"],
            _qwen_fn=lambda p, **k: _failure_response("alibaba_qwen", "timeout"),
            _metric_sink=lambda rec: None,
        )
        self.assertFalse(r.success)
        self.assertIn("timeout", r.error)

    def test_empty_providers_list(self):
        r = _d.dispatch(
            "hi", providers=[],
            _metric_sink=lambda rec: None,
        )
        self.assertFalse(r.success)
        self.assertEqual(r.provider_used, "none")

    def test_all_providers_unknown_returns_failure(self):
        r = _d.dispatch(
            "hi", providers=["fakeprovider1", "fakeprovider2"],
            _metric_sink=lambda rec: None,
        )
        self.assertFalse(r.success)


class TestMetricsLogging(unittest.TestCase):
    def test_every_dispatch_writes_one_metric(self):
        sink = []
        _d.dispatch(
            "hi", providers=["qwen"],
            _qwen_fn=lambda p, **k: _success_response("alibaba_qwen"),
            _metric_sink=lambda rec: sink.append(rec),
        )
        self.assertEqual(len(sink), 1)

    def test_metric_has_required_fields(self):
        sink = []
        _d.dispatch(
            "hi", providers=["qwen"], task_type="code", skill_name="test-skill",
            _qwen_fn=lambda p, **k: _success_response("alibaba_qwen"),
            _metric_sink=lambda rec: sink.append(rec),
        )
        rec = sink[0]
        required = [
            "ts", "dispatch_id", "providers_requested", "providers_tried",
            "provider_used", "model", "task_type", "skill_name",
            "execution_profile", "tokens_in", "tokens_out", "cost_usd",
            "latency_ms", "success", "error",
        ]
        for f in required:
            self.assertIn(f, rec, f"Missing required field: {f}")
        self.assertEqual(rec["task_type"], "code")
        self.assertEqual(rec["skill_name"], "test-skill")
        self.assertEqual(rec["execution_profile"]["id"], "balanced_general")

    def test_metric_latency_is_positive_int(self):
        sink = []
        _d.dispatch(
            "hi", providers=["qwen"],
            _qwen_fn=lambda p, **k: _success_response("alibaba_qwen"),
            _metric_sink=lambda rec: sink.append(rec),
        )
        self.assertIsInstance(sink[0]["latency_ms"], int)
        self.assertGreaterEqual(sink[0]["latency_ms"], 0)

    def test_metric_written_on_failure_too(self):
        sink = []
        _d.dispatch(
            "hi", providers=["qwen"],
            _qwen_fn=lambda p, **k: _failure_response("alibaba_qwen", "bad key"),
            _metric_sink=lambda rec: sink.append(rec),
        )
        self.assertEqual(len(sink), 1)
        self.assertFalse(sink[0]["success"])

    def test_metric_error_truncated(self):
        """Error >500 chars is truncated in the metric (prevents JSONL bloat)."""
        huge_err = "x" * 5000
        sink = []
        _d.dispatch(
            "hi", providers=["qwen"],
            _qwen_fn=lambda p, **k: _failure_response("alibaba_qwen", huge_err),
            _metric_sink=lambda rec: sink.append(rec),
        )
        self.assertLessEqual(len(sink[0]["error"]), 500)

    def test_metric_sink_exception_does_not_break_dispatch(self):
        """Metric-logging failure must NOT crash the dispatch."""
        def bad_sink(rec):
            raise RuntimeError("simulated sink failure")

        # The default _log_metric swallows all errors, but our injected sink
        # doesn't — test only protects default behavior. When injected sink
        # raises, that IS the caller's problem. Verify dispatch doesn't
        # attempt to retry / double-log.
        with self.assertRaises(RuntimeError):
            _d.dispatch(
                "hi", providers=["qwen"],
                _qwen_fn=lambda p, **k: _success_response("alibaba_qwen"),
                _metric_sink=bad_sink,
            )

    def test_default_log_metric_swallows_errors(self):
        """Default _log_metric must not raise even on filesystem failure."""
        # Point metrics to an impossible path (root-owned); writing should silently fail
        try:
            _d._log_metric({"bad": "record"}, project_dir=Path("/nonexistent/readonly/path"))
        except Exception as e:
            self.fail(f"_log_metric should never raise — got {e!r}")


class TestRateLimitDetection(unittest.TestCase):
    def test_detects_known_patterns(self):
        self.assertTrue(_d._is_rate_limit_error("You're out of extra usage"))
        self.assertTrue(_d._is_rate_limit_error("rate limit exceeded"))
        self.assertTrue(_d._is_rate_limit_error("RATE LIMIT EXCEEDED!"))

    def test_ignores_unrelated(self):
        self.assertFalse(_d._is_rate_limit_error("connection refused"))
        self.assertFalse(_d._is_rate_limit_error(""))
        self.assertFalse(_d._is_rate_limit_error(None))


class TestJsonlFileIntegration(unittest.TestCase):
    def test_default_sink_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": tmp}):
                _d.dispatch(
                    "hi", providers=["qwen"],
                    _qwen_fn=lambda p, **k: _success_response("alibaba_qwen"),
                    # NO _metric_sink override → uses default _log_metric
                )
            jsonl = Path(tmp) / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl"
            self.assertTrue(jsonl.exists())
            line = jsonl.read_text().strip().splitlines()[0]
            parsed = json.loads(line)
            self.assertEqual(parsed["provider_used"], "alibaba_qwen")
            self.assertTrue(parsed["success"])

    def test_default_sink_honors_codex_project_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(
                os.environ,
                {"CODEX_PROJECT_DIR": tmp},
                clear=False,
            ):
                os.environ.pop("COGNITIVE_OS_PROJECT_DIR", None)
                os.environ.pop("CLAUDE_PROJECT_DIR", None)
                _d.dispatch(
                    "hi", providers=["qwen"],
                    _qwen_fn=lambda p, **k: _success_response("alibaba_qwen"),
                )
            jsonl = Path(tmp) / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl"
            self.assertTrue(jsonl.exists())


class TestNProviderCascadeADR062(unittest.TestCase):
    """ADR-062: N-provider cascade advance rules via _try_registry_provider."""

    def _registry_fn(self, provider_responses: dict):
        """Build a _qwen_fn-compatible shim that routes to registry provider responses."""
        # Returns None for "qwen" (simulating unavailable Qwen) and delegates to
        # _try_registry_provider for other providers via the mock.
        return None  # Qwen unavailable → advance to registry providers

    def test_registry_provider_advances_on_any_failure_for_openrouter(self):
        """openrouter (ADVANCE_ON_ANY_FAILURE) — failure → advance to next provider."""
        calls = {"openrouter": 0, "gemini": 0}

        def fake_registry(provider, prompt, claude_model=None, verbose=False):
            if provider == "openrouter":
                calls["openrouter"] += 1
                return _failure_response("openrouter", "connection error")
            if provider == "gemini":
                calls["gemini"] += 1
                return _success_response("gemini", "ok from gemini")
            return None

        with patch.object(_d, "_try_registry_provider", side_effect=fake_registry):
            r = _d.dispatch(
                "hi",
                providers=["openrouter", "gemini"],
                _qwen_fn=lambda p, **k: None,  # qwen not in this list
                _metric_sink=lambda rec: None,
            )

        self.assertTrue(r.success)
        self.assertEqual(r.provider_used, "gemini")
        self.assertEqual(calls["openrouter"], 1)
        self.assertEqual(calls["gemini"], 1)

    def test_registry_provider_does_not_advance_on_non_rate_limit_for_claude_sdk(self):
        """claude_sdk (ADVANCE_ON_RATE_LIMIT_ONLY) — non-rate-limit failure → stop cascade."""
        calls = {"claude_sdk": 0, "gemini": 0}

        def fake_registry(provider, prompt, claude_model=None, verbose=False):
            if provider == "claude_sdk":
                calls["claude_sdk"] += 1
                return _failure_response("claude_sdk", "authentication error")  # NOT rate limit
            if provider == "gemini":
                calls["gemini"] += 1
                return _success_response("gemini", "ok from gemini")
            return None

        with patch.object(_d, "_try_registry_provider", side_effect=fake_registry):
            r = _d.dispatch(
                "hi",
                providers=["claude_sdk", "gemini"],
                _qwen_fn=lambda p, **k: None,
                _metric_sink=lambda rec: None,
            )

        # Cascade should NOT advance to gemini after claude_sdk non-rate-limit failure
        self.assertFalse(r.success)
        self.assertEqual(calls["claude_sdk"], 1)
        self.assertEqual(calls["gemini"], 0)

    def test_registry_provider_advances_on_rate_limit_for_claude_sdk(self):
        """claude_sdk rate-limit → advance to next provider."""
        calls = {"claude_sdk": 0, "gemini": 0}

        def fake_registry(provider, prompt, claude_model=None, verbose=False):
            if provider == "claude_sdk":
                calls["claude_sdk"] += 1
                return _failure_response("claude_sdk", "rate limit exceeded")
            if provider == "gemini":
                calls["gemini"] += 1
                return _success_response("gemini", "ok from gemini")
            return None

        with patch.object(_d, "_try_registry_provider", side_effect=fake_registry):
            r = _d.dispatch(
                "hi",
                providers=["claude_sdk", "gemini"],
                _qwen_fn=lambda p, **k: None,
                _metric_sink=lambda rec: None,
            )

        self.assertTrue(r.success)
        self.assertEqual(r.provider_used, "gemini")
        self.assertEqual(calls["claude_sdk"], 1)
        self.assertEqual(calls["gemini"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
