# SCOPE: os-only
"""
File Mutation Queue — Per-file serialization for concurrent writes.

Ensures that concurrent modifications to the same file are serialized,
while modifications to different files proceed in parallel.

Ported from: Pi coding-agent file-mutation-queue.ts (MIT license)
Adapted to Python using threading.Lock per resolved path.

Key differences from our advisory-only concurrent-write-guard.sh:
- ACTUALLY serializes writes (not just warns)
- Symlink-aware path resolution
- Self-cleaning when queue drains
- Thread-safe for multi-agent scenarios
"""

import threading
import os
from pathlib import Path
from typing import Callable, TypeVar
from contextlib import contextmanager

T = TypeVar('T')


class FileMutationQueue:
    """Per-file lock manager that serializes concurrent mutations."""

    def __init__(self):
        # canonical path -> [lock, users]. `users` counts every thread that has
        # entered lock() and not yet left it, holder plus waiters, so eviction
        # can never race an acquire() that is already in flight.
        self._locks: dict[str, list] = {}
        self._meta_lock = threading.Lock()  # protects _locks dict

    def _resolve_path(self, file_path: str) -> str:
        """Resolve symlinks to canonical path (Pi pattern: realpathSync.native)"""
        try:
            return str(Path(file_path).resolve())
        except (OSError, ValueError):
            return os.path.abspath(file_path)

    @contextmanager
    def lock(self, file_path: str):
        """Context manager that serializes access to a file.

        Usage:
            with queue.lock("/path/to/file"):
                # read, modify, write the file
                pass
        """
        canonical = self._resolve_path(file_path)

        with self._meta_lock:
            entry = self._locks.get(canonical)
            if entry is None:
                entry = [threading.Lock(), 0]
                self._locks[canonical] = entry
            # Register as a user BEFORE acquiring: a thread blocked in
            # acquire() must keep the entry alive, otherwise the releasing
            # thread evicts it and the next arrival mints a second lock for
            # the same path — two threads then run the critical section at once.
            entry[1] += 1

        file_lock = entry[0]
        file_lock.acquire()
        try:
            yield
        finally:
            file_lock.release()
            self._release_user(canonical, entry)

    def _release_user(self, canonical: str, entry: list):
        """Drop this thread's claim, evicting the entry only when nobody is left."""
        with self._meta_lock:
            entry[1] -= 1
            if entry[1] <= 0 and self._locks.get(canonical) is entry:
                del self._locks[canonical]

    def execute(self, file_path: str, fn: Callable[[], T]) -> T:
        """Execute a function while holding the file lock.

        Usage:
            result = queue.execute("/path/to/file", lambda: write_file(...))
        """
        with self.lock(file_path):
            return fn()

    @property
    def active_locks(self) -> int:
        """Number of currently tracked file paths."""
        with self._meta_lock:
            return len(self._locks)


# Global singleton (like Pi's module-level Map)
_global_queue = FileMutationQueue()


@contextmanager
def with_file_mutation_lock(file_path: str):
    """Convenience wrapper using the global queue.

    Usage:
        with with_file_mutation_lock("/path/to/file"):
            content = read_file(path)
            write_file(path, modified_content)
    """
    with _global_queue.lock(file_path):
        yield


def execute_with_file_lock(file_path: str, fn: Callable[[], T]) -> T:
    """Convenience wrapper using the global queue."""
    return _global_queue.execute(file_path, fn)
