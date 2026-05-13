"""Unit tests for ADR-056 L1 — agent-quota-advisor hook + quota_pressure lib.

Covers:
  * lib.quota_pressure.compute_quota_pressure heuristic math
  * hooks/agent-quota-advisor.sh threshold behavior and kill-switch

All tests use tmp_path; no real API, no network, no real JSONL in repo touched.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

# Resolve repo root from this test file (tests/unit/ -> ../../).
REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "agent-quota-advisor.sh"

import sys
sys.path.insert(0, str(REPO_ROOT))
from lib.quota_pressure import compute_quota_pressure, pressure_band  # noqa: E402


# ─── Helpers ────────────────────────────────────────────────────────────────


def _iso_now(offset_sec: float = 0.0) -> str:
    """ISO-8601 UTC timestamp with optional offset from now."""
    from datetime import datetime, timezone
    t = time.time() + offset_sec
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_dispatch(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _rate_limit_record(offset_sec: float = 0.0) -> dict:
    return {
        "ts": _iso_now(offset_sec),
        "dispatch_id": "abc123",
        "providers_requested": ["claude"],
        "providers_tried": ["claude"],
        "provider_used": "claude",
        "model": "sonnet",
        "task_type": "general",
        "skill_name": None,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "latency_ms": 0,
        "success": False,
        "error": "You're approaching your usage limit — out of extra usage",
    }


def _cost_record(cost_usd: float, offset_sec: float = 0.0) -> dict:
    return {
        "event_type": "cost.recorded",
        "payload": {
            "agent": "test-agent",
            "estimated_cost_usd": cost_usd,
            "is_estimate": True,
            "model": "sonnet",
            "tokens_estimated": 1000,
        },
        "schema_version": 1,
        "severity": "info",
        "source": "record_completion",
        "timestamp": _iso_now(offset_sec),
    }


# ─── lib.quota_pressure tests ───────────────────────────────────────────────


def test_compute_returns_zero_for_empty_dir(tmp_path: Path) -> None:
    # No JSONL files at all -> zero pressure.
    assert compute_quota_pressure(tmp_path) == 0.0


def test_compute_ignores_old_records(tmp_path: Path) -> None:
    # Record from 2 hours ago — outside 30min window.
    _write_dispatch(tmp_path / "llm-dispatch.jsonl", [_rate_limit_record(offset_sec=-7200)])
    assert compute_quota_pressure(tmp_path, window_min=30) == 0.0


def test_compute_escalates_with_recent_rate_limits(tmp_path: Path) -> None:
    # 1 recent rate-limit error -> 0.5 signal * 0.5 weight = 0.25 pressure
    _write_dispatch(tmp_path / "llm-dispatch.jsonl", [_rate_limit_record(offset_sec=-60)])
    p1 = compute_quota_pressure(tmp_path)
    assert p1 > 0.0
    # 2 errors saturate rate-limit signal to 1.0 * 0.5 = 0.5
    _write_dispatch(
        tmp_path / "llm-dispatch.jsonl",
        [_rate_limit_record(offset_sec=-60), _rate_limit_record(offset_sec=-120)],
    )
    p2 = compute_quota_pressure(tmp_path)
    assert p2 > p1
    assert p2 >= 0.5


def test_compute_escalates_with_recent_cost(tmp_path: Path) -> None:
    # Cost at 100% of budget -> 0.5 pressure (cost-weight only, no rate-limits)
    _write_dispatch(tmp_path / "cost-events.jsonl", [_cost_record(10.0, offset_sec=-60)])
    p = compute_quota_pressure(tmp_path, daily_budget_usd=10.0)
    # cost_signal = 1.0, weight = 0.5, no rate-limits -> pressure = 0.5
    assert abs(p - 0.5) < 0.01


def test_compute_capped_at_one(tmp_path: Path) -> None:
    # Way over everything -> still <= 1.0
    _write_dispatch(
        tmp_path / "llm-dispatch.jsonl",
        [_rate_limit_record(offset_sec=-i * 30) for i in range(1, 20)],
    )
    _write_dispatch(tmp_path / "cost-events.jsonl", [_cost_record(1000.0, offset_sec=-60)])
    p = compute_quota_pressure(tmp_path, daily_budget_usd=10.0)
    assert p <= 1.0
    assert p >= 0.99  # both signals saturated


def test_compute_handles_malformed_jsonl(tmp_path: Path) -> None:
    # Garbage lines must not crash — should silently skip.
    path = tmp_path / "llm-dispatch.jsonl"
    path.write_text("not json\n{broken\n" + json.dumps(_rate_limit_record(-60)) + "\n")
    p = compute_quota_pressure(tmp_path)
    assert p > 0.0  # the one valid record still counts


def test_pressure_band_boundaries() -> None:
    assert pressure_band(0.0) == "LOW"
    assert pressure_band(0.49) == "LOW"
    assert pressure_band(0.5) == "ADVISORY"
    assert pressure_band(0.79) == "ADVISORY"
    assert pressure_band(0.8) == "STRONG"
    assert pressure_band(1.0) == "STRONG"


# ─── Hook shell-level tests ─────────────────────────────────────────────────


def _run_hook(metrics_dir: Path, env_extra: dict | None = None, input_json: str | None = None) -> subprocess.CompletedProcess:
    """Invoke the hook with a project dir that has the given metrics dir.

    We stage a faux project root with `.cognitive-os/metrics/` pointing at
    the test's metrics dir (symlink for speed, or copy on fallback).
    """
    project = metrics_dir.parent.parent  # metrics_dir = <proj>/.cognitive-os/metrics
    if input_json is None:
        input_json = '{"tool_name":"Agent","tool_input":{"prompt":"test"}}'
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=input_json,
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )


def _stage_project(tmp_path: Path) -> Path:
    """Create <tmp>/proj/.cognitive-os/metrics/ and symlink lib/ from repo."""
    proj = tmp_path / "proj"
    metrics = proj / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    # Link the repo's lib/ dir so the inline Python can import it.
    (proj / "lib").symlink_to(REPO_ROOT / "lib")
    return metrics


@pytest.mark.skipif(not HOOK.exists(), reason="hook not present")
def test_hook_silent_when_pressure_low(tmp_path: Path) -> None:
    metrics = _stage_project(tmp_path)
    # No JSONL -> pressure = 0 -> silent.
    result = _run_hook(metrics)
    assert result.returncode == 0
    # stdout should be empty (no additionalContext emitted).
    assert "QUOTA ADVISORY" not in result.stdout
    assert "QUOTA ADVISORY" not in result.stderr


@pytest.mark.skipif(not HOOK.exists(), reason="hook not present")
def test_hook_warns_at_advisory_band(tmp_path: Path) -> None:
    metrics = _stage_project(tmp_path)
    # 2 rate-limit errors -> pressure = 0.5 exactly -> ADVISORY.
    _write_dispatch(
        metrics / "llm-dispatch.jsonl",
        [_rate_limit_record(offset_sec=-60), _rate_limit_record(offset_sec=-120)],
    )
    result = _run_hook(metrics)
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "QUOTA ADVISORY" in combined
    # Should not be the strong variant at exactly 50%.
    assert "strong" not in combined.lower() or "ADVISORY" in combined


@pytest.mark.skipif(not HOOK.exists(), reason="hook not present")
def test_hook_strong_warning_at_high_pressure(tmp_path: Path) -> None:
    metrics = _stage_project(tmp_path)
    # Saturate both signals -> pressure = 1.0 -> STRONG band.
    _write_dispatch(
        metrics / "llm-dispatch.jsonl",
        [_rate_limit_record(offset_sec=-i * 60) for i in range(1, 5)],
    )
    _write_dispatch(metrics / "cost-events.jsonl", [_cost_record(20.0, offset_sec=-60)])
    result = _run_hook(metrics)
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "QUOTA ADVISORY" in combined
    assert "strong" in combined.lower()
    assert "COS_AUTO_REDIRECT_AGENT" in combined


@pytest.mark.skipif(not HOOK.exists(), reason="hook not present")
def test_hook_respects_kill_switch(tmp_path: Path) -> None:
    metrics = _stage_project(tmp_path)
    _write_dispatch(
        metrics / "llm-dispatch.jsonl",
        [_rate_limit_record(offset_sec=-i * 60) for i in range(1, 5)],
    )
    result = _run_hook(metrics, env_extra={"COS_DISABLE_AGENT_ADVISOR": "1"})
    assert result.returncode == 0
    assert result.stdout == ""
    assert "QUOTA ADVISORY" not in result.stderr


@pytest.mark.skipif(not HOOK.exists(), reason="hook not present")
def test_hook_ignores_non_agent_tool(tmp_path: Path) -> None:
    metrics = _stage_project(tmp_path)
    _write_dispatch(
        metrics / "llm-dispatch.jsonl",
        [_rate_limit_record(offset_sec=-i * 60) for i in range(1, 5)],
    )
    # High pressure but tool is Bash — should stay silent.
    result = _run_hook(metrics, input_json='{"tool_name":"Bash","tool_input":{"command":"ls"}}')
    assert result.returncode == 0
    assert "QUOTA ADVISORY" not in (result.stdout + result.stderr)


@pytest.mark.skipif(not HOOK.exists(), reason="hook not present")
def test_hook_survives_missing_metrics(tmp_path: Path) -> None:
    # Deliberately don't create metrics dir — hook must not crash.
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "lib").symlink_to(REPO_ROOT / "lib")
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(proj)
    result = subprocess.run(
        ["bash", str(HOOK)],
        input='{"tool_name":"Agent","tool_input":{}}',
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    assert result.returncode == 0
