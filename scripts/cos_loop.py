#!/usr/bin/env python3
# SCOPE: os-only
"""Agent loop contract runtime, reporting, guard, replay, and eval export.

The runtime is intentionally harness-neutral: it does not assume Claude, Codex,
OpenCode, or an IDE. A project supplies a loop contract, and this command keeps
state and traces under `.cognitive-os/loops/` so any harness can resume, audit,
or replay the same loop.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - exercised only when PyYAML is unavailable
    yaml = None

SCHEMA_VERSION = "cos.loop-contract.v1"
STATE_SCHEMA_VERSION = "cos.loop-state.v1"
TRACE_SCHEMA_VERSION = "cos.loop-trace.v1"
EVAL_SCHEMA_VERSION = "cos.loop-eval.v1"
COMPLETION_STATUSES = {"complete", "completed", "done", "pass", "passed", "success", "succeeded"}
DEFAULT_LOOP_ID = "default-loop"


@dataclass(frozen=True)
class Paths:
    project_dir: Path
    loops_dir: Path
    loop_dir: Path
    state_path: Path
    trace_path: Path
    observations_path: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid JSONL in {path}:{lineno}: {exc}") from exc
        if isinstance(row, dict):
            rows.append(row)
    return rows


def load_contract(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        if yaml is None:
            raise SystemExit("PyYAML is required to read YAML loop contracts; use JSON or install PyYAML")
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise SystemExit(f"loop contract must be a mapping: {path}")
    return normalize_contract(data, path)


def normalize_contract(data: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    contract = dict(data)
    contract.setdefault("schemaVersion", SCHEMA_VERSION)
    contract.setdefault("id", DEFAULT_LOOP_ID)
    contract.setdefault("trigger", {"type": "manual", "description": "Manual loop invocation"})
    contract.setdefault("goal", {"statement": "Complete the requested loop safely"})
    contract.setdefault("allowedTools", [])
    contract.setdefault("verificationCommands", [])
    stop = dict(contract.get("stopConditions") or {})
    budget = dict(contract.get("budgetPolicy") or {})
    stop.setdefault("maxIterations", budget.get("maxIterations", 5))
    stop.setdefault("maxRetries", budget.get("maxRetries", 2))
    stop.setdefault("maxNoProgressIterations", 2)
    stop.setdefault("maxToolRepetitions", 3)
    stop.setdefault("requireVerification", True)
    budget.setdefault("maxIterations", stop.get("maxIterations", 5))
    budget.setdefault("maxWallClockSeconds", 1800)
    budget.setdefault("maxObservationBytes", 200_000)
    budget.setdefault("maxVerificationSeconds", 120)
    memory = dict(contract.get("memoryPolicy") or {})
    memory.setdefault("write", "observations")
    memory.setdefault("retention", "project-local")
    memory.setdefault("paths", [".cognitive-os/loops"])
    contract["stopConditions"] = stop
    contract["budgetPolicy"] = budget
    contract["memoryPolicy"] = memory
    if path is not None:
        contract["_contract_path"] = str(path)
    return contract


def paths_for(project_dir: Path, loop_id: str) -> Paths:
    project_dir = project_dir.resolve()
    loops_dir = project_dir / ".cognitive-os" / "loops"
    loop_dir = loops_dir / sanitize_id(loop_id)
    return Paths(
        project_dir=project_dir,
        loops_dir=loops_dir,
        loop_dir=loop_dir,
        state_path=loop_dir / "state.json",
        trace_path=loop_dir / "trace.jsonl",
        observations_path=loop_dir / "observations.jsonl",
    )


def sanitize_id(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in value.strip())
    return safe or DEFAULT_LOOP_ID


def contract_hash(contract: dict[str, Any]) -> str:
    filtered = {k: v for k, v in contract.items() if not str(k).startswith("_")}
    payload = json.dumps(filtered, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def observation_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def tool_allowed(contract: dict[str, Any], tool: str | None) -> bool:
    if not tool:
        return True
    allowed = contract.get("allowedTools") or []
    if not allowed:
        return True
    for item in allowed:
        if isinstance(item, str) and item == tool:
            return True
        if isinstance(item, dict) and str(item.get("name")) == tool and str(item.get("mode", "write")) != "blocked":
            return True
    return False


def verification_commands(contract: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, item in enumerate(contract.get("verificationCommands") or [], 1):
        if isinstance(item, str):
            out.append({"id": f"verify-{idx}", "command": item, "required": True})
        elif isinstance(item, dict):
            command = str(item.get("command") or "").strip()
            if command:
                out.append({"id": str(item.get("id") or f"verify-{idx}"), "command": command, "required": bool(item.get("required", True))})
    return out


def run_verification(project_dir: Path, contract: dict[str, Any]) -> dict[str, Any]:
    timeout = int((contract.get("budgetPolicy") or {}).get("maxVerificationSeconds", 120))
    results: list[dict[str, Any]] = []
    all_required_passed = True
    for item in verification_commands(contract):
        started = time.time()
        proc = subprocess.run(
            item["command"],
            cwd=project_dir,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        elapsed = round(time.time() - started, 3)
        passed = proc.returncode == 0
        if item.get("required", True) and not passed:
            all_required_passed = False
        results.append(
            {
                "id": item["id"],
                "command": item["command"],
                "required": bool(item.get("required", True)),
                "returncode": proc.returncode,
                "passed": passed,
                "elapsed_seconds": elapsed,
                "stdout_tail": proc.stdout[-2000:],
                "stderr_tail": proc.stderr[-2000:],
            }
        )
    return {
        "ran": bool(results),
        "all_required_passed": all_required_passed if results else False,
        "commands": results,
        "updated_at": utc_now(),
    }


def initial_state(contract: dict[str, Any], loop_id: str) -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "loop_id": loop_id,
        "contract_hash": contract_hash(contract),
        "contract_path": contract.get("_contract_path"),
        "status": "running",
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "iterations": 0,
        "retries": 0,
        "stop_reasons": [],
        "budget": {
            "max_iterations": int((contract.get("stopConditions") or {}).get("maxIterations", 5)),
            "max_retries": int((contract.get("stopConditions") or {}).get("maxRetries", 2)),
            "max_observation_bytes": int((contract.get("budgetPolicy") or {}).get("maxObservationBytes", 200_000)),
        },
        "verification": {"ran": False, "all_required_passed": False, "commands": []},
        "last_decision": None,
        "last_observation_hash": None,
    }


def update_stop_state(state: dict[str, Any], contract: dict[str, Any], traces: list[dict[str, Any]], requested_status: str | None = None) -> dict[str, Any]:
    stop = contract.get("stopConditions") or {}
    require_verification = bool(stop.get("requireVerification", True))
    max_iterations = int(stop.get("maxIterations", 5))
    max_retries = int(stop.get("maxRetries", 2))
    max_no_progress = int(stop.get("maxNoProgressIterations", 2))
    max_tool_repetitions = int(stop.get("maxToolRepetitions", 3))
    reasons: list[str] = []

    if int(state.get("iterations", 0)) >= max_iterations:
        reasons.append("max-iterations")
    if int(state.get("retries", 0)) > max_retries:
        reasons.append("max-retries")

    guard_report = guard_from_rows(contract, traces)
    for issue in guard_report["issues"]:
        if issue["kind"] in {"ping-pong", "no-progress"}:
            if issue["kind"] == "ping-pong" and issue["count"] > max_tool_repetitions:
                reasons.append("ping-pong")
            if issue["kind"] == "no-progress" and issue["count"] >= max_no_progress:
                reasons.append("no-progress")

    verification = state.get("verification") or {}
    verification_passed = bool(verification.get("all_required_passed"))
    normalized_status = (requested_status or state.get("status") or "running").lower()
    if normalized_status in COMPLETION_STATUSES:
        if require_verification and not verification_passed:
            reasons.append("false-completion-risk")
            state["status"] = "false_completion_risk"
        else:
            state["status"] = "passed"
    elif reasons:
        state["status"] = "blocked" if any(r in reasons for r in ("no-progress", "ping-pong", "false-completion-risk")) else "budget_limited"
    else:
        state["status"] = normalized_status if normalized_status not in COMPLETION_STATUSES else "running"

    state["stop_reasons"] = sorted(set(reasons))
    state["updated_at"] = utc_now()
    return state


def guard_from_rows(contract: dict[str, Any], rows: list[dict[str, Any]], state: dict[str, Any] | None = None) -> dict[str, Any]:
    stop = contract.get("stopConditions") or {}
    max_tool_repetitions = int(stop.get("maxToolRepetitions", 3))
    max_no_progress = int(stop.get("maxNoProgressIterations", 2))
    require_verification = bool(stop.get("requireVerification", True))
    issues: list[dict[str, Any]] = []

    tool_counts: dict[str, int] = {}
    for row in rows:
        tool = row.get("tool")
        if isinstance(tool, str) and tool:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
    for tool, count in sorted(tool_counts.items()):
        if count > max_tool_repetitions:
            issues.append({"kind": "ping-pong", "tool": tool, "count": count, "limit": max_tool_repetitions})

    tail = rows[-max_no_progress:] if max_no_progress > 0 else []
    if tail and len(tail) >= max_no_progress and all(row.get("progress") is False for row in tail):
        issues.append({"kind": "no-progress", "count": len(tail), "limit": max_no_progress})

    hashes = [row.get("observation_hash") for row in tail if row.get("observation_hash")]
    if len(hashes) >= max_no_progress and len(set(hashes)) == 1:
        issues.append({"kind": "no-progress", "count": len(hashes), "reason": "repeated-observation"})

    completion_events = [row for row in rows if str(row.get("status", "")).lower() in COMPLETION_STATUSES]
    verification = (state or {}).get("verification") or {}
    verification_passed = bool(verification.get("all_required_passed"))
    if require_verification and completion_events and not verification_passed:
        issues.append({"kind": "false-completion", "count": len(completion_events), "required_verification_passed": False})

    return {
        "schema_version": "cos.loop-guard.v1",
        "status": "pass" if not issues else "warn",
        "issues": issues,
        "tool_counts": tool_counts,
        "event_count": len(rows),
    }


def command_run(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    contract = load_contract(Path(args.contract).resolve())
    loop_id = args.loop_id or str(contract.get("id") or DEFAULT_LOOP_ID)
    if args.tool and not tool_allowed(contract, args.tool):
        print(json.dumps({"status": "blocked", "reason": "tool-not-allowed", "tool": args.tool}, indent=2))
        return 2
    paths = paths_for(project_dir, loop_id)
    state = load_json(paths.state_path, initial_state(contract, loop_id))
    if not state:
        state = initial_state(contract, loop_id)

    observation = args.observation or "manual loop tick"
    budget = contract.get("budgetPolicy") or {}
    max_observation_bytes = int(budget.get("maxObservationBytes", 200_000))
    if len(observation.encode("utf-8")) > max_observation_bytes:
        print(json.dumps({"status": "blocked", "reason": "observation-budget-exceeded"}, indent=2))
        return 2

    iteration = int(state.get("iterations", 0)) + 1
    progress = args.progress
    if progress is None:
        progress = observation_hash(observation) != state.get("last_observation_hash")

    row = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "ts": utc_now(),
        "loop_id": loop_id,
        "iteration": iteration,
        "event": "observation",
        "tool": args.tool,
        "decision": args.decision,
        "observation": observation,
        "observation_hash": observation_hash(observation),
        "progress": bool(progress),
        "status": args.status or "running",
    }
    append_jsonl(paths.trace_path, row)
    if (contract.get("memoryPolicy") or {}).get("write") in {"observations", "all"}:
        append_jsonl(paths.observations_path, row)

    state["iterations"] = iteration
    if args.retry:
        state["retries"] = int(state.get("retries", 0)) + 1
    state["last_decision"] = args.decision
    state["last_observation_hash"] = row["observation_hash"]

    if args.run_verification:
        state["verification"] = run_verification(project_dir, contract)

    traces = load_jsonl(paths.trace_path)
    update_stop_state(state, contract, traces, args.status)
    write_json(paths.state_path, state)

    payload = {"status": state["status"], "loop_id": loop_id, "state_path": str(paths.state_path), "trace_path": str(paths.trace_path), "stop_reasons": state.get("stop_reasons", [])}
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else f"loop={loop_id} status={state['status']} stop_reasons={','.join(state.get('stop_reasons', [])) or 'none'}")
    return 0 if state["status"] not in {"blocked", "false_completion_risk", "budget_limited"} else 2


def report_for(project_dir: Path, loop_id: str) -> dict[str, Any]:
    paths = paths_for(project_dir, loop_id)
    state = load_json(paths.state_path, initial_state({"id": loop_id}, loop_id))
    rows = load_jsonl(paths.trace_path)
    tool_counts: dict[str, int] = {}
    no_progress = 0
    for row in rows:
        tool = row.get("tool")
        if isinstance(tool, str) and tool:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
        if row.get("progress") is False:
            no_progress += 1
    return {
        "schema_version": "cos.loop-report.v1",
        "loop_id": loop_id,
        "status": state.get("status", "unknown"),
        "iterations": state.get("iterations", 0),
        "retries": state.get("retries", 0),
        "stop_reasons": state.get("stop_reasons", []),
        "tool_repetition": tool_counts,
        "no_progress_events": no_progress,
        "budget": state.get("budget", {}),
        "verification": state.get("verification", {}),
        "state_path": str(paths.state_path),
        "trace_path": str(paths.trace_path),
    }


def command_report(args: argparse.Namespace) -> int:
    payload = report_for(Path(args.project_dir).resolve(), args.loop_id)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"# Loop report: {payload['loop_id']}")
        print(f"status: {payload['status']}")
        print(f"iterations: {payload['iterations']} retries: {payload['retries']}")
        print(f"stop_reasons: {', '.join(payload['stop_reasons']) if payload['stop_reasons'] else 'none'}")
        print(f"tool_repetition: {json.dumps(payload['tool_repetition'], sort_keys=True)}")
        print(f"verification_passed: {bool((payload.get('verification') or {}).get('all_required_passed'))}")
    return 0


def command_guard(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    contract = load_contract(Path(args.contract).resolve()) if args.contract else normalize_contract({"id": args.loop_id})
    paths = paths_for(project_dir, args.loop_id)
    state = load_json(paths.state_path, {})
    rows = load_jsonl(paths.trace_path)
    payload = guard_from_rows(contract, rows, state)
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else f"guard={payload['status']} issues={len(payload['issues'])}")
    return 2 if args.strict and payload["issues"] else 0


def command_replay(args: argparse.Namespace) -> int:
    paths = paths_for(Path(args.project_dir).resolve(), args.loop_id)
    rows = load_jsonl(paths.trace_path)
    replay = {
        "schema_version": "cos.loop-replay.v1",
        "loop_id": args.loop_id,
        "events": [
            {
                "iteration": row.get("iteration"),
                "ts": row.get("ts"),
                "tool": row.get("tool"),
                "decision": row.get("decision"),
                "status": row.get("status"),
                "progress": row.get("progress"),
                "observation_hash": row.get("observation_hash"),
            }
            for row in rows
        ],
    }
    if args.json:
        print(json.dumps(replay, indent=2, sort_keys=True))
    else:
        print(f"# Loop replay: {args.loop_id}")
        for event in replay["events"]:
            print(f"{event['iteration']}: tool={event['tool'] or '-'} status={event['status']} progress={event['progress']} decision={event['decision'] or '-'}")
    return 0


def command_eval(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    loop_id = args.loop_id
    paths = paths_for(project_dir, loop_id)
    state = load_json(paths.state_path, {})
    rows = load_jsonl(paths.trace_path)
    output = Path(args.output).resolve() if args.output else project_dir / ".cognitive-os" / "evals" / "agent-loops" / f"{sanitize_id(loop_id)}.json"
    cases = []
    for row in rows:
        cases.append(
            {
                "name": f"{loop_id}-iteration-{row.get('iteration')}",
                "input": {"tool": row.get("tool"), "observation_hash": row.get("observation_hash")},
                "expected": {"progress": row.get("progress"), "status": row.get("status")},
                "decision": row.get("decision"),
            }
        )
    payload = {
        "schema_version": EVAL_SCHEMA_VERSION,
        "loop_id": loop_id,
        "source_trace": str(paths.trace_path),
        "source_state": str(paths.state_path),
        "final_status": state.get("status"),
        "generated_at": utc_now(),
        "cases": cases,
    }
    write_json(output, payload)
    print(json.dumps({"status": "written", "output": str(output), "cases": len(cases)}, indent=2, sort_keys=True) if args.json else f"wrote {output} cases={len(cases)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cognitive OS agent loop engineering primitives")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="append a loop iteration and apply stop conditions")
    run.add_argument("--project-dir", default=os.getcwd())
    run.add_argument("--contract", required=True)
    run.add_argument("--loop-id")
    run.add_argument("--observation")
    run.add_argument("--decision")
    run.add_argument("--tool")
    run.add_argument("--status", default="running")
    run.add_argument("--retry", action="store_true")
    run.add_argument("--progress", dest="progress", action="store_true", default=None)
    run.add_argument("--no-progress", dest="progress", action="store_false")
    run.add_argument("--run-verification", action="store_true")
    run.add_argument("--json", action="store_true")
    run.set_defaults(func=command_run)

    report = sub.add_parser("report", help="show progress, retries, tool repetition, and budget")
    report.add_argument("--project-dir", default=os.getcwd())
    report.add_argument("--loop-id", required=True)
    report.add_argument("--json", action="store_true")
    report.set_defaults(func=command_report)

    guard = sub.add_parser("guard", help="detect ping-pong, no-progress, and false completion")
    guard.add_argument("--project-dir", default=os.getcwd())
    guard.add_argument("--loop-id", required=True)
    guard.add_argument("--contract")
    guard.add_argument("--strict", action="store_true")
    guard.add_argument("--json", action="store_true")
    guard.set_defaults(func=command_guard)

    replay = sub.add_parser("replay", help="reproduce loop decisions from traces")
    replay.add_argument("--project-dir", default=os.getcwd())
    replay.add_argument("--loop-id", required=True)
    replay.add_argument("--json", action="store_true")
    replay.set_defaults(func=command_replay)

    ev = sub.add_parser("eval", help="convert loop traces into regression eval fixtures")
    ev.add_argument("--project-dir", default=os.getcwd())
    ev.add_argument("--loop-id", required=True)
    ev.add_argument("--output")
    ev.add_argument("--json", action="store_true")
    ev.set_defaults(func=command_eval)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except subprocess.TimeoutExpired as exc:
        print(json.dumps({"status": "blocked", "reason": "verification-timeout", "command": exc.cmd}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
