"""Session leak detection tests.

Covers SLO 4 (rules/so-slo.md: "0 orphans/session") which was incumplido
as of 2026-04-20 — 8+ abandoned claude sessions accumulated, each holding
an engram MCP child.

The tests run `scripts/session-leak-diagnostic.sh` and assert:
- It exits non-zero when leak thresholds are breached (for alerting).
- The JSONL record it produces is well-formed.
- Threshold overrides via env vars work (so CI can set lenient caps
  without masking real regressions locally).
- The "old session" heuristic correctly identifies sessions by etime.

Run locally with tight thresholds to force a visible signal:
    MAX_CONCURRENT_SESSIONS=2 pytest tests/unit/test_session_leak_detection.py -v
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_DIR / "scripts" / "session-leak-diagnostic.sh"
METRICS = PROJECT_DIR / ".cognitive-os" / "metrics" / "session-leak.jsonl"


def _run(extra_env: dict | None = None, mode: str = "--json") -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(SCRIPT), mode],
        env=env,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_DIR),
        timeout=30,
    )


def test_script_exists_and_executable():
    assert SCRIPT.exists(), f"diagnostic script missing at {SCRIPT}"
    assert os.access(SCRIPT, os.X_OK), f"{SCRIPT} is not executable"


def test_json_mode_produces_valid_json():
    result = _run(mode="--json")
    # stdout is one JSON object line
    lines = [ln for ln in result.stdout.splitlines() if ln.strip().startswith("{")]
    assert lines, f"no JSON line in stdout:\n{result.stdout}"
    payload = json.loads(lines[0])
    for key in (
        "timestamp",
        "verdict",
        "session_count",
        "old_sessions",
        "engram_mcp_children",
        "reasons",
        "suspicious",
    ):
        assert key in payload, f"missing key '{key}' in payload: {payload}"
    assert payload["verdict"] in {"OK", "LEAK"}
    assert isinstance(payload["session_count"], int)
    assert isinstance(payload["reasons"], list)
    assert isinstance(payload["suspicious"], list)


def test_metrics_file_is_appended():
    before = METRICS.stat().st_size if METRICS.exists() else 0
    _run(mode="--json")
    assert METRICS.exists(), "metrics file not created"
    after = METRICS.stat().st_size
    assert after > before, "metrics file was not appended to"
    # Last line must be valid JSON
    with METRICS.open() as f:
        last = [ln for ln in f if ln.strip()][-1]
    json.loads(last)


def test_leak_verdict_when_thresholds_are_zero():
    """Force LEAK verdict by setting impossibly low thresholds."""
    result = _run(
        extra_env={
            "MAX_CONCURRENT_SESSIONS": "0",
            "MAX_SESSION_AGE_MIN": "0",
            "MAX_ENGRAM_CHILDREN": "0",
        },
        mode="--json",
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.strip().startswith("{")]
    payload = json.loads(lines[0])
    # With this environment having >=1 session (the one running pytest), LEAK must fire.
    assert payload["verdict"] == "LEAK", f"expected LEAK with 0 thresholds, got: {payload}"
    assert result.returncode == 1, "LEAK verdict must exit non-zero for alerting"
    assert payload["reasons"], "LEAK verdict must include at least one reason"


def test_ok_verdict_when_thresholds_are_generous():
    """Smoke test: very high thresholds → verdict OK regardless of state."""
    result = _run(
        extra_env={
            "MAX_CONCURRENT_SESSIONS": "9999",
            "MAX_SESSION_AGE_MIN": "999999",
            "MAX_ENGRAM_CHILDREN": "9999",
        },
        mode="--json",
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.strip().startswith("{")]
    payload = json.loads(lines[0])
    assert payload["verdict"] == "OK"
    assert result.returncode == 0


def test_slo_4_contract():
    """SLO 4 (rules/so-slo.md): orphan rate should be 0.

    This test documents the contract. It's allowed to fail today (known breach,
    see scripts/session-leak-diagnostic.sh header). Once ADR-046 lands and the
    watchdog auto-reaps, remove the xfail marker.
    """
    pytest.xfail(
        "SLO 4 contract currently broken — session-leak-watchdog pending (ADR-046). "
        "Remove this xfail when watchdog is deployed."
    )
    result = _run(
        extra_env={
            "MAX_CONCURRENT_SESSIONS": "4",
            "MAX_SESSION_AGE_MIN": "30",
            "MAX_ENGRAM_CHILDREN": "3",
        },
        mode="--json",
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.strip().startswith("{")]
    payload = json.loads(lines[0])
    assert payload["old_sessions"] == 0, (
        f"SLO 4 violated: {payload['old_sessions']} abandoned sessions detected. "
        f"Suspicious: {payload['suspicious']}"
    )
