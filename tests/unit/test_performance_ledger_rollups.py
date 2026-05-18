"""Tests for Phase 1 semantic rollups in lib/performance_ledger.py.

Covers: rollup_skill_metrics, rollup_provider_metrics, rollup_primitive_metrics,
        attach_source_refs, attach_harness_metadata.

Fixtures use small in-memory event lists that mirror the real JSONL schemas
observed in .cognitive-os/metrics/*.jsonl — no file I/O required.
"""
from __future__ import annotations

import pytest

from lib.performance_ledger import (
    attach_harness_metadata,
    attach_source_refs,
    rollup_primitive_metrics,
    rollup_provider_metrics,
    rollup_skill_metrics,
)


# ---------------------------------------------------------------------------
# Fixtures — small representative event lists
# ---------------------------------------------------------------------------

SKILL_METRICS_EVENTS = [
    {"timestamp": "2026-05-16T15:37:34Z", "skill": "rewrite", "model": "unknown", "tokens": 2545, "duration_ms": 707, "success": True},
    {"timestamp": "2026-05-16T15:50:50Z", "skill": "rewrite", "model": "unknown", "tokens": 3020, "duration_ms": 837, "success": False},
    {"timestamp": "2026-05-16T16:09:44Z", "skill": "rewrite", "model": "unknown", "tokens": 1556, "duration_ms": 1905, "success": True},
]

SKILL_INVOCATION_EVENTS = [
    {
        "event_type": "skill.invoked",
        "payload": {"skill_name": "sdd-explore", "args": "", "session_id": "unknown"},
        "schema_version": 1,
        "severity": "info",
        "source": "skill-invocation-logger",
        "timestamp": "2026-05-16T16:09:45+00:00",
    },
    {
        "event_type": "skill.invoked",
        "payload": {"skill_name": "sdd-explore", "args": "", "session_id": "unknown"},
        "schema_version": 1,
        "severity": "info",
        "source": "skill-invocation-logger",
        "timestamp": "2026-05-16T16:19:03+00:00",
    },
    {
        "event_type": "skill.error",
        "payload": {"skill_name": "sdd-explore", "args": "", "session_id": "unknown"},
        "schema_version": 1,
        "severity": "error",
        "source": "skill-invocation-logger",
        "timestamp": "2026-05-16T16:30:57+00:00",
    },
    {
        "event_type": "skill.override",
        "payload": {"skill_name": "sdd-explore", "args": "", "session_id": "unknown"},
        "schema_version": 1,
        "severity": "warn",
        "source": "skill-invocation-logger",
        "timestamp": "2026-05-16T16:40:00+00:00",
    },
]

PROVIDER_ROUTING_EVENTS = [
    {"timestamp": "2026-05-16T01:18:13Z", "primitive": "skill-router", "action": "BLOCK", "reason_code": "dependency_update_bypass", "target_ref": "dep"},
    {"timestamp": "2026-05-16T01:18:21Z", "primitive": "skill-router", "action": "allow", "reason_code": "ok", "target_ref": "ok-ref"},
    {"timestamp": "2026-05-16T01:18:30Z", "primitive": "skill-router", "action": "fallback", "reason_code": "primary_unavailable", "target_ref": "fallback-ref"},
]

PROVIDER_DISPATCH_EVENTS = [
    {"timestamp": "2026-05-16T15:28:22Z", "active": 0, "max": 5, "action": "allow", "description": ""},
    {"timestamp": "2026-05-16T15:39:12Z", "active": 1, "max": 5, "action": "allow", "description": ""},
    {"timestamp": "2026-05-16T16:09:38Z", "active": 0, "max": 5, "action": "allow", "description": ""},
]

