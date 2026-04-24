# SCOPE: both
# scope: both
"""Observability tracing module (Phoenix-only, post-ADR-058 / ADR-060).

Emits OTel spans via Phoenix. No cloud sinks. Compliant with the SO's
local-only policy (ADR-060): Phoenix is the supported trace surface;
Langfuse (ADR-058) and Opik (ADR-060) were removed.

Most callers should use ``lib/record_completion.py::_send_otel_trace``
directly; this module is a thin helper for ad-hoc tracing from scripts
and hooks that want to emit a single span with arbitrary metadata
(e.g., `trace_claude_result` below).

Usage:
    from lib.observability import trace, is_phoenix_available

    if is_phoenix_available():
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
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Timeout for HTTP requests (seconds)
_CONNECT_TIMEOUT = 3
_READ_TIMEOUT = 5


def _http_post(
    url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
) -> int:
    """POST JSON to a URL and return the HTTP status code.

    Generic helper retained for any future HTTP-based observability sink;
    not currently used by the Phoenix OTel path (OTel handles transport).
    Uses urllib to avoid external dependencies. Returns 0 on connection
    failure (service unreachable). Tested by `test_observability.py`.
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


def is_phoenix_available() -> bool:
    """Check if the Phoenix OTel bridge is importable.

    Returns True if ``phoenix.otel`` can be imported; does NOT test whether
    the collector is actually reachable (OTel exporters buffer + retry
    transparently, so reachability is not a gate).
    """
    try:
        import phoenix.otel  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False


def trace_to_phoenix(
    name: str,
    start: str,  # kept for API compatibility; OTel spans capture start automatically
    end: str,    # kept for API compatibility; OTel spans capture end automatically
    metadata: Dict[str, Any],
    input_text: Optional[str] = None,
    output_text: Optional[str] = None,
) -> bool:
    """Send a trace to Phoenix via OTel. Returns True on success.

    Silent no-op when ``arize-phoenix-otel`` is not installed — observability
    must never block the calling code.
    """
    try:
        from phoenix.otel import register as _phoenix_register  # type: ignore

        tracer = _phoenix_register(
            project_name="cognitive-os",
            auto_instrument=False,
        ).get_tracer(__name__)
        with tracer.start_as_current_span(name=name) as span:
            for key, value in metadata.items():
                # OTel attributes must be scalar or sequence-of-scalar.
                try:
                    span.set_attribute(str(key), value)
                except Exception:
                    span.set_attribute(str(key), str(value))
            if input_text is not None:
                span.set_attribute("input.value", input_text[:4000])
            if output_text is not None:
                span.set_attribute("output.value", output_text[:4000])
            # Duration is derived from span lifecycle; the caller-supplied
            # start/end strings are captured verbatim for downstream queries.
            span.set_attribute("trace.start", start)
            span.set_attribute("trace.end", end)
        return True
    except Exception as e:
        logger.debug("Phoenix trace failed: %s", e)
        return False


def trace(
    name: str,
    start: str,
    end: str,
    metadata: Dict[str, Any],
    input_text: Optional[str] = None,
    output_text: Optional[str] = None,
) -> Dict[str, bool]:
    """Send a trace to the active observability provider (Phoenix, if available).

    Failures are logged but never raise exceptions.

    Args:
        name: Trace name.
        start: ISO 8601 start timestamp.
        end: ISO 8601 end timestamp.
        metadata: Metadata dict.
        input_text: Optional input text.
        output_text: Optional output text.

    Returns:
        Dict with provider names as keys and success booleans as values.
        Only includes providers that were available.
    """
    results: Dict[str, bool] = {}

    if is_phoenix_available():
        try:
            results["phoenix"] = trace_to_phoenix(
                name, start, end, metadata,
                input_text=input_text, output_text=output_text,
            )
        except Exception as e:
            logger.warning("Phoenix trace error: %s", e)
            results["phoenix"] = False

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
