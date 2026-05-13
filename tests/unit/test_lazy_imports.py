"""Unit tests for lib.lazy_imports (ADR-290 Pattern 1)."""
from __future__ import annotations

import threading

import pytest

from lib.lazy_imports import LazyImport


def test_factory_called_exactly_once_under_concurrent_first_access():
    """10 threads racing first ``get()`` must call factory exactly once."""
    counter = {"n": 0}
    barrier = threading.Barrier(10)

    def factory():
        counter["n"] += 1
        return object()

    lazy = LazyImport(factory)
    results: list[object] = []
    results_lock = threading.Lock()
    errors: list[BaseException] = []

    def worker():
        try:
            # Block until all threads are ready, maximising the race window
            # before the first LazyImport.get() call. The factory itself runs
            # under the LazyImport lock, so a barrier inside the factory would
            # deadlock by design.
            barrier.wait(timeout=5)
            value = lazy.get()
            with results_lock:
                results.append(value)
        except BaseException as exc:  # noqa: BLE001 - propagate for assertion
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, errors
    assert counter["n"] == 1
    assert len(results) == 10
    # Every thread observed the same object.
    first = results[0]
    for r in results[1:]:
        assert r is first


def test_loaded_transitions_false_to_true():
    lazy = LazyImport(lambda: 42)
    assert lazy.loaded is False
    assert lazy.get() == 42
    assert lazy.loaded is True
    # Subsequent calls do not reset the flag.
    assert lazy.get() == 42
    assert lazy.loaded is True


def test_instances_are_independent():
    """Two LazyImport instances do not share state."""
    a = LazyImport(lambda: "A")
    b = LazyImport(lambda: "B")
    assert a.loaded is False
    assert b.loaded is False
    assert a.get() == "A"
    assert a.loaded is True
    assert b.loaded is False  # independence
    assert b.get() == "B"
    assert b.loaded is True


def test_non_callable_factory_rejected():
    with pytest.raises(TypeError):
        LazyImport(123)  # type: ignore[arg-type]


def test_factory_exception_propagates_and_loaded_stays_false():
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        raise RuntimeError("boom")

    lazy = LazyImport(factory)
    with pytest.raises(RuntimeError, match="boom"):
        lazy.get()
    assert lazy.loaded is False
    # Retry behaviour — factory is invoked again on next get().
    with pytest.raises(RuntimeError):
        lazy.get()
    assert calls["n"] == 2
