"""Unit tests for lib/bifrost_client.py

Validates Bifrost client configuration, model routing decisions,
health checking, and chat completion with mocked HTTP responses.
"""

import json
import os
from http.server import BaseHTTPRequestHandler
from unittest.mock import MagicMock, patch

import pytest

from lib.bifrost_client import (
    BIFROST_EXCLUDED_MODELS,
    BIFROST_PROVIDERS,
    MODEL_TO_BIFROST,
    BifrostClient,
    BifrostError,
    BifrostUnavailable,
    get_bifrost_model_name,
    is_bifrost_available,
    is_bifrost_enabled,
    is_model_bifrost_routable,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# is_bifrost_enabled
# ---------------------------------------------------------------------------


class TestIsBifrostEnabled:
    """Tests for is_bifrost_enabled()."""

    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove BIFROST_ENABLED if set
            os.environ.pop("BIFROST_ENABLED", None)
            assert is_bifrost_enabled() is False

    def test_enabled_true(self):
        with patch.dict(os.environ, {"BIFROST_ENABLED": "true"}):
            assert is_bifrost_enabled() is True

    def test_enabled_1(self):
        with patch.dict(os.environ, {"BIFROST_ENABLED": "1"}):
            assert is_bifrost_enabled() is True

    def test_enabled_yes(self):
        with patch.dict(os.environ, {"BIFROST_ENABLED": "yes"}):
            assert is_bifrost_enabled() is True

    def test_disabled_false(self):
        with patch.dict(os.environ, {"BIFROST_ENABLED": "false"}):
            assert is_bifrost_enabled() is False

    def test_disabled_random_string(self):
        with patch.dict(os.environ, {"BIFROST_ENABLED": "maybe"}):
            assert is_bifrost_enabled() is False

    def test_case_insensitive(self):
        with patch.dict(os.environ, {"BIFROST_ENABLED": "TRUE"}):
            assert is_bifrost_enabled() is True


# ---------------------------------------------------------------------------
# is_model_bifrost_routable
# ---------------------------------------------------------------------------


class TestIsModelBifrostRoutable:
    """Tests for is_model_bifrost_routable()."""

    def test_claude_models_excluded(self):
        assert is_model_bifrost_routable("claude-opus-4-6") is False
        assert is_model_bifrost_routable("claude-sonnet-4") is False
        assert is_model_bifrost_routable("claude-haiku-3.5") is False

    def test_claude_catchall(self):
        assert is_model_bifrost_routable("claude-anything-new") is False

    def test_openrouter_excluded(self):
        assert is_model_bifrost_routable("openrouter/free") is False
        assert is_model_bifrost_routable("qwen/qwen3-32b:free") is False

    def test_local_models_excluded(self):
        assert is_model_bifrost_routable("llama-3-70b") is False
        assert is_model_bifrost_routable("qwen-3-32b") is False

    def test_gpt4o_routable(self):
        assert is_model_bifrost_routable("gpt-4o") is True

    def test_gemini_routable(self):
        assert is_model_bifrost_routable("gemini-2.5-pro") is True

    def test_deepseek_routable(self):
        assert is_model_bifrost_routable("deepseek-r1") is True

    def test_provider_prefixed_routable(self):
        assert is_model_bifrost_routable("openai/gpt-4o-mini") is True
        assert is_model_bifrost_routable("groq/llama-3-70b") is True
        assert is_model_bifrost_routable("mistral/mistral-large") is True

    def test_provider_prefixed_claude_still_excluded(self):
        """Even with provider prefix, Claude models are excluded from Bifrost."""
        assert is_model_bifrost_routable("anthropic/claude-3-sonnet") is False

    def test_unknown_provider_prefixed_not_routable(self):
        assert is_model_bifrost_routable("unknownprovider/some-model") is False

    def test_all_excluded_models_are_not_routable(self):
        for model in BIFROST_EXCLUDED_MODELS:
            assert is_model_bifrost_routable(model) is False, f"{model} should not be routable"


# ---------------------------------------------------------------------------
# get_bifrost_model_name
# ---------------------------------------------------------------------------


class TestGetBifrostModelName:
    """Tests for get_bifrost_model_name()."""

    def test_known_mapping(self):
        assert get_bifrost_model_name("gpt-4o") == "openai/gpt-4o"

    def test_gemini_mapping(self):
        assert get_bifrost_model_name("gemini-2.5-pro") == "gemini/gemini-2.5-pro"

    def test_deepseek_mapping(self):
        assert get_bifrost_model_name("deepseek-r1") == "deepseek/deepseek-r1"

    def test_already_prefixed_passthrough(self):
        assert get_bifrost_model_name("openai/gpt-4o-mini") == "openai/gpt-4o-mini"

    def test_unknown_model_raises(self):
        with pytest.raises(ValueError, match="No Bifrost mapping"):
            get_bifrost_model_name("unknown-model-without-prefix")

    def test_all_mappings_have_provider_prefix(self):
        for flat_name, prefixed in MODEL_TO_BIFROST.items():
            assert "/" in prefixed, f"Mapping {flat_name} -> {prefixed} missing provider prefix"


# ---------------------------------------------------------------------------
# is_bifrost_available (mocked)
# ---------------------------------------------------------------------------


class TestIsBifrostAvailable:
    """Tests for is_bifrost_available() with mocked HTTP."""

    @patch("lib.bifrost_client.urlopen")
    def test_available_on_200(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        assert is_bifrost_available(url="http://fake:8081") is True

    @patch("lib.bifrost_client.urlopen")
    def test_unavailable_on_connection_error(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection refused")
        assert is_bifrost_available(url="http://fake:8081") is False

    @patch("lib.bifrost_client.urlopen")
    def test_unavailable_on_timeout(self, mock_urlopen):
        mock_urlopen.side_effect = OSError("timed out")
        assert is_bifrost_available(url="http://fake:8081") is False


# ---------------------------------------------------------------------------
# BifrostClient
# ---------------------------------------------------------------------------


class TestBifrostClient:
    """Tests for BifrostClient class."""

    def test_default_url(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BIFROST_URL", None)
            client = BifrostClient()
            assert "localhost" in client.base_url
            assert "8081" in client.base_url

    def test_custom_url(self):
        client = BifrostClient(base_url="http://custom:9999")
        assert client.base_url == "http://custom:9999"

    def test_env_url(self):
        with patch.dict(os.environ, {"BIFROST_URL": "http://env-host:7777"}):
            client = BifrostClient()
            assert client.base_url == "http://env-host:7777"

    @patch("lib.bifrost_client.urlopen")
    def test_chat_completion_success(self, mock_urlopen):
        response_data = {
            "choices": [{"message": {"content": "Hello from Bifrost"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client = BifrostClient(base_url="http://fake:8081")
        result = client.chat_completion(
            "openai/gpt-4o",
            [{"role": "user", "content": "Hi"}],
        )
        assert result["choices"][0]["message"]["content"] == "Hello from Bifrost"
        assert result["usage"]["prompt_tokens"] == 10

    @patch("lib.bifrost_client.urlopen")
    def test_chat_completion_connection_error(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection refused")

        client = BifrostClient(base_url="http://fake:8081")
        with pytest.raises(BifrostUnavailable):
            client.chat_completion(
                "openai/gpt-4o",
                [{"role": "user", "content": "Hi"}],
            )

    @patch("lib.bifrost_client.urlopen")
    def test_health_check_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"{}"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client = BifrostClient(base_url="http://fake:8081")
        assert client.health_check() is True

    @patch("lib.bifrost_client.urlopen")
    def test_health_check_failure(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection refused")

        client = BifrostClient(base_url="http://fake:8081")
        assert client.health_check() is False


# ---------------------------------------------------------------------------
# Provider coverage
# ---------------------------------------------------------------------------


class TestProviderCoverage:
    """Verify provider and model mapping consistency."""

    def test_bifrost_providers_nonempty(self):
        assert len(BIFROST_PROVIDERS) >= 5

    def test_model_mapping_covers_common_models(self):
        expected = {"gpt-4o", "gemini-2.5-pro", "deepseek-r1"}
        assert expected.issubset(set(MODEL_TO_BIFROST.keys()))

    def test_excluded_models_include_claude(self):
        claude_excluded = [m for m in BIFROST_EXCLUDED_MODELS if "claude" in m]
        assert len(claude_excluded) >= 3

    def test_excluded_models_include_openrouter(self):
        openrouter_excluded = [m for m in BIFROST_EXCLUDED_MODELS if "free" in m or "openrouter" in m]
        assert len(openrouter_excluded) >= 1
