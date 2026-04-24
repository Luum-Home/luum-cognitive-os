"""Behavioral tests for lib/observability.py.

ADR-058 (2026-04-24): the former remote-trace sink was retired.
These tests now cover:
- trace() returns an empty dict when no providers are enabled AND the
  Phoenix OTel bridge is not installed (pure noop).
- is_phoenix_available() returns True/False honestly based on whether
  ``phoenix.otel`` can be imported.
- _http_post() returns gracefully (0) on connection timeout / unreachable host.
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
    is_phoenix_available,
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
        """trace() must return {} when OPIK_ENABLED is unset and Phoenix is unavailable."""
        monkeypatch.delenv("OPIK_ENABLED", raising=False)

        # Force the Phoenix branch to report unavailable so this is a true noop.
        with patch("lib.observability.is_phoenix_available", return_value=False):
            result = trace(
                name="test-agent",
                start="2026-01-01T00:00:00Z",
                end="2026-01-01T00:01:00Z",
                metadata={"phase": "reconstruction"},
            )

        assert result == {}, (
            f"Expected empty dict when no providers enabled, got: {result}"
        )

    def test_trace_returns_dict_type(self, monkeypatch):
        """trace() always returns a dict, never None."""
        monkeypatch.delenv("OPIK_ENABLED", raising=False)

        with patch("lib.observability.is_phoenix_available", return_value=False):
            result = trace(
                name="noop",
                start="2026-01-01T00:00:00Z",
                end="2026-01-01T00:00:01Z",
                metadata={},
            )
        assert isinstance(result, dict)


class TestIsPhoenixAvailable:
    def test_returns_bool(self):
        """is_phoenix_available() always returns a bool based on import status."""
        result = is_phoenix_available()
        assert isinstance(result, bool)

    def test_returns_false_when_import_fails(self, monkeypatch):
        """When `phoenix.otel` import raises, the helper must report False."""
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "phoenix.otel" or name.startswith("phoenix"):
                raise ImportError("simulated: phoenix not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        assert is_phoenix_available() is False


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
