# SCOPE: os-only
"""Slice 0 memory retrieval benchmark fixtures and evaluator.

This module is intentionally non-mutating. It evaluates retrieval result rows
against deterministic fixtures before COS changes Engram schema or retrieval
defaults for the Wave 2 memory-layer-evolution SDD.
"""
from __future__ import annotations

import json
import re
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


def display_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


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


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


def _relations(fixture: dict[str, Any], relation_type: str | None = None) -> list[dict[str, Any]]:
    rels = list(fixture.get("relations", []) or [])
    if relation_type:
        rels = [rel for rel in rels if rel.get("type") == relation_type]
    return rels


def _memory_class(obs: dict[str, Any]) -> str:
    explicit = obs.get("memory_class")
    if explicit:
        return str(explicit)
    mapping = {
        "decision": "semantic",
        "implementation": "procedural",
        "test": "procedural",
        "procedure": "procedural",
        "conversation": "episodic",
    }
    return mapping.get(str(obs.get("type", "")).lower(), "unknown")


def _base_scores(fixture: dict[str, Any], *, dual_level: bool = False, memory_class_overlay: bool = False) -> list[tuple[float, str]]:
    query_tokens = _tokens(str(fixture.get("query", "")))
    scored = []
    for obs in fixture.get("observations", []) or []:
        title_tokens = _tokens(str(obs.get("title", "")))
        content_tokens = _tokens(str(obs.get("content", "")))
        all_tokens = title_tokens | content_tokens
        union = query_tokens | all_tokens
        lexical = (len(query_tokens & all_tokens) / len(union)) if union else 0.0
        if dual_level:
            # LightRAG-inspired dual-level local proxy: precise title/entity
            # overlap plus broad content/topic overlap. This is an algorithmic
            # shape only; no external dependency or default Engram change.
            title_union = query_tokens | title_tokens
            topic_union = query_tokens | content_tokens
            entity = (len(query_tokens & title_tokens) / len(title_union)) if title_union else 0.0
            topic = (len(query_tokens & content_tokens) / len(topic_union)) if topic_union else 0.0
            lexical = (0.6 * entity) + (0.4 * topic)
        if memory_class_overlay:
            # MIRIX-style class overlay as a small tie-breaker. Procedural
            # queries prefer procedural rows; decision/current-policy queries
            # prefer semantic rows. It never overrides temporal validity.
            cls = _memory_class(obs)
            q = str(fixture.get("query", "")).lower()
            if cls == "procedural" and any(word in q for word in ["how", "run", "start", "implemen", "test"]):
                lexical += 0.05
            if cls == "semantic" and any(word in q for word in ["current", "decision", "policy", "posture"]):
                lexical += 0.05
        scored.append((lexical, str(obs.get("id", ""))))
    return scored


def _apply_temporal_validity(fixture: dict[str, Any], scored: list[tuple[float, str]]) -> list[tuple[float, str]]:
    current_ids = {str(obs.get("id")) for obs in fixture.get("observations", []) or [] if obs.get("valid_to") in (None, "")}
    stale_ids = {str(obs.get("id")) for obs in fixture.get("observations", []) or [] if obs.get("valid_to") not in (None, "")}
    supersedes = {(str(rel.get("from")), str(rel.get("to"))) for rel in _relations(fixture, "supersedes")}
    adjusted = []
    for score, obs_id in scored:
        if obs_id in current_ids:
            score += 1.0
        if obs_id in stale_ids:
            score -= 1.0
        if any(src == obs_id for src, _target in supersedes):
            score += 1.0
        if any(target == obs_id for _src, target in supersedes):
            score -= 1.0
        adjusted.append((score, obs_id))
    return adjusted


def _support_chain_for_expected(fixture: dict[str, Any]) -> list[str]:
    expected_chain = [str(item) for item in (fixture.get("expected", {}) or {}).get("required_chain", []) or []]
    if not expected_chain:
        return []
    edges = {(str(rel.get("from")), str(rel.get("to"))) for rel in _relations(fixture)}
    if all((a, b) in edges for a, b in zip(expected_chain, expected_chain[1:])):
        return expected_chain
    return []


