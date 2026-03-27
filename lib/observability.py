"""Observability tracing module for Langfuse and Opik.

Provides functions to send execution traces to Langfuse and/or Opik
observability backends. Both providers are disabled by default and
controlled via environment variables.

Usage:
    from lib.observability import trace, is_langfuse_available, is_opik_available

    trace(
        name="sdd-apply",
        start="2026-03-27T10:00:00Z",
        end="2026-03-27T10:05:00Z",
        metadata={"agent": "sdd-apply", "phase": "reconstruction", "tokens": 1500},
        input_text="Apply the spec changes...",
        output_text="Changes applied successfully.",
    )

Python 3.9+ compatible.
"""

import json
import logging
import os
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default endpoints matching docker-compose.cognitive-os.yml
_LANGFUSE_DEFAULT_HOST = "http://localhost:3100"
_OPIK_DEFAULT_HOST = "http://localhost:5173"

# Timeout for HTTP requests (seconds)
_CONNECT_TIMEOUT = 3
_READ_TIMEOUT = 5


def _http_post(
    url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
) -> int:
    """POST JSON to a URL and return the HTTP status code.

    Uses urllib to avoid external dependencies. Returns 0 on connection
    failure (service unreachable).
    """
    import urllib.request
    import urllib.error

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)

    try:
        with urllib.request.urlopen(req, timeout=_READ_TIMEOUT) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        logger.debug("HTTP POST to %s failed: %s", url, e)
        return 0


def _base64_encode(text: str) -> str:
    """Base64 encode a string."""
    import base64

    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def is_langfuse_available() -> bool:
    """Check if Langfuse is enabled and reachable.

    Returns True if LANGFUSE_ENABLED=true and the health endpoint responds.
    """
    if os.environ.get("LANGFUSE_ENABLED", "false").lower() != "true":
        return False

    host = os.environ.get("LANGFUSE_HOST", _LANGFUSE_DEFAULT_HOST)
    try:
        import urllib.request
        import urllib.error

        req = urllib.request.Request(
            "%s/api/public/health" % host, method="GET"
        )
        with urllib.request.urlopen(req, timeout=_CONNECT_TIMEOUT) as resp:
            return resp.status == 200
    except Exception:
        return False


def is_opik_available() -> bool:
    """Check if Opik is enabled and reachable.

    Returns True if OPIK_ENABLED=true and the health endpoint responds.
    """
    if os.environ.get("OPIK_ENABLED", "false").lower() != "true":
        return False

    host = os.environ.get("OPIK_HOST", _OPIK_DEFAULT_HOST)
    try:
        import urllib.request
        import urllib.error

        req = urllib.request.Request(
            "%s/is-alive/ping" % host, method="GET"
        )
        with urllib.request.urlopen(req, timeout=_CONNECT_TIMEOUT) as resp:
            return resp.status == 200
    except Exception:
        return False


def trace_to_langfuse(
    name: str,
    start: str,
    end: str,
    metadata: Dict[str, Any],
    input_text: Optional[str] = None,
    output_text: Optional[str] = None,
) -> bool:
    """Send a trace to Langfuse.

    Args:
        name: Trace name (e.g., agent or skill name).
        start: ISO 8601 start timestamp.
        end: ISO 8601 end timestamp.
        metadata: Arbitrary metadata dict (agent, phase, tokens, cost, etc.).
        input_text: Optional input/prompt text.
        output_text: Optional output/result text.

    Returns:
        True if the trace was accepted (HTTP 2xx), False otherwise.
    """
    host = os.environ.get("LANGFUSE_HOST", _LANGFUSE_DEFAULT_HOST)
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")

    if not public_key or not secret_key:
        logger.warning(
            "Langfuse trace skipped: LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY not set"
        )
        return False

    trace_id = str(uuid.uuid4())
    payload = {
        "batch": [
            {
                "id": trace_id,
                "type": "trace-create",
                "timestamp": end,
                "body": {
                    "id": trace_id,
                    "name": name,
                    "input": input_text,
                    "output": output_text,
                    "metadata": metadata,
                },
            }
        ]
    }

    auth = _base64_encode("%s:%s" % (public_key, secret_key))
    headers = {"Authorization": "Basic %s" % auth}

    url = "%s/api/public/ingestion" % host
    status = _http_post(url, payload, headers=headers)

    if 200 <= status < 300:
        logger.debug("Langfuse trace sent: %s (HTTP %d)", name, status)
        return True
    else:
        logger.warning("Langfuse trace failed: %s (HTTP %d)", name, status)
        return False


