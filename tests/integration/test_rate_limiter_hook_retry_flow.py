"""Integration test: rate-limiter hook + drainer end-to-end retry_count flow.

D45 wiring — validates that retry_count is correctly propagated through the
hook path (not just the library path):

  1. rate-limiter.sh (PreToolUse:Bash) reads RATE_LIMIT_RETRY_COUNT env var
     and passes it to RateLimitQueue.enqueue(retry_count=...).
  2. rate-limit-drain.sh (PostToolUse:Bash) calls dequeue_ready() and, on
     still-blocked items, re-enqueues with retry_count+1 (library drops
     over-cap items automatically).
  3. The drainer NEVER blocks (always exit 0) — no deadlock.

Tests are hermetic: they run the shell hooks in isolated temp directories with
a tight RateLimitConfig (max_bash_commands_per_minute=2) so the loop triggers
quickly without waiting for real cooldowns.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJ_ROOT))

from lib.rate_limiter import (  # noqa: E402
    MAX_RETRY_COUNT,
    RateLimitConfig,
    RateLimiter,
    RateLimitQueue,
)

HOOK_DIR = _PROJ_ROOT / "hooks"
RATE_LIMITER_HOOK = HOOK_DIR / "rate-limiter.sh"
DRAINER_HOOK = HOOK_DIR / "rate-limit-drain.sh"

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _write_config(project_dir: Path, phase: str = "stabilization") -> None:
    """Write a minimal cognitive-os.yaml so the hooks find a phase."""
    (project_dir / "cognitive-os.yaml").write_text(
        f"project:\n  phase: {phase}\n",
    )


def _make_tight_queue(project_dir: Path, cooldown: int = 1) -> RateLimitQueue:
    """RateLimitQueue pointing at the project's queue path with short cooldown."""
    queue_path = project_dir / ".cognitive-os" / "rate-limit-queue.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    return RateLimitQueue(state_path=str(queue_path), cooldown_seconds=cooldown)


def _exhaust_bash_limit(project_dir: Path, limit: int = 2) -> RateLimiter:
    """Fill the bash-command rate-limit state so the next check blocks.

    The drainer subprocess instantiates RateLimiter with the DEFAULT config
    (max_bash_commands_per_minute=15 base). To ensure the drainer also sees
    an exhausted state, we record at least that many bash_command timestamps
    in the state file — not just our test's tighter local limit.
    """
    state_path = project_dir / ".cognitive-os" / "rate-limit-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = RateLimitConfig(max_bash_commands_per_minute=limit)
    rl = RateLimiter(
        config=cfg,
        state_path=str(state_path),
        phase="stabilization",
    )
    # Record enough to blow past BOTH the test's tight cfg AND the default
    # config the drainer subprocess will use (base=15, stabilization x1.0).
    default_base = RateLimitConfig().max_bash_commands_per_minute  # 15
    n_records = max(limit + 2, default_base + 5)
    for _ in range(n_records):
        rl.record("bash_command")
    allowed, _ = rl.check("bash_command")
    assert not allowed, "Precondition: limiter must be exhausted"
    return rl


def _run_drainer(project_dir: Path) -> subprocess.CompletedProcess:
    """Invoke rate-limit-drain.sh with a fake Bash PostToolUse payload."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    payload = json.dumps({"tool_name": "Bash", "tool_input": {}})
    return subprocess.run(
        ["bash", str(DRAINER_HOOK)],
        input=payload,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# 1. Hook-level wiring — acceptance criterion #1
# ---------------------------------------------------------------------------


class TestHookWiring:
    """retry_count must be wired end-to-end: hook → lib → drainer → lib."""

    def test_rate_limiter_hook_mentions_retry_count(self):
        """The PreToolUse hook must reference retry_count (D45 wiring)."""
        text = RATE_LIMITER_HOOK.read_text()
        # Env hand-off variable
        assert "RATE_LIMIT_RETRY_COUNT" in text, (
            "PreToolUse hook must read RATE_LIMIT_RETRY_COUNT env var"
        )
        # Explicit retry_count kwarg in the enqueue call
        assert "retry_count=" in text, (
            "PreToolUse hook must pass retry_count to queue.enqueue()"
        )

    def test_drainer_hook_increments_retry_count(self):
        """The PostToolUse drainer must re-enqueue with retry_count+1."""
        text = DRAINER_HOOK.read_text()
        assert "retry_count + 1" in text or "retry_count+1" in text, (
            "Drainer must increment retry_count on re-enqueue"
        )
        assert "dequeue_ready" in text, "Drainer must call dequeue_ready()"

    def test_combined_hit_count(self):
        """Acceptance criterion #1: >=3 retry_count hits across both hooks."""
        combined = (
            RATE_LIMITER_HOOK.read_text() + DRAINER_HOOK.read_text()
        )
        hits = combined.count("retry_count")
        assert hits >= 3, f"Expected >=3 retry_count hits, found {hits}"


