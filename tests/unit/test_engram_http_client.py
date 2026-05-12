"""Unit tests for lib.engram_http_client — HTTP wrapper for the engram REST API.

All tests mock the HTTP transport layer so no real daemon is required.
Covers both the requests-backed and urllib-backed code paths.

ADR reference: docs/02-Decisions/adrs/ADR-071-engram-lifecycle-evolution.md (addendum 2026-04-27)
"""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE = "http://127.0.0.1:7437"


def _json_bytes(obj) -> bytes:
    return json.dumps(obj).encode("utf-8")


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------


class TestIsAvailable:
    def test_returns_true_on_200(self):
        from lib import engram_http_client

        with patch.object(engram_http_client, "_http_get", return_value=(200, b"{}")):
            assert engram_http_client.is_available(_BASE) is True

    def test_returns_false_on_500(self):
        from lib import engram_http_client

        with patch.object(engram_http_client, "_http_get", return_value=(500, b"error")):
            assert engram_http_client.is_available(_BASE) is False

    def test_returns_false_on_connection_refused(self):
        from lib import engram_http_client

        with patch.object(engram_http_client, "_http_get", return_value=(0, b"")):
            assert engram_http_client.is_available(_BASE) is False


# ---------------------------------------------------------------------------
# get_observation
# ---------------------------------------------------------------------------


class TestGetObservation:
    def test_returns_dict_on_200(self):
        from lib import engram_http_client

        obs = {"id": 42, "title": "Test", "content": "body"}
        with patch.object(engram_http_client, "_http_get", return_value=(200, _json_bytes(obs))):
            result = engram_http_client.get_observation(42, base_url=_BASE)
        assert result == obs

    def test_returns_none_on_404(self):
        from lib import engram_http_client

        with patch.object(engram_http_client, "_http_get", return_value=(404, b"not found")):
            result = engram_http_client.get_observation(999, base_url=_BASE)
        assert result is None

    def test_returns_none_on_connection_error(self):
        from lib import engram_http_client

        with patch.object(engram_http_client, "_http_get", return_value=(0, b"")):
            result = engram_http_client.get_observation(1, base_url=_BASE)
        assert result is None

    def test_calls_correct_url(self):
        from lib import engram_http_client

        obs = {"id": 7, "title": "t", "content": "c"}
        calls = []

        def fake_get(url, timeout):
            calls.append(url)
            return (200, _json_bytes(obs))

        with patch.object(engram_http_client, "_http_get", side_effect=fake_get):
            engram_http_client.get_observation(7, base_url=_BASE)

        assert calls == [f"{_BASE}/observations/7"]


# ---------------------------------------------------------------------------
# search_observations
# ---------------------------------------------------------------------------


class TestSearchObservations:
    def _patch_get_requests(self, module, status: int, body):
        """Patch the requests.get call inside search_observations."""
        mock_resp = MagicMock()
        mock_resp.status_code = status
        mock_resp.json.return_value = body
        return patch.object(
            sys.modules.get("requests", MagicMock()),
            "get",
            return_value=mock_resp,
        )

    def test_returns_list_on_200(self):
        from lib import engram_http_client

        observations = [{"id": 1}, {"id": 2}]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = observations

        with patch("requests.get", return_value=mock_resp):
            result = engram_http_client.search_observations("test query", base_url=_BASE)
        assert result == observations

    def test_returns_empty_list_on_error(self):
        from lib import engram_http_client

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = []

        with patch("requests.get", return_value=mock_resp):
            result = engram_http_client.search_observations("query", base_url=_BASE)
        assert result == []

    def test_returns_empty_list_on_requests_exception(self):
        from lib import engram_http_client
        import requests

        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("refused")):
            result = engram_http_client.search_observations("query", base_url=_BASE)
        assert result == []

    def test_encodes_query_params(self):
        from lib import engram_http_client

        calls = []
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []

        def fake_get(url, params=None, timeout=None):
            calls.append(params)
            return mock_resp

        with patch("requests.get", side_effect=fake_get):
            engram_http_client.search_observations(
                "my query",
                limit=10,
                type_filter="decision",
                project="luum",
                base_url=_BASE,
            )

        assert len(calls) == 1
        params = calls[0]
        assert params["q"] == "my query"
        assert params["limit"] == "10"
        assert params["type"] == "decision"
        assert params["project"] == "luum"

    def test_omits_empty_type_and_project(self):
        from lib import engram_http_client

        calls = []
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []

        def fake_get(url, params=None, timeout=None):
            calls.append(params)
            return mock_resp

        with patch("requests.get", side_effect=fake_get):
            engram_http_client.search_observations("bare query", base_url=_BASE)

        params = calls[0]
        assert "type" not in params
        assert "project" not in params


