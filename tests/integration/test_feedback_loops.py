#!/usr/bin/env python3
"""Integration tests: COS feedback loops end-to-end.

Validates:
  consequence_engine degrade/disable streaks
  consequence_engine promote streaks + skill_archive snapshot
  streak reset on low score interruption
  error-pattern detection in learning_pipeline
  full pipeline: record_completion → learning_pipeline → consequence_engine

Run:
    python3 -m pytest tests/integration/test_feedback_loops.py -v --tb=short
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from tests.utils.jsonl import read_first_jsonl, read_jsonl

# ---------------------------------------------------------------------------
# Path setup — ensure repo root is on sys.path
# ---------------------------------------------------------------------------
_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# ---------------------------------------------------------------------------
# Lib imports — skip entire module if not importable
# ---------------------------------------------------------------------------
lib_available = True
_import_error: str = ""

try:
    from lib.consequence_engine import (
        ConsequenceEngine,
        Consequence,
        ConsequenceAction,
        PerformanceRecord,
    )
    from lib.skill_archive import SkillArchiveManager
    from lib.learning_pipeline import LearningPipeline
    from lib.record_completion import (
        extract_skill_name,
        extract_trust_score,
        estimate_tokens,
        detect_success,
        append_cost_event,
        classify_task_type,
    )
except Exception as exc:
    lib_available = False
    _import_error = str(exc)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not lib_available,
        reason=f"lib modules not importable: {_import_error}",
    ),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_engine(tmp_metrics: Path) -> ConsequenceEngine:
    return ConsequenceEngine(
        history_path=str(tmp_metrics / "consequence-history.jsonl"),
    )


def _make_archive(tmp_metrics: Path) -> SkillArchiveManager:
    return SkillArchiveManager(
        archive_path=str(tmp_metrics / "skill-archive.jsonl"),
    )


def _make_pipeline(tmp_metrics: Path) -> LearningPipeline:
    archive = _make_archive(tmp_metrics)
    engine = _make_engine(tmp_metrics)
    return LearningPipeline(
        skill_archive=archive,
        consequence_engine=engine,
        correlations_path=str(tmp_metrics / "error-skill-correlations.jsonl"),
        errors_path=str(tmp_metrics / "error-learning.jsonl"),
    )


def _record(
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
        timestamp=_now_iso(),
    )
    return engine.evaluate(rec)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_metrics(tmp_path: Path) -> Path:
    """Isolated tmp metrics dir — never touches real .cognitive-os/."""
    d = tmp_path / ".cognitive-os" / "metrics"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Test 1 — degrade loop: WARN → DEGRADE → DISABLE on consecutive low scores
# ---------------------------------------------------------------------------


class TestDegradeLoopOnConsecutiveLowScores:
    """Record 3 completions < 60. Expect WARN, DEGRADE, DISABLE in order."""

    def test_first_low_score_is_warn(self, tmp_metrics: Path) -> None:
        engine = _make_engine(tmp_metrics)
        action = _record(engine, "skill-A", trust_score=45.0)
        assert action.consequence == Consequence.WARN, (
            f"1st low score must be WARN, got {action.consequence}"
        )

    def test_second_consecutive_low_score_is_degrade(self, tmp_metrics: Path) -> None:
        engine = _make_engine(tmp_metrics)
        _record(engine, "skill-A", trust_score=45.0)
        action = _record(engine, "skill-A", trust_score=45.0)
        assert action.consequence == Consequence.DEGRADE, (
            f"2nd consecutive low score must be DEGRADE, got {action.consequence}"
        )

    def test_third_consecutive_low_score_is_disable(self, tmp_metrics: Path) -> None:
        engine = _make_engine(tmp_metrics)
        _record(engine, "skill-A", trust_score=45.0)
        _record(engine, "skill-A", trust_score=45.0)
        action = _record(engine, "skill-A", trust_score=45.0)
        assert action.consequence == Consequence.DISABLE, (
            f"3rd consecutive low score must be DISABLE, got {action.consequence}"
        )

    def test_disabled_skill_appears_in_get_disabled_skills(
        self, tmp_metrics: Path
    ) -> None:
        engine = _make_engine(tmp_metrics)
        for _ in range(3):
            action = _record(engine, "skill-A", trust_score=45.0)
            # apply_consequence writes the disable/degrade records that
            # get_disabled_skills reads (evaluate only writes 'performance' records)
            engine.apply_consequence(action)

        disabled = engine.get_disabled_skills()
        names = [d["skill"] for d in disabled]
        assert "skill-A" in names, (
            f"skill-A must appear in disabled skills after 3 WARN/DEGRADE/DISABLE; "
            f"got {names}"
        )

    def test_full_sequence_produces_correct_actions(self, tmp_metrics: Path) -> None:
        """All three records together: verify exact consequence sequence."""
        engine = _make_engine(tmp_metrics)
        actions = [_record(engine, "skill-A", trust_score=45.0) for _ in range(3)]
        consequences = [a.consequence for a in actions]
        assert consequences == [
            Consequence.WARN,
            Consequence.DEGRADE,
            Consequence.DISABLE,
        ], f"Expected [WARN, DEGRADE, DISABLE], got {consequences}"


# ---------------------------------------------------------------------------
# Test 2 — promote loop: PROMOTE after 5 consecutive high scores
# ---------------------------------------------------------------------------


class TestPromoteLoopOnConsecutiveHighScores:
    """Record 5 completions >= 85. Verify PROMOTE and skill_archive snapshot."""

    def test_promote_fires_on_fifth_high_score(self, tmp_metrics: Path) -> None:
        engine = _make_engine(tmp_metrics)
        actions = [_record(engine, "skill-B", trust_score=90.0) for _ in range(5)]
        last = actions[-1]
        assert last.consequence == Consequence.PROMOTE, (
            f"After 5 consecutive >= 85 scores, expected PROMOTE, got {last.consequence}"
        )

    def test_fourth_high_score_is_not_yet_promote(self, tmp_metrics: Path) -> None:
        engine = _make_engine(tmp_metrics)
        actions = [_record(engine, "skill-B", trust_score=90.0) for _ in range(4)]
        last = actions[-1]
        assert last.consequence != Consequence.PROMOTE, (
            "After only 4 high scores, must NOT yet be PROMOTE"
        )

    def test_skill_archive_has_snapshot_after_promote(
        self, tmp_metrics: Path
    ) -> None:
        """After promotion pipeline, skill-archive.jsonl must have 5 entries."""
        pipeline = _make_pipeline(tmp_metrics)
        for i in range(5):
            pipeline.record_agent_completion(
                task_id=f"task-{i}",
                success=True,
                trust_score=90.0,
                skill_name="skill-B",
                tokens_used=500,
            )

        archive_file = tmp_metrics / "skill-archive.jsonl"
        assert archive_file.exists(), "skill-archive.jsonl must exist after 5 completions"

        lines = read_jsonl(archive_file)
        skill_b_entries = [e for e in lines if e.get("skill_name") == "skill-B"]
        assert len(skill_b_entries) == 5, (
            f"Expected 5 archive entries for skill-B, got {len(skill_b_entries)}"
        )

    def test_best_version_is_set_after_promote(self, tmp_metrics: Path) -> None:
        archive = _make_archive(tmp_metrics)
        for _ in range(5):
            archive.record_execution(
                skill_name="skill-B",
                skill_content="# skill-B v1 content",
                trust_score=90.0,
                success=True,
                task="promote-test",
                tokens=500,
            )
        best = archive.get_best_version("skill-B")
        assert best is not None, "get_best_version must return a snapshot after successful runs"
        assert best.trust_score == 90.0
        assert best.skill_name == "skill-B"

    def test_promote_logged_in_consequence_history(self, tmp_metrics: Path) -> None:
        engine = _make_engine(tmp_metrics)
        for _ in range(5):
            action = _record(engine, "skill-B", trust_score=90.0)
            # apply_consequence writes the 'promotion' record_type entry
            engine.apply_consequence(action)

        history_file = tmp_metrics / "consequence-history.jsonl"
        lines = read_jsonl(history_file)
        promotion_entries = [l for l in lines if l.get("record_type") == "promotion"]
        assert len(promotion_entries) >= 1, (
            "At least one 'promotion' record_type entry must be in consequence-history.jsonl"
        )
        assert promotion_entries[-1]["target"] == "skill-B"


# ---------------------------------------------------------------------------
# Test 3 — streak resets on a low score, then promote after 5 more highs
# ---------------------------------------------------------------------------


class TestPromoteResetsOnLowScore:
    """4 high scores → 1 low → streak resets → 5 more high → PROMOTE."""

    def test_four_high_then_one_low_does_not_promote(self, tmp_metrics: Path) -> None:
        engine = _make_engine(tmp_metrics)
        for _ in range(4):
            _record(engine, "skill-C", trust_score=90.0)
        action = _record(engine, "skill-C", trust_score=40.0)
        assert action.consequence != Consequence.PROMOTE, (
            "After 4 high + 1 low, must NOT be PROMOTE"
        )
        # Low score breaks the streak so it should be WARN (first low)
        assert action.consequence == Consequence.WARN, (
            f"Low score after streak should be WARN, got {action.consequence}"
        )

    def test_five_high_after_reset_triggers_promote(self, tmp_metrics: Path) -> None:
        engine = _make_engine(tmp_metrics)
        # 4 high scores (streak building)
        for _ in range(4):
            _record(engine, "skill-C", trust_score=90.0)
        # 1 low score (streak reset)
        _record(engine, "skill-C", trust_score=40.0)
        # 5 more high scores — NOW the streak is rebuilt from scratch
        actions = [_record(engine, "skill-C", trust_score=90.0) for _ in range(5)]
        last = actions[-1]
        assert last.consequence == Consequence.PROMOTE, (
            f"After reset + 5 new high scores, expected PROMOTE, got {last.consequence}"
        )

    def test_total_history_reflects_all_records(self, tmp_metrics: Path) -> None:
        """10 records total (4+1+5) should all appear in consequence-history.jsonl."""
        engine = _make_engine(tmp_metrics)
        for _ in range(4):
            _record(engine, "skill-C", trust_score=90.0)
        _record(engine, "skill-C", trust_score=40.0)
        for _ in range(5):
            _record(engine, "skill-C", trust_score=90.0)

        history_file = tmp_metrics / "consequence-history.jsonl"
        lines = read_jsonl(history_file)
        perf_entries = [
            l for l in lines
            if l.get("record_type") == "performance"
            and l.get("agent_or_skill") == "skill-C"
        ]
        assert len(perf_entries) == 10, (
            f"Expected 10 performance entries for skill-C, got {len(perf_entries)}"
        )


# ---------------------------------------------------------------------------
# Test 4 — error pattern detection returns a warning after 3 identical errors
# ---------------------------------------------------------------------------


class TestErrorPatternDetection:
    """Write 3 identical errors; check_learning_triggers must surface warn trigger."""

    def _write_errors(
        self, correlations_path: Path, error_type: str, service: str, count: int
    ) -> None:
        correlations_path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(count):
            entry = {
                "error_type": error_type,
                "service": service,
                "message": f"Test {error_type} error in {service}",
                "category": "test_failure",
                "skill_name": "test-skill",
                "timestamp": _now_iso(),
            }
            with open(correlations_path, "a") as fh:
                fh.write(json.dumps(entry) + "\n")

    def test_three_same_errors_produce_warn_trigger(self, tmp_metrics: Path) -> None:
        correlations_path = tmp_metrics / "error-skill-correlations.jsonl"
        self._write_errors(correlations_path, "TEST_FAILURE", "my-service", count=3)

        pipeline = _make_pipeline(tmp_metrics)
        # Override the correlations path to point to our pre-written file
        pipeline._correlations_path = str(correlations_path)

        triggers = pipeline.check_learning_triggers()

        error_triggers = [t for t in triggers if t.trigger_type == "error_pattern"]
        assert len(error_triggers) >= 1, (
            f"Expected at least 1 error_pattern trigger after 3 identical errors; "
            f"got {len(error_triggers)}. All triggers: {triggers}"
        )

    def test_trigger_contains_service_and_count(self, tmp_metrics: Path) -> None:
        correlations_path = tmp_metrics / "error-skill-correlations.jsonl"
        self._write_errors(correlations_path, "BUILD_ERROR", "api-service", count=4)

        pipeline = _make_pipeline(tmp_metrics)
        pipeline._correlations_path = str(correlations_path)

        triggers = pipeline.check_learning_triggers()
        error_triggers = [t for t in triggers if t.trigger_type == "error_pattern"]
        assert error_triggers, "Must have at least one error_pattern trigger"

        t = error_triggers[0]
        assert t.severity == "warn", f"Expected severity='warn', got {t.severity!r}"
        assert "api-service" in t.target or "api-service" in t.message, (
            f"Trigger must reference 'api-service'; message={t.message!r}"
        )
        assert t.detail.get("count", 0) >= 3, (
            f"Trigger count must be >= 3; got {t.detail.get('count')}"
        )

    def test_two_errors_do_not_produce_trigger(self, tmp_metrics: Path) -> None:
        """Only 2 errors — below threshold — must NOT trigger."""
        correlations_path = tmp_metrics / "error-skill-correlations.jsonl"
        self._write_errors(correlations_path, "LINT_ERROR", "svc-x", count=2)

        pipeline = _make_pipeline(tmp_metrics)
        pipeline._correlations_path = str(correlations_path)

        triggers = pipeline.check_learning_triggers()
        error_triggers = [t for t in triggers if t.trigger_type == "error_pattern"]
        lint_triggers = [
            t for t in error_triggers
            if "svc-x" in t.target or "svc-x" in t.message
        ]
        assert len(lint_triggers) == 0, (
            f"2 errors must NOT trigger a warning; got {lint_triggers}"
        )


# ---------------------------------------------------------------------------
# Test 5 — full pipeline integration with realistic completion data
# ---------------------------------------------------------------------------


class TestFullPipelineIntegration:
    """Simulate realistic completions through the full feedback chain."""

    def _make_completion_data(self, score: int, description: str) -> dict:
        output = (
            f"TRUST_REPORT: SCORE={score} STATUS=MEDIUM EVIDENCE=3 UNCERTAINTIES=1\n"
            "---\n"
            f"Score: {score}/100\n\n"
            "EVIDENCE PROVIDED:\n"
            "  [check] go build ./... exits 0\n"
            "  [check] go test ./... — 10 passed, 0 failed\n"
            "  [warn] integration test not run\n\n"
            "WHAT I'M CONFIDENT ABOUT:\n"
            "  - Implementation complete\n\n"
            "WHAT I'M UNSURE ABOUT:\n"
            "  - Edge cases under load\n\n"
            "WHAT THE HUMAN SHOULD VERIFY:\n"
            "  - Run full integration test suite\n"
        )
        return {
            "tool_call_id": "toolu_test123",
            "tool_name": "Agent",
            "tool_input": {
                "description": description,
                "prompt": f"Implement: {description}",
            },
            "tool_response": {"result": output},
        }

    def test_low_score_completion_produces_cost_event(
        self, tmp_metrics: Path
    ) -> None:
        data = self._make_completion_data(score=45, description="implement-auth-module")
        output = data["tool_response"]["result"]

        skill_name = extract_skill_name(data)
        tokens = estimate_tokens(output)
        append_cost_event(str(tmp_metrics), skill_name, tokens, model="sonnet")

        cost_file = tmp_metrics / "cost-events.jsonl"
        assert cost_file.exists(), "cost-events.jsonl must exist"
        entry = read_first_jsonl(cost_file)
        assert entry["estimated_cost_usd"] > 0
        assert entry["tokens_estimated"] == tokens

    def test_low_score_feeds_warn_consequence(self, tmp_metrics: Path) -> None:
        data = self._make_completion_data(score=45, description="implement-auth-module")
        output = data["tool_response"]["result"]

        skill_name = extract_skill_name(data)
        trust_score = extract_trust_score(output)
        tokens = estimate_tokens(output)
        success = detect_success(output, data)

        assert trust_score == 45, f"extract_trust_score must return 45, got {trust_score}"

        pipeline = _make_pipeline(tmp_metrics)
        action = pipeline.record_agent_completion(
            task_id="toolu_test123",
            success=success,
            trust_score=trust_score,
            skill_name=skill_name,
            tokens_used=tokens,
        )
        assert action.consequence == Consequence.WARN, (
            f"Score 45 on first run must yield WARN, got {action.consequence}"
        )

    def test_low_score_archived_in_skill_archive(self, tmp_metrics: Path) -> None:
        data = self._make_completion_data(score=45, description="implement-auth-module")
        output = data["tool_response"]["result"]
        skill_name = extract_skill_name(data)
        trust_score = extract_trust_score(output)
        tokens = estimate_tokens(output)
        success = detect_success(output, data)

        pipeline = _make_pipeline(tmp_metrics)
        pipeline.record_agent_completion(
            task_id="toolu_test123",
            success=success,
            trust_score=trust_score,
            skill_name=skill_name,
            tokens_used=tokens,
        )

        archive_file = tmp_metrics / "skill-archive.jsonl"
        assert archive_file.exists(), "skill-archive.jsonl must be written"
        lines = read_jsonl(archive_file)
        assert len(lines) >= 1
        assert lines[0]["trust_score"] == trust_score

    def test_high_score_completion_feeds_maintain_then_promote(
        self, tmp_metrics: Path
    ) -> None:
        """Score=90 five times through pipeline → final consequence is PROMOTE."""
        data = self._make_completion_data(score=90, description="review-code-quality")
        output = data["tool_response"]["result"]

        skill_name = extract_skill_name(data)
        trust_score = extract_trust_score(output)
        tokens = estimate_tokens(output)
        success = detect_success(output, data)

        assert trust_score == 90, f"extract_trust_score must return 90, got {trust_score}"

        pipeline = _make_pipeline(tmp_metrics)
        actions = []
        for i in range(5):
            action = pipeline.record_agent_completion(
                task_id=f"toolu_high_{i}",
                success=success,
                trust_score=trust_score,
                skill_name=skill_name,
                tokens_used=tokens,
            )
            actions.append(action)

        last = actions[-1]
        assert last.consequence == Consequence.PROMOTE, (
            f"5 consecutive trust_score=90 completions must yield PROMOTE, "
            f"got {last.consequence}"
        )

    def test_high_score_promote_leaves_five_archive_entries(
        self, tmp_metrics: Path
    ) -> None:
        data = self._make_completion_data(score=90, description="review-code-quality")
        output = data["tool_response"]["result"]
        skill_name = extract_skill_name(data)
        trust_score = extract_trust_score(output)
        tokens = estimate_tokens(output)
        success = detect_success(output, data)

        pipeline = _make_pipeline(tmp_metrics)
        for i in range(5):
            pipeline.record_agent_completion(
                task_id=f"toolu_high_{i}",
                success=success,
                trust_score=trust_score,
                skill_name=skill_name,
                tokens_used=tokens,
            )

        archive_file = tmp_metrics / "skill-archive.jsonl"
        lines = read_jsonl(archive_file)
        skill_entries = [e for e in lines if e.get("skill_name") == skill_name]
        assert len(skill_entries) == 5, (
            f"Expected 5 archive entries after 5 completions, got {len(skill_entries)}"
        )

    def test_full_chain_cost_event_and_consequence_both_written(
        self, tmp_metrics: Path
    ) -> None:
        """Both cost-events.jsonl AND consequence-history.jsonl must be written."""
        data = self._make_completion_data(score=45, description="debug-payment-flow")
        output = data["tool_response"]["result"]

        skill_name = extract_skill_name(data)
        trust_score = extract_trust_score(output)
        tokens = estimate_tokens(output)
        success = detect_success(output, data)
        model = "sonnet"

        pipeline = _make_pipeline(tmp_metrics)
        pipeline.record_agent_completion(
            task_id="toolu_full_chain",
            success=success,
            trust_score=trust_score,
            skill_name=skill_name,
            tokens_used=tokens,
        )
        append_cost_event(str(tmp_metrics), skill_name, tokens, model=model)

        cost_file = tmp_metrics / "cost-events.jsonl"
        history_file = tmp_metrics / "consequence-history.jsonl"
        archive_file = tmp_metrics / "skill-archive.jsonl"

        assert cost_file.exists(), "cost-events.jsonl must be written"
        assert history_file.exists(), "consequence-history.jsonl must be written"
        assert archive_file.exists(), "skill-archive.jsonl must be written"

        cost_entry = read_first_jsonl(cost_file)
        assert cost_entry["estimated_cost_usd"] > 0

        history_lines = read_jsonl(history_file)
        perf_entries = [l for l in history_lines if l.get("record_type") == "performance"]
        assert len(perf_entries) >= 1

        archive_lines = read_jsonl(archive_file)
        assert len(archive_lines) >= 1
        assert archive_lines[0]["skill_name"] == skill_name
