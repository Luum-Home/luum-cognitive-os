"""Bifrost AI Gateway Client — High-performance gateway for multi-provider routing.

Provides an OpenAI-compatible chat completion interface via the Bifrost
gateway running at http://localhost:8081. Bifrost adds only 11 microseconds
of latency overhead at 5K RPS, making it the preferred fast path for
provider calls.

Bifrost uses provider-prefixed model names (e.g., openai/gpt-4o,
anthropic/claude-3-sonnet, gemini/gemini-2.5-pro).

Usage:
    from lib.bifrost_client import BifrostClient, is_bifrost_available

    if is_bifrost_available():
        client = BifrostClient()
        result = client.chat_completion(
            "openai/gpt-4o",
            [{"role": "user", "content": "Hello"}],
        )
        print(result["choices"][0]["message"]["content"])

Python 3.9+ compatible.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from lib.model_catalog import ModelCatalog

logger = logging.getLogger(__name__)

# Default Bifrost gateway URL (port 8081 externally, 8080 internal)
DEFAULT_BIFROST_URL = "http://localhost:8081"

# Providers natively supported by Bifrost with their model prefix
# Bifrost requires provider-prefixed model names: "provider/model-id"
BIFROST_PROVIDERS = {
    "openai",
    "anthropic",
    "google",       # Gemini models
    "gemini",       # Alternative prefix for Google
    "groq",
    "mistral",
    "cohere",
    "bedrock",      # AWS Bedrock
    "azure",        # Azure OpenAI
}

# Map from model_router model names -> Bifrost provider-prefixed names
# This bridges the gap between model_router's flat names and Bifrost's
# provider/model format.
MODEL_TO_BIFROST: Dict[str, str] = {
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gemini-2.5-pro": "gemini/gemini-2.5-pro",
    "gemini-2.0-flash": "gemini/gemini-2.0-flash",
    "deepseek-r1": "deepseek/deepseek-r1",
    "deepseek-chat": "deepseek/deepseek-chat",
}

# Models that should NOT go through Bifrost — derived from ModelCatalog:
# - Claude models (Anthropic): use ClaudeExecutor directly
# - OpenRouter models: only LiteLLM handles OpenRouter free tier
# - Local models: only accessible via LiteLLM (Ollama/vLLM proxy)
BIFROST_EXCLUDED_MODELS = (
    {e.id for e in ModelCatalog.by_provider("anthropic")}
    | {e.id for e in ModelCatalog.by_provider("openrouter")}
    | {e.id for e in ModelCatalog.all_entries() if e.local}
    # Keep non-catalog entries that may not be in the catalog yet
    | {"llama-3-8b", "qwen-3-8b"}
)


class BifrostUnavailable(Exception):
    """Raised when Bifrost gateway is not reachable."""
    pass


class BifrostError(Exception):
    """Raised when Bifrost returns an error response."""

    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


def is_bifrost_enabled() -> bool:
    """Check if Bifrost routing is enabled via environment variable.

    Returns:
        True if BIFROST_ENABLED is set to a truthy value.
    """
    val = os.environ.get("BIFROST_ENABLED", "false").lower()
    return val in ("true", "1", "yes")


def is_bifrost_available(url: Optional[str] = None, timeout: float = 3.0) -> bool:
    """Check if the Bifrost gateway is reachable and healthy.

    Args:
        url: Base URL for the Bifrost gateway. Defaults to DEFAULT_BIFROST_URL.
        timeout: Connection timeout in seconds.

    Returns:
        True if the health endpoint responds successfully.
    """
    base_url = url or os.environ.get("BIFROST_URL", DEFAULT_BIFROST_URL)
    health_url = f"{base_url.rstrip('/')}/"
    try:
        req = Request(health_url, method="GET")
        with urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except (URLError, OSError, Exception):
        return False


def is_model_bifrost_routable(model: str) -> bool:
    """Check if a model should be routed through Bifrost.

    A model is Bifrost-routable if:
    1. It is not in the exclusion list (Claude, OpenRouter, local models)
    2. It has a known Bifrost provider mapping, OR
    3. It already uses provider/model format for a supported provider

    For provider-prefixed models (e.g., "groq/llama-3-70b"), the exclusion
    check matches against the full string exactly (not substring), since
    the local model "llama-3-70b" should not block "groq/llama-3-70b".

    Args:
        model: Model identifier string.

    Returns:
        True if the model can go through Bifrost.
    """
    model_lower = model.lower()

    # Claude catch-all (always excluded regardless of prefix)
    if "claude" in model_lower:
        return False

    # For provider-prefixed models, check if the provider is supported
    if "/" in model:
        provider = model.split("/")[0].lower()
        # OpenRouter free-tier models are LiteLLM-only
        if model_lower in {m.lower() for m in BIFROST_EXCLUDED_MODELS}:
            return False
        return provider in BIFROST_PROVIDERS

    # For flat model names, check the exclusion list (exact match)
    if model_lower in {m.lower() for m in BIFROST_EXCLUDED_MODELS}:
        return False

    # Check if we have a direct mapping
    if model in MODEL_TO_BIFROST:
        return True

    return False


def get_bifrost_model_name(model: str) -> str:
    """Convert a model_router model name to Bifrost's provider-prefixed format.

    Args:
        model: Model identifier from model_router (e.g., "gpt-4o").

    Returns:
        Bifrost-compatible model name (e.g., "openai/gpt-4o").

    Raises:
        ValueError: If no mapping exists for the model.
    """
    # Already in provider/model format
    if "/" in model:
        return model

    # Look up in mapping table
    if model in MODEL_TO_BIFROST:
        return MODEL_TO_BIFROST[model]

    raise ValueError(
        f"No Bifrost mapping for model '{model}'. "
        f"Known mappings: {list(MODEL_TO_BIFROST.keys())}"
    )


class BifrostClient:
    """Client for the Bifrost AI gateway with OpenAI-compatible API.

    Args:
        base_url: Bifrost gateway URL. Defaults to BIFROST_URL env or localhost:8081.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        self.base_url = (
            base_url or os.environ.get("BIFROST_URL", DEFAULT_BIFROST_URL)
        ).rstrip("/")
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the Bifrost gateway.

        Args:
            method: HTTP method (GET, POST).
            path: URL path (e.g., /v1/chat/completions).
            body: JSON body for POST requests.

        Returns:
            Parsed JSON response.

        Raises:
            BifrostUnavailable: If the gateway is not reachable.
            BifrostError: If the gateway returns an error.
        """
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}

        data = json.dumps(body).encode("utf-8") if body else None
        req = Request(url, data=data, headers=headers, method=method)

        try:
            with urlopen(req, timeout=self.timeout) as resp:
                resp_body = resp.read().decode("utf-8")
                return json.loads(resp_body) if resp_body else {}
        except URLError as e:
            if hasattr(e, "reason"):
                raise BifrostUnavailable(
                    f"Bifrost gateway not reachable at {self.base_url}: {e.reason}"
                ) from e
            # HTTP error with response
            status = getattr(e, "code", 0)
            resp_text = ""
            if hasattr(e, "read"):
                try:
                    resp_text = e.read().decode("utf-8")
                except Exception:
                    pass
            raise BifrostError(
                f"Bifrost error (HTTP {status}): {resp_text[:500]}",
                status_code=status,
                response_body=resp_text,
            ) from e
        except OSError as e:
            raise BifrostUnavailable(
                f"Bifrost gateway not reachable at {self.base_url}: {e}"
            ) from e

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Send a chat completion request through the Bifrost gateway.

        Uses the OpenAI-compatible /v1/chat/completions endpoint.
        The model name should be in Bifrost's provider-prefixed format
        (e.g., "openai/gpt-4o"). Use get_bifrost_model_name() to convert
        from model_router names.

        Args:
            model: Provider-prefixed model identifier (e.g., "openai/gpt-4o").
            messages: List of message dicts with "role" and "content" keys.
            temperature: Optional sampling temperature (0.0 - 2.0).
            max_tokens: Optional maximum tokens in the response.
            **kwargs: Additional parameters passed to the API.

        Returns:
            OpenAI-compatible response dict with choices, usage, etc.

        Raises:
            BifrostUnavailable: If the gateway is not reachable.
            BifrostError: If the API returns an error.
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

        logger.debug("Bifrost chat_completion: model=%s, messages=%d", model, len(messages))
        return self._request("POST", "/v1/chat/completions", body=body)

    def health_check(self) -> bool:
        """Check if the Bifrost gateway is healthy.

        Returns:
            True if the root endpoint responds successfully.
        """
        try:
            self._request("GET", "/")
            return True
        except (BifrostUnavailable, BifrostError):
            return False
