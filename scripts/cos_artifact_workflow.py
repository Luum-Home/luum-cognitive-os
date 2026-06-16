#!/usr/bin/env python3
# SCOPE: both
"""Portable artifact, work-graph, refutation, and advisor primitives.

These primitives provide a generic filesystem-backed operating loop for any
project/harness: ingest artifacts, dedupe work by fingerprint, track tasks,
challenge claims through a refutation loop, and run bounded second-pass advisor
commands with receipts. They are advisory by default and intentionally avoid any
security-domain behavior.
"""
from __future__ import annotations

import argparse
import hashlib
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

ARTIFACT_SCHEMA = "cos.artifact-ledger.v1"
WORK_GRAPH_SCHEMA = "cos.work-graph.v1"
REFUTATION_SCHEMA = "cos.refutation-review.v1"
ADVISOR_SCHEMA = "cos.second-pass-advisor.v1"
TEXT_EXTENSIONS = {
    ".txt", ".md", ".mdx", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt",
    ".rb", ".php", ".cs", ".swift", ".sh", ".sql", ".css", ".scss", ".html",
    ".xml", ".csv", ".log", ".patch", ".diff", ".http",
}
IGNORED_DIRS = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist", "build", "target", "__pycache__", ".pytest_cache"}
DONE_STATUSES = {"done", "complete", "completed", "passed", "verified"}
OPEN_STATUSES = {"open", "blocked", "todo", "pending", "running"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sanitize_id(value: str | None, fallback: str = "default") -> str:
    raw = (value or fallback).strip()
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in raw)
    return safe or fallback


def project_root(path: str | None) -> Path:
    return Path(path or os.getcwd()).resolve()


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def is_ignored(path: Path, root: Path) -> bool:
    parts = rel(path, root).split(os.sep)
    return any(part in IGNORED_DIRS for part in parts)


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload.get("message") or json.dumps(payload, sort_keys=True))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def artifact_paths(root: Path) -> dict[str, Path]:
    base = root / ".cognitive-os" / "artifacts"
    return {"root": base, "ledger": base / "ledger.json", "events": base / "events.jsonl"}


def work_paths(root: Path, graph_id: str) -> dict[str, Path]:
    base = root / ".cognitive-os" / "work-graphs" / sanitize_id(graph_id, "default-graph")
    return {"root": base, "state": base / "state.json", "events": base / "events.jsonl"}


def process_paths(root: Path, process_id: str) -> dict[str, Path]:
    base = root / ".cognitive-os" / "process-loops" / sanitize_id(process_id, "default-process")
    return {"root": base, "review": base / "review-findings.jsonl", "refutations": base / "refutation-review.jsonl", "advisor": base / "advisor-receipts.jsonl"}


