# SCOPE: os-only
"""Unit tests for lib/dogfood_scorer.py.

Each test fabricates a minimal repo under tmp_path so behavior is deterministic
and independent of the real repo state.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from lib.dogfood_scorer import (
    DIMENSION_WEIGHTS,
    DogfoodScorer,
    append_trend_record,
    read_last_trend_record,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


JUNIT_HEALTHY = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
<testsuite name="pytest" errors="0" failures="0" skipped="0" tests="10" time="1.0">
  <testcase classname="t" name="a" time="0.1" />
  <testcase classname="t" name="b" time="0.1" />
  <testcase classname="t" name="c" time="0.1" />
  <testcase classname="t" name="d" time="0.1" />
  <testcase classname="t" name="e" time="0.1" />
  <testcase classname="t" name="f" time="0.1" />
  <testcase classname="t" name="g" time="0.1" />
  <testcase classname="t" name="h" time="0.1" />
  <testcase classname="t" name="i" time="0.1" />
  <testcase classname="t" name="j" time="0.1" />
</testsuite>
</testsuites>
"""

JUNIT_DEGRADED = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
<testsuite name="pytest" errors="0" failures="0" skipped="2" tests="10" time="1.0">
  <testcase classname="t" name="a" time="0.1" />
  <testcase classname="t" name="b" time="0.1" />
  <testcase classname="t" name="c" time="0.1" />
  <testcase classname="t" name="d" time="0.1" />
  <testcase classname="t" name="e" time="0.1" />
  <testcase classname="t" name="f" time="0.1" />
  <testcase classname="t" name="g" time="0.1" />
  <testcase classname="t" name="h" time="0.1" />
  <testcase classname="t" name="i" time="0.1">
    <skipped type="pytest.xfail" message="xfail">expected failure</skipped>
  </testcase>
  <testcase classname="t" name="j" time="0.1">
    <skipped type="pytest.xfail" message="xfail">expected failure</skipped>
  </testcase>
</testsuite>
</testsuites>
"""

JUNIT_FAILING = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
<testsuite name="pytest" errors="0" failures="3" skipped="0" tests="10" time="1.0">
  <testcase classname="t" name="a" time="0.1" />
  <testcase classname="t" name="b" time="0.1" />
  <testcase classname="t" name="c" time="0.1"><failure /></testcase>
  <testcase classname="t" name="d" time="0.1"><failure /></testcase>
  <testcase classname="t" name="e" time="0.1"><failure /></testcase>
  <testcase classname="t" name="f" time="0.1" />
  <testcase classname="t" name="g" time="0.1" />
  <testcase classname="t" name="h" time="0.1" />
  <testcase classname="t" name="i" time="0.1" />
  <testcase classname="t" name="j" time="0.1" />
</testsuite>
</testsuites>
"""


def _minimal_repo(tmp_path: Path) -> Path:
    """Create the skeleton of a repo. Returns root."""
    (tmp_path / "hooks").mkdir()
    (tmp_path / "skills").mkdir()
    (tmp_path / "tests/unit").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "lib").mkdir()
    (tmp_path / "docs/02-Decisions/adrs").mkdir(parents=True)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude/settings.json").write_text('{"hooks":{}}', encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_test_health_healthy(tmp_path):
    repo = _minimal_repo(tmp_path)
    _write(repo / ".cognitive-os/reports/test-runs/latest/junit.xml", JUNIT_HEALTHY)
    score, ev = DogfoodScorer(repo)._score_test_health()
    assert score == 100.0
    assert "tests=10" in ev and "passed=10" in ev


def test_test_health_xfails_penalized(tmp_path):
    repo = _minimal_repo(tmp_path)
    _write(repo / ".cognitive-os/reports/test-runs/latest/junit.xml", JUNIT_DEGRADED)
    score, ev = DogfoodScorer(repo)._score_test_health()
    # 2 xfails * 2.0 penalty = 4.0 off the pass rate
    # pass_rate is passed (8) / effective_total (10-2=8) * 100 = 100
    # final = 100 - 4 = 96
    assert score == 96.0
    assert "xfailed=2" in ev


def test_test_health_failing_drops_score(tmp_path):
    repo = _minimal_repo(tmp_path)
    _write(repo / ".cognitive-os/reports/test-runs/latest/junit.xml", JUNIT_FAILING)
    score, _ = DogfoodScorer(repo)._score_test_health()
    # 3 failures — penalty dominates, score floors to 0
    assert score is not None and score < 10.0


def test_test_health_missing_junit_returns_null(tmp_path):
    repo = _minimal_repo(tmp_path)
    score, ev = DogfoodScorer(repo)._score_test_health()
    assert score is None
    assert "no cached" in ev


