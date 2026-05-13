"""Unit tests for lib.agent_spawn_benchmark (ADR-303).

These tests exercise the harness building blocks. The few that run live hooks
are marked `benchmark` so they can be skipped in flaky-environment CI.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from lib.agent_spawn_benchmark import (  # noqa: E402
    DEFAULT_PAYLOAD_TOKEN_BUDGET,
    DEFAULT_WALL_BUDGET_MS,
    PER_HOOK_TIMEOUT_SEC,
    bytes_to_tokens,
    build_record,
    default_settings_path,
    load_subagent_start_hooks,
)


# ── Static checks ────────────────────────────────────────────────────────────


def test_can_locate_preamble():
    preamble = _PROJECT_ROOT / "templates" / "agent-preamble.md"
    assert preamble.is_file(), f"missing canonical preamble at {preamble}"
    assert preamble.stat().st_size > 0


def test_can_enumerate_subagent_hooks():
    settings = default_settings_path(_PROJECT_ROOT)
    hooks = load_subagent_start_hooks(settings)
    assert hooks, "expected at least one SubagentStart hook in .claude/settings.json"
    # The canonical injector must be wired up
    joined = "\n".join(hooks)
    assert "subagent-context-injector" in joined, (
        "SubagentStart group must reference subagent-context-injector.sh"
    )


def test_payload_token_estimate_is_bytes_over_4():
    assert bytes_to_tokens(0) == 0
    assert bytes_to_tokens(4) == 1
    assert bytes_to_tokens(40) == 10
    assert bytes_to_tokens(1000) == 250


def test_default_budgets_match_adr_targets():
    # ADR-303: 3000ms wall, 20000 token payload — operator-side cap before
    # the sub-agent does its first useful work.
    assert DEFAULT_WALL_BUDGET_MS == 3000
    assert DEFAULT_PAYLOAD_TOKEN_BUDGET == 20000


# ── Live benchmark exercises ────────────────────────────────────────────────


@pytest.mark.benchmark
def test_record_includes_slo_status(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENT_SPAWN_BUDGET_MS", raising=False)
    monkeypatch.delenv("AGENT_SPAWN_TOKEN_BUDGET", raising=False)
    record = build_record(_PROJECT_ROOT, default_settings_path(_PROJECT_ROOT))
    assert record.slo["status"] in {"pass", "breach"}
    assert "wall_target_ms" in record.slo
    assert "payload_target_tokens" in record.slo


@pytest.mark.benchmark
def test_no_hook_exceeds_timeout():
    record = build_record(_PROJECT_ROOT, default_settings_path(_PROJECT_ROOT))
    cap_ms = PER_HOOK_TIMEOUT_SEC * 1000
    for h in record.subagent_start_hooks:
        assert h["duration_ms"] <= cap_ms, (
            f"hook {h['hook']} timed out at {h['duration_ms']} ms (cap {cap_ms} ms)"
        )


@pytest.mark.benchmark
def test_records_one_jsonl_line_per_run(tmp_path):
    output = tmp_path / "spawn-bench.jsonl"
    script = _PROJECT_ROOT / "scripts" / "cos-agent-spawn-benchmark"
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(_PROJECT_ROOT)
    result = subprocess.run(
        ["bash", str(script), "--output", str(output), "--json"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(_PROJECT_ROOT),
        timeout=60,
    )
    assert result.returncode == 0, (
        f"benchmark script failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert output.is_file(), "benchmark did not append a JSONL record"
    lines = [ln for ln in output.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1, f"expected 1 record, got {len(lines)}"
    # Must be valid JSON with the expected keys
    rec = json.loads(lines[0])
    for key in (
        "timestamp",
        "preamble",
        "subagent_start_hooks",
        "context_injector",
        "totals",
        "slo",
    ):
        assert key in rec, f"record missing key: {key}"
