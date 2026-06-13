#!/usr/bin/env python3
# SCOPE: both
"""Portable process-loop contract runtime for agent implementation workflows.

This layer sits above the lower-level loop trace primitives. It records the
process contract that a coding agent is following: source issue/spec, selected
skills, apply progress, fresh review findings, verification report, fix-review
loop state, and final verdict.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

PROCESS_SCHEMA = "cos.process-contract.v1"
STATE_SCHEMA = "cos.process-state.v1"
TRACE_SCHEMA = "cos.process-trace.v1"
VERIFY_SCHEMA = "cos.verify-report.v1"
SKILL_SELECTION_SCHEMA = "cos.skill-selection-report.v1"
DEFAULT_PROCESS_ID = "default-process"
BLOCKING_FINDING_SEVERITIES = {"blocker", "critical"}
DONE_STATUSES = {"done", "complete", "completed", "passed", "verified"}
PASS_VERDICTS = {"pass", "passed", "complete", "completed", "success", "succeeded"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sanitize_id(value: str | None, fallback: str = DEFAULT_PROCESS_ID) -> str:
    raw = (value or fallback).strip()
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in raw)
    return safe or fallback


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


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


def load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        if yaml is None:
            raise SystemExit("PyYAML is required for YAML process contracts; use JSON or install PyYAML")
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise SystemExit(f"process contract must be a mapping: {path}")
    return data


def normalize_contract(data: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    contract = dict(data)
    contract.setdefault("schemaVersion", PROCESS_SCHEMA)
    contract.setdefault("id", DEFAULT_PROCESS_ID)
    contract.setdefault("source", {"type": "manual", "ref": "manual"})
    contract.setdefault("goal", {"statement": "Complete the requested process with evidence"})
    contract.setdefault("selectedSkills", [])
    contract.setdefault("applyProgress", {"required": True})
    contract.setdefault("freshReview", {"required": True, "blockOnSeverities": sorted(BLOCKING_FINDING_SEVERITIES)})
    contract.setdefault("verifyReport", {"required": True, "commands": []})
    contract.setdefault("fixReviewLoop", {"requiredForBlockingFindings": True})
    contract.setdefault("finalVerdict", {"requireVerificationPass": True, "requireNoOpenBlockingFindings": True})
    if path is not None:
        contract["_contract_path"] = str(path)
    return contract


def process_paths(project_dir: Path, process_id: str) -> dict[str, Path]:
    root = project_dir.resolve() / ".cognitive-os" / "process-loops" / sanitize_id(process_id)
    return {
        "root": root,
        "contract": root / "contract.json",
        "state": root / "state.json",
        "trace": root / "trace.jsonl",
        "apply": root / "apply-progress.jsonl",
        "review": root / "review-findings.jsonl",
        "verify": root / "verify-report.json",
        "skill_selection": root / "skill-selection-report.json",
        "review_runs": root / "review-runs.jsonl",
        "verdict": root / "final-verdict.json",
    }


def initial_state(contract: dict[str, Any], process_id: str) -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA,
        "process_id": process_id,
        "status": "running",
        "source": contract.get("source"),
        "goal": contract.get("goal"),
        "selected_skills": contract.get("selectedSkills") or [],
        "source_gate": {"required": False, "passed": True, "required_status": None, "actual_status": None},
        "skill_selection": {"ran": False, "recommended": [], "selected": contract.get("selectedSkills") or []},
        "next_recommended": {"action": "apply", "reason": "process-initialized"},
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "apply_progress": {"total": 0, "done": 0, "blocked": 0, "latest": None},
        "review_findings": {"total": 0, "open": 0, "blocking_open": 0},
        "verification": {"ran": False, "all_required_passed": False, "commands": []},
        "final_verdict": None,
    }


def load_state(paths: dict[str, Path], contract: dict[str, Any], process_id: str) -> dict[str, Any]:
    state = load_json(paths["state"], {})
    return state if state else initial_state(contract, process_id)


def trace(paths: dict[str, Path], event: str, payload: dict[str, Any]) -> None:
    row = {"schema_version": TRACE_SCHEMA, "ts": utc_now(), "event": event, **payload}
    append_jsonl(paths["trace"], row)


def summarize_apply(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latest_by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        task_id = str(row.get("task_id") or "")
        if task_id:
            latest_by_id[task_id] = row
    statuses = [str(row.get("status") or "").lower() for row in latest_by_id.values()]
    return {
        "total": len(latest_by_id),
        "done": sum(1 for status in statuses if status in DONE_STATUSES),
        "blocked": sum(1 for status in statuses if status == "blocked"),
        "latest": rows[-1] if rows else None,
    }


def summarize_review(rows: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    latest_by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        finding_id = str(row.get("finding_id") or "")
        if finding_id:
            latest_by_id[finding_id] = row
    block_on = set((contract.get("freshReview") or {}).get("blockOnSeverities") or sorted(BLOCKING_FINDING_SEVERITIES))
    open_rows = [row for row in latest_by_id.values() if str(row.get("status") or "open").lower() != "resolved"]
    blocking_open = [row for row in open_rows if str(row.get("severity") or "").lower() in block_on]
    return {"total": len(latest_by_id), "open": len(open_rows), "blocking_open": len(blocking_open)}


def source_gate(contract: dict[str, Any]) -> dict[str, Any]:
    source = contract.get("source") or {}
    required_status = source.get("requiredStatus") or source.get("required_status") or (contract.get("sourcePolicy") or {}).get("requiredStatus")
    actual_status = source.get("status")
    required = bool(required_status)
    passed = not required or str(actual_status or "").lower() == str(required_status).lower()
    return {
        "required": required,
        "passed": passed,
        "required_status": required_status,
        "actual_status": actual_status,
    }


def load_skill_selection(paths: dict[str, Path], state: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    default = {"ran": False, "recommended": [], "selected": contract.get("selectedSkills") or []}
    report = load_json(paths["skill_selection"], {})
    if report:
        return {
            "ran": True,
            "recommended": report.get("recommended_skills") or [],
            "selected": report.get("selected_skills") or [],
            "stack_signals": report.get("stack_signals") or [],
            "change_signals": report.get("change_signals") or [],
            "report_path": str(paths["skill_selection"]),
        }
    return state.get("skill_selection") or default


def next_recommended_action(state: dict[str, Any], contract: dict[str, Any]) -> dict[str, str]:
    source = state.get("source_gate") or {}
    if source.get("required") and not source.get("passed"):
        return {"action": "source-approval", "reason": "source status has not reached the required approval state"}
    skill_policy = contract.get("skillSelection") or {}
    skill_state = state.get("skill_selection") or {}
    if skill_policy.get("required") and not skill_state.get("ran"):
        return {"action": "skill-selection", "reason": "skill selection report is required before apply"}
    review_policy = contract.get("freshReview") or {}
    review_state = state.get("review_findings") or {}
    if int(review_state.get("blocking_open", 0)) > 0:
        return {"action": "fix-review-findings", "reason": "blocking review findings remain open"}
    apply_policy = contract.get("applyProgress") or {}
    apply_state = state.get("apply_progress") or {}
    if apply_policy.get("required", True):
        if int(apply_state.get("blocked", 0)) > 0:
            return {"action": "fix-apply-blocker", "reason": "apply progress contains blocked tasks"}
        if int(apply_state.get("total", 0)) == 0:
            return {"action": "apply", "reason": "no apply progress has been recorded"}
    if review_policy.get("required", True):
        if int(review_state.get("total", 0)) == 0:
            return {"action": "fresh-review", "reason": "fresh review evidence is required"}
    verify_policy = contract.get("verifyReport") or {}
    verification = state.get("verification") or {}
    if verify_policy.get("required", True):
        if not verification.get("ran"):
            return {"action": "verify", "reason": "verification has not run"}
        if not verification.get("all_required_passed"):
            return {"action": "fix-verification", "reason": "required verification did not pass"}
    verdict = state.get("final_verdict")
    if not verdict:
        return {"action": "final-verdict", "reason": "all gates are satisfied; record final verdict"}
    if verdict == "blocked":
        return {"action": "blocked", "reason": "final verdict is blocked"}
    return {"action": "done", "reason": "final verdict recorded"}


def refresh_state(paths: dict[str, Path], contract: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    state["source_gate"] = source_gate(contract)
    state["skill_selection"] = load_skill_selection(paths, state, contract)
    state["apply_progress"] = summarize_apply(load_jsonl(paths["apply"]))
    state["review_findings"] = summarize_review(load_jsonl(paths["review"]), contract)
    state["verification"] = load_json(paths["verify"], state.get("verification") or {"ran": False, "all_required_passed": False, "commands": []})
    state["final_verdict"] = load_json(paths["verdict"], {}).get("verdict") if paths["verdict"].exists() else state.get("final_verdict")
    state["next_recommended"] = next_recommended_action(state, contract)
    state["updated_at"] = utc_now()
    write_json(paths["state"], state)
    return state


def contract_from_args(project_dir: Path, process_id: str, contract_path: str | None) -> tuple[dict[str, Any], dict[str, Path]]:
    paths = process_paths(project_dir, process_id)
    if contract_path:
        contract = normalize_contract(load_mapping(Path(contract_path).resolve()), Path(contract_path).resolve())
    elif paths["contract"].exists():
        contract = normalize_contract(load_json(paths["contract"]), paths["contract"])
    else:
        contract = normalize_contract({"id": process_id})
    return contract, paths


def output(payload: dict[str, Any], as_json: bool) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True) if as_json else payload.get("message", json.dumps(payload, sort_keys=True)))


def command_process_init(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    if args.contract:
        contract = normalize_contract(load_mapping(Path(args.contract).resolve()), Path(args.contract).resolve())
    else:
        contract = normalize_contract({
            "id": args.process_id or DEFAULT_PROCESS_ID,
            "source": {"type": args.source_type, "ref": args.source_ref},
            "goal": {"statement": args.goal},
            "selectedSkills": args.skill or [],
        })
    process_id = sanitize_id(args.process_id or str(contract.get("id") or DEFAULT_PROCESS_ID))
    contract["id"] = process_id
    paths = process_paths(project_dir, process_id)
    write_json(paths["contract"], {k: v for k, v in contract.items() if not str(k).startswith("_")})
    state = initial_state(contract, process_id)
    write_json(paths["state"], state)
    trace(paths, "process.init", {"process_id": process_id, "source": contract.get("source"), "selected_skills": contract.get("selectedSkills") or []})
    output({"status": "initialized", "process_id": process_id, "state_path": str(paths["state"]), "message": f"process={process_id} initialized"}, args.json)
    return 0


def command_process_report(args: argparse.Namespace) -> int:
    process_id = sanitize_id(args.process_id)
    contract, paths = contract_from_args(Path(args.project_dir).resolve(), process_id, args.contract)
    state = refresh_state(paths, contract, load_state(paths, contract, process_id))
    payload = {"schema_version": "cos.process-report.v1", **state, "paths": {name: str(path) for name, path in paths.items() if name != "root"}}
    output(payload, args.json)
    return 0


def command_process_verdict(args: argparse.Namespace) -> int:
    process_id = sanitize_id(args.process_id)
    contract, paths = contract_from_args(Path(args.project_dir).resolve(), process_id, args.contract)
    state = refresh_state(paths, contract, load_state(paths, contract, process_id))
    requested = str(args.status).lower()
    final_policy = contract.get("finalVerdict") or {}
    blockers: list[str] = []
    if requested in PASS_VERDICTS:
        if (state.get("source_gate") or {}).get("required") and not (state.get("source_gate") or {}).get("passed"):
            blockers.append("source-status-not-approved")
        if (contract.get("skillSelection") or {}).get("required") and not (state.get("skill_selection") or {}).get("ran"):
            blockers.append("skill-selection-not-recorded")
        if final_policy.get("requireVerificationPass", True) and not bool((state.get("verification") or {}).get("all_required_passed")):
            blockers.append("verification-not-passed")
        if final_policy.get("requireNoOpenBlockingFindings", True) and int((state.get("review_findings") or {}).get("blocking_open", 0)) > 0:
            blockers.append("open-blocking-review-findings")
        if int((state.get("apply_progress") or {}).get("blocked", 0)) > 0:
            blockers.append("blocked-apply-progress")
    verdict = "blocked" if blockers else requested
    payload = {"schema_version": "cos.final-verdict.v1", "process_id": process_id, "verdict": verdict, "requested_status": requested, "summary": args.summary, "blockers": blockers, "updated_at": utc_now()}
    write_json(paths["verdict"], payload)
    trace(paths, "process.verdict", payload)
    state["status"] = verdict
    state["final_verdict"] = verdict
    state["next_recommended"] = next_recommended_action(state, contract)
    write_json(paths["state"], state)
    output(payload, args.json)
    return 2 if blockers else 0


def command_apply_record(args: argparse.Namespace) -> int:
    process_id = sanitize_id(args.process_id)
    contract, paths = contract_from_args(Path(args.project_dir).resolve(), process_id, args.contract)
    state = load_state(paths, contract, process_id)
    row = {
        "ts": utc_now(),
        "process_id": process_id,
        "task_id": args.task_id,
        "title": args.title,
        "status": args.status,
        "evidence": args.evidence,
        "notes": args.notes,
    }
    append_jsonl(paths["apply"], row)
    trace(paths, "apply.progress", row)
    state = refresh_state(paths, contract, state)
    output({"status": "recorded", "process_id": process_id, "apply_progress": state["apply_progress"], "message": f"task={args.task_id} status={args.status}"}, args.json)
    return 0


def command_review_finding(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    process_id = sanitize_id(args.process_id)
    contract, paths = contract_from_args(project_dir, process_id, args.contract)
    state = load_state(paths, contract, process_id)
    timeout = int(args.timeout_seconds or (contract.get("freshReview") or {}).get("timeoutSeconds") or 120)
    if args.command:
        results: list[dict[str, Any]] = []
        all_passed = True
        for index, command in enumerate(args.command, 1):
            started = time.time()
            proc = subprocess.run(command, cwd=project_dir, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
            elapsed = round(time.time() - started, 3)
            passed = proc.returncode == 0
            all_passed = all_passed and passed
            finding_id = args.finding_id or f"{args.adapter_id}-{index}"
            result = {
                "ts": utc_now(),
                "process_id": process_id,
                "adapter_id": args.adapter_id,
                "finding_id": finding_id,
                "severity": args.severity,
                "status": "resolved" if passed else args.status,
                "summary": args.summary or f"fresh review command {'passed' if passed else 'failed'}: {command}",
                "file": args.file,
                "line": args.line,
                "recommendation": args.recommendation,
                "command": command,
                "returncode": proc.returncode,
                "passed": passed,
                "elapsed_seconds": elapsed,
                "stdout_tail": proc.stdout[-2000:],
                "stderr_tail": proc.stderr[-2000:],
            }
            append_jsonl(paths["review"], result)
            append_jsonl(paths["review_runs"], result)
            trace(paths, "fresh_review.command", result)
            results.append(result)
        state = refresh_state(paths, contract, state)
        payload = {
            "status": "passed" if all_passed else "blocked",
            "process_id": process_id,
            "all_passed": all_passed,
            "commands": results,
            "review_findings": state["review_findings"],
        }
        output(payload, args.json)
        return 0 if all_passed else 2
    if not args.finding_id:
        raise SystemExit("--finding-id is required when --command is not provided")
    if not args.summary:
        raise SystemExit("--summary is required when --command is not provided")
    row = {
        "ts": utc_now(),
        "process_id": process_id,
        "finding_id": args.finding_id,
        "severity": args.severity,
        "status": args.status,
        "summary": args.summary,
        "file": args.file,
        "line": args.line,
        "recommendation": args.recommendation,
    }
    append_jsonl(paths["review"], row)
    trace(paths, "fresh_review.finding", row)
    state = refresh_state(paths, contract, state)
    output({"status": "recorded", "process_id": process_id, "review_findings": state["review_findings"], "message": f"finding={args.finding_id} status={args.status}"}, args.json)
    return 0


def existing_skill_names(project_dir: Path) -> set[str]:
    names: set[str] = set()
    for base in (
        project_dir / "skills",
        project_dir / ".cognitive-os" / "skills",
        project_dir / ".cognitive-os" / "skills" / "cos",
        project_dir / ".claude" / "skills",
    ):
        if not base.exists():
            continue
        for child in base.iterdir():
            if child.is_dir() and (child / "SKILL.md").exists():
                names.add(child.name)
    return names


def detect_stack_signals(project_dir: Path) -> list[str]:
    checks = {
        "node": ["package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json"],
        "python": ["pyproject.toml", "requirements.txt", "setup.py", "tox.ini"],
        "go": ["go.mod"],
        "rust": ["Cargo.toml"],
        "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "storybook": [".storybook/main.js", ".storybook/main.ts", ".storybook/main.cjs"],
        "docker": ["Dockerfile", "docker-compose.yml", "compose.yaml"],
    }
    signals = [name for name, rels in checks.items() if any((project_dir / rel).exists() for rel in rels)]
    package_json = project_dir / "package.json"
    if package_json.exists():
        text = package_json.read_text(encoding="utf-8", errors="ignore")
        if any(token in text for token in ('"react"', '"next"', '"vue"', '"svelte"', '"vite"')):
            signals.append("frontend")
        if any(token in text for token in ('"express"', '"fastify"', '"nestjs"', '"hono"')):
            signals.append("backend")
    suffixes = bounded_suffix_scan(project_dir, {".tsx", ".jsx", ".stories.ts", ".stories.tsx", ".stories.js", ".stories.jsx"})
    if suffixes & {".tsx", ".jsx"}:
        signals.append("frontend")
        signals.append("component")
    if any(suffix.startswith(".stories.") for suffix in suffixes):
        signals.append("storybook")
    return sorted(set(signals))


def bounded_suffix_scan(project_dir: Path, suffixes: set[str], *, max_files: int = 2000) -> set[str]:
    ignored = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist", "build", ".next", "target", "__pycache__"}
    found: set[str] = set()
    visited = 0
    for root, dirnames, filenames in os.walk(project_dir):
        dirnames[:] = [name for name in dirnames if name not in ignored and not name.startswith(".pytest")]
        for filename in filenames:
            visited += 1
            lower = filename.lower()
            for suffix in suffixes:
                if lower.endswith(suffix):
                    found.add(suffix)
            if visited >= max_files:
                return found
    return found


def detect_change_signals(changed_files: list[str]) -> list[str]:
    signals: set[str] = set()
    for raw in changed_files:
        path = raw.lower()
        if path.endswith((".tsx", ".jsx", ".vue", ".svelte", ".css", ".scss")):
            signals.update({"frontend", "component"})
        if ".stories." in path or "/storybook" in path or path.startswith(".storybook/"):
            signals.add("storybook")
        if path.endswith((".py", ".go", ".rs", ".java", ".kt", ".ts", ".js")) and not path.endswith((".tsx", ".jsx")):
            signals.add("backend")
        if "/test" in path or path.endswith(("_test.go", "_test.py", ".test.ts", ".spec.ts", ".test.js", ".spec.js")):
            signals.add("tests")
        if path.endswith((".md", ".mdx", ".rst")):
            signals.add("docs")
    return sorted(signals)


def recommend_skills(stack_signals: list[str], change_signals: list[str], available: set[str]) -> list[dict[str, Any]]:
    wanted: list[tuple[str, str]] = [
        ("plan-feature", "default planning contract for non-trivial implementation"),
        ("run-tests", "verification runner for changed surfaces"),
        ("code-review", "fresh review policy after implementation"),
    ]
    combined = set(stack_signals) | set(change_signals)
    if "frontend" in combined:
        wanted.append(("frontend-dod", "frontend stack or UI files detected"))
    if "backend" in combined or {"python", "go", "rust", "java"} & combined:
        wanted.append(("backend-dod", "backend or service files detected"))
    if "component" in combined:
        wanted.append(("component-dod", "component files detected"))
    if "storybook" in combined:
        wanted.append(("storybook-dod", "storybook files or configuration detected"))
    if "docs" in combined:
        wanted.append(("doc-review-personas", "documentation files detected"))
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name, reason in wanted:
        if name in seen:
            continue
        seen.add(name)
        results.append({"name": name, "reason": reason, "available": name in available})
    return results


def git_changed_files(project_dir: Path) -> list[str]:
    proc = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=project_dir, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def command_skill_selection_report(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    process_id = sanitize_id(args.process_id)
    contract, paths = contract_from_args(project_dir, process_id, args.contract)
    changed_files = list(args.changed_file or [])
    if args.from_git_diff:
        changed_files.extend(git_changed_files(project_dir))
    stack_signals = detect_stack_signals(project_dir)
    change_signals = detect_change_signals(changed_files)
    available = existing_skill_names(project_dir)
    recommendations = recommend_skills(stack_signals, change_signals, available)
    selected = [item["name"] for item in recommendations if item["available"]]
    if not selected:
        selected = contract.get("selectedSkills") or [item["name"] for item in recommendations[:3]]
    report = {
        "schema_version": SKILL_SELECTION_SCHEMA,
        "process_id": process_id,
        "stack_signals": stack_signals,
        "change_signals": change_signals,
        "changed_files": sorted(set(changed_files)),
        "available_skills": sorted(available),
        "recommended_skills": recommendations,
        "selected_skills": selected,
        "updated_at": utc_now(),
    }
    write_json(paths["skill_selection"], report)
    trace(paths, "skill_selection.report", {"process_id": process_id, "selected_skills": selected, "stack_signals": stack_signals, "change_signals": change_signals})
    state = refresh_state(paths, contract, load_state(paths, contract, process_id))
    payload = {**report, "next_recommended": state["next_recommended"]}
    output(payload, args.json)
    return 0


def verification_commands(contract: dict[str, Any], cli_commands: list[str]) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    for index, command in enumerate(cli_commands, 1):
        commands.append({"id": f"cli-{index}", "command": command, "required": True})
    if commands:
        return commands
    verify = contract.get("verifyReport") or {}
    for index, item in enumerate(verify.get("commands") or [], 1):
        if isinstance(item, str):
            commands.append({"id": f"verify-{index}", "command": item, "required": True})
        elif isinstance(item, dict) and str(item.get("command") or "").strip():
            commands.append({"id": str(item.get("id") or f"verify-{index}"), "command": str(item["command"]), "required": bool(item.get("required", True))})
    return commands


def command_verify_run(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    process_id = sanitize_id(args.process_id)
    contract, paths = contract_from_args(project_dir, process_id, args.contract)
    state = load_state(paths, contract, process_id)
    commands = verification_commands(contract, args.command or [])
    timeout = int(args.timeout_seconds or (contract.get("verifyReport") or {}).get("timeoutSeconds") or 120)
    results: list[dict[str, Any]] = []
    all_required_passed = True
    for item in commands:
        started = time.time()
        proc = subprocess.run(item["command"], cwd=project_dir, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
        elapsed = round(time.time() - started, 3)
        passed = proc.returncode == 0
        if item.get("required", True) and not passed:
            all_required_passed = False
        results.append({
            "id": item["id"],
            "command": item["command"],
            "required": bool(item.get("required", True)),
            "returncode": proc.returncode,
            "passed": passed,
            "elapsed_seconds": elapsed,
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
        })
    if not results:
        all_required_passed = False
    report = {"schema_version": VERIFY_SCHEMA, "process_id": process_id, "ran": bool(results), "all_required_passed": all_required_passed, "commands": results, "updated_at": utc_now()}
    write_json(paths["verify"], report)
    trace(paths, "verify.report", {"process_id": process_id, "ran": report["ran"], "all_required_passed": all_required_passed, "command_count": len(results)})
    state["verification"] = report
    refresh_state(paths, contract, state)
    output(report, args.json)
    return 0 if all_required_passed else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cognitive OS process-loop contract primitives")
    sub = parser.add_subparsers(dest="command", required=True)

    proc = sub.add_parser("process-loop")
    proc_sub = proc.add_subparsers(dest="process_command", required=True)
    init = proc_sub.add_parser("init")
    init.add_argument("--project-dir", default=os.getcwd())
    init.add_argument("--contract")
    init.add_argument("--process-id")
    init.add_argument("--source-type", default="manual")
    init.add_argument("--source-ref", default="manual")
    init.add_argument("--goal", default="Complete the requested process with evidence")
    init.add_argument("--skill", action="append")
    init.add_argument("--json", action="store_true")
    init.set_defaults(func=command_process_init)
    report = proc_sub.add_parser("report")
    report.add_argument("--project-dir", default=os.getcwd())
    report.add_argument("--process-id", required=True)
    report.add_argument("--contract")
    report.add_argument("--json", action="store_true")
    report.set_defaults(func=command_process_report)
    verdict = proc_sub.add_parser("verdict")
    verdict.add_argument("--project-dir", default=os.getcwd())
    verdict.add_argument("--process-id", required=True)
    verdict.add_argument("--contract")
    verdict.add_argument("--status", required=True)
    verdict.add_argument("--summary", default="")
    verdict.add_argument("--json", action="store_true")
    verdict.set_defaults(func=command_process_verdict)

    apply = sub.add_parser("apply-progress")
    apply.add_argument("--project-dir", default=os.getcwd())
    apply.add_argument("--process-id", required=True)
    apply.add_argument("--contract")
    apply.add_argument("--task-id", required=True)
    apply.add_argument("--title", required=True)
    apply.add_argument("--status", required=True)
    apply.add_argument("--evidence", default="")
    apply.add_argument("--notes", default="")
    apply.add_argument("--json", action="store_true")
    apply.set_defaults(func=command_apply_record)

    review = sub.add_parser("fresh-review")
    review.add_argument("--project-dir", default=os.getcwd())
    review.add_argument("--process-id", required=True)
    review.add_argument("--contract")
    review.add_argument("--finding-id")
    review.add_argument("--severity", default="major")
    review.add_argument("--status", default="open")
    review.add_argument("--summary", default="")
    review.add_argument("--file", default="")
    review.add_argument("--line", type=int)
    review.add_argument("--recommendation", default="")
    review.add_argument("--command", action="append")
    review.add_argument("--adapter-id", default="command-review")
    review.add_argument("--timeout-seconds", type=int)
    review.add_argument("--json", action="store_true")
    review.set_defaults(func=command_review_finding)

    skill_selection = sub.add_parser("skill-selection-report")
    skill_selection.add_argument("--project-dir", default=os.getcwd())
    skill_selection.add_argument("--process-id", required=True)
    skill_selection.add_argument("--contract")
    skill_selection.add_argument("--changed-file", action="append")
    skill_selection.add_argument("--from-git-diff", action="store_true")
    skill_selection.add_argument("--json", action="store_true")
    skill_selection.set_defaults(func=command_skill_selection_report)

    verify = sub.add_parser("verify-report")
    verify.add_argument("--project-dir", default=os.getcwd())
    verify.add_argument("--process-id", required=True)
    verify.add_argument("--contract")
    verify.add_argument("--command", action="append")
    verify.add_argument("--timeout-seconds", type=int)
    verify.add_argument("--json", action="store_true")
    verify.set_defaults(func=command_verify_run)
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
