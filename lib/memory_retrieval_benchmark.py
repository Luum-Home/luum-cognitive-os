# SCOPE: os-only
"""Slice 0 memory retrieval benchmark fixtures and evaluator.

This module is intentionally non-mutating. It evaluates retrieval result rows
against deterministic fixtures before COS changes Engram schema or retrieval
defaults for the Wave 2 memory-layer-evolution SDD.
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "memory-retrieval-benchmark-report/v1"
DEFAULT_TOP_K = 5


@dataclass(frozen=True)
class BenchmarkFinding:
    severity: str
    code: str
    fixture_id: str
    message: str
    expected: Any = None
    actual: Any = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "severity": self.severity,
            "code": self.code,
            "fixture_id": self.fixture_id,
            "message": self.message,
        }
        if self.expected is not None:
            payload["expected"] = self.expected
        if self.actual is not None:
            payload["actual"] = self.actual
        return payload


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_fixtures(manifest: dict[str, Any], manifest_path: Path) -> list[dict[str, Any]]:
    fixture_dir = Path(manifest.get("fixture_dir", "tests/fixtures/memory_retrieval"))
    if not fixture_dir.is_absolute():
        fixture_dir = manifest_path.parent.parent / fixture_dir
    fixtures = []
    for item in manifest.get("fixtures", []) or []:
        fixture_path = fixture_dir / str(item["file"])
        fixture = load_json(fixture_path)
        fixture.setdefault("id", item.get("id") or fixture_path.stem)
        fixture.setdefault("class", item.get("class", "unknown"))
        fixtures.append(fixture)
    return fixtures


def oracle_result_for_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    expected = fixture.get("expected", {}) or {}
    must_include = list(expected.get("must_include", []) or [])
    retrieved = list(dict.fromkeys(must_include))
    known_ids = [obs.get("id") for obs in fixture.get("observations", []) if obs.get("id")]
    for obs_id in known_ids:
        if obs_id not in retrieved:
            retrieved.append(obs_id)
    return {
        "fixture_id": fixture["id"],
        "strategy": "oracle",
        "retrieved_ids": retrieved,
        "support_chain": list(expected.get("required_chain", []) or []),
        "latency_ms": 0.0,
    }


def candidate_map(fixtures: list[dict[str, Any]], candidate_rows: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    if candidate_rows is None:
        return {fixture["id"]: oracle_result_for_fixture(fixture) for fixture in fixtures}
    return {str(row.get("fixture_id")): row for row in candidate_rows}


def _rank(retrieved_ids: list[str], target: str) -> int | None:
    try:
        return retrieved_ids.index(target)
    except ValueError:
        return None


def evaluate_fixture(fixture: dict[str, Any], candidate: dict[str, Any], *, top_k: int = DEFAULT_TOP_K) -> dict[str, Any]:
    fixture_id = str(fixture["id"])
    expected = fixture.get("expected", {}) or {}
    retrieved_ids = [str(item) for item in candidate.get("retrieved_ids", []) or []]
    support_chain = [str(item) for item in candidate.get("support_chain", []) or []]
    findings: list[BenchmarkFinding] = []

    must_include = [str(item) for item in expected.get("must_include", []) or []]
    missing = [item for item in must_include if item not in retrieved_ids[:top_k]]
    if missing:
        findings.append(
            BenchmarkFinding(
                "block",
                "missing-required-result",
                fixture_id,
                f"Required result missing from top-{top_k} retrieval output.",
                expected=must_include,
                actual=retrieved_ids[:top_k],
            )
        )

    for relation in expected.get("must_rank_above", []) or []:
        higher = str(relation["higher"])
        lower = str(relation["lower"])
        higher_rank = _rank(retrieved_ids, higher)
        lower_rank = _rank(retrieved_ids, lower)
        if higher_rank is None or lower_rank is None or higher_rank >= lower_rank:
            findings.append(
                BenchmarkFinding(
                    "block",
                    "stale-temporal-answer",
                    fixture_id,
                    "Temporal benchmark expected the current/superseding memory to rank above the stale memory.",
                    expected={"higher": higher, "lower": lower},
                    actual={"higher_rank": higher_rank, "lower_rank": lower_rank, "retrieved_ids": retrieved_ids},
                )
            )

    required_chain = [str(item) for item in expected.get("required_chain", []) or []]
    if required_chain and support_chain != required_chain:
        findings.append(
            BenchmarkFinding(
                "block",
                "unsupported-multi-hop-chain",
                fixture_id,
                "Multi-hop benchmark expected an exact supported evidence chain.",
                expected=required_chain,
                actual=support_chain,
            )
        )

    precision_hits = sum(1 for item in retrieved_ids[:top_k] if item in must_include)
    precision_at_k = precision_hits / top_k if top_k else 0.0
    temporal_correct = not any(f.code == "stale-temporal-answer" for f in findings)
    source_supported = not any(f.code in {"missing-required-result", "unsupported-multi-hop-chain"} for f in findings)
    return {
        "fixture_id": fixture_id,
        "class": fixture.get("class", "unknown"),
        "strategy": candidate.get("strategy", "unknown"),
        "passed": not findings,
        "precision_at_k": round(precision_at_k, 4),
        "temporal_correct": temporal_correct,
        "source_supported": source_supported,
        "latency_ms": float(candidate.get("latency_ms", 0.0) or 0.0),
        "retrieved_ids": retrieved_ids,
        "support_chain": support_chain,
        "findings": [finding.to_dict() for finding in findings],
    }


def run_benchmark(manifest_path: Path, *, candidate_results_path: Path | None = None, top_k: int | None = None) -> dict[str, Any]:
    manifest = load_yaml(manifest_path)
    top = int(top_k or manifest.get("metrics", {}).get("top_k", DEFAULT_TOP_K) or DEFAULT_TOP_K)
    fixtures = load_fixtures(manifest, manifest_path)
    candidate_rows = load_jsonl(candidate_results_path) if candidate_results_path else None
    candidates = candidate_map(fixtures, candidate_rows)
    results = []
    findings = []
    for fixture in fixtures:
        fixture_id = str(fixture["id"])
        candidate = candidates.get(fixture_id)
        if not candidate:
            result = {
                "fixture_id": fixture_id,
                "class": fixture.get("class", "unknown"),
                "strategy": "missing",
                "passed": False,
                "precision_at_k": 0.0,
                "temporal_correct": False,
                "source_supported": False,
                "latency_ms": 0.0,
                "retrieved_ids": [],
                "support_chain": [],
                "findings": [
                    BenchmarkFinding("block", "missing-candidate-result", fixture_id, "Candidate results did not include this fixture.").to_dict()
                ],
            }
        else:
            result = evaluate_fixture(fixture, candidate, top_k=top)
        results.append(result)
        findings.extend(result["findings"])

    latency_values = sorted(result["latency_ms"] for result in results)
    p95_latency_ms = latency_values[-1] if len(latency_values) < 2 else statistics.quantiles(latency_values, n=20, method="inclusive")[18]
    block_count = sum(1 for finding in findings if finding["severity"] == "block")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "block" if block_count else "pass",
        "manifest": str(manifest_path),
        "candidate_results": str(candidate_results_path) if candidate_results_path else None,
        "summary": {
            "fixtures": len(results),
            "passed": sum(1 for result in results if result["passed"]),
            "block": block_count,
            "precision_at_k_avg": round(sum(result["precision_at_k"] for result in results) / len(results), 4) if results else 0.0,
            "temporal_correct": sum(1 for result in results if result["temporal_correct"]),
            "source_supported": sum(1 for result in results if result["source_supported"]),
            "p95_latency_ms": round(float(p95_latency_ms), 4) if results else 0.0,
        },
        "results": results,
        "findings": findings,
    }