PRIMITIVE_EVENTS = [
    {
        "schema_version": "primitive-intervention.v1",
        "timestamp": "2026-05-14T14:46:39Z",
        "session_id": "",
        "primitive_id": "reinvention-check",
        "primitive_family": "validation",
        "primitive_source": "hooks/reinvention-check.sh",
        "harness": "claude-code",
        "tool": "Agent",
        "action_kind": "warn",
        "reason_code": "possible_reinvention",
        "source_metric": ".cognitive-os/metrics/reinvention-checks.jsonl",
    },
    {
        "schema_version": "primitive-intervention.v1",
        "timestamp": "2026-05-14T14:51:42Z",
        "session_id": "",
        "primitive_id": "reinvention-check",
        "primitive_family": "validation",
        "primitive_source": "hooks/reinvention-check.sh",
        "harness": "claude-code",
        "tool": "Agent",
        "action_kind": "block",
        "reason_code": "confirmed_reinvention",
        "source_metric": ".cognitive-os/metrics/reinvention-checks.jsonl",
    },
    {
        "schema_version": "primitive-intervention.v1",
        "timestamp": "2026-05-14T15:13:36Z",
        "session_id": "",
        "primitive_id": "reinvention-check",
        "primitive_family": "validation",
        "primitive_source": "hooks/reinvention-check.sh",
        "harness": "vscode",
        "tool": "Agent",
        "action_kind": "warn",
        "reason_code": "possible_reinvention",
        "source_metric": ".cognitive-os/metrics/reinvention-checks.jsonl",
    },
]


# ---------------------------------------------------------------------------
# attach_source_refs
# ---------------------------------------------------------------------------

class TestAttachSourceRefs:
    def test_returns_one_ref_per_event(self):
        events = [{"a": 1}, {"b": 2}, {"c": 3}]
        refs = attach_source_refs(events, "foo.jsonl")
        assert len(refs) == 3

    def test_line_numbers_are_one_based(self):
        events = [{"x": 1}, {"x": 2}]
        refs = attach_source_refs(events, "f.jsonl")
        assert refs[0]["line"] == 1
        assert refs[1]["line"] == 2

    def test_prefers_source_metric_field(self):
        events = [{"source_metric": ".cognitive-os/metrics/custom.jsonl"}]
        refs = attach_source_refs(events, "fallback.jsonl")
        assert refs[0]["file"] == ".cognitive-os/metrics/custom.jsonl"

    def test_falls_back_to_source_file_param(self):
        events = [{"no_source_metric": True}]
        refs = attach_source_refs(events, "fallback.jsonl")
        assert refs[0]["file"] == "fallback.jsonl"

    def test_empty_events_returns_empty(self):
        assert attach_source_refs([], "f.jsonl") == []


# ---------------------------------------------------------------------------
# attach_harness_metadata
# ---------------------------------------------------------------------------

class TestAttachHarnessMetadata:
    def test_returns_most_frequent_harness(self):
        events = [{"harness": "claude-code"}, {"harness": "claude-code"}, {"harness": "vscode"}]
        assert attach_harness_metadata(events) == "claude-code"

    def test_returns_none_when_no_harness_field(self):
        events = [{"foo": 1}, {"bar": 2}]
        assert attach_harness_metadata(events) is None

    def test_returns_none_on_empty(self):
        assert attach_harness_metadata([]) is None

    def test_single_harness(self):
        events = [{"harness": "vscode"}, {"harness": "vscode"}]
        assert attach_harness_metadata(events) == "vscode"


# ---------------------------------------------------------------------------
# rollup_skill_metrics — skill-metrics.jsonl schema
# ---------------------------------------------------------------------------

class TestRollupSkillMetricsFromMetricsSchema:
    def setup_method(self):
        self.rollup = rollup_skill_metrics(SKILL_METRICS_EVENTS, source_file="skill-metrics.jsonl")

    def test_rollup_kind(self):
        assert self.rollup["rollup_kind"] == "skill"

    def test_subject_id_from_skill_field(self):
        assert self.rollup["subject_id"] == "rewrite"

    def test_invocation_count(self):
        assert self.rollup["metrics"]["invocations"] == 3

    def test_success_and_failure_counts(self):
        m = self.rollup["metrics"]
        assert m["success_count"] == 2
        assert m["failure_count"] == 1

    def test_override_rate_zero(self):
        assert self.rollup["metrics"]["override_rate"] == 0.0

    def test_trust_pass_rate_is_none(self):
        # No trust signal in current schema — documented null
        assert self.rollup["metrics"]["trust_pass_rate"] is None

    def test_time_to_complete_ms_is_avg(self):
        expected = round((707 + 837 + 1905) / 3, 3)
        assert self.rollup["metrics"]["time_to_complete_ms"] == expected

    def test_window_has_start_end_duration(self):
        w = self.rollup["window"]
        assert w["start"] is not None
        assert w["end"] is not None
        assert w["duration_seconds"] is not None

    def test_source_refs_count(self):
        assert len(self.rollup["source_refs"]) == 3

    def test_harness_is_none(self):
        assert self.rollup["harness"] is None