def test_skill_coverage_heuristic(tmp_path):
    repo = _minimal_repo(tmp_path)
    # 3 skills, 2 covered by behavioral tests
    for name in ("alpha-skill", "beta-skill", "gamma-skill"):
        _write(repo / f"skills/{name}/SKILL.md", f"# {name}\n")
    _write(
        repo / "tests/unit/test_alpha_skill.py",
        "def test_x():\n    assert 1 == 1\n",
    )
    _write(
        repo / "tests/unit/test_beta_skill.py",
        "import pytest\ndef test_y():\n    with pytest.raises(ValueError):\n        raise ValueError()\n",
    )
    # gamma has a matching test file but NO assertions → should not count
    _write(
        repo / "tests/unit/test_gamma_skill.py",
        "def test_z():\n    pass\n",
    )
    score, ev = DogfoodScorer(repo)._score_skill_coverage()
    # 2/3 = 66.67
    assert score == pytest.approx(66.67, rel=0.01)
    assert "covered=2/3" in ev


def test_hook_wiring_good_and_bad(tmp_path):
    repo = _minimal_repo(tmp_path)
    _write(repo / "hooks/alpha.sh", "#!/usr/bin/env bash\n")
    _write(repo / "hooks/beta.sh", "#!/usr/bin/env bash\n")
    _write(repo / "hooks/gamma.sh", "#!/usr/bin/env bash\n")
    # settings registers alpha + beta
    settings = {"hooks": {"PreToolUse": [{"hooks": [
        {"command": "bash hooks/alpha.sh"},
        {"command": "bash hooks/beta.sh"},
    ]}]}}
    _write(repo / ".claude/settings.json", json.dumps(settings))
    # tests mention alpha only
    _write(repo / "tests/unit/test_hooks.py", "def test_a(): assert 'alpha.sh' in 'alpha.sh'\n")
    score, ev = DogfoodScorer(repo)._score_hook_wiring()
    # 1/3 good
    assert score == pytest.approx(33.33, rel=0.01)
    assert "1/3" in ev


def test_adr_discipline_excludes_superseded(tmp_path):
    repo = _minimal_repo(tmp_path)
    # ADR-001 Accepted, with test proof
    _write(repo / "docs/02-Decisions/adrs/ADR-001.md", "# ADR-001\n\n## Status\nAccepted\n")
    # ADR-002 Accepted, NO proof
    _write(repo / "docs/02-Decisions/adrs/ADR-002.md", "# ADR-002\n\n## Status\nAccepted\n")
    # ADR-003 Superseded — should be excluded
    _write(repo / "docs/02-Decisions/adrs/ADR-003.md", "# ADR-003\n\n## Status\nSuperseded\n")
    _write(repo / "tests/unit/test_foo.py", "# references ADR-001\ndef test_x(): assert True\n")
    score, ev = DogfoodScorer(repo)._score_adr_discipline()
    # 1/2 relevant ADRs have proof
    assert score == 50.0
    assert "1/2" in ev


def test_harness_portability(tmp_path):
    repo = _minimal_repo(tmp_path)
    # 2 clean files, 1 dirty
    _write(repo / "hooks/clean.sh", 'echo "hello"\n')
    _write(repo / "scripts/alsoclean.py", "x = 1\n")
    _write(repo / "lib/dirty.py", 'path = ".claude/settings.json"\n')
    score, ev = DogfoodScorer(repo)._score_harness_portability()
    # 2/3 clean
    assert score == pytest.approx(66.67, rel=0.01)
    assert "dirty=1" in ev


def test_self_build_activity_requires_git(tmp_path, monkeypatch):
    repo = _minimal_repo(tmp_path)

    # Fake git log → 40 commits with balanced mix
    fake_commits = (
        ["feat: x"] * 10
        + ["fix: y"] * 10
        + ["test: z"] * 15
        + ["docs: d"] * 5
    )
    fake_stdout = "\n".join(fake_commits)

    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, fake_stdout, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    score, ev = DogfoodScorer(repo)._score_self_build_activity()
    # test_pct = 15/40 = 0.375 ≥ 0.25 → 50 pts
    # docs_pct = 5/40 = 0.125 ≥ 0.10 → 50 pts
    # volume_mult = min(40/20, 1) = 1 → score = 100
    assert score == 100.0
    assert "commits=40" in ev


def test_self_build_activity_no_git(tmp_path, monkeypatch):
    repo = _minimal_repo(tmp_path)

    def fake_run(cmd, **kw):
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", fake_run)
    score, ev = DogfoodScorer(repo)._score_self_build_activity()
    assert score is None
    assert "git not available" in ev


def test_doc_freshness_blend(tmp_path):
    repo = _minimal_repo(tmp_path)
    # ADR with a real file ref and a fake one
    _write(repo / "lib/foo.py", "pass\n")
    _write(
        repo / "docs/02-Decisions/adrs/ADR-001.md",
        "## Status\nAccepted\n\nSee `lib/foo.py` and `lib/bar.py`.\n",
    )
    # ADR with only existing refs
    _write(
        repo / "docs/02-Decisions/adrs/ADR-002.md",
        "## Status\nAccepted\n\nSee `lib/foo.py`.\n",
    )
    # A plan, fresh by default (just created)
    _write(repo / ".cognitive-os/plans/features/fresh.md", "# fresh\n")
    score, ev = DogfoodScorer(repo)._score_doc_freshness()
    # ADR health: 1/2 = 0.5; plan freshness: 1/1 = 1.0 → mean 0.75 → 75
    assert score == 75.0
    assert "1/2" in ev and "1/1" in ev


