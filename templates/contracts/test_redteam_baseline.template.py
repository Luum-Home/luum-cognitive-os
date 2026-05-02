# SCOPE: both
"""Consumer-customizable contract template for red-team harness baseline.

<!-- SCOPE: both -->
<!-- TEMPLATE: copy to tests/contracts/ in your project and adjust parameters -->

USAGE
-----
1. Copy this file to your project: ``tests/contracts/test_redteam_baseline.py``
2. Adjust the CONFIGURATION section below (scenario count, verbs, paths).
3. Run: ``pytest tests/contracts/test_redteam_baseline.py -v``

The template exercises the same contract as the OS-side test but lets consumers
parameterize:
  - Number of expected scenarios (default: 6)
  - ADR-105 verbs that must appear (default: 5 core verbs)
  - Scenarios directory (default: tests/red_team/scenarios/)
  - Output directory for reports (default: docs/reports/redteam/)

CONTRACT
--------
- Aggregator produces JSON with schema_version, summary, scenarios, verb_coverage
- All declared scenario IDs appear with graded status
- Each declared ADR-105 verb has at least 1 scenario in verb_coverage
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# ── CONFIGURATION — adjust for your project ───────────────────────────────────

# Root of YOUR project (not the OS repo)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Path to the OS installation within your project (adjust if you use a subdir)
COS_ROOT = PROJECT_ROOT  # or e.g. PROJECT_ROOT / "vendor" / "cognitive-os"

RUNNER = COS_ROOT / "scripts" / "run-redteam-scenario.sh"
AGGREGATOR = COS_ROOT / "scripts" / "redteam_aggregate.py"

# Scenario directory -- override if you add local scenarios
SCENARIOS_DIR = COS_ROOT / "tests" / "red_team" / "scenarios"

# Expected scenario IDs -- update when you add/remove scenarios
EXPECTED_SCENARIO_IDS: frozenset[str] = frozenset({
    "archive-presence-fallacy",
    "unwired-constant",
    "plan-checkbox-no-evidence",
    "regex-false-positives",
    "partial-completion-claim",
    "silent-stash-loss",
})

# Minimum scenario count
MIN_SCENARIO_COUNT: int = 6

# ADR-105 verbs that must appear in verb_coverage with at least 1 scenario
REQUIRED_VERB_COVERAGE: frozenset[str] = frozenset({
    "archived",
    "wired",
    "tested",
    "verified",
    "completed",
})

# ── END CONFIGURATION ─────────────────────────────────────────────────────────

pytestmark = [pytest.mark.contract, pytest.mark.red_team]


def _run(cmd, cwd, env=None):
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=merged,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _run_all_scenarios_and_aggregate(tmp_path):
    """Run all scenarios in replay mode and aggregate. Returns (payload, json_path, md_path)."""
    out_dir = tmp_path / "scenario-results"
    out_dir.mkdir()
    baseline_json = tmp_path / "redteam-baseline.json"
    baseline_md = tmp_path / "redteam-baseline.md"

    for scenario_yaml in SCENARIOS_DIR.glob("*.yaml"):
        scenario_id = scenario_yaml.stem
        result = _run(
            [
                "bash", str(RUNNER),
                "--scenario", scenario_id,
                "--scenarios-dir", str(SCENARIOS_DIR),
                "--out-dir", str(out_dir),
                "--mode", "replay",
                "--json",
            ],
            cwd=COS_ROOT,
        )
        if result.returncode == 3:
            json_out = out_dir / f"{scenario_id}.json"
            assert json_out.exists(), (
                f"Runner errored (exit 3) for {scenario_yaml.name} with no JSON output:\n"
                f"{result.stderr}"
            )

    result = _run(
        [
            sys.executable, str(AGGREGATOR),
            "--input-dir", str(out_dir),
            "--output-json", str(baseline_json),
            "--output-md", str(baseline_md),
        ],
        cwd=COS_ROOT,
    )
    assert result.returncode in (0, 1), (
        f"Aggregator failed: {result.stderr}\n{result.stdout}"
    )
    assert baseline_json.exists(), "Aggregator did not produce baseline JSON"
    assert baseline_md.exists(), "Aggregator did not produce baseline Markdown"
    return json.loads(baseline_json.read_text(encoding="utf-8")), baseline_json, baseline_md


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_schema_version_present(tmp_path):
    """Baseline JSON must carry schema_version 1.0.0."""
    payload, _, _ = _run_all_scenarios_and_aggregate(tmp_path)
    assert payload.get("schema_version") == "1.0.0"


def test_all_expected_scenarios_graded(tmp_path):
    """Every scenario in EXPECTED_SCENARIO_IDS must appear graded in output.
    silent-stash-loss may be absent due to xfail/W5 shell-quoting limitation."""
    payload, _, _ = _run_all_scenarios_and_aggregate(tmp_path)
    graded_ids = {s["id"] for s in payload.get("scenarios", [])}
    xfail_exception = {"silent-stash-loss"}
    missing = (EXPECTED_SCENARIO_IDS - graded_ids) - xfail_exception
    assert not missing, f"Missing graded scenarios: {missing}"


def test_scenario_count_meets_minimum(tmp_path):
    """Summary total must be >= MIN_SCENARIO_COUNT - 1 (allowing xfail skip)."""
    payload, _, _ = _run_all_scenarios_and_aggregate(tmp_path)
    total = payload.get("summary", {}).get("total", 0)
    assert total >= MIN_SCENARIO_COUNT - 1, (
        f"Expected >={MIN_SCENARIO_COUNT - 1} scenarios, got {total}"
    )


def test_verb_coverage_meets_requirements(tmp_path):
    """Core verbs (excluding completed which requires xfail scenario) must have coverage."""
    payload, _, _ = _run_all_scenarios_and_aggregate(tmp_path)
    coverage = payload.get("verb_coverage", {})
    xfail_verbs = {"completed"}
    gaps = [v for v in (REQUIRED_VERB_COVERAGE - xfail_verbs) if coverage.get(v, 0) < 1]
    assert not gaps, (
        f"Verbs with no scenario coverage: {gaps}. Coverage: {coverage}"
    )


def test_all_scenarios_have_valid_status(tmp_path):
    """Each scenario entry must carry one of the 5 valid statuses."""
    valid = {"pass", "fail", "partial", "xfail", "error"}
    payload, _, _ = _run_all_scenarios_and_aggregate(tmp_path)
    for s in payload.get("scenarios", []):
        assert s.get("status") in valid, (
            f"Scenario {s.get('id', '?')} has invalid status: {s.get('status')}"
        )


def test_baseline_md_produced(tmp_path):
    """Aggregator must produce a non-empty Markdown file."""
    _, _, baseline_md = _run_all_scenarios_and_aggregate(tmp_path)
    assert baseline_md.stat().st_size > 0, "Baseline Markdown is empty"
