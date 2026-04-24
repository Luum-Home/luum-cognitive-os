"""Tests for lib/qwen_provider.py — Alibaba Qwen Coding Plan Pro dispatcher.

All network calls are mocked. Tests cover:
  - is_configured() reads env var
  - _get_openai_client() returns None when SDK missing or key absent
  - call() returns success result on mocked 200 response
  - call() returns error result (not raise) on SDK exception
  - call() preserves token counts from response
  - estimate_cost() math
  - select_model() task/vision/long-context heuristics
  - Config defaults (base URL, model)
"""
from __future__ import annotations

import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from lib import qwen_provider  # noqa: E402


class TestConfigDetection(unittest.TestCase):
    def test_is_configured_false_without_env(self):
        with patch.dict(os.environ, {"_COS_QWEN_DOTENV_LOADED": "1"}, clear=True):
            self.assertFalse(qwen_provider.is_configured())

    def test_is_configured_true_with_env(self):
        with patch.dict(os.environ, {"ALIBABA_QWEN_API_KEY": "sk-test"}):
            self.assertTrue(qwen_provider.is_configured())

    def test_is_configured_false_with_empty_env(self):
        with patch.dict(os.environ, {"ALIBABA_QWEN_API_KEY": ""}):
            self.assertFalse(qwen_provider.is_configured())


class TestClientFactory(unittest.TestCase):
    def test_client_none_when_sdk_missing(self):
        """If openai package is absent, _get_openai_client returns None."""
        # Simulate ImportError by temporarily hiding the module
        with patch.dict(sys.modules, {"openai": None}):
            with patch.dict(os.environ, {"ALIBABA_QWEN_API_KEY": "sk-test"}):
                # Inject an ImportError on `from openai import OpenAI`
                real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __import__
                def fake_import(name, *args, **kwargs):
                    if name == "openai":
                        raise ImportError("openai not installed (simulated)")
                    return real_import(name, *args, **kwargs)
                with patch("builtins.__import__", side_effect=fake_import):
                    client = qwen_provider._get_openai_client()
                    self.assertIsNone(client)

    def test_client_none_when_key_missing(self):
        """Even if openai SDK is present, no key → no client."""
        mock_openai = MagicMock()
        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch.dict(os.environ, {"_COS_QWEN_DOTENV_LOADED": "1"}, clear=True):
                client = qwen_provider._get_openai_client()
                self.assertIsNone(client)


class TestCallErrorPaths(unittest.TestCase):
    def test_call_returns_error_result_when_not_configured(self):
        with patch.dict(os.environ, {"_COS_QWEN_DOTENV_LOADED": "1"}, clear=True):
            result = qwen_provider.call([{"role": "user", "content": "hi"}])
            self.assertFalse(result.success)
            self.assertIn("ALIBABA_QWEN_API_KEY", result.error)

    def test_call_captures_sdk_exception_into_result(self):
        """SDK raises → call returns QwenResult(success=False, error=...) — does NOT raise."""
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = RuntimeError("upstream 503")

        with patch.dict(os.environ, {"ALIBABA_QWEN_API_KEY": "sk-test"}):
            with patch.object(qwen_provider, "_get_openai_client", return_value=fake_client):
                result = qwen_provider.call([{"role": "user", "content": "hi"}])
        self.assertFalse(result.success)
        self.assertIn("upstream 503", result.error)

    def test_call_handles_malformed_response_without_raising(self):
        """If response parsing fails, returns error result instead of crashing."""
        # Craft a response object whose attribute access raises
        bad_response = MagicMock()
        bad_response.choices = property(lambda self: (_ for _ in ()).throw(
            AttributeError("borked")
        ))
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = bad_response

        with patch.dict(os.environ, {"ALIBABA_QWEN_API_KEY": "sk-test"}):
            with patch.object(qwen_provider, "_get_openai_client", return_value=fake_client):
                result = qwen_provider.call([{"role": "user", "content": "hi"}])
        # Either parses to empty string (defensive getattr path) or returns error —
        # the important invariant is: does not raise.
        self.assertIsNotNone(result)


