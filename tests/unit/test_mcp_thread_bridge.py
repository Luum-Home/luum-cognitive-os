"""Unit tests for lib.mcp_thread_bridge (ADR-290 Pattern 3)."""
from __future__ import annotations

import asyncio
import time

import pytest

from lib.mcp_thread_bridge import MCPThreadBridge


async def _value() -> str:
    await asyncio.sleep(0)
    return "ok"


async def _slow() -> str:
    await asyncio.sleep(1)
    return "late"


async def _raise() -> str:
    await asyncio.sleep(0)
    raise RuntimeError("from-coro")


def test_bridge_runs_coroutine_from_sync_context() -> None:
    with MCPThreadBridge() as bridge:
        assert bridge.call(_value(), timeout=1) == "ok"


def test_bridge_timeout_cancels_slow_coroutine() -> None:
    with MCPThreadBridge() as bridge:
        with pytest.raises(TimeoutError):
            bridge.call(_slow(), timeout=0.01)


def test_bridge_propagates_coroutine_exception() -> None:
    with MCPThreadBridge() as bridge:
        with pytest.raises(RuntimeError, match="from-coro"):
            bridge.call(_raise(), timeout=1)


def test_close_joins_worker_thread() -> None:
    bridge = MCPThreadBridge()
    assert bridge._thread is not None and bridge._thread.is_alive()
    bridge.close(join_timeout=2.0)
    # Give the OS a moment after join.
    deadline = time.monotonic() + 2.0
    while bridge._thread is not None and bridge._thread.is_alive():
        if time.monotonic() > deadline:
            break
    assert bridge._thread is None or not bridge._thread.is_alive()


def test_call_on_closed_bridge_raises() -> None:
    bridge = MCPThreadBridge()
    bridge.close()
    coro = _value()
    try:
        with pytest.raises(RuntimeError, match="closed"):
            bridge.call(coro, timeout=1)
    finally:
        coro.close()


def test_close_is_idempotent() -> None:
    bridge = MCPThreadBridge()
    bridge.close()
    # Second close must not raise.
    bridge.close()


def test_multiple_sequential_calls_share_loop() -> None:
    """The same bridge handles multiple calls without recreating the loop."""
    with MCPThreadBridge() as bridge:
        assert bridge.call(_value(), timeout=1) == "ok"
        assert bridge.call(_value(), timeout=1) == "ok"
        assert bridge.call(_value(), timeout=1) == "ok"
