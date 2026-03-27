"""Unit tests for lib/phase_timing.py

Validates PhaseTimer context manager, timing table formatting,
JSONL append, cost estimation per model tier, and Engram content building.
"""
import json
import sys
import time
from pathlib import Path

import pytest

_LIB_DIR = str(Path(__file__).resolve().parent.parent.parent / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from phase_timing import (
    MODEL_COSTS,
    PHASE_ESTIMATED_TOKENS,
    PHASE_MODEL_ROUTING,
    PhaseTimer,
    TimingRecord,
    _format_duration,
    append_timing_jsonl,
    build_engram_timing_content,
    estimate_phase_cost,
    format_timing_table,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# TimingRecord dataclass
# ---------------------------------------------------------------------------


class TestTimingRecord:
    def test_creation(self):
        record = TimingRecord(
            phase="apply",
            duration_secs=42.5,
            model="sonnet",
            estimated_cost_usd=0.05,
            timestamp="2026-01-01T00:00:00Z",
            change_name="add-auth",
        )
        assert record.phase == "apply"
        assert record.duration_secs == 42.5
        assert record.model == "sonnet"
        assert record.actual_input_tokens is None
        assert record.actual_output_tokens is None


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


class TestEstimatePhaseCost:
    def test_default_routing(self):
        # apply -> sonnet by default
        cost = estimate_phase_cost("apply")
        assert cost > 0

    def test_explicit_model(self):
        cost_opus = estimate_phase_cost("apply", model="opus")
        cost_haiku = estimate_phase_cost("apply", model="haiku")
        assert cost_opus > cost_haiku

    def test_with_actual_tokens(self):
        cost = estimate_phase_cost(
            "apply", model="sonnet",
            input_tokens=1000, output_tokens=500,
        )
        # sonnet: 1000 * 3.0/1M + 500 * 15.0/1M = 0.003 + 0.0075 = 0.0105
        assert abs(cost - 0.0105) < 0.001

    def test_unknown_phase_uses_defaults(self):
        cost = estimate_phase_cost("unknown-phase")
        assert cost > 0  # Uses default estimates

    def test_unknown_model_uses_sonnet(self):
        cost = estimate_phase_cost("apply", model="unknown")
        cost_sonnet = estimate_phase_cost("apply", model="sonnet")
        assert cost == cost_sonnet

    def test_zero_tokens(self):
        cost = estimate_phase_cost("apply", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_haiku_cheapest(self):
        cost_haiku = estimate_phase_cost("archive", model="haiku")
        cost_sonnet = estimate_phase_cost("archive", model="sonnet")
        cost_opus = estimate_phase_cost("archive", model="opus")
        assert cost_haiku < cost_sonnet < cost_opus


# ---------------------------------------------------------------------------
# PhaseTimer context manager
# ---------------------------------------------------------------------------


class TestPhaseTimer:
    def test_records_duration(self):
        with PhaseTimer("apply", change_name="add-auth") as timer:
            time.sleep(0.05)
        assert timer.record is not None
        assert timer.record.duration_secs >= 0.04
        assert timer.record.phase == "apply"
        assert timer.record.change_name == "add-auth"

    def test_default_model_from_routing(self):
        with PhaseTimer("propose") as timer:
            pass
        assert timer.model == "opus"  # propose -> opus in routing

    def test_custom_model(self):
        with PhaseTimer("apply", model="haiku") as timer:
            pass
        assert timer.model == "haiku"
        assert timer.record.model == "haiku"

    def test_cost_estimated(self):
        with PhaseTimer("apply") as timer:
            pass
        assert timer.record.estimated_cost_usd > 0

    def test_duration_secs_property_during_execution(self):
        timer = PhaseTimer("apply")
        assert timer.duration_secs == 0.0
        with timer:
            # During execution, duration_secs should return current elapsed
            time.sleep(0.05)
            dur = timer.duration_secs
            assert dur >= 0.04

    def test_duration_secs_property_after_completion(self):
        with PhaseTimer("apply") as timer:
            time.sleep(0.05)
        assert timer.duration_secs == timer.record.duration_secs

    def test_to_dict(self):
        with PhaseTimer("apply", change_name="x") as timer:
            pass
        d = timer.to_dict()
        assert d["phase"] == "apply"
        assert d["change_name"] == "x"
        assert "duration_secs" in d
        assert "estimated_cost_usd" in d

    def test_to_dict_before_completion(self):
        timer = PhaseTimer("apply")
        assert timer.to_dict() == {}

    def test_timestamp_set(self):
        with PhaseTimer("apply") as timer:
            pass
        assert timer.record.timestamp != ""
        assert "T" in timer.record.timestamp


# ---------------------------------------------------------------------------
# Timing table formatting
# ---------------------------------------------------------------------------


class TestFormatTimingTable:
    def test_empty_timings(self):
        result = format_timing_table({})
        assert "No timing data" in result

    def test_basic_table(self):
        timings = {"explore": 30.0, "propose": 60.0}
        table = format_timing_table(timings)
        assert "Phase" in table
        assert "Duration" in table
        assert "explore" in table
        assert "propose" in table
        assert "TOTAL" in table
        # Should have separators
        assert "+-" in table

    def test_table_with_models(self):
        timings = {"apply": 120.0}
        models = {"apply": "opus"}
        table = format_timing_table(timings, models)
        assert "opus" in table

    def test_cost_column(self):
        timings = {"apply": 10.0}
        table = format_timing_table(timings)
        assert "$" in table

    def test_total_row(self):
        timings = {"explore": 10.0, "propose": 20.0}
        table = format_timing_table(timings)
        assert "TOTAL" in table


# ---------------------------------------------------------------------------
# Duration formatting
# ---------------------------------------------------------------------------


class TestFormatDuration:
    def test_seconds(self):
        assert _format_duration(30.5) == "30.5s"

    def test_minutes(self):
        result = _format_duration(125.0)
        assert "2m" in result

    def test_hours(self):
        result = _format_duration(7200.0)
        assert "2h" in result


# ---------------------------------------------------------------------------
# JSONL append
# ---------------------------------------------------------------------------


class TestAppendTimingJsonl:
    def test_creates_file(self, tmp_path):
        filepath = str(tmp_path / "timings.jsonl")
        record = append_timing_jsonl(
            filepath, "apply", 30.0,
            change_name="add-auth", model="sonnet",
        )
        assert record["phase"] == "apply"
        assert record["duration_secs"] == 30.0
        assert record["change_name"] == "add-auth"
        assert record["model"] == "sonnet"
        assert "timestamp" in record
        assert "estimated_cost_usd" in record

        # Verify file content
        with open(filepath) as f:
            line = f.readline()
            data = json.loads(line)
            assert data["phase"] == "apply"

    def test_appends_to_existing(self, tmp_path):
        filepath = str(tmp_path / "timings.jsonl")
        append_timing_jsonl(filepath, "explore", 10.0)
        append_timing_jsonl(filepath, "propose", 20.0)

        with open(filepath) as f:
            lines = f.readlines()
        assert len(lines) == 2

    def test_with_actual_tokens(self, tmp_path):
        filepath = str(tmp_path / "timings.jsonl")
        record = append_timing_jsonl(
            filepath, "apply", 30.0,
            input_tokens=5000, output_tokens=3000,
        )
        assert record["input_tokens"] == 5000
        assert record["output_tokens"] == 3000

    def test_creates_parent_dirs(self, tmp_path):
        filepath = str(tmp_path / "sub" / "dir" / "timings.jsonl")
        append_timing_jsonl(filepath, "apply", 10.0)
        assert Path(filepath).exists()

    def test_default_model_from_routing(self, tmp_path):
        filepath = str(tmp_path / "timings.jsonl")
        record = append_timing_jsonl(filepath, "propose", 10.0)
        assert record["model"] == "opus"  # propose -> opus


# ---------------------------------------------------------------------------
# Engram content building
# ---------------------------------------------------------------------------


class TestBuildEngramTimingContent:
    def test_basic_content(self):
        timings = {"explore": 10.0, "propose": 20.0}
        result = build_engram_timing_content("add-auth", timings)
        assert result["title"] == "SDD timings: add-auth"
        assert result["topic_key"] == "planning/add-auth/timings"
        assert result["type"] == "pattern"
        assert "Phases timed" in result["content"]
        assert "2" in result["content"]  # 2 phases
        assert "add-auth" in result["content"]

    def test_content_includes_table(self):
        timings = {"apply": 30.0}
        result = build_engram_timing_content("x", timings)
        assert "```" in result["content"]
        assert "Phase" in result["content"]

    def test_with_models(self):
        timings = {"apply": 30.0}
        models = {"apply": "opus"}
        result = build_engram_timing_content("x", timings, models)
        assert "opus" in result["content"]
