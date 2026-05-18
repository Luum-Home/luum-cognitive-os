#!/usr/bin/env python3
# SCOPE: os-only
"""Permanent routing-quality gate for language-agnostic skill routing."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GateThresholds:
    min_candidate_skills: int = 100
    min_corpus_prompts: int = 8
    min_precision_at_1: float = 0.80
    min_precision_at_5: float = 0.90
    max_failures: int = 0
    min_top_2_margin: float = 0.0
    max_low_margin_hits: int | None = None
    allow_top1_misses: bool = True


@dataclass(frozen=True)
class GateResult:
    ok: bool
    messages: list[str]


def latest_report_json(output_dir: Path) -> Path:
    reports = sorted(output_dir.glob("routing-benchmark-*.json"))
    if not reports:
        raise FileNotFoundError(f"no routing benchmark JSON report in {output_dir}")
    return reports[-1]


def evaluate_report(report: dict[str, Any], thresholds: GateThresholds) -> GateResult:
    messages: list[str] = []
    ok = True

    candidate_skills = int(report.get("candidate_skills") or 0)
    corpus_prompts = int(report.get("corpus_prompts") or 0)
    if candidate_skills < thresholds.min_candidate_skills:
        ok = False
        messages.append(
            f"candidate_skills {candidate_skills} < required {thresholds.min_candidate_skills}"
        )
    if corpus_prompts < thresholds.min_corpus_prompts:
        ok = False
        messages.append(
            f"corpus_prompts {corpus_prompts} < required {thresholds.min_corpus_prompts}"
        )

    models = report.get("models") or []
    if not models:
        return GateResult(False, messages + ["no model metrics in report"])

    for model in models:
        model_id = str(model.get("model_id") or "<unknown>")
        if not model.get("loaded"):
            ok = False
            messages.append(f"{model_id}: model did not load: {model.get('load_error')}")
            continue
        failures = int(model.get("failures") or 0)
        p1 = float(model.get("precision_at_1") or 0.0)
        p5 = float(model.get("precision_at_5") or 0.0)
        misses = model.get("top1_misses") or []
        min_margin = float(model.get("min_top_2_margin") or 0.0)
        low_margin_hits = int(model.get("low_margin_hit_count") or len(model.get("low_margin_hits") or []))
        if failures > thresholds.max_failures:
            ok = False
            messages.append(f"{model_id}: failures {failures} > {thresholds.max_failures}")
        if p1 < thresholds.min_precision_at_1:
            ok = False
            messages.append(
                f"{model_id}: precision_at_1 {p1:.3f} < {thresholds.min_precision_at_1:.3f}"
            )
        if p5 < thresholds.min_precision_at_5:
            ok = False
            messages.append(
                f"{model_id}: precision_at_5 {p5:.3f} < {thresholds.min_precision_at_5:.3f}"
            )
        if min_margin < thresholds.min_top_2_margin:
            ok = False
            messages.append(
                f"{model_id}: min_top_2_margin {min_margin:.4f} < {thresholds.min_top_2_margin:.4f}"
            )
        if (
            thresholds.max_low_margin_hits is not None
            and low_margin_hits > thresholds.max_low_margin_hits
        ):
            ok = False
            messages.append(
                f"{model_id}: low_margin_hit_count {low_margin_hits} > {thresholds.max_low_margin_hits}"
            )
        if misses and not thresholds.allow_top1_misses:
            ok = False
            messages.append(f"{model_id}: top1_misses present ({len(misses)})")
        messages.append(
            f"{model_id}: p1={p1:.3f} p5={p5:.3f} failures={failures} "
            f"top1_misses={len(misses)} min_top_2_margin={min_margin:.4f} "
            f"low_margin_hits={low_margin_hits}"
        )
    messages.append(
        f"candidate_skills={candidate_skills} corpus_prompts={corpus_prompts} "
        f"candidate_signature={report.get('candidate_signature', '')}"
    )
    return GateResult(ok, messages)


def run_command(cmd: list[str], *, cwd: Path) -> None:
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True, timeout=30)  # timeout per ADR-278 (default - review)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the routing quality gate.")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--output", default="", help="Benchmark output directory; temp dir if omitted")
    parser.add_argument("--skip-pytest", action="store_true", help="Skip audit pytest checks")
    parser.add_argument("--skip-intent-audit", action="store_true", help="Skip advisory routing_intents audit")
    parser.add_argument("--skip-benchmark", action="store_true", help="Skip benchmark execution and evaluate --report-json")
    parser.add_argument("--report-json", default="", help="Existing benchmark JSON to evaluate")
    parser.add_argument("--min-candidate-skills", type=int, default=100)
    parser.add_argument("--min-corpus-prompts", type=int, default=8)
    parser.add_argument("--min-precision-at-1", type=float, default=0.80)
    parser.add_argument("--min-precision-at-5", type=float, default=0.90)
    parser.add_argument("--max-failures", type=int, default=0)
    parser.add_argument("--min-top-2-margin", type=float, default=0.0)
    parser.add_argument("--max-low-margin-hits", type=int, default=None)
    parser.add_argument("--fail-on-top1-misses", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    python = root / ".venv" / "bin" / "python"
    py = str(python if python.exists() else Path(sys.executable))

    if not args.skip_pytest:
        run_command(
            [
                py,
                "-m",
                "pytest",
                "tests/audit/test_skill_routing_patterns_ascii.py",
                "tests/audit/test_multilingual_corpus_schema.py",
                "-q",
            ],
            cwd=root,
        )

    if not args.skip_intent_audit:
        run_command([py, "scripts/routing_intent_audit.py", "--root", str(root), "--limit", "20"], cwd=root)

    output_dir: Path
    temp_ctx: tempfile.TemporaryDirectory[str] | None = None
    try:
        if args.report_json:
            report_path = Path(args.report_json)
        else:
            if args.output:
                output_dir = Path(args.output)
                output_dir.mkdir(parents=True, exist_ok=True)
                temp_ctx = None
            else:
                temp_ctx = tempfile.TemporaryDirectory(prefix="cos-routing-quality-gate-")
                output_dir = Path(temp_ctx.name)
            if not args.skip_benchmark:
                run_command(
                    [py, "-m", "lib.routing_benchmark", "--multilingual", "--output", str(output_dir)],
                    cwd=root,
                )
            report_path = latest_report_json(output_dir)

        report = json.loads(report_path.read_text(encoding="utf-8"))
        thresholds = GateThresholds(
            min_candidate_skills=args.min_candidate_skills,
            min_corpus_prompts=args.min_corpus_prompts,
            min_precision_at_1=args.min_precision_at_1,
            min_precision_at_5=args.min_precision_at_5,
            max_failures=args.max_failures,
            min_top_2_margin=args.min_top_2_margin,
            max_low_margin_hits=args.max_low_margin_hits,
            allow_top1_misses=not args.fail_on_top1_misses,
        )
        result = evaluate_report(report, thresholds)
        print("\n# Routing Quality Gate")
        print(f"report: {report_path}")
        for message in result.messages:
            print(f"- {message}")
        print(f"status: {'PASS' if result.ok else 'FAIL'}")
        return 0 if result.ok else 2
    finally:
        if temp_ctx is not None:
            temp_ctx.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
