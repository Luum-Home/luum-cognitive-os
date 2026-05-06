"""Contract tests for lib.validator_soak_evaluator.evaluate_validator_soak.

Covers:
  - Low FP rate + sufficient entries  → proposal artifact created
  - High FP rate                      → no proposal
  - Empty JSONL                       → no proposal
  - JSONL file missing                → no proposal
  - Insufficient entries              → no proposal
  - Idempotency (second call same day → does not overwrite)
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.validator_soak_evaluator import evaluate_validator_soak


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts(days_ago: int = 0) -> str:
    """ISO-8601 timestamp N days before now."""
    dt = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat()


def _make_metrics_file(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")


def _warn_entry(slug: str, outcome: str = "", days_ago: int = 1) -> dict:
    return {"timestamp": _ts(days_ago), "level": "warn", "skill_slug": slug, "outcome": outcome}


def _pass_entry(slug: str, days_ago: int = 0) -> dict:
    return {"timestamp": _ts(days_ago), "level": "pass", "skill_slug": slug}


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestLowFpRateEmitsProposal:
    def test_proposal_file_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            metrics_path = tmp_path / "metrics" / "skill-md-routing-validator.jsonl"

            # 35 entries: 5 warns without accepted_unchanged → 0 FPs
            entries = [_warn_entry(f"skill-{i}") for i in range(5)]
            entries += [_pass_entry(f"other-{i}") for i in range(30)]
            _make_metrics_file(metrics_path, entries)

            report = evaluate_validator_soak(
                metrics_path=metrics_path,
                soak_days=30,
                fp_threshold=0.05,
                min_entries=30,
                project_root=tmp_path,
            )

            assert report.proposal_emitted is True
            assert report.proposal_path is not None
            assert Path(report.proposal_path).exists()

    def test_proposal_contains_soak_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            metrics_path = tmp_path / "metrics" / "skill-md-routing-validator.jsonl"

            entries = [_warn_entry(f"skill-{i}") for i in range(5)]
            entries += [_pass_entry(f"other-{i}") for i in range(30)]
            _make_metrics_file(metrics_path, entries)

            report = evaluate_validator_soak(
                metrics_path=metrics_path,
                project_root=tmp_path,
                min_entries=30,
            )

            if report.proposal_path:
                content = Path(report.proposal_path).read_text()
                assert "Soak Data Summary" in content
                assert "False-positive rate" in content
                assert "Rollback Path" in content

    def test_fp_rate_below_threshold_triggers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            metrics_path = tmp_path / "metrics" / "skill-md-routing-validator.jsonl"

            # 31 warn entries, 1 FP (accepted_unchanged) → fp_rate = 1/31 ≈ 3.2% < 5%
            entries = [_warn_entry("fp-skill", outcome="accepted_unchanged")]
            entries += [_warn_entry(f"skill-{i}") for i in range(30)]
            entries += [_pass_entry(f"other-{i}") for i in range(5)]
            _make_metrics_file(metrics_path, entries)

            report = evaluate_validator_soak(
                metrics_path=metrics_path,
                project_root=tmp_path,
                min_entries=30,
            )

            assert report.proposal_emitted is True
            assert report.fp_rate < 0.05


class TestHighFpRateNoProposal:
    def test_high_fp_rate_skips_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            metrics_path = tmp_path / "metrics" / "skill-md-routing-validator.jsonl"

            # 30 warn entries, 10 FPs → fp_rate = 10/30 ≈ 33% >> 5%
            entries = [_warn_entry(f"fp-skill-{i}", outcome="accepted_unchanged") for i in range(10)]
            entries += [_warn_entry(f"ok-skill-{i}") for i in range(20)]
            entries += [_pass_entry(f"other-{i}") for i in range(5)]
            _make_metrics_file(metrics_path, entries)

            report = evaluate_validator_soak(
                metrics_path=metrics_path,
                project_root=tmp_path,
                min_entries=30,
            )

            assert report.proposal_emitted is False
            assert report.skip_reason is not None
            assert "fp_rate_too_high" in (report.skip_reason or "")

    def test_no_proposal_path_returned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            metrics_path = tmp_path / "metrics" / "skill-md-routing-validator.jsonl"

            entries = [_warn_entry(f"fp-{i}", outcome="accepted_unchanged") for i in range(30)]
            entries += [_pass_entry(f"p-{i}") for i in range(5)]
            _make_metrics_file(metrics_path, entries)

            report = evaluate_validator_soak(
                metrics_path=metrics_path,
                project_root=tmp_path,
                min_entries=30,
            )

            assert report.proposal_path is None


class TestEmptyOrMissingJsonl:
    def test_empty_jsonl_no_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            metrics_path = tmp_path / "metrics" / "skill-md-routing-validator.jsonl"
            _make_metrics_file(metrics_path, [])

            report = evaluate_validator_soak(
                metrics_path=metrics_path,
                project_root=tmp_path,
                min_entries=30,
            )

            assert report.proposal_emitted is False
            assert report.total_entries == 0

    def test_missing_metrics_file_no_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            nonexistent = tmp_path / "metrics" / "does-not-exist.jsonl"

            report = evaluate_validator_soak(
                metrics_path=nonexistent,
                project_root=tmp_path,
            )

            assert report.proposal_emitted is False
            assert "metrics_file_not_found" in (report.skip_reason or "")

    def test_insufficient_entries_no_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            metrics_path = tmp_path / "metrics" / "skill-md-routing-validator.jsonl"

            # Only 5 entries — below min_entries=30
            entries = [_warn_entry(f"skill-{i}") for i in range(5)]
            _make_metrics_file(metrics_path, entries)

            report = evaluate_validator_soak(
                metrics_path=metrics_path,
                project_root=tmp_path,
                min_entries=30,
            )

            assert report.proposal_emitted is False
            assert "insufficient_entries" in (report.skip_reason or "")


class TestIdempotency:
    def test_second_call_same_day_does_not_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            metrics_path = tmp_path / "metrics" / "skill-md-routing-validator.jsonl"

            entries = [_warn_entry(f"skill-{i}") for i in range(5)]
            entries += [_pass_entry(f"other-{i}") for i in range(30)]
            _make_metrics_file(metrics_path, entries)

            # First call — creates proposal
            report1 = evaluate_validator_soak(
                metrics_path=metrics_path,
                project_root=tmp_path,
                min_entries=30,
            )
            assert report1.proposal_emitted is True
            proposal_path = Path(report1.proposal_path)
            mtime1 = proposal_path.stat().st_mtime

            # Second call — should NOT overwrite (idempotent)
            report2 = evaluate_validator_soak(
                metrics_path=metrics_path,
                project_root=tmp_path,
                min_entries=30,
            )
            assert report2.proposal_emitted is True
            mtime2 = Path(report2.proposal_path).stat().st_mtime
            assert mtime1 == mtime2, "Proposal file was overwritten on second call"


class TestEvalLogWritten:
    def test_eval_log_appended(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            metrics_path = tmp_path / "metrics" / "skill-md-routing-validator.jsonl"
            _make_metrics_file(metrics_path, [])

            evaluate_validator_soak(metrics_path=metrics_path, project_root=tmp_path)

            eval_log = tmp_path / ".cognitive-os" / "metrics" / "validator-promotion-evaluations.jsonl"
            assert eval_log.exists()
            lines = [l for l in eval_log.read_text().splitlines() if l.strip()]
            assert len(lines) >= 1
            entry = json.loads(lines[0])
            assert "evaluated_at" in entry
            assert "proposal_emitted" in entry
