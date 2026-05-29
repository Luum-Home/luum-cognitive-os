# SCOPE: both
"""Benchmark-bound self-improvement primitives for Cognitive OS.

This module implements a SIA-inspired but COS-governed loop: run measurable
benchmark generations, record artifacts, produce feedback proposals, and keep
mutation behind an explicit review gate.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "cos-improve.v1"
RUNS_DIR = Path(".cognitive-os") / "improvement-runs"
REQUIRED_TASK_FILES = ("task.md", "evaluate.py", "expected_metrics.yaml", "anti-overfit.md")
REQUIRED_TASK_DIRS = ("public", "private")


@dataclass(frozen=True)
class BenchmarkTask:
    """Validated benchmark task contract."""

    root: Path
    task_md: Path
    evaluate_py: Path
    public_dir: Path
    private_dir: Path
    expected_metrics: dict[str, Any]
    anti_overfit_md: Path


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_task(task_dir: Path) -> BenchmarkTask:
    """Load and validate a benchmark task directory."""

    task_dir = task_dir.resolve()
    missing: list[str] = []
    for name in REQUIRED_TASK_FILES:
        if not (task_dir / name).is_file():
            missing.append(name)
    for name in REQUIRED_TASK_DIRS:
        if not (task_dir / name).is_dir():
            missing.append(f"{name}/")
    if missing:
        raise ValueError(f"benchmark task contract missing: {', '.join(sorted(missing))}")
    metrics = yaml.safe_load((task_dir / "expected_metrics.yaml").read_text(encoding="utf-8")) or {}
    if not isinstance(metrics, dict) or not metrics.get("metrics"):
        raise ValueError("expected_metrics.yaml must define a metrics mapping")
    return BenchmarkTask(
        root=task_dir,
        task_md=task_dir / "task.md",
        evaluate_py=task_dir / "evaluate.py",
        public_dir=task_dir / "public",
        private_dir=task_dir / "private",
        expected_metrics=metrics,
        anti_overfit_md=task_dir / "anti-overfit.md",
    )


def default_run_id(task_dir: Path) -> str:
    return f"{task_dir.name}-{utc_stamp()}"


def run_root(project_root: Path, run_id: str) -> Path:
    return project_root.resolve() / RUNS_DIR / run_id


def _copy_initial_target(task: BenchmarkTask, target_dir: Path) -> None:
    source = task.public_dir / "baseline_target"
    if source.is_dir():
        shutil.copytree(str(source), str(target_dir), dirs_exist_ok=True)
    else:
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "TARGET.md").write_text(
            "# Baseline target\n\nNo baseline target was provided; this generation records benchmark context only.\n",
            encoding="utf-8",
        )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def _run_evaluator(task: BenchmarkTask, target_dir: Path, output_path: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(task.evaluate_py),
        "--target",
        str(target_dir),
        "--public",
        str(task.public_dir),
        "--private",
        str(task.private_dir),
        "--output",
        str(output_path),
    ]
    proc = subprocess.run(cmd, cwd=task.root, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"benchmark evaluator failed with {proc.returncode}: {proc.stderr or proc.stdout}")
    if not output_path.exists():
        raise RuntimeError("benchmark evaluator did not write evaluation.json")
    return json.loads(output_path.read_text(encoding="utf-8"))


def _metric_passes(evaluation: dict[str, Any]) -> bool:
    metrics = evaluation.get("metrics", {})
    checks = evaluation.get("checks", {})
    if isinstance(checks, dict) and "passed" in checks:
        return bool(checks["passed"])
    return bool(metrics) and all(bool(value) for value in metrics.values() if isinstance(value, bool))


def run_improvement_loop(project_root: Path, task_dir: Path, *, run_id: str | None = None, max_gen: int = 1) -> dict[str, Any]:
    """Run a bounded benchmark loop and write generation artifacts."""

    if max_gen < 1:
        raise ValueError("max_gen must be >= 1")
    project_root = project_root.resolve()
    task = load_task(task_dir)
    rid = run_id or default_run_id(task.root)
    destination = run_root(project_root, rid)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "task_contract.json").write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "task_dir": str(task.root),
                "required_files": list(REQUIRED_TASK_FILES),
                "required_dirs": list(REQUIRED_TASK_DIRS),
                "expected_metrics": task.expected_metrics,
                "anti_overfit": task.anti_overfit_md.read_text(encoding="utf-8"),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    generations: list[dict[str, Any]] = []
    for gen in range(1, max_gen + 1):
        gen_dir = destination / f"gen_{gen}"
        target_dir = gen_dir / "target"
        gen_dir.mkdir(parents=True, exist_ok=True)
        if gen == 1:
            _copy_initial_target(task, target_dir)
        else:
            previous = destination / f"gen_{gen - 1}" / "target"
            shutil.copytree(str(previous), str(target_dir), dirs_exist_ok=True)
        eval_path = gen_dir / "evaluation.json"
        events = [
            {"event": "generation_started", "generation": gen, "timestamp": utc_stamp(), "target": str(target_dir)},
            {"event": "evaluation_started", "generation": gen, "timestamp": utc_stamp(), "evaluate_py": str(task.evaluate_py)},
        ]
        evaluation = _run_evaluator(task, target_dir, eval_path)
        events.append(
            {
                "event": "evaluation_completed",
                "generation": gen,
                "timestamp": utc_stamp(),
                "passed": _metric_passes(evaluation),
                "evaluation": str(eval_path),
            }
        )
        _write_jsonl(gen_dir / "agent_execution.jsonl", events)
        (gen_dir / "improvement.md").write_text(render_generation_improvement(task, gen, evaluation), encoding="utf-8")
        (gen_dir / "patch.diff").write_text("", encoding="utf-8")
        generations.append({"generation": gen, "dir": str(gen_dir), "evaluation": evaluation})

    summary = {
        "schema_version": SCHEMA_VERSION,
        "run_id": rid,
        "task_dir": str(task.root),
        "run_dir": str(destination),
        "max_gen": max_gen,
        "generations": [
            {
                "generation": row["generation"],
                "dir": row["dir"],
                "passed": _metric_passes(row["evaluation"]),
                "metrics": row["evaluation"].get("metrics", {}),
            }
            for row in generations
        ],
    }
    (destination / "run_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def render_generation_improvement(task: BenchmarkTask, generation: int, evaluation: dict[str, Any]) -> str:
    status = "passed" if _metric_passes(evaluation) else "needs-feedback"
    return "\n".join(
        [
            f"# Generation {generation} Improvement Rationale",
            "",
            f"Task: `{task.root}`",
            f"Status: `{status}`",
            "",
            "## Metrics",
            "",
            "```json",
            json.dumps(evaluation.get("metrics", {}), indent=2, sort_keys=True),
            "```",
            "",
            "## Mutation Boundary",
            "",
            "This generation does not auto-apply changes. Use `cos improve feedback` to produce gated proposals.",
            "",
        ]
    )


def latest_generation_dir(run_dir: Path) -> Path:
    candidates = sorted(
        [path for path in run_dir.glob("gen_*") if path.is_dir()],
        key=lambda path: int(path.name.split("_", 1)[1]) if path.name.split("_", 1)[1].isdigit() else -1,
    )
    if not candidates:
        raise ValueError(f"no generation artifacts found in {run_dir}")
    return candidates[-1]


def build_feedback(project_root: Path, run_id: str, *, generation: int | None = None) -> dict[str, Any]:
    """Build propose-only feedback from execution logs and evaluation results."""

    rr = run_root(project_root, run_id)
    gen_dir = rr / f"gen_{generation}" if generation else latest_generation_dir(rr)
    evaluation = json.loads((gen_dir / "evaluation.json").read_text(encoding="utf-8"))
    events = [json.loads(line) for line in (gen_dir / "agent_execution.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    passed = _metric_passes(evaluation)
    proposals: list[dict[str, Any]] = []
    if not passed:
        proposals.append(
            {
                "target": "skill|hook|rule|agent",
                "title": "Improve target behavior against benchmark failures",
                "rationale": "Evaluation did not meet expected metrics; inspect failure_cases before editing runtime primitives.",
                "allowed_paths": ["skills/", "hooks/", "rules/", "agents/", "tests/"],
                "required_gate": "human_review_plus_targeted_tests",
                "applied": False,
            }
        )
    feedback = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "generation": gen_dir.name,
        "passed": passed,
        "evaluation": evaluation,
        "event_count": len(events),
        "proposals": proposals,
        "gate": {"auto_apply": False, "human_approval_required": True},
    }
    (gen_dir / "feedback.json").write_text(json.dumps(feedback, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (gen_dir / "feedback.md").write_text(render_feedback_markdown(feedback), encoding="utf-8")
    return feedback


def render_feedback_markdown(feedback: dict[str, Any]) -> str:
    lines = [
        f"# Feedback for {feedback['run_id']} / {feedback['generation']}",
        "",
        f"Passed: `{str(feedback['passed']).lower()}`",
        "",
        "## Gate",
        "",
        "- Auto-apply: `false`",
        "- Human approval required: `true`",
        "",
        "## Proposals",
        "",
    ]
    if not feedback["proposals"]:
        lines.append("No runtime change proposed; benchmark passed.")
    for proposal in feedback["proposals"]:
        lines.extend(
            [
                f"### {proposal['title']}",
                "",
                proposal["rationale"],
                "",
                f"Required gate: `{proposal['required_gate']}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def build_context(project_root: Path, run_id: str) -> str:
    """Render a context.md-style packet integrated with run artifacts and reports."""

    rr = run_root(project_root, run_id)
    reports_dir = project_root / ".cognitive-os" / "reports"
    reports = sorted(reports_dir.glob("**/*"), key=lambda path: path.stat().st_mtime, reverse=True)[:10] if reports_dir.exists() else []
    summary_path = rr / "run_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    lines = [
        f"# Improvement Context — {run_id}",
        "",
        "## Run Summary",
        "",
        "```json",
        json.dumps(summary, indent=2, sort_keys=True),
        "```",
        "",
        "## Engram Integration",
        "",
        "Use Engram memory search/context tools before proposing changes; cite relevant prior decisions in feedback.",
        "",
        "## Local Reports",
        "",
    ]
    if reports:
        for report in reports:
            if report.is_file():
                lines.append(f"- `{report.relative_to(project_root)}`")
    else:
        lines.append("- No `.cognitive-os/reports` files found.")
    lines.append("")
    rendered = "\n".join(lines)
    (rr / "context.md").write_text(rendered, encoding="utf-8")
    return rendered
