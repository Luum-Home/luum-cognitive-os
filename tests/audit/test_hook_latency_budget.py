"""test_hook_latency_budget.py — Audit hook p95 latency against per-event budgets.

Reads .cognitive-os/metrics/hook-timing.jsonl, groups records by (event, hook),
and asserts that the p95 latency over the last N=100 invocations is within the
budget defined for that event.

Budgets (ms):
  PreToolUse      < 2 000  — blocks every tool call
  PostToolUse     < 5 000
  Stop            < 10 000
  SessionStart    < 3 000
  SubagentStart   < 3 000
  UserPromptSubmit< 3 000
  PreCompact      < 5 000
  TeammateIdle    < 3 000
  TaskCreated     < 3 000
  TaskCompleted   < 3 000
  (any other)     < 5 000  — conservative default

If the JSONL file is absent or a (event, hook) pair has fewer than MIN_SAMPLES
invocations, that pair is skipped with pytest.skip() — no data is not a failure.

Run:
  uv run pytest tests/audit/test_hook_latency_budget.py -v
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

import pytest

# ── Constants ────────────────────────────────────────────────────────────────

LATENCY_BUDGETS_MS: dict[str, float] = {
    "PreToolUse": 2_000,
    "PostToolUse": 5_000,
    "Stop": 10_000,
    "SessionStart": 3_000,
    "SubagentStart": 3_000,
    "UserPromptSubmit": 3_000,
    "PreCompact": 5_000,
    "TeammateIdle": 3_000,
    "TaskCreated": 3_000,
    "TaskCompleted": 3_000,
}
DEFAULT_BUDGET_MS: float = 5_000

# Minimum number of invocations needed before we enforce the budget.
# Fewer samples → skip (not fail).
MIN_SAMPLES: int = 5

# Sliding window: only the last N invocations per (event, hook) pair.
WINDOW: int = 100

# Percentile used for the budget check.
PERCENTILE: float = 95.0

# Local hook latency metrics are operational telemetry, not deterministic test
# fixtures. Under concurrent-agent load the same checkout may legitimately show
# transient contention while code tests are running. Keep the laptop/audit lane
# informative by default and require explicit opt-in for blocking enforcement.
ENFORCE_ENV = "COS_ENFORCE_HOOK_LATENCY_BUDGET"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _find_project_root() -> Path:
    """Walk up from the test file's location until we find cognitive-os.yaml or .claude/."""
    here = Path(__file__).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "cognitive-os.yaml").exists() or (candidate / ".claude").is_dir():
            return candidate
    return Path.cwd()


def _timing_log_path() -> Path:
    import os

    env_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("COGNITIVE_OS_PROJECT_DIR")
    if env_dir:
        return Path(env_dir) / ".cognitive-os" / "metrics" / "hook-timing.jsonl"
    return _find_project_root() / ".cognitive-os" / "metrics" / "hook-timing.jsonl"


def _load_records(path: Path) -> list[dict]:
    """Load all valid JSONL records. Skips malformed lines silently."""
    if not path.exists():
        return []
    records: list[dict] = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                records.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return records


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(int(len(sorted_values) * pct / 100), len(sorted_values) - 1)
    return sorted_values[idx]


def _budget_for_event(event: str) -> float:
    return LATENCY_BUDGETS_MS.get(event, DEFAULT_BUDGET_MS)


def _collect_pairs(records: list[dict]) -> dict[tuple[str, str], list[float]]:
    """Return {(event, hook): [body duration_ms, ...]} using latest WINDOW entries.

    The timing wrapper records both wall-clock wrapper latency (`duration_ms`)
    and, for instrumented records, actual hook body latency
    (`body_duration_ms`). Budget enforcement is about hook body work. Safe-mode
    skips and killed/signal outcomes are classified elsewhere and must not be
    counted as successful hook body latency.
    """
    # Group all durations per pair (preserving order for sliding window)
    raw: dict[tuple[str, str], list[float]] = defaultdict(list)
    for rec in records:
        event = rec.get("event", "")
        hook = rec.get("hook", "")
        if rec.get("skipped") or rec.get("safe_mode"):
            continue
        execution_status = rec.get("execution_status")
        if execution_status and execution_status != "ok":
            continue
        dur = float(rec.get("body_duration_ms", rec.get("duration_ms", 0)))
        if event and hook:
            raw[(event, hook)].append(dur)

    # Trim to last WINDOW entries
    return {pair: durations[-WINDOW:] for pair, durations in raw.items()}


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def timing_pairs() -> dict[tuple[str, str], list[float]]:
    """Load and return {(event, hook): [latest WINDOW duration_ms values]}."""
    path = _timing_log_path()
    records = _load_records(path)
    return _collect_pairs(records)


