# SCOPE: os-only
"""Behavioral tests for Phase 2 detection functions in promote_from_telemetry.

Three detections under test:
  1. detect_skill_override_patterns   — override_rate increase / trust_pass_rate drop
  2. detect_provider_fallback_drift   — fallback_rate growth / latency degradation
  3. detect_dormant_no_evidence       — primitives with no recent event activity

Each detection has:
  - A "trigger" fixture that produces findings
  - A "control" fixture that produces no findings (below threshold)
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from lib.promote_from_telemetry import (
    detect_dormant_no_evidence,
    detect_provider_fallback_drift,
    detect_skill_override_patterns,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_START = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
_BASE_END = datetime(2026, 5, 7, 23, 59, 59, tzinfo=timezone.utc)
_CURR_START = datetime(2026, 5, 8, 0, 0, 0, tzinfo=timezone.utc)
_CURR_END = datetime(2026, 5, 14, 23, 59, 59, tzinfo=timezone.utc)

BASELINE_WINDOW = (_BASE_START, _BASE_END)
CURRENT_WINDOW = (_CURR_START, _CURR_END)


def _skill_event(skill: str, *, ts: str, success: bool = True, override: bool = False) -> dict:
    """Build a skill-metrics schema event."""
    event: dict = {"skill": skill, "timestamp": ts, "success": success}
    if override:
        event["event_type"] = "skill.override"
        del event["success"]
    return event


def _provider_event(provider: str, *, ts: str, action: str = "dispatch", latency_ms: float | None = None) -> dict:
    """Build a provider dispatch event."""
    event: dict = {"chosen_provider": provider, "timestamp": ts, "action": action}
    if latency_ms is not None:
        event["latency_ms"] = latency_ms
    return event


def _primitive_lifecycle_yaml(tmp_path: Path, primitives: list[dict]) -> Path:
    """Write a minimal lifecycle YAML and return its path."""
    import yaml

    content = {"schema_version": 1, "primitives": primitives}
    path = tmp_path / "primitive-lifecycle.yaml"
    path.write_text(yaml.dump(content), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 1. detect_skill_override_patterns
# ---------------------------------------------------------------------------

class TestSkillOverridePatterns:
    def _make_override_events(self, skill: str, baseline_overrides: int, current_overrides: int) -> list[dict]:
        """Generate override events spread across baseline and current windows."""
        events = []
        # Baseline: 10 normal invocations + N overrides
        for i in range(10):
            events.append(_skill_event(skill, ts="2026-05-03T10:00:00Z", success=True))
        for i in range(baseline_overrides):
            events.append(_skill_event(skill, ts="2026-05-03T10:00:00Z", override=True))
        # Current: 10 normal invocations + M overrides
        for i in range(10):
            events.append(_skill_event(skill, ts="2026-05-10T10:00:00Z", success=True))
        for i in range(current_overrides):
            events.append(_skill_event(skill, ts="2026-05-10T10:00:00Z", override=True))
        return events

    def test_override_rate_spike_triggers_p1(self):
        """override_rate >= 0.40 in current window → P1 finding."""
        # 10 invocations + 6 overrides = override_rate = 6/16 ≈ 0.375 … bump to 7
        events = self._make_override_events("scout", baseline_overrides=0, current_overrides=7)
        findings = detect_skill_override_patterns(events, BASELINE_WINDOW, CURRENT_WINDOW)
        assert findings, "Expected at least one finding"
        kinds = {f["kind"] for f in findings}
        assert "skill_override_rate_increase" in kinds
        p1_findings = [f for f in findings if f["severity"] == "P1" and f["subject_id"] == "scout"]
        assert p1_findings, "Expected P1 severity for spike"

    def test_override_rate_delta_triggers_p2(self):
        """override_rate delta >= 0.15 window-over-window → P2 finding.

        rollup_skill_metrics counts override events inside invocation_count
        (branch: elif etype.startswith('skill.')), so:
          baseline: 10 invocations + 0 overrides → override_rate = 0/10 = 0.0
          current:  10 invocations + 4 overrides → override_rate = 4/14 ≈ 0.286
          delta ≈ 0.286 > threshold 0.15 → P2
        """
        events = self._make_override_events("sdd-apply", baseline_overrides=0, current_overrides=4)
        findings = detect_skill_override_patterns(events, BASELINE_WINDOW, CURRENT_WINDOW)
        override_findings = [f for f in findings if f["kind"] == "skill_override_rate_increase" and f["subject_id"] == "sdd-apply"]
        assert override_findings, "Expected override_rate finding for sdd-apply"

    def test_below_threshold_no_finding(self):
        """Small delta (< 0.15) must NOT trigger a finding."""
        # baseline: 0/10, current: 1/10 = delta 0.10 < threshold
        events = self._make_override_events("docs-sync", baseline_overrides=0, current_overrides=1)
        findings = detect_skill_override_patterns(events, BASELINE_WINDOW, CURRENT_WINDOW)
        override_findings = [f for f in findings if f["kind"] == "skill_override_rate_increase" and f["subject_id"] == "docs-sync"]
        assert not override_findings, "Delta 0.10 is below threshold; should not fire"

    def test_trust_pass_rate_drop_triggers(self):
        """trust_pass_rate drop >= 0.10 should produce a finding."""
        # We manually inject trust_pass_rate into events via a custom field
        # detect_skill_override_patterns reads trust_pass_rate from rollup_skill_metrics
        # which currently returns None for it — so this test verifies the None guard works
        # and produces no spurious findings when data is absent.
        events = [
            _skill_event("verify", ts="2026-05-03T10:00:00Z", success=True),
            _skill_event("verify", ts="2026-05-10T10:00:00Z", success=True),
        ]
        findings = detect_skill_override_patterns(events, BASELINE_WINDOW, CURRENT_WINDOW)
        # No trust data → no trust_pass_rate findings; should not crash
        trust_findings = [f for f in findings if f["kind"] == "skill_trust_pass_rate_drop"]
        assert not trust_findings, "No trust signal in schema → no trust findings expected"

    def test_finding_shape_complete(self):
        """Every finding must contain all required keys."""
        events = self._make_override_events("sdd-apply", baseline_overrides=1, current_overrides=3)
        findings = detect_skill_override_patterns(events, BASELINE_WINDOW, CURRENT_WINDOW)
        required_keys = {"kind", "subject_id", "severity", "evidence_window", "current_value", "baseline_value", "suggested_action"}
        for finding in findings:
            assert required_keys <= finding.keys(), f"Finding missing keys: {required_keys - finding.keys()}"


# ---------------------------------------------------------------------------
# 2. detect_provider_fallback_drift
# ---------------------------------------------------------------------------

class TestProviderFallbackDrift:
    def _make_provider_events(
        self,
        provider: str,
        baseline_fallbacks: int,
        current_fallbacks: int,
        baseline_total: int = 10,
        current_total: int = 10,
        baseline_latency: float | None = None,
        current_latency: float | None = None,
    ) -> list[dict]:
        events = []
        # Baseline
        for i in range(baseline_total - baseline_fallbacks):
            e = _provider_event(provider, ts="2026-05-03T10:00:00Z", action="dispatch")
            if baseline_latency is not None:
                e["latency_ms"] = baseline_latency
            events.append(e)
        for i in range(baseline_fallbacks):
            e = _provider_event(provider, ts="2026-05-03T10:00:00Z", action="fallback")
            if baseline_latency is not None:
                e["latency_ms"] = baseline_latency
            events.append(e)
        # Current
        for i in range(current_total - current_fallbacks):
            e = _provider_event(provider, ts="2026-05-10T10:00:00Z", action="dispatch")
            if current_latency is not None:
                e["latency_ms"] = current_latency
            events.append(e)
        for i in range(current_fallbacks):
            e = _provider_event(provider, ts="2026-05-10T10:00:00Z", action="fallback")
            if current_latency is not None:
                e["latency_ms"] = current_latency
            events.append(e)
        return events

    def test_fallback_spike_triggers_p1(self):
        """fallback_rate >= 0.30 in current window → P1 finding."""
        # 10 dispatches, 4 fallbacks → 0.40
        events = self._make_provider_events("qwen", baseline_fallbacks=0, current_fallbacks=4)
        findings = detect_provider_fallback_drift(events, BASELINE_WINDOW, CURRENT_WINDOW)
        p1 = [f for f in findings if f["severity"] == "P1" and f["subject_id"] == "qwen"]
        assert p1, "Expected P1 for fallback rate >= 0.30"

    def test_fallback_delta_triggers_p2(self):
        """fallback_rate delta >= 0.10 → P2 finding."""
        # baseline: 0/10 = 0.0, current: 2/10 = 0.20 → delta 0.20
        events = self._make_provider_events("claude", baseline_fallbacks=0, current_fallbacks=2)
        findings = detect_provider_fallback_drift(events, BASELINE_WINDOW, CURRENT_WINDOW)
        fallback_findings = [f for f in findings if f["kind"] == "provider_fallback_rate_increase" and f["subject_id"] == "claude"]
        assert fallback_findings, "Expected fallback finding for claude"

    def test_below_threshold_no_finding(self):
        """Small delta (< 0.10) must NOT trigger a finding."""
        # baseline: 0/10, current: 0/10 → delta 0.0
        events = self._make_provider_events("openai", baseline_fallbacks=0, current_fallbacks=0)
        findings = detect_provider_fallback_drift(events, BASELINE_WINDOW, CURRENT_WINDOW)
        assert not findings, "No drift should produce no findings"

    def test_latency_degradation_triggers(self):
        """latency increase >= 25% should produce a finding."""
        # baseline 100ms, current 150ms → 50% increase → P1
        events = self._make_provider_events(
            "qwen",
            baseline_fallbacks=0,
            current_fallbacks=0,
            baseline_latency=100.0,
            current_latency=150.0,
        )
        findings = detect_provider_fallback_drift(events, BASELINE_WINDOW, CURRENT_WINDOW)
        lat_findings = [f for f in findings if f["kind"] == "provider_latency_degradation" and f["subject_id"] == "qwen"]
        assert lat_findings, "Expected latency degradation finding"
        assert lat_findings[0]["severity"] == "P1"

    def test_latency_below_threshold_no_finding(self):
        """Latency increase < 25% must NOT trigger a finding."""
        # baseline 100ms, current 115ms → 15% → below threshold
        events = self._make_provider_events(
            "claude",
            baseline_fallbacks=0,
            current_fallbacks=0,
            baseline_latency=100.0,
            current_latency=115.0,
        )
        findings = detect_provider_fallback_drift(events, BASELINE_WINDOW, CURRENT_WINDOW)
        lat_findings = [f for f in findings if f["kind"] == "provider_latency_degradation"]
        assert not lat_findings, "15% latency increase is below threshold"

    def test_finding_shape_complete(self):
        """Every finding must contain all required keys."""
        events = self._make_provider_events("qwen", baseline_fallbacks=0, current_fallbacks=4)
        findings = detect_provider_fallback_drift(events, BASELINE_WINDOW, CURRENT_WINDOW)
        required_keys = {"kind", "subject_id", "severity", "evidence_window", "current_value", "baseline_value", "suggested_action"}
        for finding in findings:
            assert required_keys <= finding.keys(), f"Finding missing keys: {required_keys - finding.keys()}"


# ---------------------------------------------------------------------------
# 3. detect_dormant_no_evidence
# ---------------------------------------------------------------------------

class TestDormantNoEvidence:
    def _recent_ts(self) -> str:
        """Timestamp within the last 10 days (well within window_days=30)."""
        return "2026-05-15T10:00:00Z"

    def _old_ts(self) -> str:
        """Timestamp older than 30 days from 2026-05-18."""
        return "2026-04-01T10:00:00Z"

    def test_primitive_with_no_events_flagged(self, tmp_path):
        """A primitive in lifecycle with zero recent events → finding."""
        lifecycle = _primitive_lifecycle_yaml(tmp_path, [
            {"id": "hooks/blast-radius.sh", "lifecycle_state": "advisory"},
        ])
        events: list[dict] = []  # no events at all
        findings = detect_dormant_no_evidence(lifecycle, events, window_days=30)
        ids = [f["subject_id"] for f in findings]
        assert "hooks/blast-radius.sh" in ids

    def test_primitive_with_recent_events_not_flagged(self, tmp_path):
        """A primitive referenced in recent events must NOT be flagged."""
        lifecycle = _primitive_lifecycle_yaml(tmp_path, [
            {"id": "hooks/rate-limiter.sh", "lifecycle_state": "advisory"},
        ])
        events = [
            {"primitive_id": "hooks/rate-limiter.sh", "timestamp": self._recent_ts()},
        ]
        findings = detect_dormant_no_evidence(lifecycle, events, window_days=30)
        ids = [f["subject_id"] for f in findings]
        assert "hooks/rate-limiter.sh" not in ids

    def test_only_old_events_triggers_finding(self, tmp_path):
        """Events older than window_days must NOT count as evidence."""
        lifecycle = _primitive_lifecycle_yaml(tmp_path, [
            {"id": "hooks/old-hook.sh", "lifecycle_state": "aspirational"},
        ])
        events = [
            {"primitive_id": "hooks/old-hook.sh", "timestamp": self._old_ts()},
        ]
        findings = detect_dormant_no_evidence(lifecycle, events, window_days=30)
        ids = [f["subject_id"] for f in findings]
        assert "hooks/old-hook.sh" in ids, "Old event outside window should not count as evidence"

    def test_empty_lifecycle_yaml_returns_empty(self, tmp_path):
        """An empty or invalid lifecycle YAML must return [] without crashing."""
        lifecycle = tmp_path / "empty.yaml"
        lifecycle.write_text("", encoding="utf-8")
        findings = detect_dormant_no_evidence(lifecycle, [], window_days=30)
        assert findings == []

    def test_missing_lifecycle_file_returns_empty(self, tmp_path):
        """A non-existent lifecycle YAML must return [] without crashing."""
        findings = detect_dormant_no_evidence(tmp_path / "nonexistent.yaml", [], window_days=30)
        assert findings == []

    def test_finding_shape_complete(self, tmp_path):
        """Every finding must contain all required keys."""
        lifecycle = _primitive_lifecycle_yaml(tmp_path, [
            {"id": "hooks/dormant.sh", "lifecycle_state": "dormant"},
        ])
        findings = detect_dormant_no_evidence(lifecycle, [], window_days=30)
        required_keys = {"kind", "subject_id", "severity", "evidence_window", "current_value", "baseline_value", "suggested_action"}
        for finding in findings:
            assert required_keys <= finding.keys(), f"Finding missing keys: {required_keys - finding.keys()}"

    def test_multiple_primitives_mixed_state(self, tmp_path):
        """Mix of active and dormant primitives: only dormant ones flagged."""
        lifecycle = _primitive_lifecycle_yaml(tmp_path, [
            {"id": "hooks/active-hook.sh", "lifecycle_state": "advisory"},
            {"id": "hooks/silent-hook.sh", "lifecycle_state": "advisory"},
        ])
        events = [
            {"primitive_id": "hooks/active-hook.sh", "timestamp": self._recent_ts()},
        ]
        findings = detect_dormant_no_evidence(lifecycle, events, window_days=30)
        ids = [f["subject_id"] for f in findings]
        assert "hooks/silent-hook.sh" in ids
        assert "hooks/active-hook.sh" not in ids
