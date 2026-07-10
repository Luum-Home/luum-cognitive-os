# SCOPE: os-only
"""Lazy import primitive (ADR-290 Pattern 1).

A thread-safe, double-checked-locking wrapper around a factory that resolves
a heavy import (or any expensive object) exactly once, lazily, on first use.

Why
---
Several ``lib/*.py`` modules import ``yaml``, ``rich``, ``litellm``, or
``openai`` at module-load time. Hook bodies that never reach the code path
needing the import still pay the cost. ``LazyImport`` shifts the cost to the
first ``.get()`` call and makes the deferred-load pattern reusable.

Contract
--------
- ``factory`` is called **exactly once**, even under concurrent first access
  from multiple threads.
- After the first successful call, every subsequent ``.get()`` is a fast
  attribute access guarded by a ``loaded`` flag check (no lock acquisition).
- ``loaded`` is a read-only property: ``False`` before resolution,
  ``True`` after.
- Instances are independent: one ``LazyImport`` does not influence another.
- If ``factory`` raises, the exception propagates and ``loaded`` remains
  ``False``; the next ``.get()`` will retry.
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")


class LazyImport(Generic[T]):
    """Lazy, thread-safe wrapper resolving ``factory`` exactly once."""

    __slots__ = ("_factory", "_value", "_loaded", "_lock")

    def __init__(self, factory: Callable[[], T]) -> None:
        if not callable(factory):
            raise TypeError("LazyImport factory must be callable")
        self._factory: Callable[[], T] = factory
        self._value: Any = None
        self._loaded: bool = False
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        """Whether the factory has been invoked successfully."""
        return self._loaded

    def get(self) -> T:
        """Return the resolved value, invoking the factory on first call.

        Subsequent calls are lock-free fast path: the ``loaded`` flag is read
        without acquiring the lock. The first call uses double-checked locking
        to guarantee ``factory`` is invoked at most once across threads.
        """
        # Fast path — already loaded, no lock.
        if self._loaded:
            return self._value  # type: ignore[no-any-return]

        # Slow path — acquire lock and re-check.
        with self._lock:
            if self._loaded:
                return self._value  # type: ignore[no-any-return]
            value = self._factory()
            self._value = value
            self._loaded = True
            return value