# ---------------------------------------------------------------------------
# rollup_skill_metrics — skill-invocations.jsonl schema
# ---------------------------------------------------------------------------

class TestRollupSkillMetricsFromInvocationsSchema:
    def setup_method(self):
        self.rollup = rollup_skill_metrics(SKILL_INVOCATION_EVENTS, source_file="skill-invocations.jsonl")

    def test_rollup_kind(self):
        assert self.rollup["rollup_kind"] == "skill"

    def test_subject_id_from_payload(self):
        assert self.rollup["subject_id"] == "sdd-explore"

    def test_invocation_count(self):
        assert self.rollup["metrics"]["invocations"] == 4

    def test_override_count_reflected_in_rate(self):
        # 1 override out of 4 total
        assert self.rollup["metrics"]["override_rate"] == pytest.approx(0.25, rel=1e-5)

    def test_failure_count(self):
        assert self.rollup["metrics"]["failure_count"] == 1

    def test_duration_none_when_no_duration_field(self):
        assert self.rollup["metrics"]["time_to_complete_ms"] is None


# ---------------------------------------------------------------------------
# rollup_skill_metrics — empty input
# ---------------------------------------------------------------------------

def test_rollup_skill_metrics_empty():
    assert rollup_skill_metrics([]) == {}


# ---------------------------------------------------------------------------
# rollup_provider_metrics — routing events
# ---------------------------------------------------------------------------

class TestRollupProviderMetricsRouting:
    def setup_method(self):
        self.rollup = rollup_provider_metrics(PROVIDER_ROUTING_EVENTS, source_file="skill-routing.jsonl")

    def test_rollup_kind(self):
        assert self.rollup["rollup_kind"] == "provider"

    def test_subject_id_from_primitive(self):
        assert self.rollup["subject_id"] == "skill-router"

    def test_total_dispatches(self):
        assert self.rollup["metrics"]["total_dispatches"] == 3

    def test_fallback_rate(self):
        # 1 BLOCK + 1 fallback = 2 out of 3
        assert self.rollup["metrics"]["fallback_rate"] == pytest.approx(2 / 3, rel=1e-5)

    def test_latency_null_when_absent(self):
        # latency_ms not in routing schema → null documented
        assert self.rollup["metrics"]["latency_ms_avg"] is None

    def test_cost_null_when_absent(self):
        assert self.rollup["metrics"]["cost_usd_total"] is None

    def test_retry_count_zero_when_absent(self):
        assert self.rollup["metrics"]["retry_count_total"] == 0

    def test_source_refs_count(self):
        assert len(self.rollup["source_refs"]) == 3


# ---------------------------------------------------------------------------
# rollup_provider_metrics — dispatch events (all "allow", no fallbacks)
# ---------------------------------------------------------------------------

class TestRollupProviderMetricsDispatch:
    def setup_method(self):
        self.rollup = rollup_provider_metrics(PROVIDER_DISPATCH_EVENTS, source_file="dispatch-gate.jsonl")

    def test_fallback_rate_zero(self):
        assert self.rollup["metrics"]["fallback_rate"] == 0.0

    def test_total_dispatches(self):
        assert self.rollup["metrics"]["total_dispatches"] == 3


def test_rollup_provider_metrics_empty():
    assert rollup_provider_metrics([]) == {}


# ---------------------------------------------------------------------------
# rollup_provider_metrics — explicit latency/cost/retry fields
# ---------------------------------------------------------------------------

