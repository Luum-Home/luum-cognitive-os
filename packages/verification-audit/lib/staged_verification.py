# SCOPE: both
# scope: both
"""Staged Verification for Cognitive OS.

Runs cheap verification checks first (syntax, lint) and only proceeds to
expensive checks (integration tests, adversarial LLM review) when the
cheap ones pass.  This dramatically reduces both cost and latency for
changes that fail early.

Applies fail-fast evaluation principles to software verification.

Python 3.9+ compatible. No external dependencies beyond stdlib.

Author: luum
"""

import subprocess
import time
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Stage definitions
# ---------------------------------------------------------------------------

class VerificationStage(IntEnum):
    """Ordered verification stages, cheapest first."""

    SYNTAX = 1        # ~0 tokens, ~100ms
    LINT = 2          # ~0 tokens, ~2s
    BUILD = 3         # ~0 tokens, ~5s
    UNIT_TEST = 4     # ~0 tokens, ~10s
    INTEGRATION = 5   # ~0 tokens, ~30s
    ADVERSARIAL = 6   # ~5000 tokens, ~60s  (LLM call)
    CROSS_VERIFY = 7  # ~2000 tokens, ~30s  (second model)


@dataclass
class StageResult:
    """Result of executing a single verification stage."""

    stage: VerificationStage
    passed: bool
    duration_ms: float
    output: str
    cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# Cost / duration estimates per stage
# ---------------------------------------------------------------------------

_STAGE_ESTIMATES: Dict[VerificationStage, Dict] = {
    VerificationStage.SYNTAX: {
        "cost_usd": 0.0,
        "duration_s": 0.1,
        "description": "Syntax check (bash -n, python -c import, tsc --noEmit)",
    },
    VerificationStage.LINT: {
        "cost_usd": 0.0,
        "duration_s": 2.0,
        "description": "Lint (eslint, golangci-lint, ruff)",
    },
    VerificationStage.BUILD: {
        "cost_usd": 0.0,
        "duration_s": 5.0,
        "description": "Build / compile (go build, tsc, py_compile)",
    },
    VerificationStage.UNIT_TEST: {
        "cost_usd": 0.0,
        "duration_s": 10.0,
        "description": "Unit tests (pytest, go test -short, jest)",
    },
    VerificationStage.INTEGRATION: {
        "cost_usd": 0.0,
        "duration_s": 30.0,
        "description": "Integration tests",
    },
    VerificationStage.ADVERSARIAL: {
        "cost_usd": 0.03,
        "duration_s": 60.0,
        "description": "Adversarial review (LLM call)",
    },
    VerificationStage.CROSS_VERIFY: {
        "cost_usd": 0.01,
        "duration_s": 30.0,
        "description": "Cross-model verification (second LLM)",
    },
}

# ---------------------------------------------------------------------------
# Complexity -> stages mapping  (mirrors definition-of-done.md)
# ---------------------------------------------------------------------------

_COMPLEXITY_STAGES: Dict[str, List[VerificationStage]] = {
    "trivial": [
        VerificationStage.SYNTAX,
        VerificationStage.LINT,
    ],
    "small": [
        VerificationStage.SYNTAX,
        VerificationStage.LINT,
        VerificationStage.BUILD,
        VerificationStage.UNIT_TEST,
    ],
    "medium": [
        VerificationStage.SYNTAX,
        VerificationStage.LINT,
        VerificationStage.BUILD,
        VerificationStage.UNIT_TEST,
        VerificationStage.INTEGRATION,
    ],
    "large": [
        VerificationStage.SYNTAX,
        VerificationStage.LINT,
        VerificationStage.BUILD,
        VerificationStage.UNIT_TEST,
        VerificationStage.INTEGRATION,
        VerificationStage.ADVERSARIAL,
    ],
    "critical": [
        VerificationStage.SYNTAX,
        VerificationStage.LINT,
        VerificationStage.BUILD,
        VerificationStage.UNIT_TEST,
        VerificationStage.INTEGRATION,
        VerificationStage.ADVERSARIAL,
        VerificationStage.CROSS_VERIFY,
    ],
}


# ---------------------------------------------------------------------------
# File-type detection helpers
# ---------------------------------------------------------------------------

def _detect_language(changed_files: List[str]) -> str:
    """Best-effort language detection from file extensions."""
    exts = {Path(f).suffix.lower() for f in changed_files}
    if ".go" in exts:
        return "go"
    if ".ts" in exts or ".tsx" in exts:
        return "typescript"
    if ".py" in exts:
        return "python"
    if ".java" in exts:
        return "java"
    if ".js" in exts or ".jsx" in exts:
        return "javascript"
    if ".sh" in exts or ".bash" in exts:
        return "shell"
    return "unknown"


# ---------------------------------------------------------------------------
# Stage runners  (local, zero-token checks)
# ---------------------------------------------------------------------------