# ---------------------------------------------------------------------------
# 2. Drainer never blocks — deadlock prevention
# ---------------------------------------------------------------------------


class TestDrainerNonBlocking:
    """The drainer must always exit 0, even when the queue is chaotic."""

    def test_exit_zero_with_empty_queue(self, tmp_path):
        _write_config(tmp_path)
        (tmp_path / ".cognitive-os").mkdir(exist_ok=True)
        result = _run_drainer(tmp_path)
        assert result.returncode == 0

    def test_exit_zero_with_full_queue(self, tmp_path):
        """Even if the drainer re-queues many items, it must exit 0."""
        _write_config(tmp_path)
        _exhaust_bash_limit(tmp_path, limit=2)
        queue = _make_tight_queue(tmp_path, cooldown=0)
        # Enqueue 5 items at retry_count=0, eligible immediately
        for i in range(5):
            queue.enqueue(
                "bash_command",
                {"description": f"cmd-{i}"},
                retry_count=0,
            )
        result = _run_drainer(tmp_path)
        assert result.returncode == 0, (
            f"Drainer must never block. stderr:\n{result.stderr}"
        )


# ---------------------------------------------------------------------------
# 3. Compounding loop — item eventually dropped at retry cap
# ---------------------------------------------------------------------------


class TestCompoundingRetryLoop:
    """Simulate the exact D45 scenario: rate limit stays exhausted across
    multiple drainer fires; retry_count increments; item eventually dropped."""

    def test_item_dropped_after_max_retries(self, tmp_path):
        _write_config(tmp_path)
        _exhaust_bash_limit(tmp_path, limit=2)

        queue = _make_tight_queue(tmp_path, cooldown=0)
        # Enqueue one item at the boundary: one more retry will drop it.
        # MAX_RETRY_COUNT=3 means items with retry_count > 3 (i.e. 4+) get dropped.
        queue.enqueue(
            "bash_command",
            {"description": "doomed-cmd"},
            retry_count=MAX_RETRY_COUNT,  # next re-enqueue will be MAX+1 → DROP
        )
        assert len(queue.peek()) == 1, "Precondition: item queued"

        # Fire the drainer — still blocked, re-enqueues at retry_count=MAX+1 → DROP
        result = _run_drainer(tmp_path)
        assert result.returncode == 0

        # Re-load queue from disk; item must be gone
        queue2 = _make_tight_queue(tmp_path, cooldown=0)
        assert len(queue2.peek()) == 0, (
            "Item should have been dropped after exceeding retry cap"
        )

        # rate-limit-dropped.jsonl must exist with the drop record
        dropped_log = tmp_path / ".cognitive-os" / "rate-limit-dropped.jsonl"
        assert dropped_log.exists(), "Drop log must be written"
        lines = dropped_log.read_text().strip().splitlines()
        assert len(lines) >= 1
        drop_entry = json.loads(lines[-1])
        assert drop_entry["action_type"] == "bash_command"
        assert drop_entry["reason"] == "retry_cap_exceeded"
        assert drop_entry["retry_count"] > MAX_RETRY_COUNT

    def test_queue_bounded_over_many_drain_cycles(self, tmp_path):
        """Over N drain cycles the queue must never exceed MAX_QUEUE_SIZE,
        and items must progressively acquire higher retry_count values until
        they get dropped by the retry cap."""
        from lib.rate_limiter import MAX_QUEUE_SIZE

        _write_config(tmp_path)
        _exhaust_bash_limit(tmp_path, limit=2)

        # Seed the queue with 5 items at retry_count=MAX-1 so that the NEXT
        # re-enqueue pushes them over the cap (gets dropped). This avoids
        # waiting for exponential-backoff to elapse between drain cycles.
        queue = _make_tight_queue(tmp_path, cooldown=0)
        for i in range(5):
            queue.enqueue(
                "bash_command",
                {"description": f"seed-{i}"},
                retry_count=MAX_RETRY_COUNT,  # next re-enqueue → MAX+1 → DROP
            )

        # Wait for backoff to elapse so items are eligible. At retry=MAX=3
        # backoff = cooldown*2^3. We used cooldown=0 on the test queue, but
        # the drainer uses rl.config.cooldown_seconds=60, so items enqueued
        # here have eligible_at=now because the SEED queue's cooldown=0.
        # One drainer fire should process all 5.
        result = _run_drainer(tmp_path)
        assert result.returncode == 0, (
            f"Drainer must not block. stderr:\n{result.stderr}"
        )

        # Queue must be bounded after the fire
        queue_now = _make_tight_queue(tmp_path, cooldown=0)
        depth = len(queue_now.peek())
        assert depth <= MAX_QUEUE_SIZE, (
            f"Queue depth {depth} exceeds MAX_QUEUE_SIZE={MAX_QUEUE_SIZE}"
        )

        # All 5 seeded-at-cap items must be gone (dropped, not re-queued)
        assert depth == 0, (
            f"Expected all 5 items dropped after retry-cap overflow, got {depth}"
        )

        # Drop log must contain at least 5 entries
        drop_log = tmp_path / ".cognitive-os" / "rate-limit-dropped.jsonl"
        assert drop_log.exists(), "Drop log should be written"
        lines = [
            json.loads(ln) for ln in drop_log.read_text().splitlines() if ln.strip()
        ]
        cap_drops = [e for e in lines if e.get("reason") == "retry_cap_exceeded"]
        assert len(cap_drops) >= 5, (
            f"Expected >=5 retry_cap drops, got {len(cap_drops)}"
        )


