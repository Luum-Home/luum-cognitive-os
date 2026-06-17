#!/usr/bin/env python3
# SCOPE: both
"""Portable epistemic review primitives for model-agnostic skeptical audits.

The goal is to turn "don't trust interested claims" into deterministic
receipts that any CLI/IDE/model can follow: rank evidence, mark interested
witnesses, run bounded verification commands, and scan benchmarks for gaming
signals. These commands are advisory unless a caller chooses to gate on rc=2.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "cos.epistemic-review.v1"
EVIDENCE_SCHEMA = "cos.evidence-rank.v1"
BENCHMARK_SCHEMA = "cos.benchmark-gaming-audit.v1"
INTERESTED_SOURCES = {"self-authored", "self-reported", "project-authored", "vendor", "unknown"}
LOW_TRUST_SOURCES = {"self-authored", "self-reported", "project-authored", "vendor"}
TEXT_SUFFIXES = {".md", ".txt", ".rst", ".json", ".yaml", ".yml", ".toml", ".py", ".js", ".ts", ".tsx", ".go", ".rs", ".java", ".sh", ".patch", ".diff"}
IGNORED_DIRS = {".git", ".venv", "venv", "node_modules", "dist", "build", "target", "__pycache__", ".pytest_cache"}

EVIDENCE_TIERS: list[tuple[str, int, tuple[str, ...]]] = [
    ("source-code-tests-now", 100, ("pytest", "go test", "npm test", "cargo test", "verify", "test passed", "build passed", "source inspection", "compiled now")),
    ("reproducible-command-output", 85, ("command output", "exit 0", "stdout", "stderr", "receipt", "log", "reproduced")),
    ("commit-diff-history", 70, ("commit", "diff", "patch", "git show", "git log", "changed files")),
    ("implementation-linked-docs", 55, ("adr", "doc", "design", "readme", "link to source", "path:")),
    ("self-reported-benchmark", 35, ("benchmark", "faster", "tokens saved", "wall-clock", "%", "improvement", "speedup")),
    ("marketing-or-aspirational-docs", 20, ("marketing", "aspirational", "should", "could", "roadmap", "claim", "promise")),
]

BENCHMARK_SIGNALS: list[tuple[str, str, int, re.Pattern[str]]] = [
    ("benchmark-special-case", "high", 4, re.compile(r"\b(if|case|match)\b.*\b(bench|benchmark|criterion|pytest-benchmark)\b", re.I)),
    ("hardcoded-benchmark-fixture", "high", 4, re.compile(r"\b(hardcoded|special[-_ ]case|golden|fixture)\b.*\b(bench|benchmark|score)\b", re.I)),
    ("benchmark-gaming-language", "high", 5, re.compile(r"\b(gam(e|ing)|cheat|optimi[sz]e for the benchmark|fold of benchmark)\b", re.I)),
    ("disabled-safety-check", "medium", 3, re.compile(r"\b(skip|xfail|disabled|ignore)\b.*\b(test|verify|assert|benchmark)\b", re.I)),
    ("metric-only-claim", "medium", 2, re.compile(r"\b(\d+\s?%|x faster|tokens saved|wall[- ]clock)\b.*\b(no tests|without verification|self[- ]reported)\b", re.I)),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_root(path: str | None) -> Path:
    return Path(path or os.getcwd()).resolve()


def sanitize_id(value: str | None, fallback: str = "default") -> str:
    raw = (value or fallback).strip()
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in raw)
    return safe or fallback


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload.get("message") or json.dumps(payload, sort_keys=True))


def evidence_tier(text: str) -> tuple[str, int]:
    lowered = text.lower()
    for tier, score, tokens in EVIDENCE_TIERS:
        if any(token in lowered for token in tokens):
            return tier, score
    if re.search(r"\b[A-Za-z0-9_./-]+\.(py|go|rs|js|ts|tsx|java|sh|md)\b", text):
        return "implementation-linked-docs", 55
    return "unclassified-assertion", 10


def rank_evidence(items: list[str]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for idx, text in enumerate(items, start=1):
        tier, score = evidence_tier(text)
        ranked.append({"index": idx, "evidence": text, "tier": tier, "score": score})
    return sorted(ranked, key=lambda item: (-int(item["score"]), int(item["index"])))


def run_verification(root: Path, command: str | None, timeout: int) -> dict[str, Any] | None:
    if not command:
        return None
    try:
        result = subprocess.run(command, cwd=root, shell=True, text=True, capture_output=True, timeout=timeout, check=False)
        return {
            "command": command,
            "returncode": result.returncode,
            "passed": result.returncode == 0,
            "stdout_tail": result.stdout[-4000:],
            "stderr_tail": result.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {"command": command, "returncode": 124, "passed": False, "timeout": True, "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "", "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else ""}


def audit_claim(args: argparse.Namespace) -> int:
    root = project_root(args.project_dir)
    source_interest = (args.source_interest or "unknown").strip().lower()
    evidence = list(args.evidence or [])
    counter = list(args.counterevidence or [])
    ranked = rank_evidence(evidence)
    best_score = int(ranked[0]["score"]) if ranked else 0
    interested = source_interest in INTERESTED_SOURCES
    low_trust = source_interest in LOW_TRUST_SOURCES
    confidence = int(args.initial_confidence)
    confidence += min(35, best_score // 3)
    confidence -= 25 if interested else 0
    confidence -= 10 if low_trust and best_score < 85 else 0
    confidence -= 15 * len(counter)
    verification = run_verification(root, args.verification_command, args.timeout_seconds)
    refutations: list[str] = []
    if not evidence:
        refutations.append("claim has no explicit evidence")
        confidence -= 30
    if interested:
        refutations.append("claim source is an interested witness; require independent source inspection or current tests")
    if low_trust and best_score < 85:
        refutations.append("best evidence is below reproducible command/source-test level for a self-interested claim")
    if counter:
        refutations.extend(counter)
    if verification is None:
        refutations.append("no bounded verification command supplied")
        confidence -= 10
    elif verification.get("passed"):
        confidence += 20
    else:
        confidence -= 40
        refutations.append("verification command failed or timed out")
    confidence = max(0, min(100, confidence))
    if confidence >= args.pass_threshold and verification and verification.get("passed") and not counter and (not low_trust or best_score >= 85):
        verdict = "supported"
    elif verification and not verification.get("passed"):
        verdict = "unsupported"
    elif low_trust and best_score < 85:
        verdict = "needs-independent-verification"
    elif confidence >= max(45, args.pass_threshold - 20):
        verdict = "partially-supported"
    else:
        verdict = "needs-review"
    payload = {
        "schema_version": SCHEMA,
        "ts": utc_now(),
        "project_root": str(root),
        "claim_id": sanitize_id(args.claim_id, "claim"),
        "claim": args.claim,
        "source": args.source,
        "source_interest": source_interest,
        "interested_witness": interested,
        "evidence_rank": ranked,
        "counterevidence": counter,
        "verification": verification,
        "refutation_questions": refutations,
        "confidence": confidence,
        "pass_threshold": args.pass_threshold,
        "verdict": verdict,
    }
    receipt = root / ".cognitive-os" / "epistemic-review" / "claim-audit.jsonl"
    append_jsonl(receipt, payload)
    payload["receipt_path"] = str(receipt)
    payload["message"] = f"claim-audit verdict={verdict} confidence={confidence} interested={interested}"
    emit(payload, args.json)
    return 0 if verdict == "supported" else 2


def evidence_rank_command(args: argparse.Namespace) -> int:
    items = list(args.evidence or [])
    for path_raw in args.evidence_file or []:
        path = Path(path_raw)
        if path.exists():
            items.append(path.read_text(encoding="utf-8", errors="ignore")[:8000])
        else:
            items.append(path_raw)
    ranked = rank_evidence(items)
    payload = {"schema_version": EVIDENCE_SCHEMA, "ts": utc_now(), "count": len(ranked), "ranked": ranked, "message": f"ranked {len(ranked)} evidence items"}
    emit(payload, args.json)
    return 0


def iter_files(paths: list[str], root: Path, max_files: int) -> list[Path]:
    found: list[Path] = []
    raw_paths = paths or [str(root)]
    for raw in raw_paths:
        path = Path(raw)
        if not path.is_absolute():
            path = root / path
        if path.is_file():
            found.append(path.resolve())
            continue
        if path.is_dir():
            for candidate in sorted(path.rglob("*")):
                if len(found) >= max_files:
                    return found
                if candidate.is_dir() or candidate.suffix.lower() not in TEXT_SUFFIXES:
                    continue
                parts = candidate.relative_to(path).parts if candidate.is_relative_to(path) else candidate.parts
                if any(part in IGNORED_DIRS for part in parts):
                    continue
                found.append(candidate.resolve())
    return found[:max_files]


def benchmark_audit(args: argparse.Namespace) -> int:
    root = project_root(args.project_dir)
    findings: list[dict[str, Any]] = []
    for path in iter_files(args.path or [], root, args.max_files):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for signal, severity, weight, pattern in BENCHMARK_SIGNALS:
                if pattern.search(line):
                    findings.append({"path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path), "line": line_no, "signal": signal, "severity": severity, "weight": weight, "excerpt": line.strip()[:240]})
    risk_score = sum(int(f["weight"]) for f in findings)
    high = sum(1 for f in findings if f["severity"] == "high")
    verdict = "needs-refutation" if high or risk_score >= args.fail_score else "no-gaming-signals"
    payload = {"schema_version": BENCHMARK_SCHEMA, "ts": utc_now(), "project_root": str(root), "finding_count": len(findings), "high_count": high, "risk_score": risk_score, "fail_score": args.fail_score, "verdict": verdict, "findings": findings, "message": f"benchmark-gaming-audit verdict={verdict} findings={len(findings)}"}
    receipt = root / ".cognitive-os" / "epistemic-review" / "benchmark-gaming-audit.jsonl"
    append_jsonl(receipt, payload)
    payload["receipt_path"] = str(receipt)
    emit(payload, args.json)
    return 0 if args.advisory or verdict == "no-gaming-signals" else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cognitive OS epistemic review primitives")
    sub = parser.add_subparsers(dest="command", required=True)

    claim = sub.add_parser("claim-audit", help="Challenge a claim as a hypothesis with evidence and verification receipts")
    claim.add_argument("--project-dir")
    claim.add_argument("--claim", required=True)
    claim.add_argument("--claim-id", default="claim")
    claim.add_argument("--source", default="unspecified")
    claim.add_argument("--source-interest", default="unknown", choices=["self-authored", "self-reported", "project-authored", "vendor", "neutral", "external", "unknown"])
    claim.add_argument("--evidence", action="append", default=[])
    claim.add_argument("--counterevidence", action="append", default=[])
    claim.add_argument("--verification-command")
    claim.add_argument("--initial-confidence", type=int, default=45)
    claim.add_argument("--pass-threshold", type=int, default=75)
    claim.add_argument("--timeout-seconds", type=int, default=60)
    claim.add_argument("--json", action="store_true")
    claim.set_defaults(func=audit_claim)

    rank = sub.add_parser("evidence-rank", help="Rank evidence by source hierarchy")
    rank.add_argument("--evidence", action="append", default=[])
    rank.add_argument("--evidence-file", action="append", default=[])
    rank.add_argument("--json", action="store_true")
    rank.set_defaults(func=evidence_rank_command)

    bench = sub.add_parser("benchmark-gaming-audit", help="Scan repo text for benchmark-gaming/refutation signals")
    bench.add_argument("--project-dir")
    bench.add_argument("--path", action="append", default=[])
    bench.add_argument("--max-files", type=int, default=500)
    bench.add_argument("--fail-score", type=int, default=4)
    bench.add_argument("--advisory", action="store_true")
    bench.add_argument("--json", action="store_true")
    bench.set_defaults(func=benchmark_audit)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