class TestCallSuccessPath(unittest.TestCase):
    def _build_response(self, content: str, tokens_in: int, tokens_out: int):
        msg = types.SimpleNamespace(content=content)
        choice = types.SimpleNamespace(message=msg)
        usage = types.SimpleNamespace(prompt_tokens=tokens_in, completion_tokens=tokens_out)
        return types.SimpleNamespace(choices=[choice], usage=usage)

    def test_call_returns_text_and_tokens(self):
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = self._build_response(
            content="hello from qwen", tokens_in=12, tokens_out=34,
        )
        with patch.dict(os.environ, {"ALIBABA_QWEN_API_KEY": "sk-test"}):
            with patch.object(qwen_provider, "_get_openai_client", return_value=fake_client):
                result = qwen_provider.call(
                    [{"role": "user", "content": "hi"}],
                    model="qwen3.6-plus",
                )
        self.assertTrue(result.success)
        self.assertEqual(result.text, "hello from qwen")
        self.assertEqual(result.tokens_in, 12)
        self.assertEqual(result.tokens_out, 34)
        self.assertEqual(result.model, "qwen3.6-plus")
        # Cost = 12 * 0.325/1M + 34 * 1.95/1M — non-zero, positive
        self.assertGreater(result.cost_usd, 0)

    def test_call_passes_max_tokens_and_temperature(self):
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = self._build_response("ok", 1, 1)

        with patch.dict(os.environ, {"ALIBABA_QWEN_API_KEY": "sk-test"}):
            with patch.object(qwen_provider, "_get_openai_client", return_value=fake_client):
                qwen_provider.call(
                    [{"role": "user", "content": "x"}],
                    model="qwen3.6-plus",
                    max_tokens=500,
                    temperature=0.2,
                )
        kwargs = fake_client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["max_tokens"], 500)
        self.assertEqual(kwargs["temperature"], 0.2)
        self.assertEqual(kwargs["model"], "qwen3.6-plus")


class TestEstimateCost(unittest.TestCase):
    def test_known_model(self):
        cost = qwen_provider.estimate_cost("qwen3.6-plus", tokens_in=1_000_000, tokens_out=0)
        # 1M input at $0.325/M = $0.325
        self.assertAlmostEqual(cost, 0.325, places=3)

    def test_known_model_output(self):
        cost = qwen_provider.estimate_cost("qwen3.6-plus", tokens_in=0, tokens_out=1_000_000)
        # 1M output at $1.95/M = $1.95
        self.assertAlmostEqual(cost, 1.95, places=3)

    def test_unknown_model_returns_zero(self):
        cost = qwen_provider.estimate_cost("nonexistent-model", 100, 100)
        self.assertEqual(cost, 0.0)


class TestSelectModel(unittest.TestCase):
    def test_long_context_picks_qwen36plus(self):
        m = qwen_provider.select_model(need_long_context=True)
        self.assertEqual(m, "qwen3.6-plus")

    def test_vision_picks_vision_capable(self):
        m = qwen_provider.select_model(need_vision=True)
        self.assertEqual(m, "qwen3.6-plus")
        self.assertTrue(qwen_provider.RECOMMENDED_MODELS[m]["vision"])

    def test_code_task_prefers_coder_model(self):
        m = qwen_provider.select_model(task="code")
        # Top preference for code tasks
        self.assertIn(m, {"qwen3-coder-plus", "qwen3-coder-next", "qwen3.6-plus"})

    def test_bulk_task_picks_cheap_model(self):
        m = qwen_provider.select_model(task="bulk")
        self.assertEqual(m, "minimax-m2.5")

    def test_unknown_task_falls_back_to_general(self):
        m = qwen_provider.select_model(task="nonsense")
        self.assertEqual(m, "qwen3.6-plus")


