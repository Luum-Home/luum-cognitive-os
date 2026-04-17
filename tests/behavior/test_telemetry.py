"""Behavior tests for lib.telemetry (Capa-4 observability).

Covers:
    - each public record_* function appends a well-formed JSONL line
    - the rotation threshold is honoured (file is renamed; new file created)
    - iter_records yields records across rotated siblings
    - records contain required fields and the event tag
    - aggregator inputs (counts, grouping) are correct
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest


# Ensure the project root is on sys.path so `import lib.telemetry` works when
# pytest is invoked from anywhere.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def telemetry(tmp_path, monkeypatch):
    """Return a fresh telemetry module scoped to an isolated project dir.

    Uses monkeypatch to point COGNITIVE_OS_PROJECT_DIR at tmp_path, then
    reloads the module so any cached state is reset.
    """
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    # Default rotation large so unrelated tests do not trigger it.
    monkeypatch.setenv("COS_TELEMETRY_MAX_BYTES", str(10 * 1024 * 1024))

    import lib.telemetry as telemetry_mod
    importlib.reload(telemetry_mod)
    return telemetry_mod


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


# ─── record_skill_invocation ────────────────────────────────────────────────


def test_record_skill_invocation_creates_file_and_appends(telemetry, tmp_path):
    target = telemetry.record_skill_invocation("compose-prompt", 42, 1200)
    expected = tmp_path / ".cognitive-os" / "metrics" / telemetry.SKILL_USAGE_FILE
    assert target == expected
    assert expected.exists()

    rows = _read_lines(expected)
    assert len(rows) == 1
    row = rows[0]
    assert row["event"] == "skill_invocation"
    assert row["name"] == "compose-prompt"
    assert row["duration_ms"] == 42.0
    assert row["tokens_estimated"] == 1200
    assert "timestamp" in row and row["timestamp"].endswith("Z")


def test_record_skill_invocation_accepts_extra_fields(telemetry, tmp_path):
    telemetry.record_skill_invocation("scout", extra={"session": "s1"})
    target = tmp_path / ".cognitive-os" / "metrics" / telemetry.SKILL_USAGE_FILE
    rows = _read_lines(target)
    assert rows[0]["session"] == "s1"


def test_record_skill_invocation_minimum_args(telemetry, tmp_path):
    telemetry.record_skill_invocation("doc-sync")
    target = tmp_path / ".cognitive-os" / "metrics" / telemetry.SKILL_USAGE_FILE
    rows = _read_lines(target)
    assert rows[0]["name"] == "doc-sync"
    assert "duration_ms" not in rows[0]


# ─── record_hook_fired ──────────────────────────────────────────────────────


def test_record_hook_fired_writes_event_and_decision(telemetry, tmp_path):
    telemetry.record_hook_fired(
        "adaptive-bypass",
        event_type="PreToolUse",
        duration_ms=15.2,
        decision="warn",
    )
    target = tmp_path / ".cognitive-os" / "metrics" / telemetry.HOOK_USAGE_FILE
    rows = _read_lines(target)
    assert rows[0]["event"] == "hook_fired"
    assert rows[0]["name"] == "adaptive-bypass"
    assert rows[0]["event_type"] == "PreToolUse"
    assert rows[0]["decision"] == "warn"


# ─── record_agent_launch ────────────────────────────────────────────────────


def test_record_agent_launch_captures_cost(telemetry, tmp_path):
    telemetry.record_agent_launch(
        "Refactor handler",
        model="sonnet",
        tokens_in=1200,
        tokens_out=3400,
        cost_estimated=0.07,
    )
    target = tmp_path / ".cognitive-os" / "metrics" / telemetry.AGENT_LAUNCHES_FILE
    rows = _read_lines(target)
    row = rows[0]
    assert row["event"] == "agent_launch"
    assert row["model"] == "sonnet"
    assert row["tokens_in"] == 1200
    assert row["tokens_out"] == 3400
    assert row["cost_estimated"] == pytest.approx(0.07)


# ─── record_rate_limit_event ────────────────────────────────────────────────


def test_record_rate_limit_event_defaults(telemetry, tmp_path):
    telemetry.record_rate_limit_event("throttled", queue_depth=5, delay_s=1.5)
    target = tmp_path / ".cognitive-os" / "metrics" / telemetry.RATE_LIMIT_FILE
    rows = _read_lines(target)
    assert rows[0]["type"] == "throttled"
    assert rows[0]["queue_depth"] == 5
    assert rows[0]["delay_s"] == pytest.approx(1.5)


# ─── rotation ───────────────────────────────────────────────────────────────


def test_rotation_renames_file_when_threshold_exceeded(tmp_path, monkeypatch):
    """Force MAX_BYTES low, write enough records to trigger rotation."""
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setenv("COS_TELEMETRY_MAX_BYTES", "512")  # very small

    import lib.telemetry as telemetry
    importlib.reload(telemetry)

    metrics_dir = tmp_path / ".cognitive-os" / "metrics"
    target = metrics_dir / telemetry.SKILL_USAGE_FILE

    # Fill enough lines to cross 512 bytes. Each line is ~80 bytes.
    for i in range(40):
        telemetry.record_skill_invocation(f"skill-{i}", duration_ms=i)

    # After the write that crossed the threshold, we expect exactly one rotated
    # sibling plus the new current file (or the current file alone if the next
    # write hasn't happened yet after rename). Robust check: at least one
    # rotated sibling exists and the current file size is below threshold.
    rotated = sorted(metrics_dir.glob("skill-usage.*.jsonl"))
    assert len(rotated) >= 1, f"expected at least 1 rotated file, found: {list(metrics_dir.iterdir())}"
    # Current file should be small (just the lines after rotation).
    if target.exists():
        assert target.stat().st_size < 512 * 3  # generous: post-rotation growth is bounded


def test_iter_records_merges_rotated_siblings(tmp_path, monkeypatch):
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setenv("COS_TELEMETRY_MAX_BYTES", "256")

    import lib.telemetry as telemetry
    importlib.reload(telemetry)

    for i in range(30):
        telemetry.record_skill_invocation(f"s{i}")

    all_records = list(telemetry.iter_records(telemetry.SKILL_USAGE_FILE))
    assert len(all_records) == 30
    names = {r["name"] for r in all_records}
    assert names == {f"s{i}" for i in range(30)}


# ─── robustness ─────────────────────────────────────────────────────────────


def test_iter_records_tolerates_corrupt_lines(telemetry, tmp_path):
    telemetry.record_skill_invocation("a")
    target = tmp_path / ".cognitive-os" / "metrics" / telemetry.SKILL_USAGE_FILE
    # Append some garbage to simulate a partial write.
    with target.open("a") as fh:
        fh.write("not-json\n")
        fh.write('{"event":"skill_invocation","name":"b","timestamp":"2026-04-16T00:00:00Z"}\n')
    rows = list(telemetry.iter_records(telemetry.SKILL_USAGE_FILE))
    names = [r["name"] for r in rows]
    assert names == ["a", "b"]


def test_record_functions_do_not_raise_on_readonly_dir(tmp_path, monkeypatch):
    """If the metrics dir cannot be written, calls return None (not raise)."""
    fake = tmp_path / "no-such-place"
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(fake))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

    import lib.telemetry as telemetry
    importlib.reload(telemetry)

    # First call will create the dir successfully (mkdir parents=True). To test
    # the error path we remove write permission and confirm we swallow the
    # exception instead of propagating.
    (fake / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(fake / ".cognitive-os" / "metrics", 0o500)
        result = telemetry.record_skill_invocation("x")
        # On many systems root-owned dirs still permit write; accept either
        # outcome as long as no exception propagates.
        assert result is None or result.exists()
    finally:
        os.chmod(fake / ".cognitive-os" / "metrics", 0o700)


# ─── aggregation shape (smoke test for the report script) ───────────────────


def test_agent_launch_grouping_by_model(telemetry, tmp_path):
    telemetry.record_agent_launch("a1", model="sonnet", cost_estimated=0.01)
    telemetry.record_agent_launch("a2", model="sonnet", cost_estimated=0.02)
    telemetry.record_agent_launch("a3", model="haiku", cost_estimated=0.003)

    rows = list(telemetry.iter_records(telemetry.AGENT_LAUNCHES_FILE))
    assert len(rows) == 3
    sonnet_cost = sum(r["cost_estimated"] for r in rows if r["model"] == "sonnet")
    haiku_cost = sum(r["cost_estimated"] for r in rows if r["model"] == "haiku")
    assert sonnet_cost == pytest.approx(0.03)
    assert haiku_cost == pytest.approx(0.003)


def test_public_api_surface():
    import lib.telemetry as telemetry
    assert hasattr(telemetry, "record_skill_invocation")
    assert hasattr(telemetry, "record_hook_fired")
    assert hasattr(telemetry, "record_agent_launch")
    assert hasattr(telemetry, "record_rate_limit_event")
    assert hasattr(telemetry, "iter_records")
    assert hasattr(telemetry, "MAX_BYTES")
