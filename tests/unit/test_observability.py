"""Behavioral tests for lib/observability.py.

Covers:
- trace() returns an empty dict when both providers are disabled (noop)
- is_langfuse_available() returns False when LANGFUSE_ENABLED is unset
- _http_post() returns gracefully (0) on connection timeout / unreachable host
"""

import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error

import pytest

# Ensure repo root is on the path so `lib.observability` is importable
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib.observability import (
    trace,
    is_langfuse_available,
    _http_post,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_env(*keys: str) -> dict:
    """Return os.environ copy with the given keys removed."""
    env = os.environ.copy()
    for k in keys:
        env.pop(k, None)
    return env


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTraceBothDisabled:
    def test_trace_both_disabled_is_noop(self, monkeypatch):
        """trace() must return {} when LANGFUSE_ENABLED and OPIK_ENABLED are unset."""
        monkeypatch.delenv("LANGFUSE_ENABLED", raising=False)
        monkeypatch.delenv("OPIK_ENABLED", raising=False)

        result = trace(
            name="test-agent",
            start="2026-01-01T00:00:00Z",
            end="2026-01-01T00:01:00Z",
            metadata={"phase": "reconstruction"},
        )

        assert result == {}, (
            f"Expected empty dict when both providers disabled, got: {result}"
        )

    def test_trace_returns_dict_type(self, monkeypatch):
        """trace() always returns a dict, never None."""
        monkeypatch.delenv("LANGFUSE_ENABLED", raising=False)
        monkeypatch.delenv("OPIK_ENABLED", raising=False)

        result = trace(
            name="noop",
            start="2026-01-01T00:00:00Z",
            end="2026-01-01T00:00:01Z",
            metadata={},
        )
        assert isinstance(result, dict)


class TestIsLangfuseAvailable:
    def test_is_langfuse_available_false_when_env_unset(self, monkeypatch):
        """is_langfuse_available() must return False when LANGFUSE_ENABLED is not set."""
        monkeypatch.delenv("LANGFUSE_ENABLED", raising=False)

        assert is_langfuse_available() is False, (
            "Expected False when LANGFUSE_ENABLED is not in environment"
        )

    def test_is_langfuse_available_false_when_set_to_false(self, monkeypatch):
        """is_langfuse_available() must return False when LANGFUSE_ENABLED=false."""
        monkeypatch.setenv("LANGFUSE_ENABLED", "false")

        assert is_langfuse_available() is False

    def test_is_langfuse_available_false_when_enabled_but_unreachable(self, monkeypatch):
        """is_langfuse_available() returns False when LANGFUSE_ENABLED=true but host is down."""
        monkeypatch.setenv("LANGFUSE_ENABLED", "true")
        monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:19999")  # nothing listening

        # Should return False, not raise
        result = is_langfuse_available()
        assert result is False, (
            "Expected False when host is unreachable, got True"
        )


class TestHttpPostTimeout:
    def test_http_post_timeout_returns_gracefully(self):
        """_http_post() must return 0 (not raise) when the server is unreachable."""
        # Use a port that is almost certainly not listening
        result = _http_post(
            url="http://localhost:19998/nonexistent",
            payload={"test": True},
        )

        assert result == 0, (
            f"Expected 0 on connection failure, got {result}"
        )

    def test_http_post_urlerror_returns_zero(self, monkeypatch):
        """_http_post() must return 0 when urllib raises URLError."""
        import urllib.request

        def _raise(*args, **kwargs):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", _raise)

        result = _http_post(
            url="http://localhost:9/fake",
            payload={"x": 1},
        )
        assert result == 0

    def test_http_post_httperror_returns_status_code(self, monkeypatch):
        """_http_post() must return the HTTP error code (e.g. 401) on HTTPError."""
        import urllib.request

        def _raise(*args, **kwargs):
            raise urllib.error.HTTPError(
                url="http://example.com",
                code=401,
                msg="Unauthorized",
                hdrs=None,  # type: ignore[arg-type]
                fp=None,
            )

        monkeypatch.setattr(urllib.request, "urlopen", _raise)

        result = _http_post(
            url="http://example.com/api",
            payload={"y": 2},
        )
        assert result == 401
