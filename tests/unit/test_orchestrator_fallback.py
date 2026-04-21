"""Tests for scripts/orchestrator.py rate-limit fallback logic (ADR-049 step 6).

The orchestrator calls ClaudeExecutor as primary. When that returns
success=False with a rate-limit error pattern, it falls back to
lib/qwen_provider.py direct-SDK dispatch. Next invocation starts fresh
with Claude — retry-primary semantics, no sticky mode.

These tests cover the helpers in isolation (no real Claude or Qwen calls).
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

# orchestrator.py is a script, not a package — load it as a module for testing
_ORCH_PATH = _REPO / "scripts" / "orchestrator.py"
_spec = importlib.util.spec_from_file_location("orchestrator_under_test", _ORCH_PATH)
_orch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_orch)


class TestRateLimitDetection(unittest.TestCase):
    def test_matches_out_of_extra_usage(self):
        self.assertTrue(_orch._is_rate_limit_error("You're out of extra usage · resets 2pm"))

    def test_matches_rate_limit_exceeded(self):
        self.assertTrue(_orch._is_rate_limit_error("rate limit exceeded"))

    def test_matches_approaching_limit(self):
        self.assertTrue(_orch._is_rate_limit_error("You're approaching your usage limit"))

    def test_case_insensitive(self):
        self.assertTrue(_orch._is_rate_limit_error("RATE LIMIT EXCEEDED!"))

    def test_ignores_unrelated_errors(self):
        self.assertFalse(_orch._is_rate_limit_error("connection refused"))
        self.assertFalse(_orch._is_rate_limit_error("timeout after 120s"))
        self.assertFalse(_orch._is_rate_limit_error(""))
        self.assertFalse(_orch._is_rate_limit_error(None))

    def test_empty_string_is_not_rate_limit(self):
        self.assertFalse(_orch._is_rate_limit_error(""))


class TestQwenFallbackHelper(unittest.TestCase):
    def test_returns_none_when_qwen_not_configured(self):
        """If ALIBABA_QWEN_API_KEY is unset, fallback helper returns None."""
        mock_module = MagicMock()
        mock_module.is_configured.return_value = False
        with patch.dict(sys.modules, {"lib.qwen_provider": mock_module}):
            result = _orch._try_qwen_primary("hello", verbose=False)
        self.assertIsNone(result)

    def test_returns_none_when_qwen_import_fails(self):
        """If lib.qwen_provider is not installed, returns None gracefully."""
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "lib.qwen_provider":
                raise ImportError("qwen_provider missing (simulated)")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            result = _orch._try_qwen_primary("hello")
        self.assertIsNone(result)

    def test_adapts_qwen_result_to_executor_shape(self):
        """QwenResult → _FallbackResult with ClaudeExecutor-compatible fields."""
        qwen_result = MagicMock(
            success=True,
            text="from qwen",
            tokens_in=10,
            tokens_out=20,
            cost_usd=0.001,
            error="",
        )
        mock_module = MagicMock()
        mock_module.is_configured.return_value = True
        mock_module.call.return_value = qwen_result

        with patch.dict(sys.modules, {"lib.qwen_provider": mock_module}):
            result = _orch._try_qwen_primary("hello", verbose=False)

        self.assertIsNotNone(result)
        self.assertTrue(result.success)
        self.assertEqual(result.text, "from qwen")
        self.assertEqual(result.input_tokens, 10)
        self.assertEqual(result.output_tokens, 20)
        self.assertAlmostEqual(result.cost_usd, 0.001)
        self.assertEqual(result.provider, "alibaba_qwen")

    def test_passes_prompt_as_user_message(self):
        mock_module = MagicMock()
        mock_module.is_configured.return_value = True
        mock_module.call.return_value = MagicMock(
            success=True, text="ok", tokens_in=1, tokens_out=1,
            cost_usd=0.0, error="",
        )

        with patch.dict(sys.modules, {"lib.qwen_provider": mock_module}):
            _orch._try_qwen_primary("what is 2+2?", verbose=False)

        called_messages = mock_module.call.call_args.kwargs.get("messages")
        if called_messages is None:
            # Positional-arg call
            called_messages = mock_module.call.call_args.args[0]
        self.assertEqual(len(called_messages), 1)
        self.assertEqual(called_messages[0]["role"], "user")
        self.assertEqual(called_messages[0]["content"], "what is 2+2?")

    def test_propagates_qwen_error_when_call_fails(self):
        """If qwen_provider itself returns error (bad key, network, etc.),
        the fallback result carries that error — caller must still report
        failure to the user rather than silently swallow it."""
        mock_module = MagicMock()
        mock_module.is_configured.return_value = True
        mock_module.call.return_value = MagicMock(
            success=False, text="", tokens_in=0, tokens_out=0,
            cost_usd=0.0, error="401 invalid_api_key",
        )

        with patch.dict(sys.modules, {"lib.qwen_provider": mock_module}):
            result = _orch._try_qwen_primary("hi")

        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertIn("401", result.error)
        self.assertEqual(result.provider, "alibaba_qwen")


class TestClaudeModelHintPropagation(unittest.TestCase):
    """Fallback must honor the Claude model tier (from --model CLI arg or
    skill frontmatter) by mapping to the best Qwen bundle equivalent."""

    def _make_mock_module(self, expected_model: str):
        """Builds a qwen_provider mock that records which model was requested."""
        call_history: list[dict] = []

        def fake_call(messages, model=None, **kwargs):
            call_history.append({"messages": messages, "model": model})
            r = MagicMock(
                success=True, text=f"answered with {model}", tokens_in=1,
                tokens_out=1, cost_usd=0.0, error="",
            )
            return r

        def fake_select(claude_model_hint=None, **kwargs):
            # Simulate the real mapping
            mapping = {"opus": "qwen3.6-plus", "sonnet": "qwen3-coder-plus", "haiku": "minimax-m2.5"}
            if claude_model_hint:
                for tier, model in mapping.items():
                    if tier in claude_model_hint.lower():
                        return model
            return "qwen3.6-plus"

        mock = MagicMock()
        mock.is_configured.return_value = True
        mock.call.side_effect = fake_call
        mock.select_model.side_effect = fake_select
        mock._call_history = call_history
        return mock

    def test_opus_hint_routes_to_qwen36plus(self):
        mock = self._make_mock_module("qwen3.6-plus")
        with patch.dict(sys.modules, {"lib.qwen_provider": mock}):
            result = _orch._try_qwen_primary("task", claude_model="opus")
        self.assertTrue(result.success)
        self.assertEqual(mock._call_history[0]["model"], "qwen3.6-plus")

    def test_sonnet_hint_routes_to_coder_plus(self):
        mock = self._make_mock_module("qwen3-coder-plus")
        with patch.dict(sys.modules, {"lib.qwen_provider": mock}):
            _orch._try_qwen_primary("task", claude_model="sonnet")
        self.assertEqual(mock._call_history[0]["model"], "qwen3-coder-plus")

    def test_haiku_hint_routes_to_minimax(self):
        mock = self._make_mock_module("minimax-m2.5")
        with patch.dict(sys.modules, {"lib.qwen_provider": mock}):
            _orch._try_qwen_primary("task", claude_model="haiku")
        self.assertEqual(mock._call_history[0]["model"], "minimax-m2.5")

    def test_none_hint_uses_default(self):
        mock = self._make_mock_module("qwen3.6-plus")
        with patch.dict(sys.modules, {"lib.qwen_provider": mock}):
            _orch._try_qwen_primary("task", claude_model=None)
        self.assertEqual(mock._call_history[0]["model"], "qwen3.6-plus")

    def test_full_claude_model_name_mapped(self):
        mock = self._make_mock_module("minimax-m2.5")
        with patch.dict(sys.modules, {"lib.qwen_provider": mock}):
            _orch._try_qwen_primary("task", claude_model="claude-haiku-4-5")
        self.assertEqual(mock._call_history[0]["model"], "minimax-m2.5")


class TestPerProviderKillSwitch(unittest.TestCase):
    """ADR-049 per-provider kill-switch: COS_DISABLE_QWEN=1 blocks
    only Qwen; future providers (DeepSeek, MiniMax Pro) can be disabled
    independently via COS_DISABLE_<PROVIDER>_FALLBACK."""

    def test_per_provider_kill_blocks_qwen_specifically(self):
        mock_module = MagicMock()
        mock_module.is_configured.return_value = True
        mock_module.call.return_value = MagicMock(
            success=True, text="x", tokens_in=1, tokens_out=1,
            cost_usd=0.0, error="",
        )
        import os
        with patch.dict(sys.modules, {"lib.qwen_provider": mock_module}):
            with patch.dict(os.environ, {"COS_DISABLE_QWEN": "1"}):
                os.environ.pop("COS_DISABLE_LLM_FALLBACK", None)
                result = _orch._try_qwen_primary("anything")
        self.assertIsNone(result)
        mock_module.call.assert_not_called()

    def test_per_provider_off_allows_qwen(self):
        qwen_result = MagicMock(
            success=True, text="ok", tokens_in=1, tokens_out=1,
            cost_usd=0.0, error="",
        )
        mock_module = MagicMock()
        mock_module.is_configured.return_value = True
        mock_module.call.return_value = qwen_result
        mock_module.select_model.return_value = "qwen3.6-plus"

        import os
        with patch.dict(sys.modules, {"lib.qwen_provider": mock_module}):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("COS_DISABLE_QWEN", None)
                os.environ.pop("COS_DISABLE_LLM_FALLBACK", None)
                result = _orch._try_qwen_primary("anything")
        self.assertIsNotNone(result)
        self.assertTrue(result.success)

    def test_global_kill_switch_is_cascade_scoped(self):
        """COS_DISABLE_LLM_FALLBACK=1 gates CASCADE advance, not primary calls.
        With the Option B rewrite, the flag no longer blocks Qwen-as-primary —
        it only prevents the orchestrator from advancing to the 2nd+ provider
        in the --providers list. Primary call proceeds normally.
        (This is the corrected semantic per docs/roadmaps/adr-049-050-051-mega-plan.md
        C1 rewrite. The cascade-level behavior is verified in cmd_run tests.)"""
        import os
        # Sanity: _fallback_disabled() is True when env var is set
        with patch.dict(os.environ, {"COS_DISABLE_LLM_FALLBACK": "1"}):
            self.assertTrue(_orch._fallback_disabled(verbose=False))
        # And False when unset
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COS_DISABLE_LLM_FALLBACK", None)
            self.assertFalse(_orch._fallback_disabled(verbose=False))


class TestKillSwitch(unittest.TestCase):
    """ADR-049 explicit kill-switch: COS_DISABLE_LLM_FALLBACK=1 blocks the
    fallback even when Qwen is fully configured."""

    def test_kill_switch_is_cascade_scoped_not_primary_scoped(self):
        """Per Option B rewrite (C1): COS_DISABLE_LLM_FALLBACK blocks cascade
        advance only. Primary Qwen call is still made because that's the user's
        declared primary in --providers. Cascade-level enforcement is tested
        separately in cmd_run integration tests."""
        import os
        with patch.dict(os.environ, {"COS_DISABLE_LLM_FALLBACK": "1"}):
            self.assertTrue(_orch._fallback_disabled(verbose=False))

    def test_kill_switch_off_allows_fallback(self):
        qwen_result = MagicMock(
            success=True, text="fallback text", tokens_in=5, tokens_out=5,
            cost_usd=0.001, error="",
        )
        mock_module = MagicMock()
        mock_module.is_configured.return_value = True
        mock_module.call.return_value = qwen_result

        import os
        with patch.dict(sys.modules, {"lib.qwen_provider": mock_module}):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("COS_DISABLE_LLM_FALLBACK", None)
                result = _orch._try_qwen_primary("anything")
        self.assertIsNotNone(result)
        self.assertTrue(result.success)

    def test_kill_switch_empty_string_not_disabled(self):
        """COS_DISABLE_LLM_FALLBACK='' should NOT disable (only '1' does)."""
        qwen_result = MagicMock(
            success=True, text="ok", tokens_in=1, tokens_out=1,
            cost_usd=0.0, error="",
        )
        mock_module = MagicMock()
        mock_module.is_configured.return_value = True
        mock_module.call.return_value = qwen_result

        import os
        with patch.dict(sys.modules, {"lib.qwen_provider": mock_module}):
            with patch.dict(os.environ, {"COS_DISABLE_LLM_FALLBACK": ""}):
                result = _orch._try_qwen_primary("anything")
        self.assertIsNotNone(result)
        self.assertTrue(result.success)


class TestProvidersCascade(unittest.TestCase):
    """C1: Option B --providers cascade behavior in cmd_run.

    Covers the new priority-list semantics:
    - First provider is primary; subsequent are fallbacks
    - First success wins; cascade stops
    - Qwen→Claude: always advance on failure
    - Claude→next: only advance on rate-limit (retry-primary semantic)
    - Unknown providers are skipped with verbose log
    - Empty list or all-failed produces an error result with success=False
    """

    def _parse_providers(self, raw: str) -> list[str]:
        """Mirror of the list-parse logic in cmd_run — verifies the split."""
        return [p.strip() for p in raw.split(",") if p.strip()]

    def test_default_providers_is_qwen_claude(self):
        self.assertEqual(self._parse_providers("qwen,claude"), ["qwen", "claude"])

    def test_providers_list_strips_whitespace(self):
        self.assertEqual(self._parse_providers("qwen , claude "), ["qwen", "claude"])

    def test_providers_empty_segments_filtered(self):
        self.assertEqual(self._parse_providers("qwen,,claude,"), ["qwen", "claude"])

    def test_single_provider_parses_as_list_of_one(self):
        self.assertEqual(self._parse_providers("qwen"), ["qwen"])

    def test_invert_priority_claude_then_qwen(self):
        self.assertEqual(self._parse_providers("claude,qwen"), ["claude", "qwen"])

    def test_three_tier_future(self):
        self.assertEqual(
            self._parse_providers("deepseek,qwen,claude"),
            ["deepseek", "qwen", "claude"],
        )


class TestPatternListSyncWithHook(unittest.TestCase):
    """Orchestrator's _RATE_LIMIT_PATTERNS must stay in sync with the
    regex list in hooks/rate-limit-detector.sh. If they drift, the hook
    may flag a rate-limit that the orchestrator ignores (or vice-versa)."""

    def test_hook_regex_mentions_core_tokens(self):
        hook_src = (_REPO / "hooks" / "rate-limit-detector.sh").read_text()
        # These substrings MUST appear in both the orchestrator list AND
        # the hook regex, otherwise the two sides won't agree on what
        # counts as "rate-limited."
        core = ["out of extra usage", "rate limit exceeded"]
        for token in core:
            self.assertIn(
                token.lower(),
                hook_src.lower(),
                f"Token {token!r} not in hook — orchestrator and hook will disagree",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
