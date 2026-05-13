"""Sub-agent spawn cold-start budget tests (ADR-303/ADR-304).

ADR-303's synthetic benchmark is now only a smoke/lower-bound signal. Real
latency authority lives in ADR-304's declarative telemetry aggregator and the
SLOs in manifests/observability-slo.yaml.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from lib.telemetry_aggregator import aggregate_streams

_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parent.parent.parent

DEFAULT_TOKEN_BUDGET = 20000
PER_HOOK_TIMEOUT_MS = 5000
REAL_SPAWN_SLOS = {"subagent-spawn-p95", "subagent-spawn-p99"}


def _benchmark_path() -> Path:
    override = os.environ.get("AGENT_SPAWN_BENCHMARK_FILE", "")
    if override:
        return Path(override)
    return _PROJECT_ROOT / ".cognitive-os" / "metrics" / "agent-spawn-benchmark.jsonl"


def _manifest_path() -> Path:
    override = os.environ.get("OBSERVABILITY_SLO_MANIFEST", "")
    if override:
        return Path(override)
    return _PROJECT_ROOT / "manifests" / "observability-slo.yaml"


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


def test_real_spawn_latency_slos_are_authoritative():
    """ADR-304 aggregator is the real latency budget gate.

    Synthetic ADR-303 wall-clock is intentionally not asserted here because it
    can be ~150x lower than production telemetry. If there is no production
    telemetry on a fresh clone, skip rather than convert smoke data into false
    authority.
    """
    report = aggregate_streams(
        _PROJECT_ROOT,
        _manifest_path(),
        enable_self_tuning=False,
    )
    evaluations = {
        e.get("slo_id"): e for e in report.evaluations if e.get("slo_id") in REAL_SPAWN_SLOS
    }
    missing = REAL_SPAWN_SLOS - set(evaluations)
    assert not missing, f"manifest missing real spawn SLOs: {sorted(missing)}"

    no_data = [sid for sid, e in evaluations.items() if e.get("status") in {"no_data", "stream_missing"}]
    if no_data:
        pytest.skip(f"No production telemetry yet for {', '.join(sorted(no_data))}")

    breaches = [e for e in evaluations.values() if e.get("status") == "breach"]
    if breaches:
        details = "\n".join(
            f"  {e['slo_id']}: {e.get('value')} {e.get('comparator')} {e.get('target')} "
            f"samples={e.get('window_summary', {}).get('n_samples')}"
            for e in breaches
        )
        pytest.fail(
            "Real sub-agent spawn telemetry breached ADR-304 SLOs.\n"
            f"{details}\n"
            "Treat ADR-303 synthetic benchmark as smoke/lower-bound only."
        )


def test_synthetic_wall_is_smoke_only(latest_record):
    measured = latest_record.get("totals", {}).get("total_wall_ms", 0)
    assert isinstance(measured, (int, float))
    assert measured >= 0


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