def test_rollup_provider_metrics_with_explicit_fields():
    events = [
        {"timestamp": "2026-05-16T12:00:00Z", "primitive": "llm-router", "action": "allow", "latency_ms": 120.0, "cost_usd": 0.001, "retry_count": 1},
        {"timestamp": "2026-05-16T12:01:00Z", "primitive": "llm-router", "action": "allow", "latency_ms": 80.0, "cost_usd": 0.002, "retry_count": 0},
    ]
    rollup = rollup_provider_metrics(events, source_file="test.jsonl")
    assert rollup["metrics"]["latency_ms_avg"] == pytest.approx(100.0, rel=1e-5)
    assert rollup["metrics"]["cost_usd_total"] == pytest.approx(0.003, rel=1e-5)
    assert rollup["metrics"]["retry_count_total"] == 1


# ---------------------------------------------------------------------------
# rollup_primitive_metrics
# ---------------------------------------------------------------------------

class TestRollupPrimitiveMetrics:
    def setup_method(self):
        self.rollup = rollup_primitive_metrics(PRIMITIVE_EVENTS, source_file="primitive-interventions.jsonl")

    def test_rollup_kind(self):
        assert self.rollup["rollup_kind"] == "primitive"

    def test_subject_id_from_primitive_id(self):
        assert self.rollup["subject_id"] == "reinvention-check"

    def test_total_interventions(self):
        assert self.rollup["metrics"]["total_interventions"] == 3

    def test_action_counts(self):
        ac = self.rollup["metrics"]["action_counts"]
        assert ac["warn"] == 2
        assert ac["block"] == 1

    def test_block_rate(self):
        assert self.rollup["metrics"]["block_rate"] == pytest.approx(1 / 3, rel=1e-5)

    def test_canonical_families_present(self):
        fc = self.rollup["metrics"]["family_counts"]
        for fam in ("dispatch", "skill-routing", "state-retention", "repair", "validation"):
            assert fam in fc

    def test_validation_family_count(self):
        assert self.rollup["metrics"]["family_counts"]["validation"] == 3

    def test_zero_for_absent_canonical_families(self):
        fc = self.rollup["metrics"]["family_counts"]
        assert fc["dispatch"] == 0
        assert fc["repair"] == 0

    def test_harness_most_frequent(self):
        # claude-code appears twice, vscode once
        assert self.rollup["harness"] == "claude-code"

    def test_source_refs_use_source_metric_field(self):
        refs = self.rollup["source_refs"]
        assert all(r["file"] == ".cognitive-os/metrics/reinvention-checks.jsonl" for r in refs)

    def test_window_populated(self):
        w = self.rollup["window"]
        assert w["start"] == "2026-05-14T14:46:39Z"
        assert w["end"] == "2026-05-14T15:13:36Z"
        assert w["duration_seconds"] is not None and w["duration_seconds"] > 0


def test_rollup_primitive_metrics_empty():
    assert rollup_primitive_metrics([]) == {}


# ---------------------------------------------------------------------------
# rollup_primitive_metrics — unknown harness field (harness-agnostic)
# ---------------------------------------------------------------------------

def test_rollup_primitive_harness_agnostic_when_field_absent():
    events = [
        {"timestamp": "2026-05-14T14:46:39Z", "primitive_id": "blast-radius", "primitive_family": "validation", "action_kind": "warn"},
    ]
    rollup = rollup_primitive_metrics(events, source_file="blast-radius.jsonl")
    assert rollup["harness"] is None


# ---------------------------------------------------------------------------
# Schema shape contract — all rollup kinds must include required keys
# ---------------------------------------------------------------------------

REQUIRED_TOP_KEYS = {"rollup_kind", "subject_id", "window", "metrics", "source_refs", "harness"}
REQUIRED_WINDOW_KEYS = {"start", "end", "duration_seconds"}


@pytest.mark.parametrize("rollup_fn,events", [
    (rollup_skill_metrics, SKILL_METRICS_EVENTS),
    (rollup_provider_metrics, PROVIDER_ROUTING_EVENTS),
    (rollup_primitive_metrics, PRIMITIVE_EVENTS),
])
def test_schema_shape_contract(rollup_fn, events):
    rollup = rollup_fn(events)
    assert REQUIRED_TOP_KEYS.issubset(rollup.keys()), f"Missing keys: {REQUIRED_TOP_KEYS - rollup.keys()}"
    assert REQUIRED_WINDOW_KEYS.issubset(rollup["window"].keys())
    assert isinstance(rollup["source_refs"], list)
    assert len(rollup["source_refs"]) == len(events)