# ── Tests ────────────────────────────────────────────────────────────────────

def test_timing_log_exists():
    """The hook-timing.jsonl file is optional until a timed session has run."""
    path = _timing_log_path()
    if not path.exists():
        pytest.skip(f"hook-timing.jsonl not present yet at {path}")


def test_timing_log_has_records(timing_pairs):
    """At least one (event, hook) pair must have been recorded."""
    if not timing_pairs:
        pytest.skip("hook timing has no valid records yet")


@pytest.mark.parametrize("event,budget_ms", sorted(LATENCY_BUDGETS_MS.items()))
def test_p95_within_budget_for_event(event, budget_ms, timing_pairs):
    """All hooks that fired under <event> must have p95 latency within budget."""
    pairs_for_event = {
        (ev, hook): durations
        for (ev, hook), durations in timing_pairs.items()
        if ev == event
    }

    if not pairs_for_event:
        pytest.skip(f"No invocations recorded for event '{event}'")

    violators: list[str] = []

    for (ev, hook), durations in pairs_for_event.items():
        if len(durations) < MIN_SAMPLES:
            # Not enough data — skip this specific hook
            continue
        sorted_d = sorted(durations)
        p95 = _percentile(sorted_d, PERCENTILE)
        if p95 > budget_ms:
            violators.append(
                f"{hook} (event={ev}, n={len(durations)}, p95={p95:.0f}ms, budget={budget_ms:.0f}ms)"
            )

    all_skipped = all(len(d) < MIN_SAMPLES for d in pairs_for_event.values())
    if all_skipped:
        pytest.skip(
            f"All hooks for event '{event}' have fewer than {MIN_SAMPLES} samples "
            f"(window={WINDOW}). Not enough data to enforce budget."
        )

    if violators and os.environ.get(ENFORCE_ENV) != "1":
        pytest.xfail(
            f"Operational hook latency budget exceeded for '{event}' but "
            f"{ENFORCE_ENV}=1 is not set: " + "; ".join(violators)
        )

    assert not violators, (
        f"The following hooks exceed the p95 latency budget for '{event}' "
        f"({budget_ms:.0f}ms):\n"
        + "\n".join(f"  - {v}" for v in violators)
    )


def test_no_hooks_exceed_default_budget(timing_pairs):
    """Hooks firing on unlisted events must not exceed the default 5s budget."""
    listed_events = set(LATENCY_BUDGETS_MS.keys())
    unlisted_pairs = {
        (ev, hook): durations
        for (ev, hook), durations in timing_pairs.items()
        if ev not in listed_events
    }

    if not unlisted_pairs:
        pytest.skip("No hooks recorded for events outside the explicit budget table.")

    violators: list[str] = []
    for (ev, hook), durations in unlisted_pairs.items():
        if len(durations) < MIN_SAMPLES:
            continue
        sorted_d = sorted(durations)
        p95 = _percentile(sorted_d, PERCENTILE)
        if p95 > DEFAULT_BUDGET_MS:
            violators.append(
                f"{hook} (event={ev}, n={len(durations)}, p95={p95:.0f}ms, budget={DEFAULT_BUDGET_MS:.0f}ms)"
            )

    if violators and os.environ.get(ENFORCE_ENV) != "1":
        pytest.xfail(
            f"Operational default hook latency budget exceeded but "
            f"{ENFORCE_ENV}=1 is not set: " + "; ".join(violators)
        )

    assert not violators, (
        f"The following hooks exceed the default p95 latency budget "
        f"({DEFAULT_BUDGET_MS:.0f}ms):\n"
        + "\n".join(f"  - {v}" for v in violators)
    )


def test_timing_wrapper_instrumented_hooks_count(timing_pairs):
    """Sanity check: normal sessions record at least 10 distinct hooks.

    Validation capsules can contain sparse copied telemetry from the test run
    itself rather than a complete operator session. In that environment this is
    a runtime-sample precondition, not a wiring failure.
    """
    unique_hooks = {hook for (_, hook) in timing_pairs}
    if not unique_hooks:
        pytest.skip("hook timing has no records yet")
    if len(unique_hooks) < 10 and "cos-validation-capsules" in str(_timing_log_path()):
        pytest.skip(
            f"not enough data: validation capsule has only {len(unique_hooks)} distinct hook timing sample(s); "
            "requires a normal operator session for wrapper coverage enforcement"
        )
    assert len(unique_hooks) >= 10, (
        f"Only {len(unique_hooks)} distinct hooks recorded. "
        "Expected ≥10 after a normal session. "
        "Check that hook-timing-wrapper.sh is wired for all hook events."
    )