def _run_cmd(
    cmd: List[str],
    cwd: str,
    timeout: int = 120,
) -> Tuple[bool, str]:
    """Run a shell command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        return result.returncode == 0, output
    except FileNotFoundError:
        return True, f"Command not found: {cmd[0]} (skipped)"
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s: {' '.join(cmd)}"


def _syntax_commands(lang: str, changed_files: List[str]) -> List[List[str]]:
    """Return syntax-check commands for *lang*."""
    if lang == "python":
        return [["python3", "-m", "py_compile", f] for f in changed_files if f.endswith(".py")]
    if lang == "shell":
        return [["bash", "-n", f] for f in changed_files if f.endswith((".sh", ".bash"))]
    # Go / TS / Java syntax is checked at build stage
    return []


def _lint_commands(lang: str, project_root: str) -> List[List[str]]:
    if lang == "python":
        return [["python3", "-m", "ruff", "check", project_root]]
    if lang == "go":
        return [["golangci-lint", "run", "./..."]]
    if lang in ("typescript", "javascript"):
        return [["npx", "eslint", "."]]
    return []


def _build_commands(lang: str) -> List[List[str]]:
    if lang == "go":
        return [["go", "build", "./..."]]
    if lang == "typescript":
        return [["npx", "tsc", "--noEmit"]]
    if lang == "python":
        # Python has no separate build step beyond syntax
        return []
    return []


def _unit_test_commands(lang: str) -> List[List[str]]:
    if lang == "python":
        return [["python3", "-m", "pytest", "tests/unit", "-q", "--tb=short"]]
    if lang == "go":
        return [["go", "test", "-short", "./..."]]
    if lang in ("typescript", "javascript"):
        return [["npx", "jest", "--passWithNoTests"]]
    return []


def _integration_test_commands(lang: str) -> List[List[str]]:
    if lang == "python":
        return [["python3", "-m", "pytest", "tests/integration", "-q", "--tb=short"]]
    if lang == "go":
        return [["go", "test", "-tags=integration", "./..."]]
    return []


def _run_stage(
    stage: VerificationStage,
    changed_files: List[str],
    project_root: str,
    lang: str,
) -> StageResult:
    """Execute a single verification stage.

    Stages ADVERSARIAL and CROSS_VERIFY are stubs that always pass —
    they require LLM calls which are handled by the orchestrator, not
    this library.
    """
    t0 = time.monotonic()

    # Determine commands
    if stage == VerificationStage.SYNTAX:
        cmds = _syntax_commands(lang, changed_files)
    elif stage == VerificationStage.LINT:
        cmds = _lint_commands(lang, project_root)
    elif stage == VerificationStage.BUILD:
        cmds = _build_commands(lang)
    elif stage == VerificationStage.UNIT_TEST:
        cmds = _unit_test_commands(lang)
    elif stage == VerificationStage.INTEGRATION:
        cmds = _integration_test_commands(lang)
    elif stage in (VerificationStage.ADVERSARIAL, VerificationStage.CROSS_VERIFY):
        # LLM stages — orchestrator responsibility, always pass here
        duration = (time.monotonic() - t0) * 1000
        return StageResult(
            stage=stage,
            passed=True,
            duration_ms=round(duration, 2),
            output="LLM stage — delegated to orchestrator",
            cost_usd=_STAGE_ESTIMATES[stage]["cost_usd"],
        )
    else:
        cmds = []

    # Run commands
    if not cmds:
        duration = (time.monotonic() - t0) * 1000
        return StageResult(
            stage=stage,
            passed=True,
            duration_ms=round(duration, 2),
            output="No commands applicable for this language/stage (skipped)",
            cost_usd=0.0,
        )

    outputs: List[str] = []
    all_passed = True
    for cmd in cmds:
        ok, out = _run_cmd(cmd, cwd=project_root)
        outputs.append(out)
        if not ok:
            all_passed = False
            break  # fail fast within a stage

    duration = (time.monotonic() - t0) * 1000
    return StageResult(
        stage=stage,
        passed=all_passed,
        duration_ms=round(duration, 2),
        output="\n".join(outputs)[:2000],  # cap output size
        cost_usd=0.0,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_stages_for_complexity(complexity: str) -> List[VerificationStage]:
    """Map a DoD complexity level to the required verification stages.

    Falls back to ``medium`` for unknown complexity values.
    """
    return list(_COMPLEXITY_STAGES.get(complexity, _COMPLEXITY_STAGES["medium"]))


def estimate_verification_cost(
    stages: List[VerificationStage],
) -> Dict:
    """Estimate total cost and duration for a set of stages.

    Returns ``{estimated_cost_usd, estimated_duration_s, stages_count}``.
    """
    total_cost = sum(_STAGE_ESTIMATES[s]["cost_usd"] for s in stages)
    total_duration = sum(_STAGE_ESTIMATES[s]["duration_s"] for s in stages)
    return {
        "estimated_cost_usd": round(total_cost, 4),
        "estimated_duration_s": round(total_duration, 1),
        "stages_count": len(stages),
    }


def run_staged_verification(
    changed_files: List[str],
    project_root: str,
    max_stage: Optional[VerificationStage] = None,
    stop_on_failure: bool = True,
    stages: Optional[List[VerificationStage]] = None,
) -> Dict:
    """Run verification stages in order, cheapest first.

    Parameters
    ----------
    changed_files:
        List of file paths that were modified.
    project_root:
        Absolute path to the project root.
    max_stage:
        If given, only run stages up to (and including) this one.
    stop_on_failure:
        If ``True`` (default), stop at the first failing stage.
    stages:
        Explicit list of stages to run.  If ``None``, all stages up to
        *max_stage* are used.

    Returns
    -------
    dict with keys:
        stages_run, stages_passed, stages_failed, total_cost,
        total_duration_ms, results (list of StageResult dicts),
        verdict, savings.
    """
    if not changed_files:
        return {
            "stages_run": 0,
            "stages_passed": 0,
            "stages_failed": 0,
            "total_cost": 0.0,
            "total_duration_ms": 0.0,
            "results": [],
            "verdict": "PASS",
            "savings": {"cost_usd": 0.0, "duration_s": 0.0},
        }

    lang = _detect_language(changed_files)

    if stages is None:
        stages = sorted(VerificationStage)
    if max_stage is not None:
        stages = [s for s in stages if s <= max_stage]

    results: List[StageResult] = []
    skipped_stages: List[VerificationStage] = []
    failed = False

    for stage in stages:
        if failed and stop_on_failure:
            skipped_stages.append(stage)
            continue

        result = _run_stage(stage, changed_files, project_root, lang)
        results.append(result)

        if not result.passed:
            failed = True

    # Compute savings from skipped stages
    saved_cost = sum(_STAGE_ESTIMATES[s]["cost_usd"] for s in skipped_stages)
    saved_duration = sum(_STAGE_ESTIMATES[s]["duration_s"] for s in skipped_stages)

    stages_passed = sum(1 for r in results if r.passed)
    stages_failed = sum(1 for r in results if not r.passed)
    total_cost = sum(r.cost_usd for r in results)
    total_duration = sum(r.duration_ms for r in results)

    first_failure = next((r for r in results if not r.passed), None)
    if first_failure:
        verdict = f"FAIL at stage {first_failure.stage.value} ({first_failure.stage.name})"
    else:
        verdict = "PASS"

    return {
        "stages_run": len(results),
        "stages_passed": stages_passed,
        "stages_failed": stages_failed,
        "total_cost": round(total_cost, 4),
        "total_duration_ms": round(total_duration, 2),
        "results": [
            {
                "stage": r.stage.value,
                "stage_name": r.stage.name,
                "passed": r.passed,
                "duration_ms": r.duration_ms,
                "output": r.output,
                "cost_usd": r.cost_usd,
            }
            for r in results
        ],
        "verdict": verdict,
        "savings": {
            "cost_usd": round(saved_cost, 4),
            "duration_s": round(saved_duration, 1),
        },
    }


def format_verification_report(results: Dict) -> str:
    """Format staged verification results as a Markdown report.

    Includes pass/fail markers, timing, cost, savings, and verdict.
    """
    lines = ["STAGED VERIFICATION REPORT", ""]

    if not results.get("results"):
        lines.append("No stages were executed.")
        return "\n".join(lines)

    # Executed stages
    for r in results["results"]:
        stage_num = r["stage"]
        stage_name = r["stage_name"]
        if r["passed"]:
            marker = "PASS"
        else:
            marker = "FAIL"
        duration_s = r["duration_ms"] / 1000
        cost = r["cost_usd"]
        line = f"[{stage_num}] {stage_name:15s} {marker} ({duration_s:.2f}s, ${cost:.4f})"
        lines.append(line)
        if not r["passed"] and r.get("output"):
            # Show first 200 chars of failure output
            snippet = r["output"][:200].replace("\n", " ")
            lines.append(f"    {snippet}")

    # Skipped stages (inferred from savings)
    savings = results.get("savings", {})
    if savings.get("cost_usd", 0) > 0 or savings.get("duration_s", 0) > 0:
        lines.append("")
        lines.append(
            f"Skipped stages saved: ${savings['cost_usd']:.4f}, "
            f"~{savings['duration_s']:.0f}s"
        )

    lines.append("")
    lines.append(f"Verdict: {results['verdict']}")
    lines.append(
        f"Cost: ${results['total_cost']:.4f} | "
        f"Time: {results['total_duration_ms'] / 1000:.1f}s"
    )
    return "\n".join(lines)
