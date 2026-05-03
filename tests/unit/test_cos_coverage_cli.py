"""Tests for scripts/cos_coverage.py — ACC CLI.

Covers:
  - JSON output schema
  - empty-history fallback (no coverage-history.jsonl)
  - trend calculation when history exists
  - --brief output format
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "cos_coverage.py"


def run_coverage(project_dir: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project-dir", str(project_dir), *args],
        capture_output=True,
        text=True,
    )


def make_audit_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def make_claim_proof_md(path: Path, mapped: int, weak: int, unmapped: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        textwrap.dedent(f"""
        # Claim-to-Proof Audit — Latest

        ## Summary

        - mapped: {mapped}
        - weak-proof: {weak}
        - unmapped: {unmapped}
        """)
    )


def audit_record(component: str, classification: str) -> dict:
    return {
        "source": "aspirational-audit",
        "event_type": "component.classified",
        "schema_version": "1.0",
        "timestamp": "2026-05-02T12:00:00+00:00",
        "payload": {
            "component": component,
            "classification": classification,
            "signals": {},
            "reason": "test",
        },
    }


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def fake_project(tmp_path: Path) -> Path:
    """Minimal fake project with aspirational-audit.jsonl and claim-proof md."""
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)

    records = [
        audit_record("scripts/real_script.py", "REAL"),
        audit_record("scripts/real_script2.py", "REAL"),
        audit_record("hooks/dormant_hook.sh", "DORMANT"),
        audit_record("scripts/aspirational.py", "ASPIRATIONAL"),
    ]
    make_audit_jsonl(metrics / "aspirational-audit.jsonl", records)
    make_claim_proof_md(
        tmp_path / "docs" / "reports" / "claim-proof-latest.md",
        mapped=10, weak=2, unmapped=1,
    )
    return tmp_path


# ── JSON output schema ─────────────────────────────────────────────────────────

class TestJsonOutput:
    def test_json_flag_produces_valid_json(self, fake_project: Path) -> None:
        result = run_coverage(fake_project, "--json")
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_json_schema_required_keys(self, fake_project: Path) -> None:
        result = run_coverage(fake_project, "--json")
        data = json.loads(result.stdout)
        for key in ("coverage_pct", "real", "dormant", "aspirational",
                    "mapped", "weak_proof", "unmapped", "trend", "generated_at"):
            assert key in data, f"Missing key: {key}"

    def test_json_coverage_pct_type(self, fake_project: Path) -> None:
        result = run_coverage(fake_project, "--json")
        data = json.loads(result.stdout)
        assert isinstance(data["coverage_pct"], (int, float))

    def test_json_real_dormant_aspirational_counts(self, fake_project: Path) -> None:
        result = run_coverage(fake_project, "--json")
        data = json.loads(result.stdout)
        assert data["real"] == 2
        assert data["dormant"] == 1
        assert data["aspirational"] == 1

    def test_json_coverage_pct_calculation(self, fake_project: Path) -> None:
        # REAL=2, DORMANT=1, ASPIRATIONAL=1 -> 2/4 = 50.0%
        result = run_coverage(fake_project, "--json")
        data = json.loads(result.stdout)
        assert data["coverage_pct"] == 50.0

    def test_json_claim_proof_keys(self, fake_project: Path) -> None:
        result = run_coverage(fake_project, "--json")
        data = json.loads(result.stdout)
        assert data["mapped"] == 10
        assert data["weak_proof"] == 2
        assert data["unmapped"] == 1

    def test_json_no_internal_cache_key(self, fake_project: Path) -> None:
        result = run_coverage(fake_project, "--json")
        data = json.loads(result.stdout)
        assert "_cached_at" not in data

    def test_json_trend_is_dict(self, fake_project: Path) -> None:
        result = run_coverage(fake_project, "--json")
        data = json.loads(result.stdout)
        assert isinstance(data["trend"], dict)

    def test_json_tiers_is_dict(self, fake_project: Path) -> None:
        result = run_coverage(fake_project, "--json")
        data = json.loads(result.stdout)
        assert isinstance(data.get("tiers", {}), dict)


# ── Empty history fallback ─────────────────────────────────────────────────────

class TestEmptyHistoryFallback:
    def test_no_history_file_exits_ok(self, fake_project: Path) -> None:
        history = fake_project / ".cognitive-os" / "metrics" / "coverage-history.jsonl"
        assert not history.exists()
        result = run_coverage(fake_project, "--json")
        assert result.returncode == 0

    def test_no_history_trend_is_empty(self, fake_project: Path) -> None:
        result = run_coverage(fake_project, "--json")
        data = json.loads(result.stdout)
        assert data["trend"] == {}

    def test_no_audit_file_exits_ok(self, tmp_path: Path) -> None:
        # No aspirational-audit.jsonl at all
        make_claim_proof_md(
            tmp_path / "docs" / "reports" / "claim-proof-latest.md",
            mapped=0, weak=0, unmapped=0,
        )
        result = run_coverage(tmp_path, "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["coverage_pct"] == 0.0
        assert data["real"] == 0
        assert data["dormant"] == 0

    def test_no_claim_proof_exits_ok(self, tmp_path: Path) -> None:
        # Only audit file, no claim-proof md
        metrics = tmp_path / ".cognitive-os" / "metrics"
        metrics.mkdir(parents=True, exist_ok=True)
        make_audit_jsonl(
            metrics / "aspirational-audit.jsonl",
            [audit_record("scripts/foo.py", "REAL")],
        )
        result = run_coverage(tmp_path, "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["mapped"] == 0
        assert data["unmapped"] == 0

    def test_empty_project_dir_all_zeros(self, tmp_path: Path) -> None:
        result = run_coverage(tmp_path, "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["coverage_pct"] == 0.0


# ── Trend calculation ──────────────────────────────────────────────────────────

class TestTrendCalculation:
    def _write_history(self, project_dir: Path, snapshots: list[dict]) -> None:
        history = project_dir / ".cognitive-os" / "metrics" / "coverage-history.jsonl"
        history.parent.mkdir(parents=True, exist_ok=True)
        # Use different dates so they're all written
        with history.open("w") as fh:
            for i, snap in enumerate(snapshots):
                entry = {
                    "timestamp": f"2026-04-{20+i:02d}T12:00:00Z",
                    "source": "cos-coverage",
                    "event_type": "acc_snapshot",
                    "payload": snap,
                }
                fh.write(json.dumps(entry) + "\n")

    def test_trend_up_when_coverage_increased(self, fake_project: Path) -> None:
        # Fake history with lower coverage_pct
        self._write_history(fake_project, [
            {"coverage_pct": 30.0, "real": 1, "dormant": 2, "aspirational": 1},
        ])
        result = run_coverage(fake_project, "--json", "--refresh")
        data = json.loads(result.stdout)
        # Current coverage_pct=50.0 > 30.0 -> up
        assert data["trend"].get("coverage_pct") == "up"

    def test_trend_down_when_coverage_decreased(self, fake_project: Path) -> None:
        self._write_history(fake_project, [
            {"coverage_pct": 80.0, "real": 10, "dormant": 1, "aspirational": 1},
        ])
        result = run_coverage(fake_project, "--json", "--refresh")
        data = json.loads(result.stdout)
        # Current coverage_pct=50.0 < 80.0 -> down
        assert data["trend"].get("coverage_pct") == "down"

    def test_trend_flat_when_unchanged(self, fake_project: Path) -> None:
        self._write_history(fake_project, [
            {"coverage_pct": 50.0, "real": 2, "dormant": 1, "aspirational": 1},
        ])
        result = run_coverage(fake_project, "--json", "--refresh")
        data = json.loads(result.stdout)
        assert data["trend"].get("coverage_pct") == "flat"

    def test_trend_uses_last_snapshot_not_first(self, fake_project: Path) -> None:
        # Write two snapshots: first says 90% (old), second says 40% (more recent)
        self._write_history(fake_project, [
            {"coverage_pct": 90.0, "real": 9, "dormant": 1, "aspirational": 0},
            {"coverage_pct": 40.0, "real": 4, "dormant": 5, "aspirational": 1},
        ])
        result = run_coverage(fake_project, "--json", "--refresh")
        data = json.loads(result.stdout)
        # Current 50.0 vs last 40.0 -> up
        assert data["trend"].get("coverage_pct") == "up"

    def test_trend_real_up_when_real_count_grew(self, fake_project: Path) -> None:
        self._write_history(fake_project, [
            {"coverage_pct": 50.0, "real": 1, "dormant": 1, "aspirational": 1},
        ])
        result = run_coverage(fake_project, "--json", "--refresh")
        data = json.loads(result.stdout)
        # real=2 now > 1 before
        assert data["trend"].get("real") == "up"

    def test_trend_dormant_up_when_dormant_grew(self, fake_project: Path) -> None:
        self._write_history(fake_project, [
            {"coverage_pct": 50.0, "real": 2, "dormant": 0, "aspirational": 1},
        ])
        result = run_coverage(fake_project, "--json", "--refresh")
        data = json.loads(result.stdout)
        # dormant=1 now > 0 before
        assert data["trend"].get("dormant") == "up"

    def test_accepts_legacy_coverage_measurement_events(self, fake_project: Path) -> None:
        """History from pre-existing pre-commit-gate format should also influence trend."""
        history = fake_project / ".cognitive-os" / "metrics" / "coverage-history.jsonl"
        history.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": "2026-04-15T12:00:00Z",
            "source": "pre-commit-gate",
            "event_type": "coverage_measurement",
            "payload": {"coverage_pct": 25, "commit_sha": "abc", "threshold": 80},
        }
        history.write_text(json.dumps(entry) + "\n")
        result = run_coverage(fake_project, "--json", "--refresh")
        data = json.loads(result.stdout)
        # coverage_pct=50.0 > 25 -> up
        assert data["trend"].get("coverage_pct") == "up"


# ── --brief output format ──────────────────────────────────────────────────────

class TestBriefFormat:
    def test_brief_output_is_single_line(self, fake_project: Path) -> None:
        result = run_coverage(fake_project, "--brief")
        assert result.returncode == 0
        lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
        assert len(lines) == 1

    def test_brief_contains_acc_prefix(self, fake_project: Path) -> None:
        result = run_coverage(fake_project, "--brief")
        assert "ACC:" in result.stdout

    def test_brief_contains_real_count(self, fake_project: Path) -> None:
        result = run_coverage(fake_project, "--brief")
        assert "REAL:" in result.stdout

    def test_brief_contains_dormant_count(self, fake_project: Path) -> None:
        result = run_coverage(fake_project, "--brief")
        assert "DORM:" in result.stdout

    def test_brief_contains_percentage(self, fake_project: Path) -> None:
        result = run_coverage(fake_project, "--brief")
        assert "%" in result.stdout

    def test_brief_values_match_json(self, fake_project: Path) -> None:
        brief = run_coverage(fake_project, "--brief", "--refresh")
        js = run_coverage(fake_project, "--json")
        data = json.loads(js.stdout)
        pct = str(data["coverage_pct"])
        real = str(data["real"])
        assert pct in brief.stdout
        assert real in brief.stdout

    def test_brief_with_no_data_shows_zero(self, tmp_path: Path) -> None:
        result = run_coverage(tmp_path, "--brief")
        assert result.returncode == 0
        assert "ACC:" in result.stdout

    def test_brief_with_trend_shows_arrow(self, fake_project: Path) -> None:
        history = fake_project / ".cognitive-os" / "metrics" / "coverage-history.jsonl"
        history.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": "2026-04-20T12:00:00Z",
            "source": "cos-coverage",
            "event_type": "acc_snapshot",
            "payload": {"coverage_pct": 10.0, "real": 1, "dormant": 8, "aspirational": 1},
        }
        history.write_text(json.dumps(entry) + "\n")
        result = run_coverage(fake_project, "--brief", "--refresh")
        # 50.0% > 10.0% -> should show ↑
        assert "↑" in result.stdout


# ── Cache behavior ─────────────────────────────────────────────────────────────

class TestCache:
    def test_cache_written_after_first_run(self, fake_project: Path) -> None:
        run_coverage(fake_project, "--refresh")
        cache = fake_project / ".cognitive-os" / "runtime" / "coverage-snapshot.json"
        assert cache.exists()

    def test_cache_contains_cached_at(self, fake_project: Path) -> None:
        run_coverage(fake_project, "--refresh")
        cache = fake_project / ".cognitive-os" / "runtime" / "coverage-snapshot.json"
        data = json.loads(cache.read_text())
        assert "_cached_at" in data
        assert isinstance(data["_cached_at"], (int, float))

    def test_refresh_flag_updates_cache(self, fake_project: Path) -> None:
        run_coverage(fake_project)
        cache = fake_project / ".cognitive-os" / "runtime" / "coverage-snapshot.json"
        first_ts = json.loads(cache.read_text())["_cached_at"]
        # Small sleep to ensure timestamp differs
        time.sleep(0.05)
        run_coverage(fake_project, "--refresh")
        second_ts = json.loads(cache.read_text())["_cached_at"]
        assert second_ts >= first_ts
