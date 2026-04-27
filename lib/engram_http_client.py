# SCOPE: both
"""Engram HTTP client — typed wrapper over the engram REST API at port 7437.

FOR (use case)
--------------
Use this module when code needs to GET or PATCH observations on the running
engram daemon via HTTP rather than via the engram CLI subprocess.  The CLI
lacks ``get`` and ``update`` sub-commands; HTTP is the only way to fetch a
single observation by ID or update its content in-place.

This module is the ONLY approved path for calling mutating HTTP endpoints
(PATCH) on the engram daemon.  Ad-hoc curl experiments MUST use a sandboxed
daemon on an alternate port.  See ``rules/engram-api-safety.md``.

CONTRACT
--------
- All functions **never raise** (except ``update_observation`` which raises
  ``ValueError`` pre-flight when no fields are supplied — this is a programming
  error, not a runtime error).
- Returns ``None`` / empty list on any HTTP, network, or JSON error.
- ``requests`` is used when available; falls back to ``urllib`` automatically so
  this module has zero hard dependencies beyond the Python standard library.
- Timeouts are applied to every network call; default values are conservative
  (1s for health, 5s for data calls).

ADR reference: ``docs/adrs/ADR-071-engram-lifecycle-evolution.md``
Safety rule:   ``rules/engram-api-safety.md``
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

_log = logging.getLogger(__name__)

_DEFAULT_BASE = os.environ.get("ENGRAM_HTTP_URL", "http://127.0.0.1:7437")

# ---------------------------------------------------------------------------
# Transport layer — try requests, fall back to urllib
# ---------------------------------------------------------------------------

# Always import urllib — it is stdlib and always available.  This ensures the
# fallback branch works even when _REQUESTS_AVAILABLE is patched to False in
# tests running in an environment where requests IS installed.
import urllib.error
import urllib.parse
import urllib.request

try:
    import requests as _requests

    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


def _http_get(url: str, timeout: float) -> tuple[int, bytes]:
    """Perform an HTTP GET. Returns (status_code, body_bytes). Never raises."""
    if _REQUESTS_AVAILABLE:
        try:
            resp = _requests.get(url, timeout=timeout)
            return resp.status_code, resp.content
        except Exception as exc:
            _log.debug("engram_http_client GET %s failed: %s", url, exc)
            return 0, b""
    else:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, b""
        except Exception as exc:
            _log.debug("engram_http_client GET %s failed: %s", url, exc)
            return 0, b""


def _http_patch(url: str, body: dict[str, Any], timeout: float) -> tuple[int, bytes]:
    """Perform an HTTP PATCH with a JSON body. Returns (status_code, body_bytes). Never raises."""
    payload = json.dumps(body).encode("utf-8")
    if _REQUESTS_AVAILABLE:
        try:
            resp = _requests.patch(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
            return resp.status_code, resp.content
        except Exception as exc:
            _log.debug("engram_http_client PATCH %s failed: %s", url, exc)
            return 0, b""
    else:
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="PATCH",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, b""
        except Exception as exc:
            _log.debug("engram_http_client PATCH %s failed: %s", url, exc)
            return 0, b""


def _parse_json(body: bytes) -> Any:
    """Parse JSON bytes. Returns None on failure. Never raises."""
    try:
        return json.loads(body.decode("utf-8"))
    except Exception as exc:
        _log.debug("engram_http_client JSON parse failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_available(base_url: str = _DEFAULT_BASE, timeout: float = 1.0) -> bool:
    """Check whether the engram daemon is up by calling GET /health.

    Args:
        base_url: Base URL of the engram daemon (default: http://127.0.0.1:7437).
        timeout:  Request timeout in seconds.

    Returns:
        True if the daemon responds with HTTP 200; False otherwise.
    """
    status, _ = _http_get(f"{base_url}/health", timeout)
    return status == 200


def get_observation(
    observation_id: int | str,
    *,
    base_url: str = _DEFAULT_BASE,
    timeout: float = 5.0,
) -> dict[str, Any] | None:
    """Fetch a single observation by ID via GET /observations/<id>.

    Args:
        observation_id: Integer or string ID of the observation.
        base_url:       Base URL of the engram daemon.
        timeout:        Request timeout in seconds.

    Returns:
        Observation dict on success, None on 404 or any error.
    """
    url = f"{base_url}/observations/{observation_id}"
    status, body = _http_get(url, timeout)
    if status != 200:
        _log.debug("get_observation(%s) returned HTTP %s", observation_id, status)
        return None
    data = _parse_json(body)
    if isinstance(data, dict):
        return data
    return None


def search_observations(
    query: str,
    *,
    limit: int = 5,
    type_filter: str = "",
    project: str = "",
    base_url: str = _DEFAULT_BASE,
    timeout: float = 5.0,
) -> list[dict[str, Any]]:
    """Search engram observations via GET /search.

    Args:
        query:       Free-text search query.
        limit:       Maximum number of results (default 5).
        type_filter: Optional observation type filter (e.g. ``"decision"``).
        project:     Optional project scope.
        base_url:    Base URL of the engram daemon.
        timeout:     Request timeout in seconds.

    Returns:
        List of observation dicts.  Empty list on any error or no results.
    """
    params: dict[str, str] = {"q": query, "limit": str(limit)}
    if type_filter:
        params["type"] = type_filter
    if project:
        params["project"] = project

    if _REQUESTS_AVAILABLE:
        try:
            import requests as _req
            resp = _req.get(f"{base_url}/search", params=params, timeout=timeout)
            if resp.status_code != 200:
                _log.debug("search_observations returned HTTP %s", resp.status_code)
                return []
            data = resp.json()
        except Exception as exc:
            _log.debug("search_observations failed: %s", exc)
            return []
    else:
        try:
            encoded = urllib.parse.urlencode(params)
            url = f"{base_url}/search?{encoded}"
            status, body = _http_get(url, timeout)
            if status != 200:
                _log.debug("search_observations returned HTTP %s", status)
                return []
            data = _parse_json(body)
        except Exception as exc:
            _log.debug("search_observations failed: %s", exc)
            return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("results", "observations", "data"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def get_recent(
    *,
    limit: int = 100,
    project: str = "",
    base_url: str = _DEFAULT_BASE,
    timeout: float = 5.0,
) -> list[dict[str, Any]]:
    """Fetch recent observations via GET /observations/recent.

    Args:
        limit:    Maximum number of results (default 100).
        project:  Optional project scope filter.
        base_url: Base URL of the engram daemon.
        timeout:  Request timeout in seconds.

    Returns:
        List of observation dicts.  Empty list on any error.
    """
    params: dict[str, str] = {"limit": str(limit)}
    if project:
        params["project"] = project

    if _REQUESTS_AVAILABLE:
        try:
            import requests as _req
            resp = _req.get(f"{base_url}/observations/recent", params=params, timeout=timeout)
            if resp.status_code != 200:
                _log.debug("get_recent returned HTTP %s", resp.status_code)
                return []
            data = resp.json()
        except Exception as exc:
            _log.debug("get_recent failed: %s", exc)
            return []
    else:
        try:
            encoded = urllib.parse.urlencode(params)
            url = f"{base_url}/observations/recent?{encoded}"
            status, body = _http_get(url, timeout)
            if status != 200:
                _log.debug("get_recent returned HTTP %s", status)
                return []
            data = _parse_json(body)
        except Exception as exc:
            _log.debug("get_recent failed: %s", exc)
            return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("results", "observations", "data"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def update_observation(
    observation_id: int | str,
    *,
    content: str | None = None,
    title: str | None = None,
    type_: str | None = None,
    topic_key: str | None = None,
    base_url: str = _DEFAULT_BASE,
    timeout: float = 5.0,
) -> dict[str, Any] | None:
    """Update an observation in-place via PATCH /observations/<id>.

    SAFETY: At least one of ``content``, ``title``, ``type_``, or ``topic_key``
    MUST be provided.  Calling with no fields is a programming error and raises
    ``ValueError`` BEFORE the HTTP call — this is the safety pre-flight check
    that prevents accidental empty PATCHes against production data.

    Args:
        observation_id: Integer or string ID of the observation to update.
        content:        New content string (optional).
        title:          New title string (optional).
        type_:          New type string (optional).
        topic_key:      New topic_key string (optional).
        base_url:       Base URL of the engram daemon.
        timeout:        Request timeout in seconds.

    Returns:
        Updated observation dict on success, None on any error.

    Raises:
        ValueError: When no fields are supplied (programming error, not a
                    runtime error — raised before any network call).
    """
    payload: dict[str, str] = {}
    if content is not None:
        payload["content"] = content
    if title is not None:
        payload["title"] = title
    if type_ is not None:
        payload["type"] = type_
    if topic_key is not None:
        payload["topic_key"] = topic_key

    if not payload:
        raise ValueError(
            "update_observation() requires at least one field (content, title, "
            "type_, or topic_key). Calling with no fields is a programming error "
            "and would send an empty PATCH to the production engram daemon. "
            "See rules/engram-api-safety.md."
        )

    url = f"{base_url}/observations/{observation_id}"
    status, body = _http_patch(url, payload, timeout)
    if status not in (200, 204):
        _log.debug("update_observation(%s) returned HTTP %s", observation_id, status)
        return None
    data = _parse_json(body)
    if isinstance(data, dict):
        return data
    # HTTP 204 No Content — return minimal dict confirming success
    if status == 204:
        return {"id": observation_id, "updated": True}
    return None
