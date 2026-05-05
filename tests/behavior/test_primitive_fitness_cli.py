"""Behavior tests for primitive fitness CLI and governed evaluation bridge."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

ROOT = Path(__file__).resolve().parents[2]
FITNESS = ROOT / "scripts" / "cos_primitive_fitness.py"
GOVERNED = ROOT / "scripts" / "cos_governed_self_improvement.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _metrics(root: Path, score: int, success_count: int) -> Path:
    metrics = root / ".cognitive-os" / "metrics"
    _write_jsonl(metrics / "trust-scores.jsonl", [{"score": score, "uncertainties_count": 1}])
    _write_jsonl(metrics / "skill-metrics.jsonl", [{"success": True} for _ in range(success_count)])
    _write_jsonl(metrics / "hallucinations.jsonl", [{"hallucinations": 0, "verified": 10}])
    _write_jsonl(metrics / "hook-events.jsonl", [{"outcome": "observe", "hook": "unit"}])
    return metrics


def test_cli_outputs_promotable_fitness_report(tmp_path: Path) -> None:
    baseline = _metrics(tmp_path / "baseline", 80, 2)
    candidate = _metrics(tmp_path / "candidate", 95, 4)

    result = subprocess.run(
        [
            "python3",
            str(FITNESS),
            "--primitive",
            "skills/example",
            "--baseline-metrics",
            str(baseline),
            "--candidate-metrics",
            str(candidate),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "promote"
    assert payload["candidate"]["overall_score"] > payload["baseline"]["overall_score"]


def test_governed_evaluate_from_fitness_records_comparative_gate(tmp_path: Path) -> None:
    metrics = tmp_path / ".cognitive-os" / "metrics"
    _write_jsonl(
        metrics / "error-learning.jsonl",
        [
            {"type": "TEST_FAILURE", "service": "checkout"},
            {"type": "TEST_FAILURE", "service": "checkout"},
            {"type": "TEST_FAILURE", "service": "checkout"},
        ],
    )
    draft = subprocess.run(
        ["python3", str(GOVERNED), "--project-dir", str(tmp_path), "draft", "repair-test-failure-checkout"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert draft.returncode == 0, draft.stderr
    report = tmp_path / "fitness.json"
    report.write_text(
        json.dumps(
            {
                "verdict": "promote",
                "required_delta": 1.0,
                "baseline": {"overall_score": 80},
                "candidate": {"overall_score": 84},
                "safety_regressions": [],
                "evidence_commands": ["scripts/cos-primitive-fitness --json"],
            }
        ),
        encoding="utf-8",
    )

    evaluation = subprocess.run(
        [
            "python3",
            str(GOVERNED),
            "--project-dir",
            str(tmp_path),
            "evaluate-from-fitness",
            "repair-test-failure-checkout",
            "--fitness-report",
            str(report),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert evaluation.returncode == 0, evaluation.stderr
    payload = json.loads(evaluation.stdout)
    assert payload["status"] == "passed"
    assert payload["candidate_score"] == 84


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_cli_accepts_consumer_and_dependency_evidence_inputs(tmp_path: Path) -> None:
    baseline = _metrics(tmp_path / "baseline", 84, 2)
    candidate = _metrics(tmp_path / "candidate", 94, 4)
    baseline_bundle = _write_json(
        tmp_path / "baseline-consumer.json",
        {
            "mode": "propose_only",
            "runtime_effect": "none",
            "action_counts": {"project-local": 1},
            "proposals": [{"action": "project-local", "runtime_effect": "none"}],
            "policy": {"auto_merge": False},
        },
    )
    candidate_bundle = _write_json(
        tmp_path / "candidate-consumer.json",
        {
            "mode": "propose_only",
            "runtime_effect": "none",
            "action_counts": {"upstream-candidate": 2},
            "proposals": [
                {"action": "upstream-candidate", "runtime_effect": "none"},
                {"action": "upstream-candidate", "runtime_effect": "none"},
            ],
            "policy": {"auto_merge": False},
        },
    )
    baseline_deps = _write_json(
        tmp_path / "baseline-deps.json",
        {
            "schema_version": "cos-deps-install.v1",
            "profile": "core",
            "platform": "macos",
            "mode": "dry-run",
            "credential_policy": "never-copy-or-read-credential-stores",
            "already_present": [{"name": "git"}],
            "installable": [{"name": "uv"}],
            "manual": [],
            "auth_bound": [],
            "unsupported_platform": [],
            "installed": [],
            "failed": [],
        },
    )
    candidate_deps = _write_json(
        tmp_path / "candidate-deps.json",
        {
            "schema_version": "cos-deps-install.v1",
            "profile": "core",
            "platform": "macos",
            "mode": "dry-run",
            "credential_policy": "never-copy-or-read-credential-stores",
            "already_present": [{"name": "git"}, {"name": "uv"}],
            "installable": [],
            "manual": [],
            "auth_bound": [],
            "unsupported_platform": [],
            "installed": [],
            "failed": [],
        },
    )

    result = subprocess.run(
        [
            "python3",
            str(FITNESS),
            "--primitive",
            "skills/example",
            "--baseline-metrics",
            str(baseline),
            "--candidate-metrics",
            str(candidate),
            "--baseline-consumer-proposals",
            str(baseline_bundle),
            "--candidate-consumer-proposals",
            str(candidate_bundle),
            "--baseline-dependency-report",
            str(baseline_deps),
            "--candidate-dependency-report",
            str(candidate_deps),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "promote"
    assert payload["candidate"]["raw"]["consumer_evidence"]["upstream_candidate_count"] == 2
    assert payload["candidate"]["raw"]["portability_readiness"]["credential_policy_ok"] is True
