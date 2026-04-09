#!/usr/bin/env python3
"""Integration tests for the Cognitive OS data pipeline.

Validates the end-to-end flow:
  agent completes → record_completion.py extracts signals
  → learning_pipeline.py processes → consequence_engine.py evaluates
  → skill_archive.jsonl / consequence-history.jsonl

Run:
    python -m pytest tests/integration/test_data_pipeline.py -v --tb=short

No Docker/testcontainers required — all tests run against lib/ modules with
tmp directories for metrics files.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Testcontainers availability guard (follow existing project pattern)
# ---------------------------------------------------------------------------
tc_available = True
try:
    from testcontainers.core.container import DockerContainer  # noqa: F401
    from testcontainers.core.network import Network  # noqa: F401
    from testcontainers.postgres import PostgresContainer  # noqa: F401
except ImportError:
    tc_available = False

# ---------------------------------------------------------------------------
# Lib imports — skip gracefully if not found
# ---------------------------------------------------------------------------
lib_available = True
_import_error: str = ""

try:
    # Ensure lib/ is on path
    _repo_root = str(Path(__file__).resolve().parents[2])
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)

    from lib.record_completion import (
        extract_skill_name,
        extract_trust_score,
        estimate_tokens,
        classify_task_type,
        detect_success,
        append_cost_event,
    )
    from lib.learning_pipeline import LearningPipeline
    from lib.consequence_engine import (
        ConsequenceEngine,
        ConsequenceAction,
        Consequence,
        PerformanceRecord,
    )
    from lib.skill_archive import SkillArchiveManager
    from lib.dispatch_helper import check_slot_availability
except Exception as exc:
    lib_available = False
    _import_error = str(exc)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not lib_available, reason=f"lib modules not importable: {_import_error}"),
]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_metrics(tmp_path: Path) -> Path:
    """Return a tmp metrics directory that is isolated per test."""
    metrics_dir = tmp_path / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    return metrics_dir


@pytest.fixture()
def realistic_completion_data() -> dict:
    """A realistic PostToolUse JSON payload with a proper Trust Report."""
    output = (
        "TRUST_REPORT: SCORE=82 STATUS=MEDIUM EVIDENCE=3 UNCERTAINTIES=1\n"
        "---\n"
        "Score: 82/100\n\n"
        "EVIDENCE PROVIDED:\n"
        "  [check] go build ./... exits 0\n"
        "  [check] go test ./internal/users/... — 14 passed, 0 skipped\n"
        "  [warn] integration test not run (no DB available)\n\n"
        "WHAT I'M CONFIDENT ABOUT:\n"
        "  - GetUserByID use case implemented with correct interfaces\n\n"
        "WHAT I'M UNSURE ABOUT:\n"
        "  - Edge case when user has no roles assigned\n\n"
        "WHAT THE HUMAN SHOULD VERIFY:\n"
        "  - Run integration test suite against real DB\n"
    )
    return {
        "tool_call_id": "toolu_abc123",
        "tool_name": "Agent",
        "tool_input": {
            "description": "Implement GetUserByID use case",
            "prompt": "Implement the GetUserByID use case in internal/users/application/...",
        },
        "tool_response": {
            "result": output,
        },
    }


# ---------------------------------------------------------------------------
# Test 1 — record_completion extracts real signals
# ---------------------------------------------------------------------------


class TestRecordCompletionExtractsRealSignals:
    """record_completion.py must extract non-trivial, non-zero values."""

    def test_skill_name_is_extracted_from_description(
        self, realistic_completion_data: dict
    ) -> None:
        skill_name = extract_skill_name(realistic_completion_data)
        assert skill_name, "skill_name must not be empty"
        assert skill_name != "unknown", "skill_name must not be 'unknown'"
        assert "GetUserByID" in skill_name or "Implement" in skill_name

    def test_trust_score_extracted_from_trust_report_header(
        self, realistic_completion_data: dict
    ) -> None:
        output = realistic_completion_data["tool_response"]["result"]
        score = extract_trust_score(output)
        # Must extract 82 from TRUST_REPORT header, NOT the hardcoded 75 default
        assert score == 82, f"Expected 82 extracted from TRUST_REPORT header, got {score}"
        assert score != 75, "Score must not be the hardcoded fallback of 75"

    def test_tokens_are_non_zero(self, realistic_completion_data: dict) -> None:
        output = realistic_completion_data["tool_response"]["result"]
        tokens = estimate_tokens(output)
        assert tokens > 0, "estimated tokens must be > 0 for non-empty output"

    def test_task_type_classified_correctly(
        self, realistic_completion_data: dict
    ) -> None:
        skill_name = extract_skill_name(realistic_completion_data)
        task_type = classify_task_type(skill_name)
        assert task_type == "implementation", (
            f"Expected 'implementation' for description starting with 'Implement', got {task_type!r}"
        )

    def test_success_detected_for_clean_output(
        self, realistic_completion_data: dict
    ) -> None:
        output = realistic_completion_data["tool_response"]["result"]
        success = detect_success(output, realistic_completion_data)
        assert success is True, "Agent output with no error keywords should be success=True"

    def test_failure_detected_when_output_contains_error(self) -> None:
        data = {
            "tool_response": {"result": "BUILD FAILED: compilation error in main.go"},
        }
        success = detect_success(data["tool_response"]["result"], data)
        assert success is False


# ---------------------------------------------------------------------------
# Test 2 — learning_pipeline processes completion and writes skill-metrics
# ---------------------------------------------------------------------------


class TestLearningPipelineProcessesCompletion:
    """LearningPipeline must persist real data to metrics JSONL."""

    def _make_pipeline(self, tmp_metrics: Path) -> LearningPipeline:
        """Build a LearningPipeline with injected tmp paths."""
        archive = SkillArchiveManager(
            archive_path=str(tmp_metrics / "skill-archive.jsonl"),
        )
        engine = ConsequenceEngine(
            history_path=str(tmp_metrics / "consequence-history.jsonl"),
        )
        correlations = str(tmp_metrics / "error-skill-correlations.jsonl")
        errors = str(tmp_metrics / "error-learning.jsonl")
        return LearningPipeline(
            skill_archive=archive,
            consequence_engine=engine,
            correlations_path=correlations,
            errors_path=errors,
        )

    def test_record_agent_completion_writes_to_skill_archive(
        self, tmp_metrics: Path, realistic_completion_data: dict
    ) -> None:
        pipeline = self._make_pipeline(tmp_metrics)
        output = realistic_completion_data["tool_response"]["result"]

        skill_name = extract_skill_name(realistic_completion_data)
        trust_score = extract_trust_score(output)
        tokens = estimate_tokens(output)

        action = pipeline.record_agent_completion(
            task_id="toolu_abc123",
            success=True,
            trust_score=trust_score,
            skill_name=skill_name,
            tokens_used=tokens,
        )

        archive_file = tmp_metrics / "skill-archive.jsonl"
        assert archive_file.exists(), "skill-archive.jsonl must be created"

        lines = [json.loads(l) for l in archive_file.read_text().splitlines() if l.strip()]
        assert len(lines) >= 1, "At least one entry must be written"

        entry = lines[0]
        assert entry.get("skill_name"), "skill_name field must be non-empty"
        assert entry["skill_name"] == skill_name
        assert entry.get("trust_score") == trust_score, (
            f"trust_score in archive ({entry.get('trust_score')}) must equal "
            f"extracted score ({trust_score})"
        )
        assert entry.get("timestamp"), "timestamp must be present"

    def test_record_returns_consequence_action(
        self, tmp_metrics: Path
    ) -> None:
        pipeline = self._make_pipeline(tmp_metrics)
        action = pipeline.record_agent_completion(
            task_id="task-001",
            success=True,
            trust_score=90.0,
            skill_name="sdd-apply",
            tokens_used=5000,
        )
        assert isinstance(action, ConsequenceAction)
        assert action.consequence in Consequence, (
            f"Unexpected consequence value: {action.consequence}"
        )

    def test_tokens_non_zero_in_archive(self, tmp_metrics: Path) -> None:
        pipeline = self._make_pipeline(tmp_metrics)
        pipeline.record_agent_completion(
            task_id="task-002",
            success=True,
            trust_score=75.0,
            skill_name="sdd-verify",
            tokens_used=1234,
        )
        archive_file = tmp_metrics / "skill-archive.jsonl"
        lines = [json.loads(l) for l in archive_file.read_text().splitlines() if l.strip()]
        entry = lines[0]
        assert entry.get("tokens_used", 0) == 1234, (
            f"tokens_used must be 1234, got {entry.get('tokens_used')}"
        )


# ---------------------------------------------------------------------------
# Test 3 — consequence_engine evaluates streaks correctly
# ---------------------------------------------------------------------------


class TestConsequenceEngineEvaluatesPerformance:
    """ConsequenceEngine must apply the correct consequence based on streaks."""

    def _now_iso(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def _make_engine(self, tmp_metrics: Path) -> ConsequenceEngine:
        return ConsequenceEngine(
            history_path=str(tmp_metrics / "consequence-history.jsonl"),
        )

    def _record(
        self,
        engine: ConsequenceEngine,
        skill: str,
        trust_score: float,
        success: bool = True,
    ) -> ConsequenceAction:
        rec = PerformanceRecord(
            agent_or_skill=skill,
            task_type="test-task",
            trust_score=trust_score,
            success=success,
            cost_usd=0.001,
            tokens_used=500,
            retries=0,
            timestamp=self._now_iso(),
        )
        return engine.evaluate(rec)

    def test_high_scores_eventually_trigger_promote(self, tmp_metrics: Path) -> None:
        engine = self._make_engine(tmp_metrics)
        skill = "test-skill-promote"
        actions = []
        for _ in range(5):
            actions.append(self._record(engine, skill, trust_score=90.0))

        last_action = actions[-1]
        assert last_action.consequence == Consequence.PROMOTE, (
            f"After 5 consecutive scores >= 85, expected PROMOTE, got {last_action.consequence}"
        )

    def test_first_low_score_triggers_warn(self, tmp_metrics: Path) -> None:
        engine = self._make_engine(tmp_metrics)
        action = self._record(engine, "test-skill-warn", trust_score=40.0)
        assert action.consequence == Consequence.WARN, (
            f"First low score should trigger WARN, got {action.consequence}"
        )

    def test_second_consecutive_low_triggers_degrade(self, tmp_metrics: Path) -> None:
        engine = self._make_engine(tmp_metrics)
        skill = "test-skill-degrade"
        self._record(engine, skill, trust_score=40.0)
        action = self._record(engine, skill, trust_score=40.0)
        assert action.consequence == Consequence.DEGRADE, (
            f"Second consecutive low score should trigger DEGRADE, got {action.consequence}"
        )

    def test_third_consecutive_low_triggers_disable(self, tmp_metrics: Path) -> None:
        engine = self._make_engine(tmp_metrics)
        skill = "test-skill-disable"
        self._record(engine, skill, trust_score=40.0)
        self._record(engine, skill, trust_score=40.0)
        action = self._record(engine, skill, trust_score=40.0)
        assert action.consequence == Consequence.DISABLE, (
            f"Third consecutive low score should trigger DISABLE, got {action.consequence}"
        )

    def test_consequence_history_written_with_correct_entries(
        self, tmp_metrics: Path
    ) -> None:
        engine = self._make_engine(tmp_metrics)
        skill = "test-skill-history"
        self._record(engine, skill, trust_score=88.0)
        self._record(engine, skill, trust_score=50.0)

        history_file = tmp_metrics / "consequence-history.jsonl"
        assert history_file.exists(), "consequence-history.jsonl must be created"

        lines = [json.loads(l) for l in history_file.read_text().splitlines() if l.strip()]
        assert len(lines) >= 2, "At least 2 performance entries must be written"

        perf_entries = [l for l in lines if l.get("record_type") == "performance"]
        assert len(perf_entries) >= 2, "Both completions must be recorded"

        skill_entries = [e for e in perf_entries if e.get("agent_or_skill") == skill]
        assert len(skill_entries) == 2

        scores = [e["trust_score"] for e in skill_entries]
        assert 88.0 in scores
        assert 50.0 in scores

    def test_promote_streak_requires_exactly_five(self, tmp_metrics: Path) -> None:
        engine = self._make_engine(tmp_metrics)
        skill = "test-skill-streak"
        # 4 high scores should NOT yet promote
        for _ in range(4):
            action = self._record(engine, skill, trust_score=90.0)
        assert action.consequence != Consequence.PROMOTE, (
            "Only 4 high scores must NOT trigger PROMOTE yet"
        )
        # 5th should promote
        action = self._record(engine, skill, trust_score=90.0)
        assert action.consequence == Consequence.PROMOTE


# ---------------------------------------------------------------------------
# Test 4 — dispatch_gate blocks when at capacity
# ---------------------------------------------------------------------------


class TestDispatchGateBlocksAtCapacity:
    """check_slot_availability must reflect in_progress task count."""

    def _write_tasks(self, tasks_path: Path, statuses: list[str]) -> None:
        tasks = [
            {"id": f"task-{i}", "status": s, "description": f"Task {i}"}
            for i, s in enumerate(statuses)
        ]
        tasks_path.parent.mkdir(parents=True, exist_ok=True)
        tasks_path.write_text(json.dumps({"tasks": tasks}))

    def _write_config(self, config_path: Path, max_parallel: int = 3) -> None:
        config_path.write_text(
            f"resources:\n  compute:\n    max_parallel_agents: {max_parallel}\n"
            f"max_parallel_agents: {max_parallel}\n"
        )

    def test_blocked_when_at_capacity(self, tmp_path: Path) -> None:
        tasks_path = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        config_path = tmp_path / "cognitive-os.yaml"
        self._write_config(config_path, max_parallel=3)
        self._write_tasks(tasks_path, ["in_progress", "in_progress", "in_progress"])

        result = check_slot_availability(
            config_path=str(config_path),
            tasks_path=str(tasks_path),
        )
        assert result["available"] is False, (
            f"Should be blocked when active ({result['active']}) >= max ({result['max']})"
        )
        assert result["active"] == 3
        assert result["max"] == 3

    def test_available_when_under_capacity(self, tmp_path: Path) -> None:
        tasks_path = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        config_path = tmp_path / "cognitive-os.yaml"
        self._write_config(config_path, max_parallel=3)
        # 2 in_progress, 1 completed
        self._write_tasks(tasks_path, ["in_progress", "in_progress", "completed"])

        result = check_slot_availability(
            config_path=str(config_path),
            tasks_path=str(tasks_path),
        )
        assert result["available"] is True, (
            f"Should be available when active ({result['active']}) < max ({result['max']})"
        )
        assert result["active"] == 2

    def test_removing_one_task_makes_slot_available(self, tmp_path: Path) -> None:
        tasks_path = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        config_path = tmp_path / "cognitive-os.yaml"
        self._write_config(config_path, max_parallel=3)

        # Start fully loaded
        self._write_tasks(tasks_path, ["in_progress", "in_progress", "in_progress"])
        result = check_slot_availability(
            config_path=str(config_path), tasks_path=str(tasks_path)
        )
        assert result["available"] is False

        # Remove one task (simulate completion)
        self._write_tasks(tasks_path, ["in_progress", "in_progress", "completed"])
        result = check_slot_availability(
            config_path=str(config_path), tasks_path=str(tasks_path)
        )
        assert result["available"] is True

    def test_empty_tasks_file_means_available(self, tmp_path: Path) -> None:
        tasks_path = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        config_path = tmp_path / "cognitive-os.yaml"
        self._write_config(config_path, max_parallel=3)
        tasks_path.parent.mkdir(parents=True, exist_ok=True)
        tasks_path.write_text(json.dumps({"tasks": []}))

        result = check_slot_availability(
            config_path=str(config_path), tasks_path=str(tasks_path)
        )
        assert result["available"] is True
        assert result["active"] == 0

    def test_missing_tasks_file_means_available(self, tmp_path: Path) -> None:
        config_path = tmp_path / "cognitive-os.yaml"
        self._write_config(config_path, max_parallel=3)
        missing_tasks = tmp_path / "nonexistent" / "active-tasks.json"

        result = check_slot_availability(
            config_path=str(config_path), tasks_path=str(missing_tasks)
        )
        assert result["available"] is True


# ---------------------------------------------------------------------------
# Test 5 — cost events written with real (non-zero) values
# ---------------------------------------------------------------------------


class TestCostEventsWrittenWithRealValues:
    """append_cost_event must produce non-zero cost for real token counts."""

    def test_cost_event_has_non_zero_estimated_cost(self, tmp_metrics: Path) -> None:
        known_tokens = 2000
        append_cost_event(str(tmp_metrics), "sdd-apply skill run", known_tokens)

        cost_file = tmp_metrics / "cost-events.jsonl"
        assert cost_file.exists(), "cost-events.jsonl must be created"

        lines = [json.loads(l) for l in cost_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 1

        entry = lines[0]
        assert entry["estimated_cost_usd"] > 0, (
            f"estimated_cost_usd must be > 0 for {known_tokens} tokens, "
            f"got {entry['estimated_cost_usd']}"
        )
        assert entry["tokens_estimated"] == known_tokens
        assert entry["agent"] == "sdd-apply skill run"
        assert "timestamp" in entry
        assert "model" in entry

    def test_cost_scales_with_token_count(self, tmp_metrics: Path) -> None:
        small_dir = tmp_metrics / "small"
        large_dir = tmp_metrics / "large"
        small_dir.mkdir()
        large_dir.mkdir()

        append_cost_event(str(small_dir), "agent", 100)
        append_cost_event(str(large_dir), "agent", 10_000)

        small_cost = json.loads(
            (small_dir / "cost-events.jsonl").read_text().strip()
        )["estimated_cost_usd"]
        large_cost = json.loads(
            (large_dir / "cost-events.jsonl").read_text().strip()
        )["estimated_cost_usd"]

        assert large_cost > small_cost, (
            f"Cost for 10K tokens ({large_cost}) must exceed cost for 100 tokens ({small_cost})"
        )

    def test_full_pipeline_produces_cost_event(self, tmp_path: Path) -> None:
        """End-to-end: record_completion path writes cost event."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True)

        output = (
            "TRUST_REPORT: SCORE=78 STATUS=MEDIUM EVIDENCE=2 UNCERTAINTIES=1\n"
            "---\n"
            "Score: 78/100\n"
            "Agent completed the sdd-verify task successfully.\n" * 20
        )
        completion_data = {
            "tool_call_id": "toolu_xyz",
            "tool_input": {"description": "sdd-verify: check the spec"},
            "tool_response": {"result": output},
        }

        skill_name = extract_skill_name(completion_data)
        tokens = estimate_tokens(output)

        append_cost_event(str(metrics_dir), skill_name, tokens)

        cost_file = metrics_dir / "cost-events.jsonl"
        assert cost_file.exists()
        entry = json.loads(cost_file.read_text().strip())
        assert entry["estimated_cost_usd"] > 0
        assert entry["tokens_estimated"] > 0
        assert entry["tokens_estimated"] == tokens
