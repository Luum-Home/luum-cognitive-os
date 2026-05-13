"""Tests asserting that migrated JSONL writers emit MetricEvent-shaped rows.

Each migrated writer must produce rows with ``schema_version`` and ``source``
top-level fields as required by ADR-028 D1.A.

Covered writers (round-2 migration):
1. lib/consequence_engine.py  → consequence-history.jsonl
2. lib/skill_archive.py       → skill-archive.jsonl
3. lib/telemetry.py           → skill-usage / hook-usage / agent-launches / rate-limit-events
4. lib/learning_pipeline.py   → error-skill-correlations.jsonl
5. lib/singularity.py         → singularity-events.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.metric_event import SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_rows(path: str) -> list[dict]:
    """Read all JSONL rows from a file."""
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _assert_metric_event_shape(row: dict, expected_source: str | None = None) -> None:
    """Assert a row has the MetricEvent canonical shape."""
    assert "schema_version" in row, f"Missing schema_version in row: {row}"
    assert "source" in row, f"Missing source in row: {row}"
    assert "event_type" in row, f"Missing event_type in row: {row}"
    assert "payload" in row, f"Missing payload in row: {row}"
    assert "timestamp" in row, f"Missing timestamp in row: {row}"
    assert row["schema_version"] == SCHEMA_VERSION
    assert isinstance(row["payload"], dict)
    if expected_source is not None:
        assert row["source"] == expected_source, (
            f"Expected source={expected_source!r}, got {row['source']!r}"
        )


# ---------------------------------------------------------------------------
# 1. consequence_engine
# ---------------------------------------------------------------------------

class TestConsequenceEngineEmitsMetricEvent:
    def test_evaluate_emits_metric_event_row(self, tmp_path: Path) -> None:
        from lib.consequence_engine import ConsequenceEngine, PerformanceRecord

        history = str(tmp_path / "consequence-history.jsonl")
        engine = ConsequenceEngine(history_path=history)
        engine.evaluate(PerformanceRecord(
            agent_or_skill="test-skill",
            task_type="general",
            trust_score=75.0,
            success=True,
            cost_usd=0.01,
            tokens_used=500,
            retries=0,
            timestamp="2026-04-20T10:00:00+00:00",
        ))
        rows = _read_rows(history)
        assert len(rows) == 1
        _assert_metric_event_shape(rows[0], expected_source="consequence-engine")

    def test_row_has_schema_version(self, tmp_path: Path) -> None:
        from lib.consequence_engine import ConsequenceEngine, PerformanceRecord

        history = str(tmp_path / "consequence-history.jsonl")
        engine = ConsequenceEngine(history_path=history)
        engine.evaluate(PerformanceRecord(
            agent_or_skill="skill-x",
            task_type="test",
            trust_score=90.0,
            success=True,
            cost_usd=0.0,
            tokens_used=100,
            retries=0,
            timestamp="2026-04-20T10:00:00+00:00",
        ))
        row = _read_rows(history)[0]
        assert row["schema_version"] == SCHEMA_VERSION

    def test_payload_preserves_original_fields(self, tmp_path: Path) -> None:
        from lib.consequence_engine import ConsequenceEngine, PerformanceRecord

        history = str(tmp_path / "consequence-history.jsonl")
        engine = ConsequenceEngine(history_path=history)
        engine.evaluate(PerformanceRecord(
            agent_or_skill="my-agent",
            task_type="deploy",
            trust_score=50.0,
            success=False,
            cost_usd=0.02,
            tokens_used=200,
            retries=1,
            timestamp="2026-04-20T10:00:00+00:00",
        ))
        row = _read_rows(history)[0]
        payload = row["payload"]
        assert payload["agent_or_skill"] == "my-agent"
        assert payload["trust_score"] == 50.0

    def test_read_back_via_engine_works(self, tmp_path: Path) -> None:
        """_read_all_raw must normalise MetricEvent rows for internal callers."""
        from lib.consequence_engine import ConsequenceEngine, PerformanceRecord

        history = str(tmp_path / "consequence-history.jsonl")
        engine = ConsequenceEngine(history_path=history)
        engine.evaluate(PerformanceRecord(
            agent_or_skill="round-trip",
            task_type="test",
            trust_score=80.0,
            success=True,
            cost_usd=0.0,
            tokens_used=0,
            retries=0,
            timestamp="2026-04-20T10:00:00+00:00",
        ))
        # Internal reader must return flat dict with record_type key
        raw = engine._read_all_raw()
        assert len(raw) == 1
        assert raw[0]["agent_or_skill"] == "round-trip"


# ---------------------------------------------------------------------------
# 2. skill_archive
# ---------------------------------------------------------------------------

class TestSkillArchiveEmitsMetricEvent:
    def test_record_execution_emits_metric_event_row(self, tmp_path: Path) -> None:
        from lib.skill_archive import SkillArchiveManager

        archive = str(tmp_path / "skill-archive.jsonl")
        mgr = SkillArchiveManager(archive_path=archive)
        mgr.record_execution(
            skill_name="sdd-apply",
            skill_content="# Apply\nDo stuff",
            trust_score=85.0,
            success=True,
            task="apply auth module",
        )
        rows = _read_rows(archive)
        assert len(rows) == 1
        _assert_metric_event_shape(rows[0], expected_source="skill-archive")

    def test_row_has_schema_version(self, tmp_path: Path) -> None:
        from lib.skill_archive import SkillArchiveManager

        archive = str(tmp_path / "skill-archive.jsonl")
        mgr = SkillArchiveManager(archive_path=archive)
        mgr.record_execution("s", "v", 70.0, True, "t")
        row = _read_rows(archive)[0]
        assert row["schema_version"] == SCHEMA_VERSION

    def test_payload_preserves_skill_fields(self, tmp_path: Path) -> None:
        from lib.skill_archive import SkillArchiveManager

        archive = str(tmp_path / "skill-archive.jsonl")
        mgr = SkillArchiveManager(archive_path=archive)
        mgr.record_execution("sdd-verify", "content", 92.0, True, "task", tokens=1000, cost=0.03)
        row = _read_rows(archive)[0]
        payload = row["payload"]
        assert payload["skill_name"] == "sdd-verify"
        assert payload["trust_score"] == 92.0
        assert payload["tokens_used"] == 1000
        assert payload["cost_usd"] == 0.03

    def test_read_back_via_manager_works(self, tmp_path: Path) -> None:
        """_read_all must normalise MetricEvent rows back to SkillSnapshot."""
        from lib.skill_archive import SkillArchiveManager

        archive = str(tmp_path / "skill-archive.jsonl")
        mgr = SkillArchiveManager(archive_path=archive)
        mgr.record_execution("round-trip-skill", "content", 78.0, True, "test-task")
        snaps = mgr._read_all()
        assert len(snaps) == 1
        assert snaps[0].skill_name == "round-trip-skill"
        assert snaps[0].trust_score == 78.0


# ---------------------------------------------------------------------------
# 3. telemetry
# ---------------------------------------------------------------------------

class TestTelemetryEmitsMetricEvent:
    def test_record_skill_invocation_emits_metric_event(self, tmp_path: Path, monkeypatch) -> None:
        import lib.telemetry as telemetry
        monkeypatch.setattr(telemetry, "_project_root", lambda: tmp_path)

        telemetry.record_skill_invocation("sdd-apply", duration_ms=150.0)

        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        rows = _read_rows(str(metrics_dir / telemetry.SKILL_USAGE_FILE))
        assert len(rows) >= 1
        _assert_metric_event_shape(rows[-1], expected_source="skill-usage")

    def test_record_hook_fired_has_schema_version(self, tmp_path: Path, monkeypatch) -> None:
        import lib.telemetry as telemetry
        monkeypatch.setattr(telemetry, "_project_root", lambda: tmp_path)

        telemetry.record_hook_fired("error-learning", "PostToolUse", duration_ms=5.0)

        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        rows = _read_rows(str(metrics_dir / telemetry.HOOK_USAGE_FILE))
        assert rows[-1]["schema_version"] == SCHEMA_VERSION

    def test_iter_records_unwraps_metric_event_rows(self, tmp_path: Path, monkeypatch) -> None:
        """iter_records must yield flat dicts with 'event' key for backward compat."""
        import lib.telemetry as telemetry
        monkeypatch.setattr(telemetry, "_project_root", lambda: tmp_path)

        telemetry.record_agent_launch("sdd-apply-agent", "sonnet", tokens_in=1000)

        results = list(telemetry.iter_records(telemetry.AGENT_LAUNCHES_FILE))
        assert len(results) >= 1
        # Flat shape should be visible to consumers
        last = results[-1]
        assert "event" in last
        assert last["event"] == "agent_launch"


# ---------------------------------------------------------------------------
# 4. learning_pipeline
# ---------------------------------------------------------------------------

class TestLearningPipelineEmitsMetricEvent:
    def test_record_error_emits_metric_event_row(self, tmp_path: Path) -> None:
        from lib.learning_pipeline import LearningPipeline

        correlations = str(tmp_path / "correlations.jsonl")
        pipeline = LearningPipeline(correlations_path=correlations)
        pipeline.record_error(
            error_type="BUILD_ERROR",
            service="payments",
            message="compilation failed",
        )
        rows = _read_rows(correlations)
        assert len(rows) == 1
        _assert_metric_event_shape(rows[0], expected_source="learning-pipeline")

    def test_error_row_has_schema_version(self, tmp_path: Path) -> None:
        from lib.learning_pipeline import LearningPipeline

        correlations = str(tmp_path / "correlations.jsonl")
        pipeline = LearningPipeline(correlations_path=correlations)
        pipeline.record_error("TEST_FAILURE", "api", "test failed")
        row = _read_rows(correlations)[0]
        assert row["schema_version"] == SCHEMA_VERSION

    def test_payload_preserves_error_fields(self, tmp_path: Path) -> None:
        from lib.learning_pipeline import LearningPipeline

        correlations = str(tmp_path / "correlations.jsonl")
        pipeline = LearningPipeline(correlations_path=correlations)
        pipeline.record_error("LINT_ERROR", "auth-service", "unused import")
        row = _read_rows(correlations)[0]
        payload = row["payload"]
        assert payload["error_type"] == "LINT_ERROR"
        assert payload["service"] == "auth-service"

    def test_read_back_via_check_triggers_works(self, tmp_path: Path) -> None:
        """check_learning_triggers must normalise MetricEvent rows."""
        from lib.learning_pipeline import LearningPipeline

        correlations = str(tmp_path / "correlations.jsonl")
        pipeline = LearningPipeline(correlations_path=correlations)
        # Write 3 same-type errors in recent time to trigger pattern detection
        for _ in range(3):
            pipeline.record_error("BUILD_ERROR", "payments", "failed")
        triggers = pipeline.check_learning_triggers()
        error_triggers = [t for t in triggers if t.trigger_type == "error_pattern"]
        assert len(error_triggers) >= 1


# ---------------------------------------------------------------------------
# 5. singularity
# ---------------------------------------------------------------------------

class TestSingularityEmitsMetricEvent:
    def test_append_jsonl_emits_metric_event_row(self, tmp_path: Path) -> None:
        """_append_jsonl must emit MetricEvent-shaped rows."""
        # Import the private function directly
        import sys as _sys
        # singularity uses local imports; ensure lib is on path
        lib_dir = str(Path(__file__).parent.parent.parent / "lib")
        if lib_dir not in _sys.path:
            _sys.path.insert(0, lib_dir)
        from singularity import _append_jsonl  # type: ignore[import]

        out = str(tmp_path / "singularity-events.jsonl")
        _append_jsonl(out, {
            "timestamp": "2026-04-20T10:00:00+00:00",
            "phase": "monitor",
            "action": "no_events",
            "message": "No actionable events detected",
        })
        rows = _read_rows(out)
        assert len(rows) == 1
        _assert_metric_event_shape(rows[0], expected_source="singularity")

    def test_singularity_row_has_schema_version(self, tmp_path: Path) -> None:
        import sys as _sys
        lib_dir = str(Path(__file__).parent.parent.parent / "lib")
        if lib_dir not in _sys.path:
            _sys.path.insert(0, lib_dir)
        from singularity import _append_jsonl  # type: ignore[import]

        out = str(tmp_path / "sing.jsonl")
        _append_jsonl(out, {
            "timestamp": "2026-04-20T10:00:00+00:00",
            "phase": "plan",
            "action": "budget_block",
        })
        row = _read_rows(out)[0]
        assert row["schema_version"] == SCHEMA_VERSION

    def test_read_back_via_read_jsonl_works(self, tmp_path: Path) -> None:
        """_read_jsonl must normalise MetricEvent rows back to flat dicts."""
        import sys as _sys
        lib_dir = str(Path(__file__).parent.parent.parent / "lib")
        if lib_dir not in _sys.path:
            _sys.path.insert(0, lib_dir)
        from singularity import _append_jsonl, _read_jsonl  # type: ignore[import]

        out = str(tmp_path / "sing.jsonl")
        _append_jsonl(out, {
            "timestamp": "2026-04-20T10:00:00+00:00",
            "phase": "cycle_complete",
            "detected": 5,
            "executed": 2,
        })
        rows = _read_jsonl(out)
        assert len(rows) == 1
        flat = rows[0]
        assert flat.get("phase") == "cycle_complete"
        assert flat.get("detected") == 5
