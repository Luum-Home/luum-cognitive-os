#!/usr/bin/env python3
# SCOPE: both
"""SO-wide impact evaluation runner.

Runs controlled workflow-level comparisons across vanilla, full Cognitive OS,
and ablation modes. The runner is intentionally harness-neutral: it creates an
isolated capsule for each mode, executes declared workflow commands, captures
trace/usage/diff/verification receipts, then renders a correctness-first report.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - import guard
    print("ERROR: PyYAML required. Install with: uv pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "docs" / "09-Quality" / "evals" / "so-impact"
SCHEMA = "cos.so-impact-eval.v1"

DEFAULT_MODES = [
    "vanilla",
    "full-so",
    "graphify-only",
    "process-loop-only",
    "skill-selection-only",
    "context-token-optimization-only",
    "governance-hooks-only",
    "full-so-minus-graphify",
    "full-so-minus-process-loop",
]

TASK_FAMILIES = [
    "bugfix",
    "refactor",
    "feature",
    "backend-endpoint",
    "frontend-component",
    "docs-release",
    "test-repair",
]

METRIC_CATALOG = [
    "total_tokens",
    "input_tokens",
    "output_tokens",
    "context_lines_read",
    "tool_calls",
    "discovery_calls",
    "files_touched",
    "relevant_files_found",
    "tests_passed",
    "wall_clock",
    "retries",
    "false_claims",
    "final_diff_quality",
]

MODE_FLAGS: dict[str, dict[str, str]] = {
    "vanilla": {
        "COS_DISABLE_ALL_GOVERNANCE": "1",
        "COS_GRAPHIFY_ENABLED": "0",
        "COS_PROCESS_LOOP_ENABLED": "0",
        "COS_SKILL_SELECTION_ENABLED": "0",
        "COS_CONTEXT_DIET_ENABLED": "0",
        "COS_TOKEN_OPTIMIZATION_ENABLED": "0",
        "COS_GOVERNANCE_HOOKS_ENABLED": "0",
    },
    "full-so": {
        "COS_DISABLE_ALL_GOVERNANCE": "0",
        "COS_GRAPHIFY_ENABLED": "1",
        "COS_PROCESS_LOOP_ENABLED": "1",
        "COS_SKILL_SELECTION_ENABLED": "1",
        "COS_CONTEXT_DIET_ENABLED": "1",
        "COS_TOKEN_OPTIMIZATION_ENABLED": "1",
        "COS_GOVERNANCE_HOOKS_ENABLED": "1",
    },
    "graphify-only": {
        "COS_DISABLE_ALL_GOVERNANCE": "0",
        "COS_GRAPHIFY_ENABLED": "1",
        "COS_PROCESS_LOOP_ENABLED": "0",
        "COS_SKILL_SELECTION_ENABLED": "0",
        "COS_CONTEXT_DIET_ENABLED": "0",
        "COS_TOKEN_OPTIMIZATION_ENABLED": "0",
        "COS_GOVERNANCE_HOOKS_ENABLED": "0",
    },
    "process-loop-only": {
        "COS_DISABLE_ALL_GOVERNANCE": "0",
        "COS_GRAPHIFY_ENABLED": "0",
        "COS_PROCESS_LOOP_ENABLED": "1",
        "COS_SKILL_SELECTION_ENABLED": "0",
        "COS_CONTEXT_DIET_ENABLED": "0",
        "COS_TOKEN_OPTIMIZATION_ENABLED": "0",
        "COS_GOVERNANCE_HOOKS_ENABLED": "0",
    },
    "skill-selection-only": {
        "COS_DISABLE_ALL_GOVERNANCE": "0",
        "COS_GRAPHIFY_ENABLED": "0",
        "COS_PROCESS_LOOP_ENABLED": "0",
        "COS_SKILL_SELECTION_ENABLED": "1",
        "COS_CONTEXT_DIET_ENABLED": "0",
        "COS_TOKEN_OPTIMIZATION_ENABLED": "0",
        "COS_GOVERNANCE_HOOKS_ENABLED": "0",
    },
    "context-token-optimization-only": {
        "COS_DISABLE_ALL_GOVERNANCE": "0",
        "COS_GRAPHIFY_ENABLED": "0",
        "COS_PROCESS_LOOP_ENABLED": "0",
        "COS_SKILL_SELECTION_ENABLED": "0",
        "COS_CONTEXT_DIET_ENABLED": "1",
        "COS_TOKEN_OPTIMIZATION_ENABLED": "1",
        "COS_GOVERNANCE_HOOKS_ENABLED": "0",
    },
    "governance-hooks-only": {
        "COS_DISABLE_ALL_GOVERNANCE": "0",
        "COS_GRAPHIFY_ENABLED": "0",
        "COS_PROCESS_LOOP_ENABLED": "0",
        "COS_SKILL_SELECTION_ENABLED": "0",
        "COS_CONTEXT_DIET_ENABLED": "0",
        "COS_TOKEN_OPTIMIZATION_ENABLED": "0",
        "COS_GOVERNANCE_HOOKS_ENABLED": "1",
    },
    "full-so-minus-graphify": {
        "COS_DISABLE_ALL_GOVERNANCE": "0",
        "COS_GRAPHIFY_ENABLED": "0",
        "COS_PROCESS_LOOP_ENABLED": "1",
        "COS_SKILL_SELECTION_ENABLED": "1",
        "COS_CONTEXT_DIET_ENABLED": "1",
        "COS_TOKEN_OPTIMIZATION_ENABLED": "1",
        "COS_GOVERNANCE_HOOKS_ENABLED": "1",
    },
    "full-so-minus-process-loop": {
        "COS_DISABLE_ALL_GOVERNANCE": "0",
        "COS_GRAPHIFY_ENABLED": "1",
        "COS_PROCESS_LOOP_ENABLED": "0",
        "COS_SKILL_SELECTION_ENABLED": "1",
        "COS_CONTEXT_DIET_ENABLED": "1",
        "COS_TOKEN_OPTIMIZATION_ENABLED": "1",
        "COS_GOVERNANCE_HOOKS_ENABLED": "1",
    },
}


@dataclass
class CommandReceipt:
    command: str
    cwd: str
    exit_code: int
    duration_ms: int
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""


@dataclass
class ModeReceipt:
    mode: str
    status: str
    capsule_dir: str
    trace_path: str
    usage_path: str
    diff_path: str
    verify_path: str
    process_path: str
    commands: list[CommandReceipt] = field(default_factory=list)
    verification: list[CommandReceipt] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class EvalReceipt:
    task_id: str
    run_id: str
    output_dir: str
    modes: dict[str, ModeReceipt]
    verdict: str
    rationale: str


def utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_contract(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if data.get("schema") != SCHEMA:
        raise ValueError(f"{path}: schema must be {SCHEMA}")
    task = data.get("task") or {}
    if not task.get("id"):
        raise ValueError(f"{path}: task.id is required")
    fixture = task.get("repo_fixture") or data.get("fixture", {}).get("repo")
    if not fixture:
        raise ValueError(f"{path}: task.repo_fixture is required")
    modes = data.get("modes") or []
    if not isinstance(modes, list) or not modes:
        raise ValueError(f"{path}: modes must be a non-empty list")
    unknown = [mode for mode in modes if mode not in MODE_FLAGS]
    if unknown:
        raise ValueError(f"{path}: unsupported modes: {', '.join(unknown)}")
    return data


def resolve_path(value: str, base: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def copy_fixture(src: Path, dst: Path) -> None:
    ignore = shutil.ignore_patterns(".git", "node_modules", "__pycache__", ".pytest_cache", ".cognitive-os")
    shutil.copytree(src, dst, ignore=ignore)
    subprocess.run(["git", "init", "-q"], cwd=dst, check=True)
    subprocess.run(["git", "config", "user.email", "cos-so-impact@example.invalid"], cwd=dst, check=True)
    subprocess.run(["git", "config", "user.name", "COS SO Impact Eval"], cwd=dst, check=True)
    subprocess.run(["git", "add", "."], cwd=dst, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture baseline"], cwd=dst, check=True)


def command_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("commands must be a list")
    out: list[str] = []
    for item in raw:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict) and isinstance(item.get("command"), str):
            out.append(item["command"])
        else:
            raise ValueError(f"unsupported command entry: {item!r}")
    return out


def mode_env(mode: str, capsule: Path, mode_dir: Path, contract: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(MODE_FLAGS[mode])
    env.update(
        {
            "COS_SO_IMPACT_MODE": mode,
            "COS_SO_IMPACT_CAPSULE_DIR": str(capsule),
            "COS_SO_IMPACT_OUTPUT_DIR": str(mode_dir),
            "COS_SO_IMPACT_CONTRACT": str(contract),
            "COS_SO_IMPACT_TRACE": str(mode_dir / "trace.jsonl"),
            "COS_SO_IMPACT_USAGE": str(mode_dir / "usage.json"),
        }
    )
    return env


def append_trace(path: Path, payload: dict[str, Any]) -> None:
    payload.setdefault("ts", datetime.now(timezone.utc).isoformat())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def run_shell(command: str, cwd: Path, env: dict[str, str], trace_path: Path, phase: str) -> CommandReceipt:
    start = time.monotonic()
    append_trace(trace_path, {"event": "command_start", "phase": phase, "command": command, "cwd": str(cwd)})
    proc = subprocess.run(command, cwd=cwd, env=env, shell=True, text=True, capture_output=True, check=False)
    duration = int((time.monotonic() - start) * 1000)
    receipt = CommandReceipt(
        command=command,
        cwd=str(cwd),
        exit_code=proc.returncode,
        duration_ms=duration,
        stdout_excerpt=(proc.stdout or "")[-2000:],
        stderr_excerpt=(proc.stderr or "")[-2000:],
    )
    append_trace(
        trace_path,
        {
            "event": "command_finish",
            "phase": phase,
            "command": command,
            "exit_code": proc.returncode,
            "duration_ms": duration,
        },
    )
    return receipt


def mark_untracked_for_diff(capsule: Path) -> None:
    # Intent-to-add makes new files visible in `git diff` without staging content
    # for commit. This is required for workflow receipts to include created files.
    subprocess.run(["git", "add", "-N", "."], cwd=capsule, text=True, capture_output=True, check=False)


def git_diff(capsule: Path) -> str:
    mark_untracked_for_diff(capsule)
    return subprocess.run(["git", "diff", "--binary"], cwd=capsule, text=True, capture_output=True, check=False).stdout


def files_touched(capsule: Path) -> list[str]:
    mark_untracked_for_diff(capsule)
    out = subprocess.run(["git", "status", "--short"], cwd=capsule, text=True, capture_output=True, check=False).stdout
    touched: list[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:] if len(line) > 3 else line.strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        touched.append(path)
    return sorted(set(touched))


def load_usage(mode_dir: Path, commands: list[CommandReceipt]) -> dict[str, Any]:
    usage_path = mode_dir / "usage.json"
    if usage_path.exists():
        try:
            data = json.loads(usage_path.read_text(encoding="utf-8"))
            data.setdefault("real_usage_available", True)
            return data
        except json.JSONDecodeError as exc:
            return {"real_usage_available": False, "usage_error": str(exc)}
    return {
        "real_usage_available": False,
        "total_tokens": None,
        "input_tokens": None,
        "output_tokens": None,
        "reason": "No provider usage receipt was emitted by the workflow commands.",
        "command_count": len(commands),
    }


def trace_metrics(trace_path: Path) -> dict[str, Any]:
    metrics = {
        "tool_calls": 0,
        "discovery_calls": 0,
        "context_lines_read": 0,
        "relevant_files_found": 0,
        "retries": 0,
        "false_claims": 0,
        "blocked_unsafe_actions": 0,
        "final_diff_quality": "unreviewed",
    }
    if not trace_path.exists():
        return metrics
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") == "tool_call":
            metrics["tool_calls"] += 1
            if event.get("phase") == "discovery":
                metrics["discovery_calls"] += 1
        if "context_lines_read" in event:
            metrics["context_lines_read"] += int(event.get("context_lines_read") or 0)
        if "relevant_files_found" in event:
            metrics["relevant_files_found"] += int(event.get("relevant_files_found") or 0)
        if event.get("event") == "retry":
            metrics["retries"] += 1
        if event.get("event") == "false_claim":
            metrics["false_claims"] += 1
        if event.get("event") == "blocked_unsafe_action":
            metrics["blocked_unsafe_actions"] += 1
        if event.get("event") == "quality_oracle" and event.get("score") is not None:
            metrics["final_diff_quality"] = event.get("score")
    return metrics


def run_mode(contract: dict[str, Any], contract_path: Path, output_dir: Path, mode: str, keep_capsules: bool) -> ModeReceipt:
    task = contract["task"]
    fixture = resolve_path(task["repo_fixture"], contract_path.parent)
    if not fixture.exists():
        raise FileNotFoundError(f"fixture not found: {fixture}")
    mode_dir = output_dir / mode
    mode_dir.mkdir(parents=True, exist_ok=True)
    capsule_parent = output_dir / "capsules"
    capsule_parent.mkdir(parents=True, exist_ok=True)
    capsule = capsule_parent / mode
    if capsule.exists():
        shutil.rmtree(capsule)
    copy_fixture(fixture, capsule)

    trace_path = mode_dir / "trace.jsonl"
    env = mode_env(mode, capsule, mode_dir, contract_path)
    workflow = contract.get("workflow") or {}
    mode_overrides = (contract.get("modeOverrides") or {}).get(mode, {})
    commands = command_list(mode_overrides.get("workflowCommands", workflow.get("commands")))
    verify_commands = command_list(mode_overrides.get("verification", {}).get("commands", task.get("verification") or contract.get("verification", {}).get("commands")))

    append_trace(trace_path, {"event": "mode_start", "mode": mode, "flags": MODE_FLAGS[mode]})
    command_receipts: list[CommandReceipt] = []
    verification_receipts: list[CommandReceipt] = []
    status = "passed"
    error = ""

    for command in commands:
        receipt = run_shell(command, capsule, env, trace_path, "workflow")
        command_receipts.append(receipt)
        if receipt.exit_code != 0:
            status = "failed"
            error = f"workflow command failed: {command}"
            break

    if status == "passed":
        for command in verify_commands:
            receipt = run_shell(command, capsule, env, trace_path, "verification")
            verification_receipts.append(receipt)
            if receipt.exit_code != 0:
                status = "failed"
                error = f"verification command failed: {command}"

    diff_text = git_diff(capsule)
    diff_path = mode_dir / "diff.patch"
    diff_path.write_text(diff_text, encoding="utf-8")

    verify_path = mode_dir / "verify.json"
    verify_payload = {
        "mode": mode,
        "all_required_passed": bool(verification_receipts) and all(r.exit_code == 0 for r in verification_receipts),
        "commands": [r.__dict__ for r in verification_receipts],
    }
    verify_path.write_text(json.dumps(verify_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    usage_payload = load_usage(mode_dir, command_receipts)
    usage_path = mode_dir / "usage.json"
    usage_path.write_text(json.dumps(usage_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    metrics = trace_metrics(trace_path)
    touched = files_touched(capsule)
    metrics.update(
        {
            "files_touched": len(touched),
            "files_touched_list": touched,
            "diff_bytes": len(diff_text.encode("utf-8")),
            "tests_passed": verify_payload["all_required_passed"],
            "wall_clock_ms": sum(r.duration_ms for r in command_receipts + verification_receipts),
        }
    )
    for key in ("total_tokens", "input_tokens", "output_tokens"):
        metrics[key] = usage_payload.get(key)

    process_path = mode_dir / "process.json"
    process_path.write_text(
        json.dumps(
            {
                "mode": mode,
                "status": status,
                "commands": [r.__dict__ for r in command_receipts],
                "verification": verify_payload,
                "metrics": metrics,
                "error": error,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    append_trace(trace_path, {"event": "mode_finish", "mode": mode, "status": status, "metrics": metrics})

    if not keep_capsules:
        # Keep the diff/receipts but remove bulky working copies.
        shutil.rmtree(capsule, ignore_errors=True)

    return ModeReceipt(
        mode=mode,
        status=status,
        capsule_dir=str(capsule if keep_capsules else "removed"),
        trace_path=str(trace_path),
        usage_path=str(usage_path),
        diff_path=str(diff_path),
        verify_path=str(verify_path),
        process_path=str(process_path),
        commands=command_receipts,
        verification=verification_receipts,
        metrics=metrics,
        error=error,
    )


def verdict_for(modes: dict[str, ModeReceipt]) -> tuple[str, str]:
    if not modes:
        return "inconclusive", "no modes executed"
    failed = [name for name, receipt in modes.items() if receipt.status != "passed"]
    if failed:
        return "inconclusive", f"one or more modes failed verification: {', '.join(failed)}"
    if "vanilla" not in modes or "full-so" not in modes:
        return "inconclusive", "vanilla and full-so are required for a broad SO-wide comparison"
    vanilla = modes["vanilla"].metrics
    full = modes["full-so"].metrics
    wins: list[str] = []
    if metric_lt(full, vanilla, "false_claims"):
        wins.append("fewer false completion events")
    if metric_lt(full, vanilla, "tool_calls"):
        wins.append("fewer tool calls")
    if metric_lt(full, vanilla, "context_lines_read"):
        wins.append("less discovery context")
    if metric_lte(full, vanilla, "diff_bytes") and metric_lte(full, vanilla, "files_touched"):
        wins.append("same-or-smaller diff footprint")
    if wins:
        return "win", "; ".join(wins)
    return "neutral", "correctness matched, but no measured efficiency/safety advantage crossed the simple gate"


def metric_lt(left: dict[str, Any], right: dict[str, Any], key: str) -> bool:
    return isinstance(left.get(key), (int, float)) and isinstance(right.get(key), (int, float)) and left[key] < right[key]


def metric_lte(left: dict[str, Any], right: dict[str, Any], key: str) -> bool:
    return isinstance(left.get(key), (int, float)) and isinstance(right.get(key), (int, float)) and left[key] <= right[key]


def render_report(receipt: EvalReceipt, contract: dict[str, Any]) -> None:
    out = Path(receipt.output_dir) / "report.md"
    lines = [
        f"# SO-Wide Impact Eval — {receipt.task_id}",
        "",
        f"Run ID: `{receipt.run_id}`",
        f"Verdict: **{receipt.verdict}** — {receipt.rationale}",
        "",
        "## Task",
        "",
        f"- Goal: {contract['task'].get('goal', '')}",
        f"- Fixture: `{contract['task'].get('repo_fixture', '')}`",
        "",
        "## Mode comparison",
        "",
        "| Mode | Status | Tests | Tokens | Context lines | Tool calls | Discovery calls | Files touched | Diff bytes | Retries | False claims | Quality |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for mode, mode_receipt in receipt.modes.items():
        m = mode_receipt.metrics
        tokens = m.get("total_tokens")
        token_text = "n/a" if tokens is None else str(tokens)
        lines.append(
            "| {mode} | {status} | {tests} | {tokens} | {context} | {tools} | {discovery} | {files} | {diff} | {retries} | {false_claims} | {quality} |".format(
                mode=mode,
                status=mode_receipt.status,
                tests="pass" if m.get("tests_passed") else "fail",
                tokens=token_text,
                context=m.get("context_lines_read", 0),
                tools=m.get("tool_calls", 0),
                discovery=m.get("discovery_calls", 0),
                files=m.get("files_touched", 0),
                diff=m.get("diff_bytes", 0),
                retries=m.get("retries", 0),
                false_claims=m.get("false_claims", 0),
                quality=m.get("final_diff_quality", "unreviewed"),
            )
        )
    lines.extend(
        [
            "",
            "## Receipts",
            "",
            "Each mode directory contains `trace.jsonl`, `usage.json`, `diff.patch`, `verify.json`, and `process.json`.",
            "Positive SO-wide claims require verification receipts first; token/cost comparisons are ignored when correctness fails.",
        ]
    )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_contract_copy(contract_path: Path, output_dir: Path) -> None:
    shutil.copy2(contract_path, output_dir / "contract.yaml")


def run_eval(contract_path: Path, output_root: Path, run_id: str | None, modes_filter: list[str] | None, keep_capsules: bool) -> EvalReceipt:
    contract = load_contract(contract_path)
    task_id = contract["task"]["id"]
    run = run_id or utc_run_id()
    output_dir = output_root / task_id / run
    output_dir.mkdir(parents=True, exist_ok=True)
    write_contract_copy(contract_path, output_dir)
    selected_modes = modes_filter or list(contract["modes"])
    unknown = [mode for mode in selected_modes if mode not in MODE_FLAGS]
    if unknown:
        raise ValueError(f"unsupported modes: {', '.join(unknown)}")
    modes: dict[str, ModeReceipt] = {}
    for mode in selected_modes:
        modes[mode] = run_mode(contract, contract_path, output_dir, mode, keep_capsules=keep_capsules)
    verdict, rationale = verdict_for(modes)
    receipt = EvalReceipt(task_id=task_id, run_id=run, output_dir=str(output_dir), modes=modes, verdict=verdict, rationale=rationale)
    (output_dir / "report.json").write_text(json.dumps(eval_to_dict(receipt), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render_report(receipt, contract)
    return receipt


def eval_to_dict(receipt: EvalReceipt) -> dict[str, Any]:
    return {
        "task_id": receipt.task_id,
        "run_id": receipt.run_id,
        "output_dir": receipt.output_dir,
        "verdict": receipt.verdict,
        "rationale": receipt.rationale,
        "modes": {
            name: {
                "mode": r.mode,
                "status": r.status,
                "capsule_dir": r.capsule_dir,
                "trace_path": r.trace_path,
                "usage_path": r.usage_path,
                "diff_path": r.diff_path,
                "verify_path": r.verify_path,
                "process_path": r.process_path,
                "commands": [c.__dict__ for c in r.commands],
                "verification": [c.__dict__ for c in r.verification],
                "metrics": r.metrics,
                "error": r.error,
            }
            for name, r in receipt.modes.items()
        },
    }


def catalog() -> dict[str, Any]:
    return {
        "schema": f"{SCHEMA}.catalog",
        "task_families": TASK_FAMILIES,
        "modes": DEFAULT_MODES,
        "metrics": METRIC_CATALOG,
        "claim_boundary": "Product claims require paired run receipts with verification passing before token/cost comparisons are interpreted.",
    }


def plan(contract_path: Path, modes_filter: list[str] | None) -> dict[str, Any]:
    contract = load_contract(contract_path)
    modes = modes_filter or contract["modes"]
    return {
        "schema": SCHEMA,
        "task_id": contract["task"]["id"],
        "fixture": str(resolve_path(contract["task"]["repo_fixture"], contract_path.parent)),
        "modes": modes,
        "workflow_commands": command_list((contract.get("workflow") or {}).get("commands")),
        "verification_commands": command_list(contract["task"].get("verification") or (contract.get("verification") or {}).get("commands")),
        "output_shape": "docs/09-Quality/evals/so-impact/{task}/{run-id}/{mode}/{trace,usage,diff,verify,process}",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SO-wide vanilla/full-SO/ablation workflow impact evals.")
    sub = parser.add_subparsers(dest="command", required=True)
    catalog_p = sub.add_parser("catalog", help="print supported task families, modes, metrics, and claim boundary")
    catalog_p.add_argument("--json", action="store_true", help="Emit JSON")
    plan_p = sub.add_parser("plan", help="validate a contract and print the planned matrix")
    run_p = sub.add_parser("run", help="execute the controlled workflow matrix")
    for p in (plan_p, run_p):
        p.add_argument("--contract", required=True, help="Path to cos.so-impact-eval.v1 YAML contract")
        p.add_argument("--mode", action="append", dest="modes", help="Mode to include; repeatable")
        p.add_argument("--json", action="store_true", help="Emit JSON")
    run_p.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Output root for run bundles")
    run_p.add_argument("--run-id", default=None, help="Override run id")
    run_p.add_argument("--keep-capsules", action="store_true", help="Keep copied working directories for inspection")

    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            payload = catalog()
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print("SO-wide impact eval catalog")
                print("Task families:")
                for family in payload["task_families"]:
                    print(f"  - {family}")
                print("Modes:")
                for mode in payload["modes"]:
                    print(f"  - {mode}")
            return 0
        contract_path = Path(args.contract).resolve()
        if args.command == "plan":
            payload = plan(contract_path, args.modes)
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(f"SO-wide impact eval task: {payload['task_id']}")
                print(f"Fixture: {payload['fixture']}")
                print("Modes:")
                for mode in payload["modes"]:
                    print(f"  - {mode}")
            return 0
        receipt = run_eval(contract_path, Path(args.output_root).resolve(), args.run_id, args.modes, keep_capsules=args.keep_capsules)
        payload = eval_to_dict(receipt)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"Report: {receipt.output_dir}/report.md")
            print(f"Verdict: {receipt.verdict} — {receipt.rationale}")
        return 0 if receipt.verdict in {"win", "neutral"} else 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
