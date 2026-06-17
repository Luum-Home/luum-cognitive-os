#!/usr/bin/env python3
# SCOPE: both
"""Portable background agent run supervision primitives.

These commands make "como venimos?" answerable with evidence in any model or
harness: git state, WIP freshness, process liveness, validation receipts,
progress metrics, no-progress counters, and handoff summaries.
"""
from __future__ import annotations

import argparse
import json
import os
import re
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

SCHEMA_STATUS = "cos.agent-run-status.v1"
SCHEMA_WATCH = "cos.agent-watch.v1"
SCHEMA_PROGRESS = "cos.progress-metric.v1"
SCHEMA_HANDOFF = "cos.agent-handoff.v1"
TEXT = {
    "en": {
        "active-progress": "active progress: process is alive and work changed recently",
        "idle-but-safe": "idle but safe: process is alive and no unsafe WIP signal was found",
        "probably-stuck": "probably stuck: process is alive but status repeated past the no-progress threshold",
        "dead-with-wip": "dead with WIP: no live process was found and the worktree is dirty",
        "ready-for-handoff": "ready for handoff: no live process and no dirty WIP blocker detected",
    },
    "es": {
        "active-progress": "progreso activo: el proceso vive y hubo cambios recientes",
        "idle-but-safe": "inactivo pero seguro: el proceso vive y no hay WIP riesgoso",
        "probably-stuck": "probablemente trabado: el proceso vive pero el estado se repitio mas que el umbral",
        "dead-with-wip": "muerto con WIP: no hay proceso vivo y el worktree esta sucio",
        "ready-for-handoff": "listo para handoff: no hay proceso vivo ni WIP sucio bloqueante",
    },
    "pt": {
        "active-progress": "progresso ativo: o processo esta vivo e houve mudancas recentes",
        "idle-but-safe": "ocioso mas seguro: o processo esta vivo e nao ha WIP arriscado",
        "probably-stuck": "provavelmente travado: o processo esta vivo mas o estado se repetiu alem do limite",
        "dead-with-wip": "morto com WIP: nenhum processo vivo foi encontrado e a arvore esta suja",
        "ready-for-handoff": "pronto para handoff: nenhum processo vivo nem WIP sujo bloqueante",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def project_root(path: str | None) -> Path:
    return Path(path or os.getcwd()).resolve()


def sanitize_id(value: str | None, fallback: str = "default") -> str:
    raw = (value or fallback).strip()
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in raw)
    return safe or fallback


def run(cmd: list[str], cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=timeout)


def run_shell(command: str, cwd: Path, timeout: int = 120) -> dict[str, Any]:
    try:
        proc = subprocess.run(command, cwd=cwd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=timeout)
        return {"command": command, "returncode": proc.returncode, "passed": proc.returncode == 0, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    except subprocess.TimeoutExpired as exc:
        return {"command": command, "returncode": 124, "passed": False, "timeout": True, "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "", "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else ""}


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], root)


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload.get("message") or json.dumps(payload, sort_keys=True))


def run_dir(root: Path, process_id: str) -> Path:
    return root / ".cognitive-os" / "agent-runs" / sanitize_id(process_id, "default-run")


def branch(root: Path) -> str:
    return git(root, "branch", "--show-current").stdout.strip()


def last_commit(root: Path) -> dict[str, str]:
    proc = git(root, "log", "-1", "--format=%H%x00%h%x00%s%x00%cI")
    parts = proc.stdout.rstrip("\n").split("\x00")
    if len(parts) < 4:
        return {"sha": "", "short": "", "subject": "", "committed_at": ""}
    return {"sha": parts[0], "short": parts[1], "subject": parts[2], "committed_at": parts[3]}


def ahead_behind(root: Path, remote: str, main: str) -> dict[str, int | str]:
    git(root, "fetch", remote, main)
    ref = f"{remote}/{main}"
    ahead = git(root, "rev-list", "--count", f"{ref}..HEAD").stdout.strip()
    behind = git(root, "rev-list", "--count", f"HEAD..{ref}").stdout.strip()
    return {"base_ref": ref, "ahead": int(ahead or 0), "behind": int(behind or 0)}