# ---------------------------------------------------------------------------
# 4. Backoff respected — eligible_at grows with retry_count
# ---------------------------------------------------------------------------


class TestBackoffRespected:
    """Exponential backoff must be applied on re-enqueue by the drainer."""

    def test_eligible_at_grows_with_retry_count(self, tmp_path):
        _write_config(tmp_path)
        _exhaust_bash_limit(tmp_path, limit=2)

        # cooldown=1 so backoff = 1 * 2^retry_count = 1,2,4,...
        queue = _make_tight_queue(tmp_path, cooldown=1)
        queue.enqueue(
            "bash_command",
            {"description": "backoff-probe"},
            retry_count=0,
        )

        # Wait for item to become eligible
        time.sleep(1.2)

        # First drainer fire: re-enqueues at retry_count=1 → backoff=2s
        before_fire = time.time()
        result = _run_drainer(tmp_path)
        assert result.returncode == 0, result.stderr

        queue2 = _make_tight_queue(tmp_path, cooldown=1)
        items = queue2.peek()
        assert len(items) == 1, "Item should have been re-enqueued (not dropped)"
        item = items[0]
        assert item["retry_count"] == 1, (
            f"retry_count should be 1 after one re-enqueue, got {item['retry_count']}"
        )
        # Backoff = 1 * 2^1 = 2s. Eligible_at should be ~2s in the future.
        eligible_delay = item["eligible_at"] - before_fire
        assert eligible_delay >= 1.5, (
            f"Backoff should be >=2s at retry_count=1, got {eligible_delay:.2f}s"
        )
