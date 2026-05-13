# SCOPE: os-only
"""ADR-288 — intent classifier and routing facade for web automation.

This is the integration seam between `lib/dispatch.py` (or any caller that
wants to dispatch a web-automation task) and `lib/browser_use_adapter.py`.
It is intentionally tiny: a regex-based intent classifier plus a route()
helper that either returns a ready-to-use :class:`BrowserUseAdapter` or
raises :class:`WebAutomationUnavailable` with a clear reason.

The dispatch ordering contract in ``lib/dispatch.py`` (ADR-236 → 232 → 228 →
226) means we do not mutate ``dispatch()`` from this ADR. A follow-up ADR
will add a phase that calls :func:`route` before the ADR-228 cost gate so
browser runs debit the session budget correctly.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from lib.browser_use_adapter import (
    BrowserUseAdapter,
    WebAutomationUnavailable,
    is_browser_use_available,
)

# Patterns ordered by specificity. A match anywhere triggers routing.
# Phrasing is anchored on verbs + URL/web nouns to keep recall reasonable
# without inflating false positives on generic "click here" docs.
_INTENT_PATTERNS = (
    re.compile(r"\bnavigate\s+to\s+https?://", re.IGNORECASE),
    re.compile(r"\bopen\s+(the\s+)?(url|page|website|site)\b", re.IGNORECASE),
    re.compile(r"\bscrape\s+(the\s+)?(page|site|website|url)\b", re.IGNORECASE),
    re.compile(r"\bextract\s+.+\s+from\s+https?://", re.IGNORECASE),
    re.compile(r"\bfill\s+(in\s+)?(the\s+)?(form|field)\b", re.IGNORECASE),
    re.compile(r"\bclick\s+(the\s+|on\s+)?(button|link|element)\b", re.IGNORECASE),
    re.compile(r"\bdownload\s+.+\s+from\s+https?://", re.IGNORECASE),
    re.compile(r"\bweb[-\s]?automation\b", re.IGNORECASE),
    re.compile(r"\bbrowse\s+(the\s+)?web\b", re.IGNORECASE),
    re.compile(r"\bbrowser[-\s]task\b", re.IGNORECASE),
)


def is_web_automation_intent(task: str) -> bool:
    """Return True when ``task`` looks like a web-automation request.

    Conservative — when in doubt, return False. The caller can still force
    routing by passing ``force=True`` to :func:`route`.
    """
    if not task:
        return False
    return any(p.search(task) for p in _INTENT_PATTERNS)


def route(
    task: str,
    *,
    force: bool = False,
    llm_provider: str = "browser_use",
    model: Optional[str] = None,
    cost_predictor: Optional[Any] = None,
    agent_bus: Optional[Any] = None,
) -> BrowserUseAdapter:
    """Return a configured :class:`BrowserUseAdapter` for ``task``.

    Raises:
        WebAutomationUnavailable: when intent does not match (and not forced),
            when the kill switch is active, or when the upstream package is
            not installed.
    """
    if not force and not is_web_automation_intent(task):
        raise WebAutomationUnavailable(
            "task does not match web-automation intent patterns; "
            "pass force=True to override"
        )
    if not is_browser_use_available():
        raise WebAutomationUnavailable(
            "browser_use is not installed. Run: uv sync --extra web-automation"
        )
    # Kill-switch is enforced inside BrowserUseAdapter.__init__ so the same
    # error envelope surfaces whether the caller goes through route() or
    # constructs the adapter directly.
    return BrowserUseAdapter(
        llm_provider=llm_provider,
        model=model,
        cost_predictor=cost_predictor,
        agent_bus=agent_bus,
    )


__all__ = ["is_web_automation_intent", "route", "WebAutomationUnavailable"]
