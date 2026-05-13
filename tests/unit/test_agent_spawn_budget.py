"""Sub-agent spawn cold-start budget regression test (ADR-303).

Reads the latest entry from .cognitive-os/metrics/agent-spawn-benchmark.jsonl
and asserts that the SubagentStart hook chain stays within wall-clock and
payload-token budgets.

Mirrors tests/unit/test_startup_budget.py. Auto-skips on fresh clones where
no benchmark has been run yet.

Environment overrides:
  AGENT_SPAWN_BUDGET_MS         — max total SubagentStart wall ms (default: 3000)
  AGENT_SPAWN_TOKEN_BUDGET      — max payload tokens per spawn (default: 20000)
  AGENT_SPAWN_BENCHMARK_FILE    — override path to the JSONL file
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parent.parent.parent

DEFAULT_WALL_BUDGET_MS = 3000
DEFAULT_TOKEN_BUDGET = 20000
PER_HOOK_TIMEOUT_MS = 5000


def _benchmark_path() -> Path:
    override = os.environ.get("AGENT_SPAWN_BENCHMARK_FILE", "")
    if override:
        return Path(override)
    return _PROJECT_ROOT / ".cognitive-os" / "metrics" / "agent-spawn-benchmark.jsonl"


def _load_latest_record() -> dict | None:
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


def _wall_budget_ms() -> int:
    return int(os.environ.get("AGENT_SPAWN_BUDGET_MS", str(DEFAULT_WALL_BUDGET_MS)))


def _token_budget() -> int:
    return int(os.environ.get("AGENT_SPAWN_TOKEN_BUDGET", str(DEFAULT_TOKEN_BUDGET)))


@pytest.fixture(scope="module")
def latest_record():
    record = _load_latest_record()
    if record is None:
        pytest.skip(
            "No agent-spawn benchmark data found. "
            "Run `bash scripts/cos-agent-spawn-benchmark` first. "
            f"Expected file: {_benchmark_path()}"
        )
    return record


def test_benchmark_file_exists():
    path = _benchmark_path()
    if not path.exists():
        pytest.skip(
            "Benchmark not yet run — skipping existence check on fresh clone. "
            "Run `bash scripts/cos-agent-spawn-benchmark` to generate baseline data."
        )
    assert path.is_file()


def test_record_has_required_keys(latest_record):
    required = {
        "timestamp",
        "preamble",
        "subagent_start_hooks",
        "context_injector",
        "totals",
        "slo",
    }
    missing = required - set(latest_record.keys())
    assert not missing, f"benchmark record missing keys: {sorted(missing)}"


def test_total_wall_within_budget(latest_record):
    budget = _wall_budget_ms()
    measured = latest_record.get("totals", {}).get("total_wall_ms", 0)
    if measured > budget:
        hooks = latest_record.get("subagent_start_hooks", [])
        offenders = sorted(hooks, key=lambda h: h.get("duration_ms", 0), reverse=True)[:5]
        formatted = "\n".join(
            f"  {h['hook']}: {h['duration_ms']} ms" for h in offenders
        )
        pytest.fail(
            f"Spawn wall-clock {measured} ms exceeds budget {budget} ms.\n"
            f"Top offenders:\n{formatted}\n"
            f"Tighten hooks or raise AGENT_SPAWN_BUDGET_MS to acknowledge the regression."
        )


def test_payload_tokens_within_budget(latest_record):
    budget = _token_budget()
    measured = latest_record.get("totals", {}).get("total_payload_tokens", 0)
    if measured > budget:
        preamble = latest_record.get("preamble", {}).get("est_tokens", 0)
        injector = latest_record.get("context_injector", {}).get("est_tokens", 0)
        rules = latest_record.get("mandatory_rules_inject", {}).get("est_tokens", 0)
        skills = latest_record.get("skill_catalog_inject", {}).get("est_tokens", 0)
        pytest.fail(
            f"Spawn payload {measured} tokens exceeds budget {budget}.\n"
            f"  preamble:        ~{preamble} tokens\n"
            f"  context_injector:~{injector} tokens (stdout)\n"
            f"  rules_compact:   ~{rules} tokens\n"
            f"  skills_catalog:  ~{skills} tokens\n"
            f"Reduce payload or raise AGENT_SPAWN_TOKEN_BUDGET to acknowledge the regression."
        )


def test_no_hook_exceeds_timeout(latest_record):
    hooks = latest_record.get("subagent_start_hooks", [])
    offenders = [h for h in hooks if h.get("duration_ms", 0) >= PER_HOOK_TIMEOUT_MS]
    if offenders:
        names = ", ".join(h["hook"] for h in offenders)
        pytest.fail(
            f"These hooks hit the {PER_HOOK_TIMEOUT_MS} ms timeout: {names}. "
            "They likely hang or spawn long-running daemons."
        )


def test_slo_fields_present(latest_record):
    slo = latest_record.get("slo", {})
    required = {
        "wall_target_ms",
        "wall_measured_ms",
        "wall_status",
        "payload_target_tokens",
        "payload_measured_tokens",
        "payload_status",
        "status",
    }
    missing = required - set(slo.keys())
    assert not missing, f"SLO block missing fields: {sorted(missing)}"
    assert slo["status"] in {"pass", "breach"}