def should_treat_as_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def summarize_text(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    lowered = text.lower()
    signals: list[str] = []
    for token, signal in [
        ("todo", "todo-marker"),
        ("fixme", "fixme-marker"),
        ("error", "error-text"),
        ("failed", "failure-text"),
        ("claim", "claim-text"),
        ("verified", "verification-text"),
        ("warning", "warning-text"),
    ]:
        if token in lowered:
            signals.append(signal)
    return {"line_count": len(lines), "signals": sorted(set(signals)), "preview": "\n".join(lines[:5])[:1000]}


def artifact_record(path: Path, root: Path) -> dict[str, Any]:
    data = path.read_bytes()
    stat = path.stat()
    content_hash = sha256_bytes(data)
    metadata: dict[str, Any] = {}
    parse_status = "binary-skipped"
    if should_treat_as_text(path):
        text = data.decode("utf-8", errors="ignore")
        metadata.update(summarize_text(text))
        parse_status = "parsed-text"
        if path.suffix.lower() == ".json":
            try:
                parsed = json.loads(text)
                metadata["json_type"] = type(parsed).__name__
                if isinstance(parsed, dict):
                    metadata["json_keys"] = sorted(str(k) for k in list(parsed)[:25])
                parse_status = "parsed-json"
            except Exception as exc:
                metadata["parse_error"] = str(exc)[:500]
                parse_status = "parse-error"
        elif path.suffix.lower() in {".yaml", ".yml"} and yaml is not None:
            try:
                parsed = yaml.safe_load(text)
                metadata["yaml_type"] = type(parsed).__name__
                if isinstance(parsed, dict):
                    metadata["yaml_keys"] = sorted(str(k) for k in list(parsed)[:25])
                parse_status = "parsed-yaml"
            except Exception as exc:
                metadata["parse_error"] = str(exc)[:500]
                parse_status = "parse-error"
    return {
        "path": rel(path, root),
        "absolute_path": str(path.resolve()),
        "fingerprint": content_hash,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "suffix": path.suffix.lower(),
        "parse_status": parse_status,
        "metadata": metadata,
        "updated_at": utc_now(),
    }


def load_artifact_ledger(root: Path) -> dict[str, Any]:
    paths = artifact_paths(root)
    ledger = read_json(paths["ledger"], {})
    if not ledger:
        ledger = {"schema_version": ARTIFACT_SCHEMA, "project_root": str(root), "artifacts": {}, "fingerprints": {}, "updated_at": utc_now()}
    return ledger


def save_artifact_ledger(root: Path, ledger: dict[str, Any]) -> None:
    ledger["updated_at"] = utc_now()
    write_json(artifact_paths(root)["ledger"], ledger)


def iter_artifact_files(root: Path, artifact_dir: Path, max_files: int) -> list[Path]:
    files: list[Path] = []
    if artifact_dir.is_file():
        return [artifact_dir]
    for path in sorted(artifact_dir.rglob("*")):
        if len(files) >= max_files:
            break
        if path.is_dir() or is_ignored(path, root):
            continue
        files.append(path)
    return files


def ingest_files(root: Path, files: list[Path]) -> dict[str, Any]:
    ledger = load_artifact_ledger(root)
    added = 0
    updated = 0
    unchanged = 0
    duplicates = 0
    records: list[dict[str, Any]] = []
    for path in files:
        if not path.exists() or path.is_dir():
            continue
        record = artifact_record(path.resolve(), root)
        key = record["path"]
        previous = ledger["artifacts"].get(key)
        if previous and previous.get("fingerprint") == record["fingerprint"] and previous.get("mtime_ns") == record["mtime_ns"]:
            unchanged += 1
            records.append({**record, "ingest_status": "unchanged"})
            continue
        status = "added" if not previous else "updated"
        if record["fingerprint"] in ledger.get("fingerprints", {}) and key not in ledger["fingerprints"][record["fingerprint"]]:
            duplicates += 1
        ledger["artifacts"][key] = record
        ledger.setdefault("fingerprints", {}).setdefault(record["fingerprint"], [])
        if key not in ledger["fingerprints"][record["fingerprint"]]:
            ledger["fingerprints"][record["fingerprint"]].append(key)
        append_jsonl(artifact_paths(root)["events"], {"ts": utc_now(), "event": "artifact.ingested", "status": status, "artifact": key, "fingerprint": record["fingerprint"]})
        added += 1 if status == "added" else 0
        updated += 1 if status == "updated" else 0
        records.append({**record, "ingest_status": status})
    save_artifact_ledger(root, ledger)
    return {"schema_version": ARTIFACT_SCHEMA, "project_root": str(root), "added": added, "updated": updated, "unchanged": unchanged, "duplicates": duplicates, "artifacts": records, "ledger_path": str(artifact_paths(root)["ledger"])}


def command_artifact_ingest(args: argparse.Namespace) -> int:
    root = project_root(args.project_dir)
    files: list[Path] = []
    for raw in args.artifact or []:
        files.append(Path(raw).resolve())
    for raw in args.artifact_dir or []:
        files.extend(iter_artifact_files(root, Path(raw).resolve(), args.max_files))
    payload = ingest_files(root, files)
    payload["message"] = f"ingested added={payload['added']} updated={payload['updated']} unchanged={payload['unchanged']} duplicates={payload['duplicates']}"
    emit(payload, args.json)
    return 0


def command_artifact_watch(args: argparse.Namespace) -> int:
    root = project_root(args.project_dir)
    cycles: list[dict[str, Any]] = []
    for _ in range(args.max_cycles):
        files = iter_artifact_files(root, Path(args.artifact_dir).resolve(), args.max_files)
        result = ingest_files(root, files)
        cycles.append({k: result[k] for k in ("added", "updated", "unchanged", "duplicates", "ledger_path")})
        if args.interval_seconds > 0 and args.max_cycles > 1:
            time.sleep(args.interval_seconds)
    payload = {"schema_version": "cos.artifact-watch.v1", "project_root": str(root), "cycles": cycles, "message": f"watch cycles={len(cycles)} latest_added={cycles[-1]['added'] if cycles else 0}"}
    emit(payload, args.json)
    return 0


def artifact_report(root: Path) -> dict[str, Any]:
    ledger = load_artifact_ledger(root)
    artifacts = list((ledger.get("artifacts") or {}).values())
    by_status: dict[str, int] = {}
    signal_counts: dict[str, int] = {}
    duplicates = 0
    for record in artifacts:
        by_status[record.get("parse_status", "unknown")] = by_status.get(record.get("parse_status", "unknown"), 0) + 1
        for signal in (record.get("metadata") or {}).get("signals") or []:
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
    for paths in (ledger.get("fingerprints") or {}).values():
        if isinstance(paths, list) and len(paths) > 1:
            duplicates += len(paths) - 1
    return {"schema_version": "cos.artifact-report.v1", "project_root": str(root), "artifact_count": len(artifacts), "parse_status_counts": by_status, "signal_counts": signal_counts, "duplicate_count": duplicates, "ledger_path": str(artifact_paths(root)["ledger"])}


def command_artifact_report(args: argparse.Namespace) -> int:
    root = project_root(args.project_dir)
    payload = artifact_report(root)
    payload["message"] = f"artifacts={payload['artifact_count']} duplicates={payload['duplicate_count']}"
    emit(payload, args.json)
    return 0


def task_fingerprint(title: str, payload: str = "") -> str:
    normalized = " ".join((title + "\n" + payload).lower().split())
    return sha256_bytes(normalized.encode("utf-8"))


def load_work_graph(root: Path, graph_id: str) -> dict[str, Any]:
    paths = work_paths(root, graph_id)
    graph = read_json(paths["state"], {})
    if not graph:
        graph = {"schema_version": WORK_GRAPH_SCHEMA, "graph_id": sanitize_id(graph_id, "default-graph"), "tasks": {}, "fingerprints": {}, "updated_at": utc_now()}
    return graph


def save_work_graph(root: Path, graph: dict[str, Any]) -> None:
    graph["updated_at"] = utc_now()
    write_json(work_paths(root, graph["graph_id"])["state"], graph)


def summarize_work_graph(graph: dict[str, Any]) -> dict[str, Any]:
    tasks = list((graph.get("tasks") or {}).values())
    statuses: dict[str, int] = {}
    for task in tasks:
        status = str(task.get("status") or "pending")
        statuses[status] = statuses.get(status, 0) + 1
    next_task = None
    candidates = [task for task in tasks if str(task.get("status") or "pending") in {"pending", "blocked"}]
    if candidates:
        next_task = sorted(candidates, key=lambda t: (-int(t.get("priority") or 0), str(t.get("created_at") or ""), str(t.get("task_id") or "")))[0]
    return {"task_count": len(tasks), "status_counts": statuses, "next_task": next_task}


def command_work_graph(args: argparse.Namespace) -> int:
    root = project_root(args.project_dir)
    graph_id = sanitize_id(args.graph_id, "default-graph")
    graph = load_work_graph(root, graph_id)
    event: dict[str, Any] | None = None
    rc = 0
    if args.graph_action == "add":
        if not args.title:
            raise SystemExit("work-graph add requires --title")
        fingerprint = args.fingerprint or task_fingerprint(args.title, args.payload or "")
        duplicate_of = graph.get("fingerprints", {}).get(fingerprint)
        task_id = sanitize_id(args.task_id or f"T{len(graph['tasks']) + 1}", f"T{len(graph['tasks']) + 1}")
        if duplicate_of and not args.allow_duplicate:
            event = {"event": "work_graph.duplicate", "task_id": task_id, "duplicate_of": duplicate_of, "fingerprint": fingerprint}
            rc = 2
        else:
            task = {"task_id": task_id, "title": args.title, "status": args.status, "priority": args.priority, "fingerprint": fingerprint, "payload": args.payload or "", "evidence": args.evidence or "", "created_at": utc_now(), "updated_at": utc_now()}
            graph["tasks"][task_id] = task
            graph.setdefault("fingerprints", {})[fingerprint] = task_id
            event = {"event": "work_graph.add", "task_id": task_id, "fingerprint": fingerprint}
    elif args.graph_action == "update":
        if not args.task_id or args.task_id not in graph.get("tasks", {}):
            raise SystemExit("work-graph update requires an existing --task-id")
        task = graph["tasks"][args.task_id]
        if args.status:
            task["status"] = args.status
        if args.evidence:
            task["evidence"] = args.evidence
        task["updated_at"] = utc_now()
        event = {"event": "work_graph.update", "task_id": args.task_id, "status": task.get("status")}
    elif args.graph_action == "next":
        event = {"event": "work_graph.next"}
    elif args.graph_action == "report":
        event = {"event": "work_graph.report"}
    save_work_graph(root, graph)
    if event:
        append_jsonl(work_paths(root, graph_id)["events"], {"ts": utc_now(), **event})
    summary = summarize_work_graph(graph)
    payload = {"schema_version": WORK_GRAPH_SCHEMA, "graph_id": graph_id, **summary, "state_path": str(work_paths(root, graph_id)["state"]), "event": event, "message": f"graph={graph_id} tasks={summary['task_count']}"}
    emit(payload, args.json)
    return rc


def run_shell(command: str, cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.time()
    proc = subprocess.run(command, cwd=cwd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
    return {"command": command, "returncode": proc.returncode, "passed": proc.returncode == 0, "elapsed_seconds": round(time.time() - started, 3), "stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-2000:]}


def command_refutation_review(args: argparse.Namespace) -> int:
    root = project_root(args.project_dir)
    process_id = sanitize_id(args.process_id, "default-process")
    evidence_items = list(args.evidence or [])
    refutations: list[str] = []
    confidence = int(args.initial_confidence)
    if not evidence_items:
        refutations.append("claim has no explicit evidence")
        confidence -= 30
    if args.verification_command:
        try:
            result = run_shell(args.verification_command, root, args.timeout_seconds)
        except subprocess.TimeoutExpired:
            result = {"command": args.verification_command, "returncode": 124, "passed": False, "elapsed_seconds": args.timeout_seconds, "stdout_tail": "", "stderr_tail": "timeout"}
        if result["passed"]:
            confidence += 15
        else:
            confidence -= 35
            refutations.append("verification command did not pass")
    else:
        result = None
        refutations.append("no verification command supplied")
        confidence -= 10
    confidence = max(0, min(100, confidence))
    verdict = "supported" if confidence >= args.pass_threshold and not refutations else "needs-review"
    severity = "major" if verdict != "supported" else "info"
    row = {"schema_version": REFUTATION_SCHEMA, "ts": utc_now(), "process_id": process_id, "claim_id": sanitize_id(args.claim_id, "claim"), "claim": args.claim, "evidence": evidence_items, "refutations": refutations, "verification": result, "confidence": confidence, "pass_threshold": args.pass_threshold, "verdict": verdict}
    paths = process_paths(root, process_id)
    append_jsonl(paths["refutations"], row)
    if args.record_fresh_review and verdict != "supported":
        finding = {"ts": utc_now(), "process_id": process_id, "finding_id": f"refutation-{row['claim_id']}", "severity": severity, "status": "open", "summary": f"Claim needs review: {args.claim}", "recommendation": "; ".join(refutations), "source": "cos-refutation-review", "confidence": confidence}
        append_jsonl(paths["review"], finding)
    payload = {**row, "refutation_path": str(paths["refutations"]), "message": f"claim={row['claim_id']} verdict={verdict} confidence={confidence}"}
    emit(payload, args.json)
    return 0 if verdict == "supported" else 2


def command_second_pass_advisor(args: argparse.Namespace) -> int:
    root = project_root(args.project_dir)
    process_id = sanitize_id(args.process_id, "default-process")
    signals = list(args.signal or [])
    should_run = args.force or len(signals) >= args.min_signals
    receipt = {"schema_version": ADVISOR_SCHEMA, "ts": utc_now(), "process_id": process_id, "advisor_id": args.advisor_id, "signals": signals, "min_signals": args.min_signals, "triggered": should_run, "read_only_required": True, "timeout_seconds": args.timeout_seconds, "command": args.command or "", "result": None}
    rc = 0
    if should_run and args.command:
        try:
            receipt["result"] = run_shell(args.command, root, args.timeout_seconds)
            rc = 0 if receipt["result"]["passed"] else 2
        except subprocess.TimeoutExpired:
            receipt["result"] = {"command": args.command, "returncode": 124, "passed": False, "elapsed_seconds": args.timeout_seconds, "stdout_tail": "", "stderr_tail": "timeout"}
            rc = 2
    elif should_run and not args.command:
        receipt["result"] = {"passed": False, "reason": "triggered-without-command"}
        rc = 2
    paths = process_paths(root, process_id)
    append_jsonl(paths["advisor"], receipt)
    payload = {**receipt, "receipt_path": str(paths["advisor"]), "message": f"advisor={args.advisor_id} triggered={should_run} rc={rc}"}
    emit(payload, args.json)
    return rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cognitive OS artifact/workgraph/refutation/advisor primitives")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("artifact-ingest")
    ingest.add_argument("--project-dir", default=os.getcwd())
    ingest.add_argument("--artifact", action="append")
    ingest.add_argument("--artifact-dir", action="append")
    ingest.add_argument("--max-files", type=int, default=1000)
    ingest.add_argument("--json", action="store_true")
    ingest.set_defaults(func=command_artifact_ingest)

    watch = sub.add_parser("artifact-watch")
    watch.add_argument("--project-dir", default=os.getcwd())
    watch.add_argument("--artifact-dir", required=True)
    watch.add_argument("--interval-seconds", type=float, default=0.0)
    watch.add_argument("--max-cycles", type=int, default=1)
    watch.add_argument("--max-files", type=int, default=1000)
    watch.add_argument("--json", action="store_true")
    watch.set_defaults(func=command_artifact_watch)

    report = sub.add_parser("artifact-report")
    report.add_argument("--project-dir", default=os.getcwd())
    report.add_argument("--json", action="store_true")
    report.set_defaults(func=command_artifact_report)

    graph = sub.add_parser("work-graph")
    graph_sub = graph.add_subparsers(dest="graph_action", required=True)
    for action in ("add", "update", "next", "report"):
        sp = graph_sub.add_parser(action)
        sp.add_argument("--project-dir", default=os.getcwd())
        sp.add_argument("--graph-id", default="default-graph")
        sp.add_argument("--task-id")
        sp.add_argument("--title")
        sp.add_argument("--status", default="pending")
        sp.add_argument("--priority", type=int, default=0)
        sp.add_argument("--fingerprint")
        sp.add_argument("--payload", default="")
        sp.add_argument("--evidence", default="")
        sp.add_argument("--allow-duplicate", action="store_true")
        sp.add_argument("--json", action="store_true")
        sp.set_defaults(func=command_work_graph)

    refute = sub.add_parser("refutation-review")
    refute.add_argument("--project-dir", default=os.getcwd())
    refute.add_argument("--process-id", default="default-process")
    refute.add_argument("--claim-id", default="claim")
    refute.add_argument("--claim", required=True)
    refute.add_argument("--evidence", action="append")
    refute.add_argument("--verification-command")
    refute.add_argument("--initial-confidence", type=int, default=70)
    refute.add_argument("--pass-threshold", type=int, default=75)
    refute.add_argument("--timeout-seconds", type=int, default=120)
    refute.add_argument("--record-fresh-review", action="store_true", default=True)
    refute.add_argument("--json", action="store_true")
    refute.set_defaults(func=command_refutation_review)

    advisor = sub.add_parser("second-pass-advisor")
    advisor.add_argument("--project-dir", default=os.getcwd())
    advisor.add_argument("--process-id", default="default-process")
    advisor.add_argument("--advisor-id", default="second-pass")
    advisor.add_argument("--signal", action="append")
    advisor.add_argument("--min-signals", type=int, default=1)
    advisor.add_argument("--force", action="store_true")
    advisor.add_argument("--command")
    advisor.add_argument("--timeout-seconds", type=int, default=120)
    advisor.add_argument("--json", action="store_true")
    advisor.set_defaults(func=command_second_pass_advisor)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except BrokenPipeError:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
