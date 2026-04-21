"""Startup budget regression test.

Reads the latest entry from .cognitive-os/metrics/startup-benchmark.jsonl and
asserts that SessionStart hook total and initial payload tokens are within budget.

Budgets are intentionally generous to accommodate the current (pre-optimisation)
baseline.  The optimisation waves (Agents A/B/C) will tighten these values.

Environment overrides:
  STARTUP_BUDGET_SECONDS  — max total SessionStart wall-clock time (default: 10s)
  STARTUP_TOKEN_BUDGET    — max initial context payload tokens (default: 50000)
  STARTUP_BENCHMARK_FILE  — override path to the JSONL file

The test auto-skips if the benchmark has never been run (fresh clone) so CI
does not break on repositories that have not yet collected baseline data.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# ── Locate project root ───────────────────────────────────────────────────────
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parent.parent.parent  # tests/unit/ → project root


# ── Helpers ───────────────────────────────────────────────────────────────────

def _benchmark_path() -> Path:
    override = os.environ.get("STARTUP_BENCHMARK_FILE", "")
    if override:
        return Path(override)
    return _PROJECT_ROOT / ".cognitive-os" / "metrics" / "startup-benchmark.jsonl"


def _load_latest_record() -> dict | None:
    """Return the most-recently-appended benchmark record, or None."""
    path = _benchmark_path()
    if not path.exists():
        return None
    lines = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return None


def _budget_seconds() -> float:
    return float(os.environ.get("STARTUP_BUDGET_SECONDS", "10"))


def _token_budget() -> int:
    return int(os.environ.get("STARTUP_TOKEN_BUDGET", "50000"))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def latest_record():
    """Load the latest benchmark record; skip if not available."""
    record = _load_latest_record()
    if record is None:
        pytest.skip(
            "No startup benchmark data found. "
            f"Run `bash scripts/startup-benchmark.sh` first. "
            f"Expected file: {_benchmark_path()}"
        )
    return record


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_benchmark_file_exists():
    """The benchmark JSONL must exist once the harness has been run at least once."""
    path = _benchmark_path()
    if not path.exists():
        pytest.skip(
            "Benchmark not yet run — skipping existence check on fresh clone. "
            f"Run `bash scripts/startup-benchmark.sh` to generate baseline data."
        )
    assert path.is_file(), f"Expected file at {path}"


def test_benchmark_record_is_valid_json(latest_record):
    """Latest record must be valid JSON with required top-level keys."""
    required_keys = {"timestamp", "session_start", "payload", "slo"}
    missing = required_keys - set(latest_record.keys())
    assert not missing, (
        f"Benchmark record is missing required keys: {sorted(missing)}\n"
        f"Record keys present: {sorted(latest_record.keys())}"
    )


def test_session_start_hook_count(latest_record):
    """Benchmark must have timed at least one SessionStart hook."""
    hook_count = latest_record.get("session_start", {}).get("hook_count", 0)
    assert hook_count > 0, (
        "Benchmark recorded 0 SessionStart hooks. "
        "Check that .claude/settings.json has a SessionStart hook group."
    )


def test_session_start_total_within_budget(latest_record):
    """Total serial SessionStart time must be within STARTUP_BUDGET_SECONDS."""
    budget_ms = int(_budget_seconds() * 1000)
    measured_ms = latest_record.get("session_start", {}).get("total_duration_ms", 0)

    if measured_ms > budget_ms:
        # Build offender list
        hooks = latest_record.get("session_start", {}).get("hooks", [])
        hooks_sorted = sorted(hooks, key=lambda h: h.get("duration_ms", 0), reverse=True)
        offenders = [
            f"  {h['hook']}: {h['duration_ms']} ms"
            for h in hooks_sorted[:5]
        ]
        offenders_str = "\n".join(offenders)
        pytest.fail(
            f"SessionStart total {measured_ms} ms exceeds budget {budget_ms} ms "
            f"({_budget_seconds()} s).\n"
            f"Top offenders:\n{offenders_str}\n"
            f"Tighten hooks or increase STARTUP_BUDGET_SECONDS to acknowledge the regression."
        )


def test_initial_payload_tokens_within_budget(latest_record):
    """Core initial context payload must be within STARTUP_TOKEN_BUDGET tokens."""
    budget = _token_budget()
    measured = latest_record.get("payload", {}).get("core_payload_tokens", 0)

    if measured > budget:
        payload = latest_record.get("payload", {})
        components = {
            "global_claude_md": payload.get("global_claude_md_bytes", 0) // 4,
            "project_claude_md": payload.get("project_claude_md_bytes", 0) // 4,
            "rules_compact": payload.get("rules_compact_bytes", 0) // 4,
            "skills_catalog": payload.get("skills_catalog_bytes", 0) // 4,
        }
        offenders = "\n".join(
            f"  {k}: ~{v} tokens"
            for k, v in sorted(components.items(), key=lambda x: -x[1])
        )
        pytest.fail(
            f"Initial payload {measured} tokens exceeds budget {budget} tokens.\n"
            f"Component breakdown:\n{offenders}\n"
            f"Reduce payload or increase STARTUP_TOKEN_BUDGET to acknowledge the regression."
        )


def test_hooks_have_no_timeout(latest_record):
    """No individual hook should hit the 8-second timeout sentinel (8000 ms)."""
    hooks = latest_record.get("session_start", {}).get("hooks", [])
    timed_out = [h for h in hooks if h.get("duration_ms", 0) >= 8000]
    if timed_out:
        names = ", ".join(h["hook"] for h in timed_out)
        pytest.fail(
            f"These hooks hit the 8 s timeout during benchmark: {names}. "
            "They likely hang or spawn long-running daemons that do not exit quickly."
        )


def test_slo_fields_present(latest_record):
    """SLO block must record both session_start and payload measurements."""
    slo = latest_record.get("slo", {})
    required = {
        "session_start_target_ms",
        "session_start_measured_ms",
        "session_start_status",
        "payload_token_target",
        "payload_token_measured",
        "payload_token_status",
    }
    missing = required - set(slo.keys())
    assert not missing, (
        f"SLO block in benchmark record is missing fields: {sorted(missing)}"
    )
