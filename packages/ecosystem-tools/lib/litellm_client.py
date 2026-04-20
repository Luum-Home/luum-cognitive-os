# SCOPE: both
# scope: both
"""LiteLLM Proxy Client — Route non-Claude models through LiteLLM gateway.

Provides an OpenAI-compatible chat completion interface via the LiteLLM
proxy. Supports both Docker proxy mode (http://localhost:4000) and pip
library mode (litellm --config config.yaml or litellm.completion() direct).

MIGRATION NOTE (Phase 2): LiteLLM is migrated from Docker to pip library.
The Docker container is kept in docker-compose for reference/CI only.
For new code, prefer using litellm.completion() directly instead of HTTP proxy.
This client remains for backward compatibility with existing code that
expects the HTTP proxy interface.

Usage:
    from lib.litellm_client import LiteLLMClient, is_litellm_available

    if is_litellm_available():
        client = LiteLLMClient()
        result = client.chat_completion("gpt-4o", [{"role": "user", "content": "Hello"}])
        print(result["choices"][0]["message"]["content"])

Python 3.9+ compatible.
"""

import logging
import os
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen
import json

logger = logging.getLogger(__name__)

# Default LiteLLM proxy URL — None means no proxy; set LITELLM_URL env var to enable.
# The old Docker-based default (localhost:4000) is intentionally removed as part of
# the Docker→pip migration (Phase 2). The proxy is no longer started automatically.
DEFAULT_LITELLM_URL: Optional[str] = os.environ.get("LITELLM_URL") or None

# Models that should be routed through LiteLLM (non-Claude)
LITELLM_ROUTABLE_MODELS = {
    "gpt-4o",
    "gpt-4o-mini",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "deepseek-r1",
    "deepseek-chat",
    "llama-3-70b",
    "llama-3-8b",
    "qwen-3-32b",
    "qwen-3-8b",
}

# Claude models — never route through LiteLLM
CLAUDE_MODELS = {
    "claude-opus-4-6",
    "claude-sonnet-4",
    "claude-haiku-3.5",
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
    "claude-haiku-3-5-20241022",
}


class LiteLLMUnavailable(Exception):
    """Raised when LiteLLM proxy is not reachable."""
    pass


class LiteLLMError(Exception):
    """Raised when LiteLLM returns an error response."""

    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


def is_litellm_enabled() -> bool:
    """Check if LiteLLM routing is enabled via environment variable.

    Returns:
        True if LITELLM_ENABLED is set to a truthy value.
    """
    val = os.environ.get("LITELLM_ENABLED", "false").lower()
    return val in ("true", "1", "yes")


def is_litellm_available(url: Optional[str] = None, timeout: float = 3.0) -> bool:
    """Check if the LiteLLM proxy is reachable and healthy.

    Args:
        url: Base URL for the LiteLLM proxy. Defaults to LITELLM_URL env var.
        timeout: Connection timeout in seconds.

    Returns:
        True if the health endpoint responds successfully.
        Returns False immediately when no URL is configured.
    """
    base_url = url or DEFAULT_LITELLM_URL
    if not base_url:
        return False
    health_url = f"{base_url.rstrip('/')}/health/liveliness"
    try:
        req = Request(health_url, method="GET")
        with urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except (URLError, OSError, Exception):
        return False


def is_model_litellm_routable(model: str) -> bool:
    """Check if a model should be routed through LiteLLM.

    Claude models are never routed through LiteLLM — they use the
    Claude CLI directly via ClaudeExecutor. All other known models
    are routable.

    Args:
        model: Model identifier string.

    Returns:
        True if the model should go through LiteLLM.
    """
    # Explicit Claude models
    model_lower = model.lower()
    for claude_id in CLAUDE_MODELS:
        if claude_id in model_lower:
            return False
    # Check for claude in the name as a catch-all
    if "claude" in model_lower:
        return False
    return True


class LiteLLMClient:
    """Client for the LiteLLM proxy with OpenAI-compatible API.

    Args:
        base_url: LiteLLM proxy URL. Defaults to LITELLM_URL env var (None if unset).
        api_key: API key for the proxy. Defaults to LITELLM_MASTER_KEY env.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 120.0,
    ):
        resolved_url = base_url or DEFAULT_LITELLM_URL or ""
        self.base_url = resolved_url.rstrip("/")
        self.api_key = api_key or os.environ.get("LITELLM_MASTER_KEY", "")
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the LiteLLM proxy.

        Args:
            method: HTTP method (GET, POST).
            path: URL path (e.g., /v1/chat/completions).
            body: JSON body for POST requests.

        Returns:
            Parsed JSON response.

        Raises:
            LiteLLMUnavailable: If the proxy is not reachable.
            LiteLLMError: If the proxy returns an error.
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
                raise LiteLLMUnavailable(
                    f"LiteLLM proxy not reachable at {self.base_url}: {e.reason}"
                ) from e
            # HTTP error with response
            status = getattr(e, "code", 0)
            resp_text = ""
            if hasattr(e, "read"):
                try:
                    resp_text = e.read().decode("utf-8")
                except Exception:
                    pass
            raise LiteLLMError(
                f"LiteLLM error (HTTP {status}): {resp_text[:500]}",
                status_code=status,
                response_body=resp_text,
            ) from e
        except OSError as e:
            raise LiteLLMUnavailable(
                f"LiteLLM proxy not reachable at {self.base_url}: {e}"
            ) from e

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Send a chat completion request through the LiteLLM proxy.

        Uses the OpenAI-compatible /v1/chat/completions endpoint.

        Args:
            model: Model identifier (e.g., "gpt-4o", "deepseek-r1").
            messages: List of message dicts with "role" and "content" keys.
            temperature: Optional sampling temperature (0.0 - 2.0).
            max_tokens: Optional maximum tokens in the response.
            **kwargs: Additional parameters passed to the API.

        Returns:
            OpenAI-compatible response dict with choices, usage, etc.

        Raises:
            LiteLLMUnavailable: If the proxy is not reachable.
            LiteLLMError: If the API returns an error.
        """
        body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        body.update(kwargs)

        logger.debug("LiteLLM chat_completion: model=%s, messages=%d", model, len(messages))
        return self._request("POST", "/v1/chat/completions", body=body)

    def list_models(self) -> List[str]:
        """List all available models configured in LiteLLM.

        Returns:
            List of model identifier strings.

        Raises:
            LiteLLMUnavailable: If the proxy is not reachable.
            LiteLLMError: If the API returns an error.
        """
        resp = self._request("GET", "/model/info")
        models: List[str] = []
        data = resp.get("data", [])
        for entry in data:
            model_name = entry.get("model_name", "")
            if model_name:
                models.append(model_name)
        return models

    def health_check(self) -> bool:
        """Check if the LiteLLM proxy is healthy.

        Returns:
            True if the health endpoint responds successfully.
        """
        try:
            self._request("GET", "/health/liveliness")
            return True
        except (LiteLLMUnavailable, LiteLLMError):
            return False
