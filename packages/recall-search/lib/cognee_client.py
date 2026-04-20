# SCOPE: both
# scope: both
"""Cognee Client — Semantic knowledge graph search for Cognitive OS.

Provides a client for Cognee's REST API to complement Engram's FTS5 search
with relationship-aware semantic retrieval via knowledge graphs.

Usage:
    from lib.cognee_client import CogneeClient, is_cognee_available

    if is_cognee_available():
        client = CogneeClient()
        client.add_knowledge("The auth service uses JWT tokens", source="auth-docs")
        results = client.search("how does authentication work")

Python 3.9+ compatible.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# Default Cognee API URL
DEFAULT_COGNEE_URL = "http://localhost:8000"


class CogneeUnavailable(Exception):
    """Raised when Cognee service is not reachable."""
    pass


class CogneeError(Exception):
    """Raised when Cognee returns an error response."""

    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


def is_cognee_enabled() -> bool:
    """Check if Cognee is enabled via environment variable.

    Returns:
        True if COGNEE_ENABLED is set to a truthy value.
    """
    val = os.environ.get("COGNEE_ENABLED", "false").lower()
    return val in ("true", "1", "yes")


def is_cognee_available(url: Optional[str] = None, timeout: float = 3.0) -> bool:
    """Check if the Cognee service is reachable and healthy.

    Args:
        url: Base URL for the Cognee service. Defaults to DEFAULT_COGNEE_URL.
        timeout: Connection timeout in seconds.

    Returns:
        True if the health endpoint responds successfully.
    """
    base_url = url or os.environ.get("COGNEE_URL", DEFAULT_COGNEE_URL)
    health_url = f"{base_url.rstrip('/')}/health"
    try:
        req = Request(health_url, method="GET")
        with urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except (URLError, OSError, Exception):
        return False


class CogneeClient:
    """Client for the Cognee knowledge graph API.

    Cognee provides an ECL (Extract, Cognify, Load) pipeline that builds
    a knowledge graph from text, enabling semantic search with relationship
    awareness.

    Args:
        base_url: Cognee service URL. Defaults to COGNEE_URL env or localhost:8000.
        api_key: Optional API key for authentication.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.base_url = (
            base_url or os.environ.get("COGNEE_URL", DEFAULT_COGNEE_URL)
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("COGNEE_API_KEY", "")
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an HTTP request to the Cognee API.

        Args:
            method: HTTP method (GET, POST).
            path: URL path (e.g., /api/v1/search).
            body: JSON body for POST requests.

        Returns:
            Parsed JSON response (dict or list).

        Raises:
            CogneeUnavailable: If the service is not reachable.
            CogneeError: If the service returns an error.
        """
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        data = json.dumps(body).encode("utf-8") if body else None
        req = Request(url, data=data, headers=headers, method=method)

        try:
            with urlopen(req, timeout=self.timeout) as resp:
                resp_body = resp.read().decode("utf-8")
                return json.loads(resp_body) if resp_body else {}
        except URLError as e:
            if hasattr(e, "reason"):
                raise CogneeUnavailable(
                    f"Cognee service not reachable at {self.base_url}: {e.reason}"
                ) from e
            status = getattr(e, "code", 0)
            resp_text = ""
            if hasattr(e, "read"):
                try:
                    resp_text = e.read().decode("utf-8")
                except Exception:
                    pass
            raise CogneeError(
                f"Cognee error (HTTP {status}): {resp_text[:500]}",
                status_code=status,
                response_body=resp_text,
            ) from e
        except OSError as e:
            raise CogneeUnavailable(
                f"Cognee service not reachable at {self.base_url}: {e}"
            ) from e

    def add_knowledge(
        self,
        text: str,
        source: str = "",
        dataset_name: str = "cognitive-os",
    ) -> str:
        """Add text knowledge to Cognee for graph extraction.

        Args:
            text: The text content to add.
            source: Optional source identifier (e.g., file path, URL).
            dataset_name: Dataset to add the knowledge to.

        Returns:
            Status string or ID of the added knowledge.

        Raises:
            CogneeUnavailable: If the service is not reachable.
            CogneeError: If the API returns an error.
        """
        body: Dict[str, Any] = {
            "text": text,
            "dataset_name": dataset_name,
        }
        if source:
            body["source"] = source

        logger.debug("Cognee add_knowledge: source=%s, len=%d", source, len(text))
        result = self._request("POST", "/api/v1/add", body=body)

        if isinstance(result, dict):
            return result.get("id", result.get("status", "ok"))
        return str(result)

    def search(
        self,
        query: str,
        limit: int = 5,
        search_type: str = "INSIGHTS",
    ) -> List[Dict[str, Any]]:
        """Search the Cognee knowledge graph.

        Args:
            query: Natural language search query.
            limit: Maximum number of results to return.
            search_type: Type of search (INSIGHTS, CHUNKS, GRAPH_COMPLETION).

        Returns:
            List of search result dicts with content and metadata.

        Raises:
            CogneeUnavailable: If the service is not reachable.
            CogneeError: If the API returns an error.
        """
        body = {
            "query": query,
            "limit": limit,
            "search_type": search_type,
        }

        logger.debug("Cognee search: query=%s, limit=%d", query[:50], limit)
        result = self._request("POST", "/api/v1/search", body=body)

        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("results", result.get("data", []))
        return []

    def cognify(
        self,
        dataset_name: str = "cognitive-os",
    ) -> Dict[str, Any]:
        """Trigger the Cognify step to build the knowledge graph.

        This processes all added knowledge through Cognee's ECL pipeline:
        Extract entities/relationships, build graph, create embeddings.

        Args:
            dataset_name: Dataset to cognify.

        Returns:
            Status dict with cognification results.

        Raises:
            CogneeUnavailable: If the service is not reachable.
            CogneeError: If the API returns an error.
        """
        body = {
            "dataset_name": dataset_name,
        }

        logger.debug("Cognee cognify: dataset=%s", dataset_name)
        result = self._request("POST", "/api/v1/cognify", body=body)

        if isinstance(result, dict):
            return result
        return {"status": str(result)}

    def health_check(self) -> bool:
        """Check if the Cognee service is healthy.

        Returns:
            True if the health endpoint responds successfully.
        """
        try:
            self._request("GET", "/health")
            return True
        except (CogneeUnavailable, CogneeError):
            return False


def search_graceful(
    query: str,
    limit: int = 5,
    url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search Cognee with graceful degradation.

    If Cognee is not available or not enabled, returns an empty list
    instead of raising an exception.

    Args:
        query: Search query.
        limit: Max results.
        url: Optional Cognee URL override.

    Returns:
        List of results, or empty list if Cognee is unavailable.
    """
    if not is_cognee_enabled():
        return []

    if not is_cognee_available(url=url):
        return []

    try:
        client = CogneeClient(base_url=url)
        return client.search(query, limit=limit)
    except (CogneeUnavailable, CogneeError) as e:
        logger.debug("Cognee search failed gracefully: %s", e)
        return []
