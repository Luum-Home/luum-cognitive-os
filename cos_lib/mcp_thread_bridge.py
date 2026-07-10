# SCOPE: os-only
"""Synchronous-to-asynchronous bridge for MCP transport (ADR-290 Pattern 3).

A synchronous caller (hook script, CLI tool, batch utility) sometimes needs
to invoke an ``async`` coroutine — typically against a long-lived MCP client
— without bringing up its own event loop on every call. Reusing the parent
thread's event loop is unsafe (the loop may already be running, or there may
not be one); spawning a fresh loop per call is wasteful and loses connection
state.

:class:`MCPThreadBridge` owns one dedicated worker thread running a single
private :mod:`asyncio` event loop. ``bridge.call(coro, timeout=30)``
schedules the coroutine via :func:`asyncio.run_coroutine_threadsafe`, blocks
the calling thread on the resulting :class:`concurrent.futures.Future`, and
either returns the coroutine's value, re-raises its exception, or raises
:class:`TimeoutError` if the timeout elapses.

The bridge is also a context manager. Forgetting to ``close()`` will leak the
worker thread until process exit.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from types import TracebackType
from typing import Any, Coroutine


class MCPThreadBridge:
    """Background asyncio loop usable from synchronous callers."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._closed = False
        self._start()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _start(self) -> None:
        def runner() -> None:
            loop = asyncio.new_event_loop()
            self._loop = loop
            asyncio.set_event_loop(loop)
            self._started.set()
            try:
                loop.run_forever()
            finally:
                # Drain pending tasks then close.
                try:
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                finally:
                    loop.close()

        self._thread = threading.Thread(
            target=runner,
            name="mcp-thread-bridge",
            daemon=True,
        )
        self._thread.start()
        # Wait for the loop to exist before returning control.
        if not self._started.wait(timeout=5):
            raise RuntimeError("MCPThreadBridge worker failed to start")

    def close(self, *, join_timeout: float = 5.0) -> None:
        """Stop the worker loop and join the thread.

        Idempotent. Safe to call from any thread other than the worker.
        """
        if self._closed:
            return
        self._closed = True
        loop = self._loop
        thread = self._thread
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        if thread is not None:
            thread.join(timeout=join_timeout)

    # ------------------------------------------------------------------
    # Call
    # ------------------------------------------------------------------

    def call(self, coro: Coroutine[Any, Any, Any], *, timeout: float = 30.0) -> Any:
        """Submit ``coro`` to the worker loop and block until it completes.

        Returns the coroutine's value. If the coroutine raises, that
        exception is re-raised here. If the coroutine does not complete
        within ``timeout`` seconds, raises :class:`TimeoutError`.
        """
        if self._closed:
            raise RuntimeError("MCPThreadBridge is closed")
        loop = self._loop
        if loop is None:
            raise RuntimeError("MCPThreadBridge has no event loop")
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise TimeoutError(
                f"MCPThreadBridge.call exceeded {timeout}s"
            ) from exc

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "MCPThreadBridge":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
