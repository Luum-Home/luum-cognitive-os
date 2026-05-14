from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lib.dispatch_optimizer import analyze, propose_routing, write_proposal
from scripts.benchmark_providers import run_benchmark, summarize

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_provider_benchmark_fixture_scores_without_external_calls() -> None:
    task_set = REPO_ROOT / "docs" / "08-References" / "benchmarks" / "provider-quality-smoke.yaml"

    results = run_benchmark(task_set, ["fixture-strong", "fixture-weak"], benchmark_id="test")
    summary = summarize(results)

    assert summary["fixture-strong"]["tasks_passed"] == 2
    assert summary["fixture-weak"]["tasks_passed"] == 0
    assert all(result.cost_usd == 0.0 for result in results)


def test_benchmark_cli_writes_jsonl(tmp_path: Path) -> None:
    output = tmp_path / "benchmark-results.jsonl"
    result = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "benchmark_providers.py"),
            "--task-set",
            str(REPO_ROOT / "docs" / "08-References" / "benchmarks" / "provider-quality-smoke.yaml"),
            "--providers",
            "fixture-strong,fixture-weak",
            "--output-jsonl",
            str(output),
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert len(output.read_text().splitlines()) == 4
    assert json.loads(result.stdout)["summary"]["fixture-strong"]["tasks_passed"] == 2


def test_dispatch_optimizer_writes_human_reviewed_proposal(tmp_path: Path) -> None:
    metrics = tmp_path / "llm-dispatch.jsonl"
    rows = [
        {"skill_name": "code-review", "task_type": "review", "provider_used": "claude", "success": True, "cost_usd": 0.02, "latency_ms": 1000}
        for _ in range(10)
    ] + [
        {"skill_name": "code-review", "task_type": "review", "provider_used": "qwen", "success": True, "cost_usd": 0.01, "latency_ms": 900}
        for _ in range(10)
    ]
    metrics.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    payload = propose_routing(analyze(metrics, min_samples_per_tuple=10))
    output = tmp_path / "auto-tuned.yaml"
    write_proposal(payload, output)

    assert payload["human_review_required"] is True
    assert payload["proposals"][0]["provider"] == "qwen"
    assert output.exists()
