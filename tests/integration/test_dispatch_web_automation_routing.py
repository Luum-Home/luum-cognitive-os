# SCOPE: os-only
"""ADR-288 — integration tests for the web-automation router.

Validates intent detection, kill-switch handling, and the unavailable
fallback when ``browser_use`` is not installed. No real browser is launched.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from lib.web_automation_router import (
    WebAutomationUnavailable,
    is_web_automation_intent,
    route,
)


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("task", [
    "Navigate to https://example.com and read the price.",
    "Open the website https://foo.bar/ and click the login button.",
    "Scrape the page at example.com",
    "Extract the headlines from https://news.example.com",
    "Fill in the form on the settings page",
    "Click the button labelled 'Submit'",
    "Download the report from https://example.com/report.pdf",
    "Run a web-automation task on the dashboard",
    "Browse the web for benchmark data",
    "This is a browser-task to drive Chromium",
])
def test_positive_intent(task):
    assert is_web_automation_intent(task) is True


@pytest.mark.parametrize("task", [
    "Summarise this codebase.",
    "Refactor the dispatch module.",
    "Write a unit test for the parser.",
    "",
    "Click? maybe later.",  # 'click' without object noun
])
def test_negative_intent(task):
    assert is_web_automation_intent(task) is False


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def test_route_rejects_non_intent_without_force(monkeypatch):
    monkeypatch.delenv("COS_DISABLE_WEB_AUTOMATION", raising=False)
    with pytest.raises(WebAutomationUnavailable, match="intent"):
        route("Refactor the parser.")


def test_route_unavailable_when_package_missing(monkeypatch):
    monkeypatch.delenv("COS_DISABLE_WEB_AUTOMATION", raising=False)
    with patch("lib.web_automation_router.is_browser_use_available", return_value=False):
        with pytest.raises(WebAutomationUnavailable, match="not installed"):
            route("Navigate to https://example.com and click login", force=False)


def test_route_returns_adapter_when_available(monkeypatch):
    monkeypatch.delenv("COS_DISABLE_WEB_AUTOMATION", raising=False)
    # Pretend browser_use is importable AND patch the adapter's availability
    # gate so __init__ doesn't actually try to import.
    with patch("lib.web_automation_router.is_browser_use_available", return_value=True), \
         patch("lib.browser_use_adapter.is_browser_use_available", return_value=True):
        adapter = route(
            "Navigate to https://example.com and extract the title",
            cost_predictor=MagicMock(),
            agent_bus=MagicMock(),
        )
    from lib.browser_use_adapter import BrowserUseAdapter
    assert isinstance(adapter, BrowserUseAdapter)


def test_route_kill_switch_blocks(monkeypatch):
    monkeypatch.setenv("COS_DISABLE_WEB_AUTOMATION", "1")
    with patch("lib.web_automation_router.is_browser_use_available", return_value=True), \
         patch("lib.browser_use_adapter.is_browser_use_available", return_value=True):
        with pytest.raises(WebAutomationUnavailable):
            route("Navigate to https://example.com", force=True)


def test_route_force_overrides_intent(monkeypatch):
    monkeypatch.delenv("COS_DISABLE_WEB_AUTOMATION", raising=False)
    with patch("lib.web_automation_router.is_browser_use_available", return_value=True), \
         patch("lib.browser_use_adapter.is_browser_use_available", return_value=True):
        adapter = route("not obviously web", force=True)
    from lib.browser_use_adapter import BrowserUseAdapter
    assert isinstance(adapter, BrowserUseAdapter)


# ---------------------------------------------------------------------------
# Smoke: end-to-end through router with injected factories
# ---------------------------------------------------------------------------

def test_smoke_end_to_end(monkeypatch):
    """Mocked end-to-end: router -> adapter -> fake agent -> result."""
    monkeypatch.delenv("COS_DISABLE_WEB_AUTOMATION", raising=False)

    from lib.browser_use_adapter import BrowserUseAdapter

    class _History:
        urls = ["https://example.com/done"]
        screenshots = []
        history = [1, 2]
        usage = {"input": 100, "output": 50}
        def is_successful(self): return True
        def final_result(self): return {"ok": True}

    class _Agent:
        def __init__(self, **kw): pass
        async def run(self, max_steps=None): return _History()

    bus = MagicMock()
    adapter = BrowserUseAdapter(
        llm_provider="browser_use",
        chat_factory=lambda p, m: MagicMock(),
        agent_factory=lambda **kw: _Agent(**kw),
        agent_bus=bus,
    )
    result = asyncio.run(adapter.run_task(
        "Navigate to https://example.com and confirm.", max_steps=5,
    ))
    assert result.success is True
    assert result.final_url == "https://example.com/done"
    assert result.token_usage == {"input": 100, "output": 50}
    assert result.cost_usd > 0  # ChatBrowserUse pricing applied
    # Bus saw at least started + completed events.
    actions = {c.kwargs.get("action") for c in bus.progress.call_args_list}
    assert "web_automation.started" in actions
    assert "web_automation.completed" in actions