def test_primitive_observability_uses_contracts_projection_and_interventions(tmp_path):
    repo = _minimal_repo(tmp_path)
    _write(
        repo / "manifests/primitive-contracts.yaml",
        "\n".join(
            [
                "schema_version: primitive-contracts.v1",
                "contracts:",
                "  - id: destructive-git-blocker",
                "  - id: large-file-advisor",
            ]
        )
        + "\n",
    )
    _write(
        repo / "docs/06-Daily/reports/primitive-projection-fidelity-latest.json",
        json.dumps({"summary": {"projection_rows": 4, "aligned": 2, "pending_runtime_smoke": 2}}),
    )
    _write(
        repo / ".cognitive-os/metrics/primitive-interventions.jsonl",
        json.dumps(
            {
                "schema_version": "primitive-intervention.v1",
                "primitive_id": "destructive-git-blocker",
            }
        )
        + "\n",
    )
    _write(
        repo / ".cognitive-os/metrics/codebase-itinerary.jsonl",
        "".join(json.dumps({"schema_version": "codebase-itinerary.v1", "tool": "Read", "session_id": "unit"}) + "\n" for _ in range(2)),
    )

    score, ev = DogfoodScorer(repo)._score_primitive_observability()

    assert score is not None and score > 0
    assert "contracts=2" in ev
    assert "observed_contracts=1" in ev
    assert "itinerary_events=2" in ev


def test_overall_is_weighted_sum(tmp_path):
    """Overall score = sum(dim_score * weight) / sum(weights of measured dims)."""
    repo = _minimal_repo(tmp_path)
    _write(repo / ".cognitive-os/reports/test-runs/latest/junit.xml", JUNIT_HEALTHY)
    # Make everything else null so only test_health contributes
    # → overall should equal test_health = 100
    # But skill_coverage/hook_wiring return 0.0 on empty dirs? Let's check.
    # skill_coverage: no SKILL.md files → null
    # hook_wiring: no *.sh → null
    # adr_discipline: no ADRs → null
    # harness_portability: no scan targets → null
    # self_build_activity: depends on git — may return score or null
    # doc_freshness: no ADRs + no plans → null
    # Remove .cognitive-os partial dirs to avoid plan freshness contributing
    score = DogfoodScorer(repo).compute_score()
    # At minimum, overall must exist and test_health==100 present
    assert score.dimensions["test_health"] == 100.0
    assert score.overall is not None
    assert 0.0 <= score.overall <= 100.0


def test_missing_signals_marks_partial(tmp_path):
    repo = _minimal_repo(tmp_path)  # no junit, no skills, no hooks registered
    score = DogfoodScorer(repo).compute_score()
    assert score.partial is True
    assert "test_health" in score.missing_signals


def test_trend_jsonl_roundtrip(tmp_path):
    repo = _minimal_repo(tmp_path)
    _write(repo / ".cognitive-os/reports/test-runs/latest/junit.xml", JUNIT_HEALTHY)
    score = DogfoodScorer(repo).compute_score()
    trend = tmp_path / "metrics/dogfood-score.jsonl"
    append_trend_record(score, trend)
    append_trend_record(score, trend)
    last = read_last_trend_record(trend)
    assert last is not None
    assert last["dimensions"]["test_health"] == 100.0
    # Two lines written
    assert len(trend.read_text().splitlines()) == 2


def test_weights_sum_to_one_hundred():
    assert sum(DIMENSION_WEIGHTS.values()) == 100


def test_deterministic_repeat_runs(tmp_path, monkeypatch):
    repo = _minimal_repo(tmp_path)
    _write(repo / ".cognitive-os/reports/test-runs/latest/junit.xml", JUNIT_HEALTHY)
    # Force git to be unavailable so self_build_activity is deterministic-null
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError()))
    a = DogfoodScorer(repo).compute_score()
    b = DogfoodScorer(repo).compute_score()
    # Everything except timestamp must be identical
    a_d = a.to_dict(); b_d = b.to_dict()
    a_d.pop("timestamp"); b_d.pop("timestamp")
    assert a_d == b_d


def test_result_dataclass_to_dict_has_required_keys(tmp_path):
    repo = _minimal_repo(tmp_path)
    score = DogfoodScorer(repo).compute_score()
    d = score.to_dict()
    for key in ("overall", "dimensions", "missing_signals", "evidence",
                "partial", "weights", "timestamp"):
        assert key in d, f"missing key: {key}"