def dirty_files(root: Path) -> list[dict[str, Any]]:
    proc = git(root, "status", "--porcelain=v1")
    rows: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        path_text = line[3:]
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1]
        if path_text == ".cognitive-os/" or path_text.startswith(".cognitive-os/agent-runs/"):
            continue
        path = root / path_text
        mtime = path.stat().st_mtime if path.exists() else None
        rows.append({"status": status, "path": path_text, "mtime": mtime})
    return rows


def last_change_age(files: list[dict[str, Any]]) -> float | None:
    mtimes = [float(row["mtime"]) for row in files if row.get("mtime") is not None]
    if not mtimes:
        return None
    return max(0.0, time.time() - max(mtimes))


def process_alive(process_id: str, pid: int | None = None, pattern: str | None = None) -> dict[str, Any]:
    if pid is not None:
        alive = Path(f"/proc/{pid}").exists() if sys.platform.startswith("linux") else run(["ps", "-p", str(pid), "-o", "pid=,command="], Path.cwd()).returncode == 0
        return {"matched": alive, "pid": pid, "mode": "pid", "matches": []}
    needle = pattern or process_id
    if not needle:
        return {"matched": False, "mode": "none", "matches": []}
    proc = subprocess.run(["ps", "-axo", "pid=,command="], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    matches: list[dict[str, str]] = []
    self_pid = str(os.getpid())
    for line in proc.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        pid_text, _, command = stripped.partition(" ")
        if pid_text == self_pid or "cos_agent_supervision.py" in command or "cos-agent-run-status" in command or "cos-agent-watch" in command or "cos-progress-metric" in command or "cos-handoff-if-dead" in command:
            continue
        if needle in command:
            matches.append({"pid": pid_text, "command": command[:500]})
    return {"matched": bool(matches), "mode": "pattern", "pattern": needle, "matches": matches[:10]}


def latest_validation(root: Path) -> dict[str, Any] | None:
    base = root / ".cognitive-os" / "reports" / "test-runs"
    if not base.exists():
        return None
    summaries = sorted(base.glob("*/summary.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not summaries:
        return None
    path = summaries[0]
    return {"path": str(path), "age_seconds": max(0.0, time.time() - path.stat().st_mtime), "tail": path.read_text(encoding="utf-8", errors="ignore")[-2000:]}


def load_progress_contract(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".yaml", ".yml"} and yaml is not None:
        return yaml.safe_load(text) or {}
    return json.loads(text)


def extract_metric_value(output: str, metric: str) -> float | None:
    try:
        data = json.loads(output)
        current: Any = data
        for part in metric.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = None
        if isinstance(current, (int, float)):
            return float(current)
    except Exception:
        pass
    match = re.search(rf"{re.escape(metric)}\s*[:=]\s*(-?\d+(?:\.\d+)?)", output)
    if match:
        return float(match.group(1))
    numbers = re.findall(r"-?\d+(?:\.\d+)?", output)
    return float(numbers[-1]) if numbers else None


def evaluate_progress(root: Path, contract: dict[str, Any] | None, timeout: int = 120) -> dict[str, Any] | None:
    if not contract:
        return None
    progress = contract.get("progress", contract)
    command = str(progress.get("command", "")).strip()
    metric = str(progress.get("metric", "value"))
    improves_when = str(progress.get("improves_when", "decreases"))
    if not command:
        return {"metric": metric, "status": "missing-command"}
    receipt = run_shell(command, root, timeout=timeout)
    value = extract_metric_value(str(receipt.get("stdout_tail", "")), metric)
    return {"metric": metric, "value": value, "improves_when": improves_when, "command_receipt": receipt, "stuck_after": int(progress.get("stuck_after", 3))}


def signature(payload: dict[str, Any]) -> str:
    metric = payload.get("progress_metric") or {}
    return json.dumps({
        "commit": payload.get("last_commit", {}).get("sha"),
        "dirty": [row.get("status") + " " + row.get("path", "") for row in payload.get("dirty_files", [])],
        "metric": metric.get("value"),
        "process": bool(payload.get("process", {}).get("matched")),
    }, sort_keys=True)


def classify(process: dict[str, Any], files: list[dict[str, Any]], age: float | None, repeated: int, threshold: int, idle_seconds: int) -> str:
    alive = bool(process.get("matched"))
    dirty = bool(files)
    recent = age is not None and age <= idle_seconds
    if alive and repeated >= threshold:
        return "probably-stuck"
    if alive and dirty and recent:
        return "active-progress"
    if alive:
        return "idle-but-safe"
    if dirty:
        return "dead-with-wip"
    return "ready-for-handoff"


def status_payload(args: argparse.Namespace, *, update_state: bool = False) -> dict[str, Any]:
    root = project_root(args.project_dir)
    rid = sanitize_id(args.process_id, "default-run")
    files = dirty_files(root)
    age = last_change_age(files)
    proc = process_alive(rid, args.pid, args.process_pattern)
    state_path = run_dir(root, rid) / "state.json"
    previous = read_json(state_path, {})
    progress = evaluate_progress(root, load_progress_contract(args.progress_contract), timeout=args.timeout)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_STATUS,
        "ts": utc_now(),
        "project_root": str(root),
        "process_id": rid,
        "branch": branch(root),
        "last_commit": last_commit(root),
        "ahead_behind": ahead_behind(root, args.remote, args.main),
        "dirty_files": files[:100],
        "dirty_count": len(files),
        "last_change_age_seconds": age,
        "process": proc,
        "latest_validation": latest_validation(root),
        "progress_metric": progress,
    }
    sig = signature(payload)
    repeated = int(previous.get("repeated_same_status", 0)) + 1 if previous.get("signature") == sig else 0
    payload["signature"] = sig
    payload["repeated_same_status"] = repeated
    state = classify(proc, files, age, repeated, args.no_progress_threshold, args.idle_seconds)
    lang = args.language if args.language in TEXT else "en"
    payload["state"] = state
    payload["state_label"] = TEXT[lang][state]
    payload["language"] = lang
    payload["message"] = f"agent-run-status process={rid} state={state} dirty={len(files)} repeated={repeated}"
    payload["receipt_path"] = str(run_dir(root, rid) / "latest-status.json")
    if update_state:
        write_json(state_path, {"signature": sig, "repeated_same_status": repeated, "updated_at": payload["ts"], "state": state})
        write_json(Path(payload["receipt_path"]), payload)
    return payload


def command_status(args: argparse.Namespace) -> int:
    payload = status_payload(args, update_state=True)
    emit(payload, args.json)
    return 2 if payload["state"] in {"probably-stuck", "dead-with-wip"} and args.strict else 0


def command_watch(args: argparse.Namespace) -> int:
    root = project_root(args.project_dir)
    events: list[dict[str, Any]] = []
    for idx in range(args.max_cycles):
        payload = status_payload(args, update_state=True)
        event = {"schema_version": SCHEMA_WATCH, "cycle": idx + 1, **payload}
        append_jsonl(run_dir(root, payload["process_id"]) / "watch.jsonl", event)
        events.append({"cycle": idx + 1, "state": payload["state"], "signature": payload["signature"], "repeated_same_status": payload["repeated_same_status"]})
        if idx + 1 < args.max_cycles and args.interval > 0:
            time.sleep(args.interval)
    result = {"schema_version": SCHEMA_WATCH, "ts": utc_now(), "process_id": sanitize_id(args.process_id, "default-run"), "cycles": events, "final_state": events[-1]["state"] if events else "unknown", "message": f"agent-watch cycles={len(events)} final={events[-1]['state'] if events else 'unknown'}"}
    emit(result, args.json)
    return 2 if result["final_state"] in {"probably-stuck", "dead-with-wip"} and args.strict else 0


def command_progress(args: argparse.Namespace) -> int:
    root = project_root(args.project_dir)
    contract = load_progress_contract(args.contract) if args.contract else {"progress": {"metric": args.metric, "command": args.command, "improves_when": args.improves_when, "stuck_after": args.stuck_after}}
    result = evaluate_progress(root, contract, timeout=args.timeout) or {}
    payload = {"schema_version": SCHEMA_PROGRESS, "ts": utc_now(), "project_root": str(root), "process_id": sanitize_id(args.process_id, "default-run"), "progress_metric": result, "message": f"progress-metric metric={result.get('metric')} value={result.get('value')}"}
    append_jsonl(run_dir(root, payload["process_id"]) / "progress.jsonl", payload)
    emit(payload, args.json)
    return 0 if result.get("command_receipt", {}).get("passed", True) else 2


def command_handoff(args: argparse.Namespace) -> int:
    payload = status_payload(args, update_state=True)
    root = project_root(args.project_dir)
    rid = payload["process_id"]
    commits = git(root, "log", "--oneline", f"{args.remote}/{args.main}..HEAD").stdout.splitlines()[:50]
    diff_stat = git(root, "diff", "--stat").stdout
    diff_name = git(root, "diff", "--name-status").stdout
    watch_path = run_dir(root, rid) / "watch.jsonl"
    watch_tail = ""
    if watch_path.exists():
        watch_tail = "\n".join(watch_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-20:])
    next_step = "preserve WIP and continue from dirty files" if payload["state"] == "dead-with-wip" else "review status receipt and continue with targeted validation"
    handoff = {"schema_version": SCHEMA_HANDOFF, "ts": utc_now(), "project_root": str(root), "process_id": rid, "status": payload, "commits_since_main": commits, "diff_stat": diff_stat, "diff_name_status": diff_name, "watch_tail": watch_tail, "next_recommended": next_step}
    out = run_dir(root, rid) / "handoff.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_handoff(handoff, args.language), encoding="utf-8")
    write_json(run_dir(root, rid) / "handoff.json", handoff)
    handoff["handoff_path"] = str(out)
    handoff["message"] = f"handoff process={rid} state={payload['state']} path={out}"
    emit(handoff, args.json)
    return 0


def render_handoff(payload: dict[str, Any], language: str) -> str:
    status = payload["status"]
    title = "Agent Run Handoff" if language != "es" else "Handoff de corrida de agente"
    return "\n".join([
        f"# {title}",
        "",
        f"- process_id: `{payload['process_id']}`",
        f"- state: `{status['state']}` — {status.get('state_label', '')}",
        f"- branch: `{status['branch']}`",
        f"- last_commit: `{status['last_commit'].get('short')}` {status['last_commit'].get('subject')}",
        f"- dirty_count: {status['dirty_count']}",
        f"- next_recommended: {payload['next_recommended']}",
        "",
        "## Commits since main",
        "\n".join(f"- {line}" for line in payload.get("commits_since_main", [])) or "- none",
        "",
        "## Diff stat",
        "```",
        payload.get("diff_stat", "").strip(),
        "```",
        "",
        "## Changed files",
        "```",
        payload.get("diff_name_status", "").strip(),
        "```",
        "",
        "## Watch tail",
        "```jsonl",
        payload.get("watch_tail", "").strip(),
        "```",
        "",
    ])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cognitive OS background agent run supervision")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project-dir", default=os.getcwd())
        p.add_argument("--process-id", default="default-run")
        p.add_argument("--remote", default="origin")
        p.add_argument("--main", default="main")
        p.add_argument("--pid", type=int)
        p.add_argument("--process-pattern")
        p.add_argument("--progress-contract")
        p.add_argument("--idle-seconds", type=int, default=120)
        p.add_argument("--no-progress-threshold", type=int, default=3)
        p.add_argument("--timeout", type=int, default=120)
        p.add_argument("--language", default="auto", choices=["auto", "en", "es", "pt"])
        p.add_argument("--strict", action="store_true")
        p.add_argument("--json", action="store_true")

    status = sub.add_parser("status", help="report live agent run status with evidence")
    common(status)
    status.set_defaults(func=command_status)

    watch = sub.add_parser("watch", help="sample agent run status repeatedly and record watch events")
    common(watch)
    watch.add_argument("--interval", type=float, default=60.0)
    watch.add_argument("--max-cycles", type=int, default=1)
    watch.set_defaults(func=command_watch)

    progress = sub.add_parser("progress-metric", help="run a generic residual/progress metric command")
    progress.add_argument("--project-dir", default=os.getcwd())
    progress.add_argument("--process-id", default="default-run")
    progress.add_argument("--contract")
    progress.add_argument("--metric", default="value")
    progress.add_argument("--command", default="")
    progress.add_argument("--improves-when", default="decreases", choices=["decreases", "increases", "changes"])
    progress.add_argument("--stuck-after", type=int, default=3)
    progress.add_argument("--timeout", type=int, default=120)
    progress.add_argument("--json", action="store_true")
    progress.set_defaults(func=command_progress)

    handoff = sub.add_parser("handoff-if-dead", help="produce a handoff summary when an agent is dead or ready to transfer")
    common(handoff)
    handoff.set_defaults(func=command_handoff)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "language", "en") == "auto":
        args.language = "es" if os.environ.get("LANG", "").lower().startswith("es") else "en"
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
