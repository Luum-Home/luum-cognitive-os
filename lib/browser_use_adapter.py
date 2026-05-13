# SCOPE: os-only
"""ADR-288 — adapter that wraps ``browser_use.Agent`` for COS dispatch.

This module is the **only** sanctioned import site for ``browser_use``. All
other COS code paths consume :class:`WebAutomationResult` or go through
:mod:`lib.web_automation_router`.

Upstream attribution: this adapter targets the public API of the MIT-licensed
``browser-use`` project (https://github.com/browser-use/browser-use). No source
is copied — we import its public exports (``Agent``, ``ChatAnthropic``,
``ChatOpenAI``, ``ChatBrowserUse``) and observe their public contract.

Public surface:
    - :class:`BrowserUseAdapter`
    - :class:`WebAutomationResult`
    - :class:`WebAutomationUnavailable`
    - :func:`is_browser_use_available`
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Upstream pricing for ChatBrowserUse, verified 2026-05-13 (ADR-288).
# $0.20 per million input tokens, $2.00 per million output tokens.
_CHAT_BROWSER_USE_INPUT_PER_TOKEN = 0.20 / 1_000_000
_CHAT_BROWSER_USE_OUTPUT_PER_TOKEN = 2.00 / 1_000_000


class WebAutomationUnavailable(RuntimeError):
    """Raised when web automation cannot be served (missing dep or kill switch)."""


@dataclass
class WebAutomationResult:
    """Typed result of a browser-use run.

    Attributes:
        success: True iff the agent reached a terminal success state.
        final_url: Last URL the browser landed on, if known.
        screenshots_paths: Paths to any screenshots captured by the agent.
        extracted_data: Structured data the agent returned (free-form dict).
        error: Error message when ``success`` is False; empty otherwise.
        token_usage: ``{"input": int, "output": int}`` aggregated across steps.
        cost_usd: Best-effort cost estimate for the run.
        steps: Number of steps the agent executed before terminating.
    """

    success: bool
    final_url: str = ""
    screenshots_paths: list[str] = field(default_factory=list)
    extracted_data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    token_usage: dict[str, int] = field(default_factory=lambda: {"input": 0, "output": 0})
    cost_usd: float = 0.0
    steps: int = 0


def is_browser_use_available() -> bool:
    """Return True if the ``browser_use`` package is importable."""
    try:
        import importlib

        importlib.import_module("browser_use")
        return True
    except Exception:  # noqa: BLE001 — defensive: any ImportError variant
        return False


def _kill_switch_active() -> bool:
    """True if ``COS_DISABLE_WEB_AUTOMATION=1`` is set."""
    return os.environ.get("COS_DISABLE_WEB_AUTOMATION", "").strip() == "1"


class BrowserUseAdapter:
    """Wraps :class:`browser_use.Agent` with COS event + cost integration.

    Args:
        llm_provider: One of ``"anthropic"``, ``"openai"``, ``"browser_use"``.
            Selects which ``Chat*`` class from ``browser_use.llm`` is
            instantiated. Defaults to ``"browser_use"`` (the hosted endpoint).
        model: Optional model hint passed through to the chat class. When
            ``None`` the upstream default is used.
        cost_predictor: Optional callable matching the signature of
            :func:`lib.dispatch_cost_predictor.predict_call_cost`. When
            provided, each step's tokens are routed through it; otherwise the
            adapter computes cost directly for ``ChatBrowserUse`` and reports
            ``0.0`` for unknown providers.
        agent_bus: Optional ``AgentPublisher``-shaped object. When provided,
            the adapter calls ``agent_bus.progress(...)`` on ``started``,
            ``step``, ``completed``, and ``failed`` events.
        agent_factory: Test seam — when provided, called instead of
            ``browser_use.Agent`` so unit tests can inject a fake.
        chat_factory: Test seam — when provided, called instead of selecting a
            ``Chat*`` class from ``browser_use.llm``.
    """

    def __init__(
        self,
        llm_provider: str = "browser_use",
        model: Optional[str] = None,
        cost_predictor: Optional[Any] = None,
        agent_bus: Optional[Any] = None,
        agent_factory: Optional[Any] = None,
        chat_factory: Optional[Any] = None,
    ) -> None:
        if _kill_switch_active():
            raise WebAutomationUnavailable(
                "COS_DISABLE_WEB_AUTOMATION=1 — web automation is disabled by operator"
            )
        if agent_factory is None and not is_browser_use_available():
            raise WebAutomationUnavailable(
                "browser_use is not installed. Run: uv sync --extra web-automation"
            )

        self.llm_provider = llm_provider
        self.model = model
        self._cost_predictor = cost_predictor
        self._agent_bus = agent_bus
        self._agent_factory = agent_factory
        self._chat_factory = chat_factory

    # ------------------------------------------------------------------
    # event emission
    # ------------------------------------------------------------------

    def _emit(self, event: str, **payload: Any) -> None:
        if self._agent_bus is None:
            return
        try:
            # AgentPublisher.progress(tool, file, action, step_current, step_total)
            self._agent_bus.progress(
                tool="browser_use",
                file=payload.get("final_url", ""),
                action=f"web_automation.{event}",
                step_current=int(payload.get("step", 0) or 0),
                step_total=int(payload.get("max_steps", 0) or 0),
            )
        except Exception as exc:  # noqa: BLE001 — event emission must not break the run
            logger.debug("agent_bus emit failed for %s: %s", event, exc)

    # ------------------------------------------------------------------
    # cost
    # ------------------------------------------------------------------

    def _compute_cost(self, tokens_in: int, tokens_out: int) -> float:
        if self._cost_predictor is not None:
            try:
                prediction = self._cost_predictor(
                    self.llm_provider,
                    model_hint=self.model,
                    input_tokens=tokens_in,
                    output_tokens=tokens_out,
                )
                # CostPrediction or dict-like
                if hasattr(prediction, "estimated_cost_usd"):
                    return float(prediction.estimated_cost_usd)
                if isinstance(prediction, dict):
                    return float(prediction.get("estimated_cost_usd", 0.0))
            except Exception as exc:  # noqa: BLE001
                logger.debug("cost_predictor failed; falling back: %s", exc)

        if self.llm_provider == "browser_use":
            return (
                tokens_in * _CHAT_BROWSER_USE_INPUT_PER_TOKEN
                + tokens_out * _CHAT_BROWSER_USE_OUTPUT_PER_TOKEN
            )
        return 0.0

    # ------------------------------------------------------------------
    # llm + agent construction
    # ------------------------------------------------------------------

    def _build_chat(self) -> Any:
        if self._chat_factory is not None:
            return self._chat_factory(self.llm_provider, self.model)

        # Lazy import: keep cold-start cheap for callers that never reach here.
        if self.llm_provider == "anthropic":
            from browser_use import ChatAnthropic

            return ChatAnthropic(model=self.model) if self.model else ChatAnthropic()
        if self.llm_provider == "openai":
            from browser_use import ChatOpenAI

            return ChatOpenAI(model=self.model) if self.model else ChatOpenAI()
        if self.llm_provider == "browser_use":
            from browser_use import ChatBrowserUse

            return ChatBrowserUse(model=self.model) if self.model else ChatBrowserUse()
        raise WebAutomationUnavailable(f"unknown llm_provider: {self.llm_provider}")

    def _build_agent(self, task: str, llm: Any, max_steps: int, headless: bool) -> Any:
        if self._agent_factory is not None:
            return self._agent_factory(task=task, llm=llm, max_steps=max_steps, headless=headless)
        from browser_use import Agent  # lazy

        # ``browser_use.Agent`` accepts at minimum (task, llm). Profile / headless
        # are configured via BrowserProfile; we keep this thin and pass through
        # only the fields the upstream signature stabilises on across 0.12.x.
        return Agent(task=task, llm=llm)

    # ------------------------------------------------------------------
    # main entry point
    # ------------------------------------------------------------------

    async def run_task(
        self,
        task: str,
        *,
        max_steps: int = 50,
        headless: bool = True,
    ) -> WebAutomationResult:
        """Execute a web-automation task and return a typed result.

        The kill switch is re-checked at the start of every call so a
        long-lived adapter cannot continue serving after the operator
        disables web automation.
        """
        if _kill_switch_active():
            raise WebAutomationUnavailable(
                "COS_DISABLE_WEB_AUTOMATION=1 — web automation is disabled by operator"
            )

        self._emit("started", max_steps=max_steps)

        llm = self._build_chat()
        agent = self._build_agent(task=task, llm=llm, max_steps=max_steps, headless=headless)

        try:
            history = await agent.run(max_steps=max_steps)
        except TypeError:
            # Older 0.12.x signatures: ``agent.run()`` with no kwargs.
            history = await agent.run()
        except Exception as exc:  # noqa: BLE001
            self._emit("failed", error=str(exc))
            return WebAutomationResult(success=False, error=str(exc))

        result = self._summarise(history)
        result.cost_usd = self._compute_cost(
            result.token_usage["input"], result.token_usage["output"]
        )
        self._emit(
            "completed" if result.success else "failed",
            step=result.steps,
            max_steps=max_steps,
            final_url=result.final_url,
        )
        return result

    def run_task_sync(self, task: str, **kwargs: Any) -> WebAutomationResult:
        """Synchronous convenience wrapper for callers outside an event loop."""
        return asyncio.run(self.run_task(task, **kwargs))

    # ------------------------------------------------------------------
    # history summarisation
    # ------------------------------------------------------------------

    @staticmethod
    def _summarise(history: Any) -> WebAutomationResult:
        """Extract a :class:`WebAutomationResult` from a ``browser_use`` history.

        We touch only the attributes the upstream public API documents:
        ``is_done()``/``is_successful()`` style accessors and ``final_result``.
        Anything else is best-effort and degrades gracefully.
        """
        success = False
        final_url = ""
        screenshots: list[str] = []
        extracted: dict[str, Any] = {}
        error = ""
        tokens_in = 0
        tokens_out = 0
        steps = 0

        for accessor in ("is_successful", "is_done"):
            fn = getattr(history, accessor, None)
            if callable(fn):
                try:
                    if bool(fn()):
                        success = True
                        break
                except Exception:  # noqa: BLE001
                    continue

        for attr in ("urls", "visited_urls"):
            urls = getattr(history, attr, None)
            if urls:
                try:
                    final_url = str(list(urls)[-1])
                    break
                except Exception:  # noqa: BLE001
                    continue

        screenshots_attr = getattr(history, "screenshots", None) or []
        try:
            screenshots = [str(p) for p in screenshots_attr]
        except Exception:  # noqa: BLE001
            screenshots = []

        final_result = getattr(history, "final_result", None)
        if callable(final_result):
            try:
                payload = final_result()
                if isinstance(payload, dict):
                    extracted = payload
                elif payload is not None:
                    extracted = {"value": payload}
            except Exception as exc:  # noqa: BLE001
                error = str(exc)

        usage = getattr(history, "usage", None) or getattr(history, "token_usage", None)
        if isinstance(usage, dict):
            tokens_in = int(usage.get("input", usage.get("prompt_tokens", 0)) or 0)
            tokens_out = int(usage.get("output", usage.get("completion_tokens", 0)) or 0)

        history_list = getattr(history, "history", None)
        if isinstance(history_list, list):
            steps = len(history_list)
        else:
            steps_attr = getattr(history, "steps", None)
            if isinstance(steps_attr, int):
                steps = steps_attr

        return WebAutomationResult(
            success=success,
            final_url=final_url,
            screenshots_paths=screenshots,
            extracted_data=extracted,
            error=error,
            token_usage={"input": tokens_in, "output": tokens_out},
            steps=steps,
        )


__all__ = [
    "BrowserUseAdapter",
    "WebAutomationResult",
    "WebAutomationUnavailable",
    "is_browser_use_available",
]
