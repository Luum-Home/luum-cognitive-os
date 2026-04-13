#!/usr/bin/env python3
# scope: both
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""
DEPRECATED: Use lib/pipeline_executor.py instead.

This module is superseded by pipeline_executor.py which provides:
- Declarative YAML workflow definitions (.cognitive-os/workflows/*.yaml)
- Resume/start-from support
- Phase timing and state persistence
- Dry-run mode

Migration:
  OLD: python lib/batch_runner.py add-auth --fast-forward
  NEW: python -m lib.pipeline_executor --workflow .cognitive-os/workflows/feature-pipeline.yaml --change add-auth

SDD Batch Runner — Execute multiple SDD changes sequentially.

Runs SDD pipeline phases for a list of changes provided via CLI args
or a YAML batch file. Supports fast-forward (all phases), single-phase,
continue-on-failure, dry-run, and JSON report output.

Usage:
  python lib/batch_runner.py add-auth refactor-payments --fast-forward
  python lib/batch_runner.py --batch batch.yaml --phase propose
  python lib/batch_runner.py add-auth --fast-forward --dry-run
  python lib/batch_runner.py --batch batch.yaml --json-report report.json

batch.yaml format:
  changes:
    - name: add-auth
      phases: [propose, spec, design]   # optional, overrides --phase/--fast-forward
    - name: refactor-payments
    - name: fix-cache-bug
      phases: [apply, verify]

Python 3.9+ compatible.
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Resolve lib/ directory for sibling imports
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from lib.claude_executor import ClaudeExecutor, ClaudeResult

# ---------------------------------------------------------------------------
# SDD phase constants
# ---------------------------------------------------------------------------
SDD_PHASES: List[str] = [
    "explore",
    "propose",
    "spec",
    "design",
    "tasks",
    "apply",
    "verify",
    "archive",
]

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_CYAN = "\033[36m"
_DIM = "\033[2m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"

logger = logging.getLogger("batch_runner")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ChangeSpec:
    """A single change to process in the batch."""

    name: str
    phases: Optional[List[str]] = None  # None means use global setting


@dataclass
class PhaseResult:
    """Timing and status for one phase of one change."""

    phase: str
    success: bool
    elapsed_seconds: float
    error_message: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


@dataclass
class ChangeResult:
    """Aggregate result for a single change."""

    name: str
    success: bool
    elapsed_seconds: float
    phase_results: List[PhaseResult] = field(default_factory=list)
    failed_phase: Optional[str] = None
    total_cost_usd: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "success": self.success,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "failed_phase": self.failed_phase,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "phases": [
                {
                    "phase": pr.phase,
                    "success": pr.success,
                    "elapsed_seconds": round(pr.elapsed_seconds, 2),
                    "error_message": pr.error_message,
                    "tokens_in": pr.tokens_in,
                    "tokens_out": pr.tokens_out,
                    "cost_usd": round(pr.cost_usd, 6),
                }
                for pr in self.phase_results
            ],
        }


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return "%0.1fs" % seconds
    minutes = int(seconds // 60)
    secs = seconds % 60
    if minutes < 60:
        return "%dm %0.0fs" % (minutes, secs)
    hours = minutes // 60
    mins = minutes % 60
    return "%dh %dm" % (hours, mins)


def _phase_list_display(phases: List[str]) -> str:
    """Compact display of phase list."""
    return " -> ".join(phases)


def _build_phase_prompt(phase: str, change_name: str) -> str:
    """Build the prompt for an SDD phase invocation."""
    prompts = {
        "explore": "/sdd-explore %s" % change_name,
        "propose": "Run sdd-propose for change: %s" % change_name,
        "spec": "Run sdd-spec for change: %s" % change_name,
        "design": "Run sdd-design for change: %s" % change_name,
        "tasks": "Run sdd-tasks for change: %s" % change_name,
        "apply": "Run sdd-apply for change: %s" % change_name,
        "verify": "Run sdd-verify for change: %s" % change_name,
        "archive": "Run sdd-archive for change: %s" % change_name,
    }
    if phase not in prompts:
        raise ValueError(
            "Unknown SDD phase: %s. Valid: %s" % (phase, ", ".join(SDD_PHASES))
        )
    return prompts[phase]


def _validate_phase(phase: str) -> bool:
    """Check if a phase name is valid."""
    return phase in SDD_PHASES


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------

def load_batch_yaml(path: str) -> List[ChangeSpec]:
    """Load change list from a batch YAML file.

    Expected format:
        changes:
          - name: add-auth
            phases: [propose, spec, design]
          - name: refactor-payments
    """
    if not HAS_YAML:
        print(
            "%sError: PyYAML is required for --batch. "
            "Install with: pip install pyyaml%s" % (_RED, _RESET),
            file=sys.stderr,
        )
        sys.exit(1)

    file_path = Path(path)
    if not file_path.exists():
        print(
            "%sError: Batch file not found: %s%s" % (_RED, path, _RESET),
            file=sys.stderr,
        )
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "changes" not in data:
        print(
            "%sError: Batch file must have a top-level "
            "'changes' key with a list of entries.%s" % (_RED, _RESET),
            file=sys.stderr,
        )
        sys.exit(1)

    changes: List[ChangeSpec] = []
    for entry in data["changes"]:
        if isinstance(entry, str):
            changes.append(ChangeSpec(name=entry))
        elif isinstance(entry, dict):
            name = entry.get("name", "")
            if not name:
                print(
                    "%sWarning: Skipping batch entry "
                    "without 'name': %s%s" % (_YELLOW, entry, _RESET),
                    file=sys.stderr,
                )
                continue
            phases = entry.get("phases")
            if phases is not None:
                for p in phases:
                    if not _validate_phase(p):
                        print(
                            "%sError: Invalid phase '%s' for change '%s'. "
                            "Valid phases: %s%s"
                            % (_RED, p, name, ", ".join(SDD_PHASES), _RESET),
                            file=sys.stderr,
                        )
                        sys.exit(1)
            changes.append(ChangeSpec(name=name, phases=phases))
        else:
            print(
                "%sWarning: Skipping invalid batch "
                "entry: %s%s" % (_YELLOW, entry, _RESET),
                file=sys.stderr,
            )

    if not changes:
        print(
            "%sError: No valid changes found in %s%s" % (_RED, path, _RESET),
            file=sys.stderr,
        )
        sys.exit(1)

    return changes


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def resolve_phases(
    change: ChangeSpec,
    global_phase: Optional[str],
    fast_forward: bool,
) -> List[str]:
    """Determine which phases to run for a change.

    Priority: change-level phases > --phase > --fast-forward > default (all).
    """
    if change.phases is not None:
        return change.phases

    if global_phase is not None:
        return [global_phase]

    if fast_forward:
        return list(SDD_PHASES)

    # Default: all phases
    return list(SDD_PHASES)


def run_single_change(
    executor: ClaudeExecutor,
    change: ChangeSpec,
    phases: List[str],
    index: int,
    total: int,
) -> ChangeResult:
    """Run all specified phases for a single change.

    Returns a ChangeResult with per-phase timing and cost tracking.
    """
    print("\n%s%s%s" % (_BOLD, "=" * 60, _RESET))
    print(
        "%s  [%d/%d] %s%s  %s%s%s" % (
            _BOLD, index, total, change.name, _RESET,
            _DIM, _phase_list_display(phases), _RESET,
        )
    )
    print("%s%s%s" % (_BOLD, "=" * 60, _RESET))

    change_start = time.time()
    phase_results: List[PhaseResult] = []
    failed_phase: Optional[str] = None

    for phase_idx, phase in enumerate(phases, 1):
        print(
            "  %s[%d/%d]%s %s " % (
                _DIM, phase_idx, len(phases), _RESET, phase.upper(),
            ),
            end="",
            flush=True,
        )

        prompt = _build_phase_prompt(phase, change.name)
        result: ClaudeResult = executor.run(prompt)

        pr = PhaseResult(
            phase=phase,
            success=result.success,
            elapsed_seconds=result.duration_secs,
            error_message=result.error_message[:500] if not result.success else "",
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
        )
        phase_results.append(pr)

        duration = _format_duration(result.duration_secs)
        if result.success:
            print(
                "%sOK%s %s%s%s" % (_GREEN, _RESET, _DIM, duration, _RESET)
            )
        else:
            print(
                "%sFAIL%s %s%s%s" % (_RED, _RESET, _DIM, duration, _RESET)
            )
            failed_phase = phase
            break

    elapsed = time.time() - change_start
    overall_success = all(pr.success for pr in phase_results)
    total_cost = sum(pr.cost_usd for pr in phase_results)
    total_in = sum(pr.tokens_in for pr in phase_results)
    total_out = sum(pr.tokens_out for pr in phase_results)

    status = (
        "%sOK%s" % (_GREEN, _RESET)
        if overall_success
        else "%sFAIL%s" % (_RED, _RESET)
    )
    cost_str = ""
    if total_cost > 0:
        cost_str = " %s$%.4f%s" % (_DIM, total_cost, _RESET)
    print(
        "\n  [%s] %s %s%s%s%s" % (
            status, change.name,
            _DIM, _format_duration(elapsed), _RESET,
            cost_str,
        )
    )

    return ChangeResult(
        name=change.name,
        success=overall_success,
        elapsed_seconds=elapsed,
        phase_results=phase_results,
        failed_phase=failed_phase,
        total_cost_usd=total_cost,
        total_tokens_in=total_in,
        total_tokens_out=total_out,
    )


def print_summary(
    results: List[ChangeResult],
    total_time: float,
    phases_mode: str,
) -> None:
    """Print a formatted batch summary table."""
    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    total_cost = sum(r.total_cost_usd for r in results)

    print("\n%s%s%s" % (_BOLD + _CYAN, "=" * 60, _RESET))
    print("%s  SDD BATCH SUMMARY%s" % (_BOLD + _CYAN, _RESET))
    print("%s%s%s" % (_BOLD + _CYAN, "=" * 60, _RESET))
    print(
        "  %sChanges:%s   %d total, %s%d OK%s, %s%d FAIL%s" % (
            _DIM, _RESET, len(results),
            _GREEN, succeeded, _RESET,
            _RED, failed, _RESET,
        )
    )
    print("  %sMode:%s      %s" % (_DIM, _RESET, phases_mode))
    print(
        "  %sDuration:%s  %s" % (_DIM, _RESET, _format_duration(total_time))
    )
    if total_cost > 0:
        print("  %sCost:%s      $%.4f" % (_DIM, _RESET, total_cost))

    # Per-change table
    print("  %s%s%s" % (_DIM, "-" * 56, _RESET))
    print(
        "  %s%-28s %-8s %8s %-12s%s" % (
            _DIM, "Change", "Status", "Time", "Failed Phase", _RESET,
        )
    )
    print("  %s%s%s" % (_DIM, "-" * 56, _RESET))

    for r in results:
        status = (
            "%sOK%s  " % (_GREEN, _RESET)
            if r.success
            else "%sFAIL%s" % (_RED, _RESET)
        )
        duration = _format_duration(r.elapsed_seconds)
        failed = r.failed_phase or ""
        name = r.name[:26] + ".." if len(r.name) > 28 else r.name
        print(
            "  %-28s [%s] %s%8s%s %s%s%s" % (
                name, status, _DIM, duration, _RESET,
                _YELLOW, failed, _RESET,
            )
        )

    print("  %s%s%s" % (_DIM, "-" * 56, _RESET))

    # Resume commands for failed changes
    failed_results = [r for r in results if not r.success]
    if failed_results:
        print("\n  %sResume failed changes:%s" % (_YELLOW, _RESET))
        for r in failed_results:
            phase_arg = (
                " --phase %s" % r.failed_phase
                if r.failed_phase
                else " --fast-forward"
            )
            print(
                "    python lib/batch_runner.py %s%s" % (r.name, phase_arg)
            )

    print()


def generate_json_report(
    results: List[ChangeResult],
    total_time: float,
    phases_mode: str,
    report_path: str,
) -> None:
    """Write a JSON report for CI/CD consumption."""
    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    total_cost = sum(r.total_cost_usd for r in results)

    report: Dict[str, Any] = {
        "summary": {
            "total_changes": len(results),
            "succeeded": succeeded,
            "failed": failed,
            "total_seconds": round(total_time, 2),
            "total_cost_usd": round(total_cost, 6),
            "phases_mode": phases_mode,
        },
        "changes": [r.to_dict() for r in results],
        "failed_changes": [
            {
                "name": r.name,
                "failed_phase": r.failed_phase,
                "resume_command": (
                    "python lib/batch_runner.py %s --phase %s"
                    % (r.name, r.failed_phase)
                    if r.failed_phase
                    else "python lib/batch_runner.py %s --fast-forward"
                    % r.name
                ),
            }
            for r in results
            if not r.success
        ],
    }

    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(
        "  %sJSON report written to: %s%s" % (_DIM, report_path, _RESET)
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "SDD Batch Runner - Execute multiple SDD changes sequentially"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python lib/batch_runner.py add-auth refactor-payments --fast-forward\n"
            "  python lib/batch_runner.py --batch batch.yaml --phase propose\n"
            "  python lib/batch_runner.py add-auth --fast-forward --dry-run\n"
            "  python lib/batch_runner.py --batch batch.yaml --json-report report.json\n"
        ),
    )
    parser.add_argument(
        "changes",
        nargs="*",
        help="Change names to process (kebab-case, e.g., add-auth refactor-payments)",
    )
    parser.add_argument(
        "--batch",
        metavar="FILE",
        help="Read change list from a YAML file (batch.yaml)",
    )
    parser.add_argument(
        "--phase",
        metavar="PHASE",
        help=(
            "Run a single phase for all changes. "
            "Valid: %s" % ", ".join(SDD_PHASES)
        ),
    )
    parser.add_argument(
        "--fast-forward",
        action="store_true",
        help="Run all SDD phases sequentially (explore through archive)",
    )
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Continue to next change even if one fails",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would execute without running anything",
    )
    parser.add_argument(
        "--json-report",
        metavar="PATH",
        help="Write JSON report to file for CI/CD integration",
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project directory (default: current directory)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout per phase in seconds (default: 600)",
    )
    parser.add_argument(
        "--model",
        help="Override Claude model (e.g., sonnet, opus, haiku)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output (stream Claude tool calls to console)",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # -----------------------------------------------------------------------
    # Resolve change list
    # -----------------------------------------------------------------------
    changes: List[ChangeSpec] = []

    if args.batch:
        changes = load_batch_yaml(args.batch)
    elif args.changes:
        changes = [ChangeSpec(name=c) for c in args.changes]
    else:
        parser.print_help()
        print(
            "\n%sError: Provide change names as arguments "
            "or use --batch <file>.%s" % (_RED, _RESET),
            file=sys.stderr,
        )
        return 1

    # -----------------------------------------------------------------------
    # Validate --phase
    # -----------------------------------------------------------------------
    if args.phase and not _validate_phase(args.phase):
        print(
            "%sError: Invalid phase '%s'. "
            "Valid phases: %s%s"
            % (_RED, args.phase, ", ".join(SDD_PHASES), _RESET),
            file=sys.stderr,
        )
        return 1

    if args.phase and args.fast_forward:
        print(
            "%sWarning: --phase and --fast-forward are "
            "mutually exclusive. Using --phase %s.%s"
            % (_YELLOW, args.phase, _RESET),
            file=sys.stderr,
        )
        args.fast_forward = False

    # -----------------------------------------------------------------------
    # Determine phases mode label
    # -----------------------------------------------------------------------
    if args.phase:
        phases_mode = "single phase: %s" % args.phase
    elif args.fast_forward:
        phases_mode = "fast-forward (all phases)"
    else:
        phases_mode = "fast-forward (all phases)"

    # -----------------------------------------------------------------------
    # Print banner
    # -----------------------------------------------------------------------
    print("\n%s%s%s" % (_BOLD + _CYAN, "=" * 60, _RESET))
    print("%s  SDD Batch Runner%s" % (_BOLD + _CYAN, _RESET))
    print("%s%s%s" % (_BOLD + _CYAN, "=" * 60, _RESET))
    print("  %sChanges:%s   %d" % (_DIM, _RESET, len(changes)))
    print("  %sMode:%s      %s" % (_DIM, _RESET, phases_mode))
    if args.continue_on_failure:
        print("  %sFailure:%s   continue-on-failure" % (_DIM, _RESET))
    else:
        print("  %sFailure:%s   stop on first failure" % (_DIM, _RESET))

    # Preview changes
    print("  %s%s%s" % (_DIM, "-" * 56, _RESET))
    for i, change in enumerate(changes, 1):
        phases = resolve_phases(change, args.phase, args.fast_forward)
        phases_str = _phase_list_display(phases)
        print(
            "  %d. %s  %s%s%s" % (i, change.name, _DIM, phases_str, _RESET)
        )
    print("  %s%s%s" % (_DIM, "-" * 56, _RESET))

    # -----------------------------------------------------------------------
    # Dry run
    # -----------------------------------------------------------------------
    if args.dry_run:
        print("\n  %s[DRY RUN] No changes executed.%s\n" % (_DIM, _RESET))
        return 0

    # -----------------------------------------------------------------------
    # Execute
    # -----------------------------------------------------------------------
    executor = ClaudeExecutor(
        working_dir=args.project_dir,
        default_model=args.model,
        default_timeout=args.timeout,
        verbose=args.verbose,
    )

    results: List[ChangeResult] = []
    batch_start = time.time()

    for i, change in enumerate(changes, 1):
        phases = resolve_phases(change, args.phase, args.fast_forward)
        result = run_single_change(
            executor, change, phases, i, len(changes)
        )
        results.append(result)

        if not result.success and not args.continue_on_failure:
            print(
                "\n  %sStopping batch: %s failed "
                "at phase '%s'. "
                "Use --continue-on-failure to skip.%s"
                % (_YELLOW, change.name, result.failed_phase, _RESET)
            )
            break

    total_time = time.time() - batch_start

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print_summary(results, total_time, phases_mode)

    # -----------------------------------------------------------------------
    # JSON report
    # -----------------------------------------------------------------------
    if args.json_report:
        generate_json_report(
            results, total_time, phases_mode, args.json_report
        )

    # -----------------------------------------------------------------------
    # Exit code: 0 if all succeeded, 1 if any failed
    # -----------------------------------------------------------------------
    failed_count = sum(1 for r in results if not r.success)
    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