def trace_to_opik(
    name: str,
    start: str,
    end: str,
    metadata: Dict[str, Any],
    input_text: Optional[str] = None,
    output_text: Optional[str] = None,
) -> bool:
    """Send a trace to Opik.

    Args:
        name: Trace name (e.g., agent or skill name).
        start: ISO 8601 start timestamp.
        end: ISO 8601 end timestamp.
        metadata: Arbitrary metadata dict.
        input_text: Optional input/prompt text.
        output_text: Optional output/result text.

    Returns:
        True if the trace was accepted (HTTP 2xx), False otherwise.
    """
    host = os.environ.get("OPIK_HOST", _OPIK_DEFAULT_HOST)

    trace_id = str(uuid.uuid4())
    payload = {
        "id": trace_id,
        "name": name,
        "start_time": start,
        "end_time": end,
        "input": {"text": input_text or ""},
        "output": {"text": output_text or ""},
        "metadata": metadata,
    }

    url = "%s/api/v1/private/traces" % host
    status = _http_post(url, payload)

    if 200 <= status < 300:
        logger.debug("Opik trace sent: %s (HTTP %d)", name, status)
        return True
    else:
        logger.warning("Opik trace failed: %s (HTTP %d)", name, status)
        return False


def trace(
    name: str,
    start: str,
    end: str,
    metadata: Dict[str, Any],
    input_text: Optional[str] = None,
    output_text: Optional[str] = None,
) -> Dict[str, bool]:
    """Send a trace to all enabled observability providers.

    Checks LANGFUSE_ENABLED and OPIK_ENABLED environment variables.
    Sends to each enabled provider independently. Failures are logged
    but never raise exceptions.

    Args:
        name: Trace name.
        start: ISO 8601 start timestamp.
        end: ISO 8601 end timestamp.
        metadata: Metadata dict.
        input_text: Optional input text.
        output_text: Optional output text.

    Returns:
        Dict with provider names as keys and success booleans as values.
        Only includes providers that were enabled.
    """
    results: Dict[str, bool] = {}

    if os.environ.get("LANGFUSE_ENABLED", "false").lower() == "true":
        try:
            results["langfuse"] = trace_to_langfuse(
                name, start, end, metadata,
                input_text=input_text, output_text=output_text,
            )
        except Exception as e:
            logger.warning("Langfuse trace error: %s", e)
            results["langfuse"] = False

    if os.environ.get("OPIK_ENABLED", "false").lower() == "true":
        try:
            results["opik"] = trace_to_opik(
                name, start, end, metadata,
                input_text=input_text, output_text=output_text,
            )
        except Exception as e:
            logger.warning("Opik trace error: %s", e)
            results["opik"] = False

    return results


def trace_claude_result(
    result: Any,
    agent_name: str = "unknown",
    phase: str = "unknown",
) -> Dict[str, bool]:
    """Convenience: send a trace from a ClaudeResult object.

    Integrates with ClaudeExecutor by accepting a ClaudeResult and
    extracting all relevant fields automatically.

    Args:
        result: A ClaudeResult dataclass instance from claude_executor.
        agent_name: Name of the agent that produced the result.
        phase: Current project phase.

    Returns:
        Dict with provider results (same as trace()).
    """
    import time

    # Build timestamps from duration
    end_epoch = time.time()
    start_epoch = end_epoch - getattr(result, "duration_secs", 0)

    start_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_epoch))
    end_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(end_epoch))

    # Estimate cost
    tokens_in = getattr(result, "tokens_in", 0)
    tokens_out = getattr(result, "tokens_out", 0)
    cost = getattr(result, "cost_usd", 0.0)
    model = getattr(result, "model_used", "unknown")
    success = getattr(result, "success", False)

    metadata = {
        "agent": agent_name,
        "phase": phase,
        "model": model,
        "tokens": tokens_in + tokens_out,
        "input_tokens": tokens_in,
        "output_tokens": tokens_out,
        "cost_usd": str(cost),
        "success": success,
        "tool_calls": len(getattr(result, "tool_calls", [])),
        "session_id": getattr(result, "session_id", ""),
    }

    # Truncate texts for trace
    input_text = ""  # We don't have the prompt in ClaudeResult
    output_text = getattr(result, "result_text", "")[:1000]

    return trace(
        name=agent_name,
        start=start_iso,
        end=end_iso,
        metadata=metadata,
        input_text=input_text,
        output_text=output_text,
    )
