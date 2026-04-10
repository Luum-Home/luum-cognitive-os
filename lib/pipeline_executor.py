"""Pipeline Executor — workflow YAML to execution engine.

Reads a workflow YAML from ``.cognitive-os/workflows/``, resolves variable
substitutions, and dispatches each step to the appropriate executor:

- ``agent``: ClaudeExecutor.slash() with the skill command
- ``script``: subprocess.run with shell=True
- ``gate``: evaluate a boolean condition against accumulated step state

Tracks state via SDDState (atomic save after each step).
Records timing via PhaseTimer and prints a summary table on completion.
Supports ``--dry-run``, ``--resume``, and ``--start-from <phase>``.

Usage::

    python3 -m lib.pipeline_executor \\
        --workflow .cognitive-os/workflows/feature-pipeline.yaml \\
        --change my-feature [--dry-run] [--resume] [--start-from apply]

Python 3.9+ compatible.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Try to import yaml; fall back to a minimal subset parser
# ---------------------------------------------------------------------------
try:
    import yaml  # type: ignore

    def _load_yaml(text: str) -> Any:
        return yaml.safe_load(text)

except ImportError:  # pragma: no cover
    def _load_yaml(text: str) -> Any:  # type: ignore[misc]
        raise RuntimeError(
            "PyYAML is required: pip install pyyaml"
        )

from lib.claude_executor import ClaudeExecutor, ClaudeResult

# phase_timing and sdd_resume stubs in lib/ are self-referential redirects.
# Attempt to load from the sdd-compound package first; fall back to stdlib-only
# inline implementations so the executor is usable even without the package.
try:
    import importlib.util as _ilu
    import os as _os

    def _load_from_package(rel: str) -> Any:
        base = _os.path.join(_os.path.dirname(__file__), "..", "packages", "sdd-compound")
        full = _os.path.abspath(_os.path.join(base, rel))
        spec = _ilu.spec_from_file_location("_pkg_mod", full)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load {full}")
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod

    _pt = _load_from_package("lib/phase_timing.py")
    PhaseTimer = _pt.PhaseTimer  # type: ignore[attr-defined]
    format_timing_table = _pt.format_timing_table  # type: ignore[attr-defined]
    append_timing_jsonl = _pt.append_timing_jsonl  # type: ignore[attr-defined]
    _resume_mod = _load_from_package("lib/sdd_resume.py")
    SDDState = _resume_mod.SDDState  # type: ignore[attr-defined]

    _HAS_SDD_MODULES = True
except Exception:  # pragma: no cover
    _HAS_SDD_MODULES = False
    # Inline minimal stubs so the module is importable and dry-run works.

    class PhaseTimer:  # type: ignore[no-redef]
        """Minimal fallback PhaseTimer."""

        def __init__(self, phase: str, change_name: str = "", model: Optional[str] = None):
            self.phase = phase
            self.change_name = change_name
            self._start = 0.0
            self.record = None

        def __enter__(self) -> "PhaseTimer":
            self._start = time.monotonic()
            return self

        def __exit__(self, *_: Any) -> None:
            self.duration_secs = round(time.monotonic() - self._start, 2)

        @property
        def duration_secs(self) -> float:
            return round(time.monotonic() - self._start, 2) if self._start else 0.0

        @duration_secs.setter
        def duration_secs(self, v: float) -> None:
            self._duration = v

    def format_timing_table(timings: Dict[str, float], models: Optional[Dict[str, str]] = None) -> str:  # type: ignore[misc]
        lines = [f"{'Phase':<20} {'Duration':>10}", "-" * 32]
        total = 0.0
        for phase, secs in timings.items():
            lines.append(f"{phase:<20} {secs:>9.1f}s")
            total += secs
        lines += ["-" * 32, f"{'TOTAL':<20} {total:>9.1f}s"]
        return "\n".join(lines)

    def append_timing_jsonl(filepath: str, phase: str, duration_secs: float, change_name: str = "", **_kw: Any) -> Dict:  # type: ignore[misc]
        record = {"phase": phase, "duration_secs": round(duration_secs, 2), "change_name": change_name}
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        return record

    class SDDState:  # type: ignore[no-redef]
        pass


# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _iso_now() -> str:
    return time.strftime(_ISO_FMT, time.gmtime())


# ---------------------------------------------------------------------------
# Variable substitution
# ---------------------------------------------------------------------------

_VAR_RE = re.compile(r"\$\{([^}]+)\}")
_BARE_VAR_RE = re.compile(r"\$([A-Z_][A-Z0-9_]*)")


def _resolve_vars(text: str, context: Dict[str, str]) -> str:
    """Substitute ``${VAR}`` and ``$VAR`` patterns from *context* and env.

    Shell default syntax ``${VAR:-default}`` is supported.
    Unresolved variables are left as-is.
    """

    def _replace_braced(m: re.Match) -> str:  # type: ignore[type-arg]
        expr = m.group(1)
        if ":-" in expr:
            var, default = expr.split(":-", 1)
            return context.get(var) or os.environ.get(var) or default
        return context.get(expr) or os.environ.get(expr) or m.group(0)

    def _replace_bare(m: re.Match) -> str:  # type: ignore[type-arg]
        var = m.group(1)
        return context.get(var) or os.environ.get(var) or m.group(0)

    text = _VAR_RE.sub(_replace_braced, text)
    text = _BARE_VAR_RE.sub(_replace_bare, text)
    return text


# ---------------------------------------------------------------------------
# Pipeline step dataclass
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    """Result from executing a single pipeline step."""

    name: str
    step_type: str
    status: str          # "PASS" | "FAIL" | "SKIP" | "ESCALATE"
    duration_secs: float = 0.0
    output: str = ""
    exit_code: int = 0
    retry_count: int = 0


@dataclass
class PipelineState:
    """Runtime state accumulated across all steps in a pipeline run."""

    change_name: str
    workflow_name: str
    steps_completed: List[str] = field(default_factory=list)
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    timings: Dict[str, float] = field(default_factory=dict)
    vars: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=_iso_now)
    updated_at: str = field(default_factory=_iso_now)

    # Path to a sdd_resume state file (JSON) for persistence
    _state_file: Optional[str] = field(default=None, repr=False)

    def mark_completed(self, step_name: str, result: StepResult) -> None:
        self.steps_completed.append(step_name)
        self.step_results[step_name] = result
        self.timings[step_name] = result.duration_secs
        self.updated_at = _iso_now()

    def save(self) -> None:
        """Persist state to a JSON file for resume support."""
        if not self._state_file:
            return
        os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
        data = {
            "change_name": self.change_name,
            "workflow_name": self.workflow_name,
            "steps_completed": self.steps_completed,
            "timings": self.timings,
            "vars": self.vars,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        with open(self._state_file, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    @classmethod
    def load(
        cls,
        state_file: str,
        change_name: str,
        workflow_name: str = "",
        *,
        state_dir: Optional[str] = None,
    ) -> "PipelineState":
        """Load persisted state or return a fresh instance.

        Can be called in two ways:

        1. Legacy: ``load(state_file_path, change_name, workflow_name)``
        2. Convenience: ``load(change_name, workflow_name, state_dir=path)``
           When *state_dir* is given the first arg is treated as *change_name*
           and the state file path is derived as ``state_dir/change_name.json``.
        """
        if state_dir is not None:
            # Convenience form: first arg is change_name, second is workflow_name
            actual_change = state_file  # first arg is actually change_name here
            actual_workflow = change_name  # second arg is workflow_name
            resolved_file = os.path.join(str(state_dir), f"{actual_change}.json")
            return cls.load(resolved_file, actual_change, actual_workflow)

        if os.path.isfile(state_file):
            try:
                with open(state_file, encoding="utf-8") as fh:
                    data = json.load(fh)
                obj = cls(
                    change_name=data.get("change_name", change_name),
                    workflow_name=data.get("workflow_name", workflow_name),
                    steps_completed=data.get("steps_completed", []),
                    timings=data.get("timings", {}),
                    vars=data.get("vars", {}),
                    created_at=data.get("created_at", _iso_now()),
                    updated_at=data.get("updated_at", _iso_now()),
                )
                obj._state_file = state_file
                return obj
            except (json.JSONDecodeError, KeyError):
                pass
        obj = cls(change_name=change_name, workflow_name=workflow_name)
        obj._state_file = state_file
        return obj


# ---------------------------------------------------------------------------
# Gate evaluation
# ---------------------------------------------------------------------------

def _evaluate_gate(condition: str, state: PipelineState) -> bool:
    """Evaluate a simple gate condition against accumulated step results.

    Supported patterns (case-insensitive comparison):

    - ``<step>.status == VALUE``   → checks StepResult.status
    - ``<step>.status != VALUE``   → negated check
    - ``<field>``                  → checks if state.vars[field] is truthy

    Returns ``True`` when the gate passes (pipeline should continue).
    """
    condition = condition.strip()

    # Pattern: "step.status == VALUE" or "step.status != VALUE"
    m = re.match(
        r"^(\w[\w.-]*)\s*(==|!=)\s*(.+)$",
        condition,
        re.IGNORECASE,
    )
    if m:
        lhs, op, rhs = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        rhs = rhs.strip("\"'")

        # Support "step.status" lookups
        if "." in lhs:
            parts = lhs.split(".", 1)
            step_name, attr = parts[0], parts[1]
            result = state.step_results.get(step_name)
            if result is None:
                # Step not run — treat as FAIL for safety
                actual = "NOT_RUN"
            else:
                actual = getattr(result, attr, "")
        else:
            actual = state.vars.get(lhs, "")

        actual_str = str(actual).strip()
        rhs_str = str(rhs).strip()

        if op == "==":
            return actual_str.upper() == rhs_str.upper()
        else:  # !=
            return actual_str.upper() != rhs_str.upper()

    # Simple truthy check: variable or step name
    if condition in state.step_results:
        return state.step_results[condition].status == "PASS"
    return bool(state.vars.get(condition))


# ---------------------------------------------------------------------------
# Step dispatchers
# ---------------------------------------------------------------------------

def _run_agent_step(
    step: Dict[str, Any],
    state: PipelineState,
    executor: ClaudeExecutor,
    dry_run: bool,
) -> StepResult:
    """Dispatch an ``agent`` step via ClaudeExecutor.slash()."""
    skill = step.get("skill", "")
    model = step.get("model", "sonnet")
    args = _resolve_vars(step.get("args", ""), state.vars)

    # Build a context hint from inputs
    inputs = step.get("inputs", [])
    if inputs:
        input_note = f"[inputs: {', '.join(inputs)}] "
        args = (input_note + args).strip()

    if args:
        # Inject change name
        if state.change_name and "$CHANGE" not in args and state.change_name not in args:
            args = f"{args} change={state.change_name}"
    else:
        if state.change_name:
            args = f"change={state.change_name}"

    if dry_run:
        print(f"    [DRY-RUN] agent: /{skill} {args} (model={model})")
        return StepResult(name=step["name"], step_type="agent", status="PASS", output="[dry-run]")

    print(f"    Launching /{skill} (model={model}) ...")
    start = time.monotonic()
    result: ClaudeResult = executor.slash(skill, args=args, model=model)
    duration = round(time.monotonic() - start, 2)

    status = "PASS" if result.success else "FAIL"
    return StepResult(
        name=step["name"],
        step_type="agent",
        status=status,
        duration_secs=duration,
        output=result.result_text[:2000],
        exit_code=0 if result.success else 1,
    )


def _run_script_step(
    step: Dict[str, Any],
    state: PipelineState,
    dry_run: bool,
) -> StepResult:
    """Dispatch a ``script`` step via subprocess.run."""
    raw_cmd = step.get("command", "")
    cmd = _resolve_vars(raw_cmd, state.vars)

    if dry_run:
        print(f"    [DRY-RUN] script: {cmd}")
        return StepResult(name=step["name"], step_type="script", status="PASS", output="[dry-run]")

    print(f"    Running: {cmd}")
    start = time.monotonic()
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    duration = round(time.monotonic() - start, 2)

    combined = (proc.stdout or "") + (proc.stderr or "")
    status = "PASS" if proc.returncode == 0 else "FAIL"
    return StepResult(
        name=step["name"],
        step_type="script",
        status=status,
        duration_secs=duration,
        output=combined[:2000],
        exit_code=proc.returncode,
    )


def _run_gate_step(
    step: Dict[str, Any],
    state: PipelineState,
    dry_run: bool,
) -> StepResult:
    """Evaluate a ``gate`` condition."""
    condition = step.get("condition", "true")

    if dry_run:
        print(f"    [DRY-RUN] gate: {condition}")
        return StepResult(name=step["name"], step_type="gate", status="PASS", output="[dry-run]")

    passed = _evaluate_gate(condition, state)
    status = "PASS" if passed else "FAIL"
    return StepResult(
        name=step["name"],
        step_type="gate",
        status=status,
        output=f"condition={condition!r} evaluated to {passed}",
    )


# ---------------------------------------------------------------------------
# Failure policy helpers
# ---------------------------------------------------------------------------

_ANSI_RED = "\033[31m"
_ANSI_GREEN = "\033[32m"
_ANSI_YELLOW = "\033[33m"
_ANSI_CYAN = "\033[36m"
_ANSI_RESET = "\033[0m"
_ANSI_BOLD = "\033[1m"


def _cprint(msg: str, color: str = "") -> None:
    print(f"{color}{msg}{_ANSI_RESET}" if color else msg)


def _resume_command(workflow_path: str, change_name: str) -> str:
    return (
        f"python3 -m lib.pipeline_executor "
        f"--workflow {workflow_path} "
        f"--change {change_name} "
        f"--resume"
    )


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------

class PipelineExecutor:
    """Execute a workflow YAML pipeline end-to-end.

    Args:
        workflow_path: Path to the YAML file.
        change_name: Name of the change/feature being worked on.
        dry_run: Print plan without executing.
        resume: Skip steps already completed (loaded from state file).
        start_from: Skip all steps before this step name.
        extra_vars: Additional variable substitutions (on top of env).
        working_dir: Working directory for ClaudeExecutor and scripts.
        state_dir: Directory to persist per-run state files.
        timings_jsonl: Path to JSONL file for timing metrics.
    """

    def __init__(
        self,
        workflow_path: str,
        change_name: str,
        dry_run: bool = False,
        resume: bool = False,
        start_from: Optional[str] = None,
        extra_vars: Optional[Dict[str, str]] = None,
        working_dir: Optional[str] = None,
        state_dir: str = ".cognitive-os/pipeline-state",
        timings_jsonl: str = ".cognitive-os/metrics/sdd-timings.jsonl",
    ):
        self.workflow_path = workflow_path
        self.change_name = change_name
        self.dry_run = dry_run
        self.do_resume = resume
        self.start_from = start_from
        self.extra_vars = extra_vars or {}
        self.working_dir = working_dir or os.getcwd()
        self.state_dir = state_dir
        self.timings_jsonl = timings_jsonl

        self._workflow: Dict[str, Any] = {}
        self._executor: Optional[ClaudeExecutor] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> bool:
        """Load the workflow and execute all steps.

        Returns:
            ``True`` if all steps passed, ``False`` on failure.
        """
        self._workflow = self._load_workflow()
        workflow_name = self._workflow.get("name", os.path.basename(self.workflow_path))

        _cprint(
            f"\n{_ANSI_BOLD}Pipeline: {workflow_name}  |  Change: {self.change_name}{_ANSI_RESET}"
        )
        if self.dry_run:
            _cprint("  [DRY-RUN mode — no actions will be executed]\n", _ANSI_YELLOW)

        # Build variable context
        base_vars: Dict[str, str] = {
            "CHANGE": self.change_name,
            "WORKFLOW": workflow_name,
        }
        base_vars.update(self.extra_vars)

        # Load or create state
        state_file = os.path.join(self.state_dir, f"{self.change_name}.json")
        state = PipelineState.load(state_file, self.change_name, workflow_name)
        state.vars.update(base_vars)

        if not self.dry_run:
            self._executor = ClaudeExecutor(
                working_dir=self.working_dir,
                verbose=False,
            )

        steps: List[Dict[str, Any]] = self._workflow.get("steps", [])
        if not steps:
            _cprint("  No steps defined in workflow.", _ANSI_YELLOW)
            return True

        # Print plan header
        _cprint(f"\n  Steps ({len(steps)}):")
        for s in steps:
            marker = "  "
            if s["name"] in state.steps_completed:
                marker = _ANSI_GREEN + "✓ " + _ANSI_RESET
            print(f"    {marker}{s['name']}  [{s.get('type', '?')}]")
        print()

        # Fast-forward to start_from
        if self.start_from:
            names = [s["name"] for s in steps]
            if self.start_from not in names:
                _cprint(f"  ERROR: --start-from '{self.start_from}' not found in workflow.", _ANSI_RED)
                return False

        overall_start = time.monotonic()
        success = self._execute_steps(steps, state)
        total_secs = round(time.monotonic() - overall_start, 2)

        self._print_summary(state, total_secs)
        return success

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_workflow(self) -> Dict[str, Any]:
        with open(self.workflow_path, encoding="utf-8") as fh:
            data = _load_yaml(fh.read())
        if not isinstance(data, dict):
            raise ValueError(f"Invalid workflow YAML: {self.workflow_path}")
        return data

    def _execute_steps(
        self,
        steps: List[Dict[str, Any]],
        state: PipelineState,
    ) -> bool:
        """Iterate over steps and execute each one, honouring resume/start-from."""
        skip_until: Optional[str] = self.start_from
        skipping_prefix = skip_until is not None

        for step in steps:
            name = step["name"]
            step_type = step.get("type", "agent")
            on_failure = step.get("on_failure", "abort")
            max_retries = int(step.get("max_retries", 1))

            # Skip until start_from is reached
            if skipping_prefix:
                if name == skip_until:
                    skipping_prefix = False  # start executing from here
                else:
                    _cprint(f"  -- {name}  [skipped: before start-from]", _ANSI_CYAN)
                    continue

            # Resume: skip already completed
            if self.do_resume and name in state.steps_completed:
                _cprint(f"  -- {name}  [already completed, resuming]", _ANSI_CYAN)
                continue

            _cprint(f"\n  >> {name}  [{step_type}]", _ANSI_BOLD)

            # Execute with retry loop
            attempt = 0
            result: Optional[StepResult] = None
            while attempt <= max_retries:
                if attempt > 0:
                    _cprint(f"     Retry {attempt}/{max_retries} ...", _ANSI_YELLOW)

                with PhaseTimer(name, change_name=self.change_name) as timer:
                    result = self._dispatch_step(step, state)

                result.duration_secs = timer.duration_secs
                result.retry_count = attempt

                if result.status == "PASS":
                    break

                if on_failure == "retry" and attempt < max_retries:
                    attempt += 1
                    continue

                break  # non-retry policy or exhausted retries

            assert result is not None  # always assigned above
            state.mark_completed(name, result)
            state.save()

            # Persist timing
            if not self.dry_run:
                try:
                    append_timing_jsonl(
                        self.timings_jsonl,
                        phase=name,
                        duration_secs=result.duration_secs,
                        change_name=self.change_name,
                    )
                except OSError:
                    pass  # non-fatal

            # Handle outcome
            if result.status == "PASS":
                _cprint(f"     PASS ({result.duration_secs:.1f}s)", _ANSI_GREEN)
            elif result.status == "SKIP":
                _cprint(f"     SKIP", _ANSI_YELLOW)
            else:
                _cprint(f"     FAIL ({result.duration_secs:.1f}s)", _ANSI_RED)
                if result.output:
                    _cprint(f"     Output: {result.output[:400]}")

                if on_failure == "abort":
                    _cprint("\n  Pipeline aborted.", _ANSI_RED)
                    _cprint(
                        f"  Resume with: {_resume_command(self.workflow_path, self.change_name)}",
                        _ANSI_CYAN,
                    )
                    return False

                elif on_failure == "escalate":
                    _cprint("\n  Escalating: human intervention required.", _ANSI_RED)
                    _cprint(f"  Failed step: {name}")
                    _cprint(
                        f"  Resume with: {_resume_command(self.workflow_path, self.change_name)}",
                        _ANSI_CYAN,
                    )
                    return False

                elif on_failure == "skip":
                    _cprint("     Skipping (on_failure=skip).", _ANSI_YELLOW)
                    result.status = "SKIP"

                # "retry" exhausted falls through to abort
                elif on_failure == "retry":
                    _cprint(f"\n  Max retries ({max_retries}) exhausted for {name}.", _ANSI_RED)
                    _cprint(
                        f"  Resume with: {_resume_command(self.workflow_path, self.change_name)}",
                        _ANSI_CYAN,
                    )
                    return False

        return True

    def _dispatch_step(
        self,
        step: Dict[str, Any],
        state: PipelineState,
    ) -> StepResult:
        """Route a step to the correct executor."""
        step_type = step.get("type", "agent")

        if step_type == "agent":
            assert self._executor is not None or self.dry_run
            return _run_agent_step(step, state, self._executor, self.dry_run)  # type: ignore[arg-type]

        elif step_type == "script":
            return _run_script_step(step, state, self.dry_run)

        elif step_type == "gate":
            return _run_gate_step(step, state, self.dry_run)

        else:
            return StepResult(
                name=step["name"],
                step_type=step_type,
                status="FAIL",
                output=f"Unknown step type: {step_type!r}",
            )

    def _print_summary(self, state: PipelineState, total_secs: float) -> None:
        """Print timing summary table and overall status."""
        print()
        _cprint("=" * 60, _ANSI_BOLD)
        _cprint("  Pipeline Summary", _ANSI_BOLD)
        _cprint("=" * 60, _ANSI_BOLD)

        if state.timings:
            table = format_timing_table(state.timings)
            for line in table.splitlines():
                print("  " + line)

        passed = [n for n, r in state.step_results.items() if r.status == "PASS"]
        failed = [n for n, r in state.step_results.items() if r.status == "FAIL"]
        skipped = [n for n, r in state.step_results.items() if r.status == "SKIP"]

        print()
        _cprint(f"  Steps passed : {len(passed)}", _ANSI_GREEN)
        if failed:
            _cprint(f"  Steps failed : {len(failed)}  ({', '.join(failed)})", _ANSI_RED)
        if skipped:
            _cprint(f"  Steps skipped: {len(skipped)}  ({', '.join(skipped)})", _ANSI_YELLOW)
        _cprint(f"  Total time   : {total_secs:.1f}s")
        print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python3 -m lib.pipeline_executor",
        description="Execute a COS workflow YAML pipeline.",
    )
    parser.add_argument(
        "--workflow",
        required=True,
        help="Path to the workflow YAML file.",
    )
    parser.add_argument(
        "--change",
        required=True,
        help="Name of the change/feature being worked on.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print the plan without executing any steps.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Skip steps already marked completed in persisted state.",
    )
    parser.add_argument(
        "--start-from",
        metavar="STEP",
        default=None,
        help="Skip all steps before this step name.",
    )
    parser.add_argument(
        "--var",
        action="append",
        metavar="KEY=VALUE",
        default=[],
        help="Extra variable substitutions (can repeat). E.g. --var BUILD_CMD='make build'.",
    )
    parser.add_argument(
        "--working-dir",
        default=None,
        help="Working directory for subprocess calls. Defaults to cwd.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)

    extra_vars: Dict[str, str] = {}
    for kv in args.var:
        if "=" in kv:
            k, v = kv.split("=", 1)
            extra_vars[k.strip()] = v.strip()

    executor = PipelineExecutor(
        workflow_path=args.workflow,
        change_name=args.change,
        dry_run=args.dry_run,
        resume=args.resume,
        start_from=args.start_from,
        extra_vars=extra_vars,
        working_dir=args.working_dir,
    )

    success = executor.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
