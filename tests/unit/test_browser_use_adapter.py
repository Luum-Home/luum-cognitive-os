# SCOPE: os-only
"""ADR-288 — unit tests for BrowserUseAdapter.

These tests never launch a real browser. They use injection seams
(``agent_factory``, ``chat_factory``) so ``browser_use`` need not be
installed for the suite to run.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from lib.browser_use_adapter import (
    BrowserUseAdapter,
    WebAutomationResult,
    WebAutomationUnavailable,
)


class _FakeHistory:
    """Mimics the subset of ``browser_use.AgentHistoryList`` the adapter reads."""

    def __init__(self, *, success=True, urls=None, screenshots=None,
                 final=None, usage=None, steps=3):
        self._success = success
        self.urls = urls or ["https://example.com/final"]
        self.screenshots = screenshots or ["/tmp/shot1.png"]
        self._final = final or {"headline": "hello"}
        self.usage = usage or {"input": 1200, "output": 800}
        self.history = list(range(steps))

    def is_successful(self):
        return self._success

    def final_result(self):
        return self._final


class _FakeAgent:
    def __init__(self, *, task, llm, max_steps=50, headless=True, history=None,
                 raise_exc=None):
        self.task = task
        self.llm = llm
        self.max_steps = max_steps
        self.headless = headless
        self._history = history or _FakeHistory()
        self._raise = raise_exc

    async def run(self, max_steps=None):
        if self._raise:
            raise self._raise
        return self._history


def _make_factories(history=None, raise_exc=None):
    captured = {}

    def chat_factory(provider, model):
        chat = MagicMock(name=f"chat:{provider}:{model}")
        captured["chat"] = chat
        captured["provider"] = provider
        captured["model"] = model
        return chat

    def agent_factory(*, task, llm, max_steps, headless):
        agent = _FakeAgent(
            task=task, llm=llm, max_steps=max_steps, headless=headless,
            history=history, raise_exc=raise_exc,
        )
        captured["agent"] = agent
        return agent

    return chat_factory, agent_factory, captured


# ---------------------------------------------------------------------------
# Kill switch
# ---------------------------------------------------------------------------

def test_kill_switch_blocks_construction(monkeypatch):
    monkeypatch.setenv("COS_DISABLE_WEB_AUTOMATION", "1")
    chat, agent, _ = _make_factories()
    with pytest.raises(WebAutomationUnavailable, match="kill_switch|disabled"):
        BrowserUseAdapter(chat_factory=chat, agent_factory=agent)


def test_kill_switch_blocks_runtime(monkeypatch):
    chat, agent, _ = _make_factories()
    adapter = BrowserUseAdapter(chat_factory=chat, agent_factory=agent)
    monkeypatch.setenv("COS_DISABLE_WEB_AUTOMATION", "1")
    with pytest.raises(WebAutomationUnavailable):
        asyncio.run(adapter.run_task("anything", max_steps=5))


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_run_task_success(monkeypatch):
    monkeypatch.delenv("COS_DISABLE_WEB_AUTOMATION", raising=False)
    chat, agent, captured = _make_factories()
    adapter = BrowserUseAdapter(
        llm_provider="anthropic", model="claude-sonnet-4",
        chat_factory=chat, agent_factory=agent,
    )
    result: WebAutomationResult = asyncio.run(
        adapter.run_task("Navigate and extract.", max_steps=20)
    )
    assert isinstance(result, WebAutomationResult)
    assert result.success is True
    assert result.final_url == "https://example.com/final"
    assert result.screenshots_paths == ["/tmp/shot1.png"]
    assert result.extracted_data == {"headline": "hello"}
    assert result.token_usage == {"input": 1200, "output": 800}
    assert result.steps == 3
    # The chat_factory must have been invoked with the requested provider/model.
    assert captured["provider"] == "anthropic"
    assert captured["model"] == "claude-sonnet-4"


def test_run_task_failure_returns_error(monkeypatch):
    monkeypatch.delenv("COS_DISABLE_WEB_AUTOMATION", raising=False)
    chat, agent, _ = _make_factories(raise_exc=RuntimeError("boom"))
    adapter = BrowserUseAdapter(chat_factory=chat, agent_factory=agent)
    result = asyncio.run(adapter.run_task("anything"))
    assert result.success is False
    assert "boom" in result.error


# ---------------------------------------------------------------------------
# Event emission
# ---------------------------------------------------------------------------

def test_emits_started_and_completed(monkeypatch):
    monkeypatch.delenv("COS_DISABLE_WEB_AUTOMATION", raising=False)
    chat, agent, _ = _make_factories()
    bus = MagicMock()
    adapter = BrowserUseAdapter(
        chat_factory=chat, agent_factory=agent, agent_bus=bus,
    )
    asyncio.run(adapter.run_task("Navigate to https://example.com.", max_steps=10))
    actions = [c.kwargs.get("action") for c in bus.progress.call_args_list]
    assert "web_automation.started" in actions
    assert "web_automation.completed" in actions


def test_emits_failed_on_error(monkeypatch):
    monkeypatch.delenv("COS_DISABLE_WEB_AUTOMATION", raising=False)
    chat, agent, _ = _make_factories(raise_exc=RuntimeError("nope"))
    bus = MagicMock()
    adapter = BrowserUseAdapter(
        chat_factory=chat, agent_factory=agent, agent_bus=bus,
    )
    asyncio.run(adapter.run_task("task"))
    actions = [c.kwargs.get("action") for c in bus.progress.call_args_list]
    assert "web_automation.failed" in actions


def test_bus_failure_does_not_break_run(monkeypatch):
    monkeypatch.delenv("COS_DISABLE_WEB_AUTOMATION", raising=False)
    chat, agent, _ = _make_factories()
    bus = MagicMock()
    bus.progress.side_effect = RuntimeError("bus down")
    adapter = BrowserUseAdapter(
        chat_factory=chat, agent_factory=agent, agent_bus=bus,
    )
    result = asyncio.run(adapter.run_task("task"))
    assert result.success is True


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------

def test_cost_via_predictor(monkeypatch):
    monkeypatch.delenv("COS_DISABLE_WEB_AUTOMATION", raising=False)
    chat, agent, _ = _make_factories()
    predictor = MagicMock(return_value=MagicMock(estimated_cost_usd=0.0123))
    adapter = BrowserUseAdapter(
        llm_provider="anthropic",
        chat_factory=chat, agent_factory=agent, cost_predictor=predictor,
    )
    result = asyncio.run(adapter.run_task("task"))
    assert result.cost_usd == pytest.approx(0.0123)
    predictor.assert_called_once()
    kwargs = predictor.call_args.kwargs
    assert kwargs["input_tokens"] == 1200
    assert kwargs["output_tokens"] == 800


def test_cost_chat_browser_use_pricing(monkeypatch):
    monkeypatch.delenv("COS_DISABLE_WEB_AUTOMATION", raising=False)
    chat, agent, _ = _make_factories()
    adapter = BrowserUseAdapter(
        llm_provider="browser_use",
        chat_factory=chat, agent_factory=agent,
    )
    result = asyncio.run(adapter.run_task("task"))
    # 1200 * 0.20/1M + 800 * 2.00/1M = 0.00024 + 0.0016 = 0.00184
    assert result.cost_usd == pytest.approx(1200 * 0.20 / 1_000_000 + 800 * 2.00 / 1_000_000)


def test_cost_unknown_provider_zero(monkeypatch):
    monkeypatch.delenv("COS_DISABLE_WEB_AUTOMATION", raising=False)
    chat, agent, _ = _make_factories()
    adapter = BrowserUseAdapter(
        llm_provider="mystery", chat_factory=chat, agent_factory=agent,
    )
    result = asyncio.run(adapter.run_task("task"))
    assert result.cost_usd == 0.0