# ---------------------------------------------------------------------------
# update_observation — safety check
# ---------------------------------------------------------------------------


class TestUpdateObservation:
    def test_raises_value_error_when_no_fields(self):
        from lib import engram_http_client

        with pytest.raises(ValueError, match="at least one field"):
            engram_http_client.update_observation(1, base_url=_BASE)

    def test_sends_only_non_none_fields(self):
        from lib import engram_http_client

        calls = []

        def fake_patch(url, body, timeout):
            calls.append(body)
            return (200, _json_bytes({"id": 1, "content": "new"}))

        with patch.object(engram_http_client, "_http_patch", side_effect=fake_patch):
            engram_http_client.update_observation(1, content="new content", base_url=_BASE)

        assert len(calls) == 1
        assert calls[0] == {"content": "new content"}
        assert "title" not in calls[0]
        assert "type" not in calls[0]

    def test_returns_dict_on_success(self):
        from lib import engram_http_client

        updated = {"id": 5, "content": "updated body", "title": "T"}
        with patch.object(engram_http_client, "_http_patch", return_value=(200, _json_bytes(updated))):
            result = engram_http_client.update_observation(5, content="updated body", base_url=_BASE)
        assert result == updated

    def test_returns_none_on_http_error(self):
        from lib import engram_http_client

        with patch.object(engram_http_client, "_http_patch", return_value=(404, b"not found")):
            result = engram_http_client.update_observation(99, content="x", base_url=_BASE)
        assert result is None

    def test_sends_all_provided_fields(self):
        from lib import engram_http_client

        calls = []

        def fake_patch(url, body, timeout):
            calls.append(body)
            return (200, _json_bytes({"id": 3}))

        with patch.object(engram_http_client, "_http_patch", side_effect=fake_patch):
            engram_http_client.update_observation(
                3,
                content="c",
                title="t",
                type_="decision",
                topic_key="adr-071/test",
                base_url=_BASE,
            )

        body = calls[0]
        assert body["content"] == "c"
        assert body["title"] == "t"
        assert body["type"] == "decision"
        assert body["topic_key"] == "adr-071/test"


# ---------------------------------------------------------------------------
# urllib fallback
# ---------------------------------------------------------------------------


class TestUrllibFallback:
    """Verify that the module works when requests is not available."""

    def test_urllib_fallback_is_available(self):
        """When requests is unavailable, _http_get uses urllib and works correctly."""
        from lib import engram_http_client

        # Simulate requests being absent by patching _REQUESTS_AVAILABLE
        with patch.object(engram_http_client, "_REQUESTS_AVAILABLE", False):

            mock_response = MagicMock()
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_response.status = 200
            mock_response.read.return_value = b'{"service":"engram","status":"ok"}'

            with patch("urllib.request.urlopen", return_value=mock_response):
                status, body = engram_http_client._http_get(f"{_BASE}/health", 1.0)

        assert status == 200
        assert b"engram" in body

    def test_urllib_fallback_get_observation(self):
        """get_observation works when requests is unavailable."""
        from lib import engram_http_client

        obs = {"id": 55, "title": "fallback obs", "content": "body"}

        with patch.object(engram_http_client, "_REQUESTS_AVAILABLE", False):
            mock_response = MagicMock()
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_response.status = 200
            mock_response.read.return_value = _json_bytes(obs)

            with patch("urllib.request.urlopen", return_value=mock_response):
                result = engram_http_client.get_observation(55, base_url=_BASE)

        assert result == obs
