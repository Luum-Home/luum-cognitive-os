#!/usr/bin/env python3
# SCOPE: both
"""Validate generic task/front closure ledgers and prevent false completion claims."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

SCHEMA_VERSION = "cos.task-closure-gate/v1"
CONTRACT = "cos.task-closure-ledger.v1"
VALID_STATUSES = {"closed", "ready_next_slice", "blocked_large", "blocked", "deferred", "open"}
REQUIRED_KEYS = {
    "id",
    "title",
    "status",
    "canClaimComplete",
    "closureGate",
    "doneEvidence",
    "remaining",
    "nextPrimitive",
}
OPEN_STATUSES = VALID_STATUSES - {"closed"}


@dataclass(frozen=True)
class GateRun:
    front_id: str
    command: str
    returncode: int
    stdout_tail: str = ""
    stderr_tail: str = ""


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    front_id: str
    message: str


@dataclass(frozen=True)
class FrontSummary:
    id: str
    title: str
    status: str
    can_claim_complete: bool
    closure_gate: str
    done_evidence_count: int
    remaining_count: int
    next_primitive: str
    gate_claimed_passed: bool | None = None


@dataclass(frozen=True)
class Report:
    schema_version: str
    ledger: str
    contract: str | None
    status: str
    total_fronts: int
    closed_fronts: int
    claimable_fronts: int
    findings: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)
    fronts: list[FrontSummary] = field(default_factory=list)
    gate_runs: list[GateRun] = field(default_factory=list)


def _tail(text: str, limit: int = 2000) -> str:
    return text[-limit:] if text else ""


def load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"FAIL: closure ledger not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"FAIL: invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"FAIL: closure ledger root must be an object: {path}")
    return payload


def _fronts(payload: dict[str, Any]) -> tuple[list[Any], str]:
    if isinstance(payload.get("fronts"), list):
        return payload["fronts"], "fronts"
    if isinstance(payload.get("items"), list):
        return payload["items"], "items"
    return [], "fronts"


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and bool(item.strip()) for item in value)


def _gate_claimed_passed(front: dict[str, Any]) -> bool | None:
    for key in ("closureGatePassed", "gatePassed"):
        if key in front:
            return bool(front[key])
    evidence = front.get("closureGateEvidence") or front.get("gateEvidence")
    if evidence is None:
        return None
    if isinstance(evidence, list):
        return bool(evidence)
    if isinstance(evidence, str):
        return bool(evidence.strip())
    return bool(evidence)


def _validate_front(
    front: Any,
    index: int,
    *,
    require_closed: bool,
    require_gates_passed: bool,
    seen: set[str],
) -> tuple[FrontSummary | None, list[Finding], list[Finding]]:
    errors: list[Finding] = []
    warnings: list[Finding] = []
    fallback_id = f"front[{index}]"
    if not isinstance(front, dict):
        return None, [Finding("error", "front-not-object", fallback_id, "front entry must be an object")], []

    fid = str(front.get("id") or fallback_id)
    missing = REQUIRED_KEYS - set(front)
    if missing:
        return None, [Finding("error", "missing-required-keys", fid, "missing keys: " + ", ".join(sorted(missing)))], []

    if fid in seen:
        errors.append(Finding("error", "duplicate-front-id", fid, "front id must be unique"))
    seen.add(fid)

    title = front.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append(Finding("error", "invalid-title", fid, "title must be a non-empty string"))
        title = fid

    status = str(front.get("status"))
    if status not in VALID_STATUSES:
        errors.append(Finding("error", "invalid-status", fid, f"invalid status {status!r}; expected one of {sorted(VALID_STATUSES)}"))

    can_claim = front.get("canClaimComplete")
    if not isinstance(can_claim, bool):
        errors.append(Finding("error", "invalid-can-claim-complete", fid, "canClaimComplete must be boolean"))
        can_claim = False

    if can_claim and status != "closed":
        errors.append(Finding("error", "claimable-requires-closed", fid, "canClaimComplete=true requires status=closed"))
    if status == "closed" and can_claim is not True:
        errors.append(Finding("error", "closed-requires-claimable", fid, "status=closed requires canClaimComplete=true"))
    if require_closed and status != "closed":
        errors.append(Finding("error", "require-closed-open-front", fid, f"require-closed requested but status={status}"))

    gate = front.get("closureGate")
    if not isinstance(gate, str) or not gate.strip():
        errors.append(Finding("error", "invalid-closure-gate", fid, "closureGate must be a non-empty string"))
        gate = ""

    for key in ("doneEvidence", "remaining"):
        if not _string_list(front.get(key)):
            errors.append(Finding("error", f"invalid-{key}", fid, f"{key} must be a list of non-empty strings"))

    remaining = front.get("remaining") if isinstance(front.get("remaining"), list) else []
    done = front.get("doneEvidence") if isinstance(front.get("doneEvidence"), list) else []
    if status in OPEN_STATUSES and not remaining:
        errors.append(Finding("error", "open-front-missing-remaining", fid, "non-closed front must list remaining work"))
    if status == "closed" and remaining:
        warnings.append(Finding("warn", "closed-front-has-remaining", fid, "closed front still lists remaining work"))

    next_primitive = front.get("nextPrimitive")
    if not isinstance(next_primitive, str) or not next_primitive.strip():
        errors.append(Finding("error", "invalid-next-primitive", fid, "nextPrimitive must be a non-empty string"))
        next_primitive = ""

    gate_claim = _gate_claimed_passed(front)
    if status == "closed" and require_gates_passed and gate_claim is not True:
        errors.append(Finding("error", "closed-front-missing-gate-evidence", fid, "closed front requires closureGatePassed=true or non-empty gate evidence"))
    if status != "closed":
        warnings.append(Finding("warn", "front-not-closed", fid, f"{status}; next={next_primitive}"))

    summary = FrontSummary(
        id=fid,
        title=str(title),
        status=status,
        can_claim_complete=bool(can_claim),
        closure_gate=str(gate),
        done_evidence_count=len(done),
        remaining_count=len(remaining),
        next_primitive=str(next_primitive),
        gate_claimed_passed=gate_claim,
    )
    return summary, errors, warnings


def _run_gate(project_dir: Path, front: FrontSummary, timeout_seconds: float) -> GateRun:
    try:
        proc = subprocess.run(
            front.closure_gate,
            cwd=str(project_dir),
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
        return GateRun(front.id, front.closure_gate, proc.returncode, _tail(proc.stdout), _tail(proc.stderr))
    except subprocess.TimeoutExpired as exc:
        return GateRun(front.id, front.closure_gate, 124, _tail(exc.stdout or ""), _tail(exc.stderr or f"timed out after {timeout_seconds}s"))


def build_report(
    ledger: Path,
    *,
    project_dir: Path,
    require_closed: bool = False,
    require_gates_passed: bool = False,
    run_closure_gates: bool = False,
    run_all_gates: bool = False,
    timeout_seconds: float = 120,
) -> Report:
    payload = load(ledger)
    findings: list[Finding] = []
    warnings: list[Finding] = []
    gate_runs: list[GateRun] = []

    if payload.get("schemaVersion") != 1:
        findings.append(Finding("error", "invalid-schema-version", "<ledger>", "schemaVersion must be 1"))
    contract = payload.get("contract")
    if contract != CONTRACT:
        findings.append(Finding("error", "invalid-contract", "<ledger>", f"contract must be {CONTRACT}"))

    raw_fronts, field_name = _fronts(payload)
    if not raw_fronts:
        findings.append(Finding("error", "missing-fronts", "<ledger>", "fronts/items must be a non-empty list"))

    seen: set[str] = set()
    fronts: list[FrontSummary] = []
    for index, raw in enumerate(raw_fronts):
        summary, errors, warns = _validate_front(
            raw,
            index,
            require_closed=require_closed,
            require_gates_passed=require_gates_passed,
            seen=seen,
        )
        findings.extend(errors)
        warnings.extend(warns)
        if summary is not None:
            fronts.append(summary)

    if field_name == "items":
        warnings.append(Finding("warn", "items-alias-used", "<ledger>", "items[] is accepted, but fronts[] is the canonical field"))

    if run_closure_gates:
        for front in fronts:
            should_run = run_all_gates or front.status == "closed" or front.can_claim_complete
            if not should_run:
                continue
            run = _run_gate(project_dir, front, timeout_seconds)
            gate_runs.append(run)
            if run.returncode != 0:
                findings.append(Finding("error", "closure-gate-command-failed", front.id, f"closureGate exited {run.returncode}: {front.closure_gate}"))

    status = "pass" if not findings else "fail"
    return Report(
        schema_version=SCHEMA_VERSION,
        ledger=str(ledger),
        contract=str(contract) if isinstance(contract, str) else None,
        status=status,
        total_fronts=len(fronts),
        closed_fronts=sum(1 for item in fronts if item.status == "closed"),
        claimable_fronts=sum(1 for item in fronts if item.can_claim_complete),
        findings=findings,
        warnings=warnings,
        fronts=fronts,
        gate_runs=gate_runs,
    )


def print_summary(report: Report) -> None:
    print(f"contract: {report.contract or '<missing>'}")
    print(f"fronts: {report.closed_fronts}/{report.total_fronts} closed")
    print(f"claimable: {report.claimable_fronts}/{report.total_fronts}")
    for item in report.fronts:
        claim = "claim-complete" if item.can_claim_complete else "do-not-claim-complete"
        print(f"- {item.id}: {item.status} ({claim})")
        if item.status != "closed":
            print(f"  remaining_count: {item.remaining_count}")
            print(f"  next: {item.next_primitive}")
        if item.status == "closed":
            gate = "gate-passed" if item.gate_claimed_passed else "gate-evidence-not-recorded"
            print(f"  closure_gate: {gate}")
    for warning in report.warnings:
        print(f"WARN: {warning.front_id}: {warning.message}", file=sys.stderr)
    for finding in report.findings:
        print(f"FAIL: {finding.front_id}: {finding.message}", file=sys.stderr)
    if report.status == "pass":
        print("PASS: task closure ledger is internally consistent")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path, help="Path to a cos.task-closure-ledger.v1 JSON ledger")
    parser.add_argument("--project-dir", type=Path, default=Path(os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()))
    parser.add_argument("--require-closed", action="store_true", help="Fail unless every front is closed and claimable")
    parser.add_argument("--require-gates-passed", action="store_true", help="Closed fronts must record closureGatePassed=true or gate evidence")
    parser.add_argument("--run-closure-gates", action="store_true", help="Execute closureGate for closed/claimable fronts")
    parser.add_argument("--run-all-gates", action="store_true", help="With --run-closure-gates, execute every front gate, including open fronts")
    parser.add_argument("--timeout-seconds", type=float, default=120)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = build_report(
        args.ledger,
        project_dir=args.project_dir.resolve(),
        require_closed=args.require_closed,
        require_gates_passed=args.require_gates_passed,
        run_closure_gates=args.run_closure_gates,
        run_all_gates=args.run_all_gates,
        timeout_seconds=args.timeout_seconds,
    )
    if args.json:
        print(json.dumps(asdict(report), indent=2, sort_keys=True))
    else:
        print_summary(report)
    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
