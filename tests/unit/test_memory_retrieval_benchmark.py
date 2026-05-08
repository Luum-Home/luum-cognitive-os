from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lib.memory_retrieval_benchmark import run_benchmark

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "manifests" / "memory-retrieval-benchmark.yaml"
SCRIPT = ROOT / "scripts" / "cos-memory-benchmark"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_memory_benchmark_oracle_fixtures_pass() -> None:
    report = run_benchmark(MANIFEST)

    assert report["schema_version"] == "memory-retrieval-benchmark-report/v1"
    assert report["status"] == "pass"
    assert report["summary"]["fixtures"] >= 3
    assert report["summary"]["block"] == 0


def test_memory_benchmark_catches_stale_temporal_answer(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.jsonl"
    write_jsonl(
        candidate,
        [
            {
                "fixture_id": "temporal-contradiction-license-policy",
                "strategy": "bad-temporal",
                "retrieved_ids": ["obs-old-license-allow-bsl", "obs-current-license-blocklist"],
                "support_chain": [],
                "latency_ms": 1,
            },
            {
                "fixture_id": "multi-hop-adr-implementation-test",
                "strategy": "oracle-like",
                "retrieved_ids": ["decision-adr-210", "file-lib-fleet-confidence", "test-fleet-confidence-export"],
                "support_chain": ["decision-adr-210", "file-lib-fleet-confidence", "test-fleet-confidence-export"],
                "latency_ms": 1,
            },
            {
                "fixture_id": "procedural-runbook-current",
                "strategy": "oracle-like",
                "retrieved_ids": ["runbook-memory-slice0", "chat-memory-idea"],
                "support_chain": [],
                "latency_ms": 1,
            },
        ],
    )

    report = run_benchmark(MANIFEST, candidate_results_path=candidate)

    assert report["status"] == "block"
    assert any(f["code"] == "stale-temporal-answer" for f in report["findings"])


def test_memory_benchmark_catches_unsupported_multi_hop_chain(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.jsonl"
    write_jsonl(
        candidate,
        [
            {
                "fixture_id": "temporal-contradiction-license-policy",
                "strategy": "oracle-like",
                "retrieved_ids": ["obs-current-license-blocklist", "obs-old-license-allow-bsl"],
                "support_chain": [],
                "latency_ms": 1,
            },
            {
                "fixture_id": "multi-hop-adr-implementation-test",
                "strategy": "unsupported-chain",
                "retrieved_ids": ["decision-adr-210", "file-lib-fleet-confidence", "test-fleet-confidence-export"],
                "support_chain": ["decision-adr-210", "test-fleet-confidence-export"],
                "latency_ms": 1,
            },
            {
                "fixture_id": "procedural-runbook-current",
                "strategy": "oracle-like",
                "retrieved_ids": ["runbook-memory-slice0", "chat-memory-idea"],
                "support_chain": [],
                "latency_ms": 1,
            },
        ],
    )

    report = run_benchmark(MANIFEST, candidate_results_path=candidate)

    assert report["status"] == "block"
    assert any(f["code"] == "unsupported-multi-hop-chain" for f in report["findings"])


def test_cos_memory_benchmark_cli_json_smoke() -> None:
    proc = subprocess.run([str(SCRIPT), "--json"], cwd=ROOT, text=True, capture_output=True, check=False)

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    assert report["summary"]["fixtures"] >= 3
