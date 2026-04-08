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
from typing import Callable, TypeVar, Any
from contextlib import contextmanager

T = TypeVar('T')


class FileMutationQueue:
    """Per-file lock manager that serializes concurrent mutations."""

    def __init__(self):
        self._locks: dict[str, threading.Lock] = {}
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
            if canonical not in self._locks:
                self._locks[canonical] = threading.Lock()
            file_lock = self._locks[canonical]

        file_lock.acquire()
        try:
            yield
        finally:
            file_lock.release()
            # Clean up if no one else is waiting
            self._try_cleanup(canonical)

    def _try_cleanup(self, canonical: str):
        """Remove lock from dict if no one is using it (Pi's self-cleaning pattern)"""
        with self._meta_lock:
            if canonical in self._locks:
                lock = self._locks[canonical]
                # Only remove if the lock is not currently held
                if not lock.locked():
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