class TestClaudeToQwenMapping(unittest.TestCase):
    """ADR-049: when the skill declares a Claude model tier, fallback must
    honor that tier by mapping to the best Qwen bundle equivalent."""

    def test_opus_maps_to_qwen36plus(self):
        self.assertEqual(qwen_provider.map_claude_model_to_qwen("opus"), "qwen3.6-plus")

    def test_sonnet_maps_to_qwen3_coder_plus(self):
        self.assertEqual(qwen_provider.map_claude_model_to_qwen("sonnet"), "qwen3-coder-plus")

    def test_haiku_maps_to_qwen3_coder_plus(self):
        # minimax-m2.5 is not callable on the current Coding Plan Pro subscription;
        # remapped to qwen3-coder-plus until Alibaba enables it. See CLAUDE_TO_QWEN_MAP note.
        self.assertEqual(qwen_provider.map_claude_model_to_qwen("haiku"), "qwen3-coder-plus")

    def test_full_claude_name_opus(self):
        self.assertEqual(qwen_provider.map_claude_model_to_qwen("claude-opus-4-7"), "qwen3.6-plus")

    def test_full_claude_name_sonnet(self):
        self.assertEqual(qwen_provider.map_claude_model_to_qwen("claude-sonnet-4-6"), "qwen3-coder-plus")

    def test_full_claude_name_haiku(self):
        self.assertEqual(qwen_provider.map_claude_model_to_qwen("claude-haiku-4-5-20251001"), "qwen3-coder-plus")

    def test_case_insensitive(self):
        self.assertEqual(qwen_provider.map_claude_model_to_qwen("OPUS"), "qwen3.6-plus")
        self.assertEqual(qwen_provider.map_claude_model_to_qwen("Claude-Sonnet-4"), "qwen3-coder-plus")

    def test_none_returns_default(self):
        self.assertEqual(qwen_provider.map_claude_model_to_qwen(None), qwen_provider.DEFAULT_MODEL)

    def test_empty_string_returns_default(self):
        self.assertEqual(qwen_provider.map_claude_model_to_qwen(""), qwen_provider.DEFAULT_MODEL)

    def test_unknown_tier_returns_default(self):
        self.assertEqual(qwen_provider.map_claude_model_to_qwen("gpt-5"), qwen_provider.DEFAULT_MODEL)

    def test_mapped_models_exist_in_bundle(self):
        """Every mapped Qwen model MUST be in RECOMMENDED_MODELS bundle —
        otherwise we'd dispatch to a model not available under subscription."""
        for claude_tier, qwen_model in qwen_provider.CLAUDE_TO_QWEN_MAP.items():
            self.assertIn(
                qwen_model,
                qwen_provider.RECOMMENDED_MODELS,
                f"{claude_tier} maps to {qwen_model} which is NOT in RECOMMENDED_MODELS",
            )

    def test_select_model_respects_claude_hint(self):
        """select_model with claude_model_hint overrides task-based heuristic."""
        # Without hint: general task → qwen3.6-plus
        self.assertEqual(qwen_provider.select_model(task="general"), "qwen3.6-plus")
        # With hint=haiku: should flip to qwen3-coder-plus regardless of task
        # (minimax-m2.5 is not callable on current plan — remapped to qwen3-coder-plus)
        self.assertEqual(
            qwen_provider.select_model(task="general", claude_model_hint="haiku"),
            "qwen3-coder-plus",
        )
        # With hint=sonnet + code task: sonnet mapping wins
        self.assertEqual(
            qwen_provider.select_model(task="code", claude_model_hint="sonnet"),
            "qwen3-coder-plus",
        )

    def test_haiku_remap_callable_model(self):
        """haiku must map to a model present in RECOMMENDED_MODELS (i.e. callable).
        This test encodes the fix for the minimax-m2.5 live-call failure (2026-04-21).
        When/if minimax-m2.5 becomes callable, update CLAUDE_TO_QWEN_MAP["haiku"]
        and this assertion accordingly."""
        haiku_model = qwen_provider.map_claude_model_to_qwen("haiku")
        self.assertEqual(haiku_model, "qwen3-coder-plus",
                         "haiku should map to qwen3-coder-plus until minimax-m2.5 is callable")
        # Ensure the mapped model is actually in the subscription bundle
        self.assertIn(haiku_model, qwen_provider.RECOMMENDED_MODELS,
                      f"haiku mapping '{haiku_model}' is not in RECOMMENDED_MODELS bundle")

    def test_select_model_long_context_overrides_hint(self):
        """need_long_context is a hard requirement — overrides even claude_model_hint."""
        self.assertEqual(
            qwen_provider.select_model(need_long_context=True, claude_model_hint="haiku"),
            "qwen3.6-plus",
        )

    def test_select_model_vision_overrides_hint(self):
        """need_vision is a hard requirement — overrides claude_model_hint."""
        m = qwen_provider.select_model(need_vision=True, claude_model_hint="haiku")
        self.assertTrue(qwen_provider.RECOMMENDED_MODELS[m]["vision"])


class TestConfigDefaults(unittest.TestCase):
    def test_default_base_url_points_to_alibaba(self):
        self.assertIn("aliyuncs.com", qwen_provider.DEFAULT_BASE_URL)
        self.assertIn("compatible-mode", qwen_provider.DEFAULT_BASE_URL)

    def test_default_model_is_qwen36plus(self):
        self.assertEqual(qwen_provider.DEFAULT_MODEL, "qwen3.6-plus")

    def test_recommended_models_nonempty(self):
        self.assertGreater(len(qwen_provider.RECOMMENDED_MODELS), 5)
        # All values have required keys
        for model, caps in qwen_provider.RECOMMENDED_MODELS.items():
            self.assertIn("vision", caps)
            self.assertIn("context", caps)
            self.assertIn("role", caps)


if __name__ == "__main__":
    unittest.main(verbosity=2)