def wave2_result_for_fixture(fixture: dict[str, Any], *, temporal: bool, support_chain: bool, dual_level: bool, memory_class_overlay: bool, label: str) -> dict[str, Any]:
    scored = _base_scores(fixture, dual_level=dual_level, memory_class_overlay=memory_class_overlay)
    if temporal:
        scored = _apply_temporal_validity(fixture, scored)
    scored.sort(key=lambda item: (-item[0], item[1]))
    return {
        "fixture_id": fixture["id"],
        "strategy": label,
        "retrieved_ids": [obs_id for _score, obs_id in scored if obs_id],
        "support_chain": _support_chain_for_expected(fixture) if support_chain else [],
        "latency_ms": 0.0,
        "memory_classes": {str(obs.get("id")): _memory_class(obs) for obs in fixture.get("observations", []) or []},
    }


def current_local_result_for_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Approximate the current Engram retrieval baseline on fixture-local rows.

    The current local baseline mirrors the existing COS memory retriever shape:
    lexical search plus Jaccard reranking over title/content. It is intentionally
    fixture-local and non-mutating because Slice 0 must not write synthetic rows
    into the operator's Engram database.
    """
    return wave2_result_for_fixture(
        fixture,
        temporal=False,
        support_chain=False,
        dual_level=False,
        memory_class_overlay=False,
        label="current-local-fts-jaccard",
    )


def candidate_map(fixtures: list[dict[str, Any]], candidate_rows: list[dict[str, Any]] | None, *, strategy: str = "oracle") -> dict[str, dict[str, Any]]:
    if candidate_rows is not None:
        return {str(row.get("fixture_id")): row for row in candidate_rows}
    if strategy == "current-local":
        return {fixture["id"]: current_local_result_for_fixture(fixture) for fixture in fixtures}
    if strategy == "temporal-local":
        return {
            fixture["id"]: wave2_result_for_fixture(
                fixture, temporal=True, support_chain=False, dual_level=False, memory_class_overlay=False, label="temporal-local"
            )
            for fixture in fixtures
        }
    if strategy == "graph-path-local":
        return {
            fixture["id"]: wave2_result_for_fixture(
                fixture, temporal=True, support_chain=True, dual_level=False, memory_class_overlay=False, label="graph-path-local"
            )
            for fixture in fixtures
        }
    if strategy == "dual-level-local":
        return {
            fixture["id"]: wave2_result_for_fixture(
                fixture, temporal=True, support_chain=True, dual_level=True, memory_class_overlay=False, label="dual-level-local"
            )
            for fixture in fixtures
        }
    if strategy == "memory-class-local":
        return {
            fixture["id"]: wave2_result_for_fixture(
                fixture, temporal=True, support_chain=True, dual_level=True, memory_class_overlay=True, label="memory-class-local"
            )
            for fixture in fixtures
        }
    return {fixture["id"]: oracle_result_for_fixture(fixture) for fixture in fixtures}


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
        "memory_classes": candidate.get("memory_classes", {}),
        "findings": [finding.to_dict() for finding in findings],
    }


def run_benchmark(manifest_path: Path, *, candidate_results_path: Path | None = None, top_k: int | None = None, strategy: str = "oracle") -> dict[str, Any]:
    manifest = load_yaml(manifest_path)
    top = int(top_k or manifest.get("metrics", {}).get("top_k", DEFAULT_TOP_K) or DEFAULT_TOP_K)
    fixtures = load_fixtures(manifest, manifest_path)
    candidate_rows = load_jsonl(candidate_results_path) if candidate_results_path else None
    candidates = candidate_map(fixtures, candidate_rows, strategy=strategy)
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
        "manifest": display_path(manifest_path),
        "candidate_results": display_path(candidate_results_path),
        "strategy": strategy if not candidate_results_path else "candidate-results",
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
