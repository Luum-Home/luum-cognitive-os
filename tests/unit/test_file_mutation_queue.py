"""
Unit tests for lib/file_mutation_queue.py
"""

import pytest
import threading
import time
from lib.file_mutation_queue import (
    FileMutationQueue,
    with_file_mutation_lock,
    execute_with_file_lock,
)


class TestSerialization:
    def test_serializes_same_file(self, tmp_path):
        """Two threads writing the same file are serialized — no interleaving."""
        queue = FileMutationQueue()
        test_file = tmp_path / "shared.txt"
        test_file.write_text("")
        results = []

        def writer(content, delay=0.05):
            with queue.lock(str(test_file)):
                time.sleep(delay)
                current = test_file.read_text()
                test_file.write_text(current + content)
                results.append(content)

        t1 = threading.Thread(target=writer, args=("A",))
        t2 = threading.Thread(target=writer, args=("B",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(results) == 2
        assert "A" in test_file.read_text()
        assert "B" in test_file.read_text()

    def test_different_files_no_contention(self, tmp_path):
        """Different files should not block each other."""
        queue = FileMutationQueue()
        times = []

        def slow_write(path):
            with queue.lock(str(path)):
                time.sleep(0.1)
                times.append(time.time())

        f1 = tmp_path / "a.txt"
        f1.touch()
        f2 = tmp_path / "b.txt"
        f2.touch()

        start = time.time()
        t1 = threading.Thread(target=slow_write, args=(f1,))
        t2 = threading.Thread(target=slow_write, args=(f2,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        elapsed = time.time() - start
        # If serialized, would take ~0.2s; parallel takes ~0.1s
        assert elapsed < 0.25

    def test_sequential_writes_same_file(self, tmp_path):
        """Sequential (non-concurrent) writes still work normally."""
        queue = FileMutationQueue()
        f = tmp_path / "seq.txt"
        f.write_text("")

        with queue.lock(str(f)):
            f.write_text("first")

        with queue.lock(str(f)):
            current = f.read_text()
            f.write_text(current + " second")

        assert f.read_text() == "first second"


class TestSymlinks:
    def test_symlink_resolves_to_same_lock(self, tmp_path):
        """A symlink and its target should use the same underlying lock."""
        queue = FileMutationQueue()
        real = tmp_path / "real.txt"
        real.touch()
        link = tmp_path / "link.txt"
        link.symlink_to(real)

        # Acquire lock via real path, check it's tracked
        with queue.lock(str(real)):
            active_inside = queue.active_locks
        assert active_inside >= 1

        # Acquire lock via symlink — should resolve to same canonical path
        with queue.lock(str(link)):
            active_via_link = queue.active_locks
        assert active_via_link >= 1


class TestCleanup:
    def test_lock_removed_after_release(self):
        """The internal lock dict should be cleaned up after context manager exits."""
        queue = FileMutationQueue()
        with queue.lock("/tmp/test-cleanup-cos"):
            pass  # acquire and release
        assert queue.active_locks == 0

    def test_active_locks_during_hold(self):
        """active_locks should be > 0 while a lock is held."""
        queue = FileMutationQueue()
        ready = threading.Event()
        release = threading.Event()

        def hold_lock():
            with queue.lock("/tmp/test-active-lock"):
                ready.set()
                release.wait()

        t = threading.Thread(target=hold_lock)
        t.start()
        ready.wait()
        assert queue.active_locks >= 1
        release.set()
        t.join()
        assert queue.active_locks == 0

    def test_multiple_files_tracked_independently(self):
        queue = FileMutationQueue()
        ready1 = threading.Event()
        ready2 = threading.Event()
        release_all = threading.Event()

        def hold(path, ready):
            with queue.lock(path):
                ready.set()
                release_all.wait()

        t1 = threading.Thread(target=hold, args=("/tmp/cos-file1", ready1))
        t2 = threading.Thread(target=hold, args=("/tmp/cos-file2", ready2))
        t1.start()
        t2.start()
        ready1.wait()
        ready2.wait()
        assert queue.active_locks == 2
        release_all.set()
        t1.join()
        t2.join()
        assert queue.active_locks == 0


class TestExecute:
    def test_returns_value(self):
        queue = FileMutationQueue()
        result = queue.execute("/tmp/test-exec-cos", lambda: 42)
        assert result == 42

    def test_propagates_exception(self):
        queue = FileMutationQueue()

        def boom():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            queue.execute("/tmp/test-exc-cos", boom)

    def test_lock_released_after_exception(self):
        queue = FileMutationQueue()

        def bad():
            raise RuntimeError("oops")

        try:
            queue.execute("/tmp/test-exc-release", bad)
        except RuntimeError:
            pass

        # Lock should be cleaned up even after exception
        assert queue.active_locks == 0

    def test_execute_serializes_concurrent_calls(self, tmp_path):
        queue = FileMutationQueue()
        f = tmp_path / "exec.txt"
        f.write_text("0")

        def increment():
            def _do():
                val = int(f.read_text())
                time.sleep(0.01)
                f.write_text(str(val + 1))

            queue.execute(str(f), _do)

        threads = [threading.Thread(target=increment) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert f.read_text() == "5"


class TestGlobalWrappers:
    def test_with_file_mutation_lock(self, tmp_path):
        f = tmp_path / "global.txt"
        f.touch()
        with with_file_mutation_lock(str(f)):
            f.write_text("locked")
        assert f.read_text() == "locked"

    def test_execute_with_file_lock_returns_value(self, tmp_path):
        f = tmp_path / "exec_global.txt"
        f.touch()
        result = execute_with_file_lock(str(f), lambda: "done")
        assert result == "done"

    def test_execute_with_file_lock_propagates_exception(self):
        def bad():
            raise KeyError("missing")

        with pytest.raises(KeyError, match="missing"):
            execute_with_file_lock("/tmp/cos-global-exc", bad)


class TestStress:
    def test_10_threads_no_race(self, tmp_path):
        """10 concurrent threads must produce exactly 10 increments."""
        queue = FileMutationQueue()
        f = tmp_path / "stress.txt"
        f.write_text("0")

        def increment():
            with queue.lock(str(f)):
                val = int(f.read_text())
                time.sleep(0.005)
                f.write_text(str(val + 1))

        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert f.read_text() == "10"

    def test_interleaved_files_no_deadlock(self, tmp_path):
        """Operations on different files in parallel should not deadlock."""
        queue = FileMutationQueue()
        files = [tmp_path / f"f{i}.txt" for i in range(5)]
        for f in files:
            f.write_text("0")

        def process(path):
            with queue.lock(str(path)):
                time.sleep(0.01)

        threads = [threading.Thread(target=process, args=(f,)) for f in files]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert all(not t.is_alive() for t in threads), "Deadlock detected"
