"""Unit tests for lib/metric_event.py (ADR-028 D1.A.1)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Make sure lib/ is importable even when running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.metric_event import (
    SCHEMA_VERSION,
    MetricEvent,
    MetricEventError,
    append_event,
    normalize_legacy_row,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(**kwargs) -> MetricEvent:
    defaults = {"source": "test-hook", "event_type": "test.event"}
    defaults.update(kwargs)
    return MetricEvent(**defaults)


# ---------------------------------------------------------------------------
# Basic construction and validation
# ---------------------------------------------------------------------------


class TestMetricEventBasic:
    def test_valid_event_created(self):
        e = _make_event()
        assert e.source == "test-hook"
        assert e.event_type == "test.event"
        assert e.severity == "info"
        assert e.schema_version == SCHEMA_VERSION
        assert e.payload == {}

    def test_auto_timestamp_set_when_omitted(self):
        e = _make_event()
        assert e.timestamp  # non-empty
        # Must be parseable as ISO-8601
        from datetime import datetime
        parsed = datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
        assert parsed is not None

    def test_explicit_timestamp_preserved(self):
        ts = "2026-01-15T10:30:00+00:00"
        e = _make_event(timestamp=ts)
        assert e.timestamp == ts

    def test_payload_stored(self):
        e = _make_event(payload={"cost_usd": 0.05, "model": "sonnet"})
        assert e.payload["cost_usd"] == 0.05
        assert e.payload["model"] == "sonnet"

    def test_all_valid_severities_accepted(self):
        for sev in ("debug", "info", "warn", "error", "critical"):
            e = _make_event(severity=sev)
            assert e.severity == sev


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestMetricEventValidation:
    def test_rejects_empty_source(self):
        with pytest.raises(MetricEventError, match="source"):
            MetricEvent(source="", event_type="x")

    def test_rejects_non_string_source(self):
        with pytest.raises((MetricEventError, TypeError)):
            MetricEvent(source=None, event_type="x")  # type: ignore[arg-type]

    def test_rejects_empty_event_type(self):
        with pytest.raises(MetricEventError, match="event_type"):
            MetricEvent(source="hook", event_type="")

    def test_rejects_invalid_severity(self):
        with pytest.raises(MetricEventError, match="severity"):
            MetricEvent(source="hook", event_type="x", severity="FATAL")

    def test_rejects_non_dict_payload(self):
        with pytest.raises(MetricEventError, match="payload"):
            MetricEvent(source="hook", event_type="x", payload="bad")  # type: ignore[arg-type]

    def test_rejects_invalid_timestamp(self):
        with pytest.raises(MetricEventError, match="timestamp"):
            MetricEvent(source="hook", event_type="x", timestamp="not-a-date")

    def test_rejects_zero_schema_version(self):
        with pytest.raises(MetricEventError, match="schema_version"):
            MetricEvent(source="hook", event_type="x", schema_version=0)

    def test_rejects_negative_schema_version(self):
        with pytest.raises(MetricEventError, match="schema_version"):
            MetricEvent(source="hook", event_type="x", schema_version=-1)


# ---------------------------------------------------------------------------
# Serialisation round-trip
# ---------------------------------------------------------------------------


class TestMetricEventSerialisation:
    def test_to_dict_contains_all_fields(self):
        e = _make_event(payload={"k": "v"})
        d = e.to_dict()
        assert set(d.keys()) == {
            "timestamp",
            "source",
            "event_type",
            "severity",
            "payload",
            "schema_version",
        }

    def test_to_jsonl_is_valid_json(self):
        e = _make_event(payload={"x": 1})
        line = e.to_jsonl()
        parsed = json.loads(line)
        assert parsed["source"] == "test-hook"
        assert parsed["payload"]["x"] == 1

    def test_to_jsonl_no_trailing_newline(self):
        e = _make_event()
        assert not e.to_jsonl().endswith("\n")

    def test_from_dict_round_trip(self):
        e = _make_event(payload={"a": 1}, severity="warn")
        recovered = MetricEvent.from_dict(e.to_dict())
        assert recovered.source == e.source
        assert recovered.event_type == e.event_type
        assert recovered.severity == e.severity
        assert recovered.payload == e.payload
        assert recovered.schema_version == e.schema_version

    def test_from_dict_tolerates_missing_fields(self):
        """Legacy rows without source/event_type/payload should not raise."""
        d = {"timestamp": "2026-01-01T00:00:00+00:00", "cost": 0.1}
        e = MetricEvent.from_dict(d)
        assert e.source == "unknown"
        assert e.event_type == "legacy"
        assert e.payload == {"cost": 0.1}

    def test_from_dict_tolerates_non_dict_payload(self):
        d = {
            "source": "s",
            "event_type": "t",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "payload": "raw-string",
        }
        e = MetricEvent.from_dict(d)
        assert isinstance(e.payload, dict)
        assert "legacy_payload" in e.payload

    def test_from_dict_tolerates_unknown_schema_version(self):
        """from_dict must not raise for any schema_version >= 1 (ADR-028c contract)."""
        d = {"schema_version": 999, "source": "x", "event_type": "y", "payload": {}}
        e = MetricEvent.from_dict(d)
        assert e.source == "x"
        assert e.event_type == "y"
        assert e.schema_version == 999


# ---------------------------------------------------------------------------
# append_event
# ---------------------------------------------------------------------------


class TestAppendEvent:
    def test_append_creates_file(self, tmp_path):
        path = str(tmp_path / "metrics" / "events.jsonl")
        e = _make_event(payload={"n": 42})
        append_event(path, e)
        assert os.path.isfile(path)

    def test_append_writes_parseable_jsonl(self, tmp_path):
        path = str(tmp_path / "events.jsonl")
        e = _make_event(event_type="cost.recorded", payload={"cost_usd": 0.01})
        append_event(path, e)
        lines = Path(path).read_text().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["event_type"] == "cost.recorded"
        assert parsed["payload"]["cost_usd"] == 0.01

    def test_append_multiple_rows(self, tmp_path):
        path = str(tmp_path / "events.jsonl")
        for i in range(3):
            append_event(path, _make_event(payload={"i": i}))
        lines = Path(path).read_text().strip().splitlines()
        assert len(lines) == 3
        for i, line in enumerate(lines):
            assert json.loads(line)["payload"]["i"] == i

    def test_new_row_has_required_keys(self, tmp_path):
        path = str(tmp_path / "events.jsonl")
        append_event(path, _make_event())
        row = json.loads(Path(path).read_text().strip())
        for key in ("timestamp", "source", "event_type", "severity", "payload", "schema_version"):
            assert key in row, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# normalize_legacy_row
# ---------------------------------------------------------------------------


class TestNormalizeLegacyRow:
    def test_converts_flat_cost_event_row(self):
        legacy = {
            "timestamp": "2026-01-10T12:00:00+00:00",
            "agent": "my-agent",
            "model": "sonnet",
            "estimated_cost_usd": 0.05,
            "tokens_estimated": 3000,
            "is_estimate": True,
        }
        result = normalize_legacy_row(legacy, source="record_completion", event_type="cost.recorded")
        assert result["source"] == "record_completion"
        assert result["event_type"] == "cost.recorded"
        assert result["timestamp"] == "2026-01-10T12:00:00+00:00"
        assert result["schema_version"] == SCHEMA_VERSION

    def test_original_fields_preserved_in_payload(self):
        legacy = {
            "timestamp": "2026-01-10T12:00:00+00:00",
            "agent": "my-agent",
            "model": "sonnet",
            "estimated_cost_usd": 0.05,
        }
        result = normalize_legacy_row(legacy, source="s", event_type="cost.recorded")
        payload = result["payload"]
        assert payload["agent"] == "my-agent"
        assert payload["model"] == "sonnet"
        assert payload["estimated_cost_usd"] == 0.05
        # timestamp should NOT be duplicated inside payload
        assert "timestamp" not in payload

    def test_does_not_mutate_input(self):
        legacy = {"timestamp": "2026-01-10T00:00:00+00:00", "x": 1}
        original_keys = set(legacy.keys())
        normalize_legacy_row(legacy, source="s", event_type="e")
        assert set(legacy.keys()) == original_keys

    def test_missing_timestamp_gets_auto_filled(self):
        legacy = {"agent": "a", "model": "sonnet"}
        result = normalize_legacy_row(legacy, source="s", event_type="e")
        assert result["timestamp"]  # non-empty

    def test_shape_b_fields_move_into_payload(self):
        """Fields like branch/change_id/session_id stay in payload after migration."""
        legacy = {
            "timestamp": "2026-02-01T00:00:00+00:00",
            "agent": "x",
            "session_id": "sess-123",
            "branch": "main",
        }
        result = normalize_legacy_row(legacy, source="s", event_type="cost.recorded")
        assert result["payload"]["session_id"] == "sess-123"
        assert result["payload"]["branch"] == "main"
