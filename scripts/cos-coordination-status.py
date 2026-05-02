#!/usr/bin/env python3
# SCOPE: both
"""One-screen coordination status for concurrent Cognitive OS sessions."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from typing import Any, Sequence

from scripts.cos_task_claims import claims_path, normalize_claims, prune_claims, project_dir, read_json


def run(project: Path, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=project, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def parse_iso_epoch(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except Exception:
            return None
    return None


def age(value: Any) -> str:
    epoch = parse_iso_epoch(value)
    if epoch is None:
        return "?"
    seconds = max(0, int(time.time() - epoch))
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds//60}m"
    return f"{seconds//3600}h{(seconds%3600)//60:02d}m"


def pid_alive(pid: Any) -> bool:
    try:
        p = int(pid)
        os.kill(p, 0)
        return True
    except PermissionError:
        return True
    except Exception:
        return False


def active_sessions(project: Path) -> list[dict[str, Any]]:
    data = read_json(project / ".cognitive-os" / "sessions" / "active-sessions.json", {"sessions": []})
    rows = []
    for s in data.get("sessions", []) if isinstance(data, dict) else []:
        if isinstance(s, dict):
            rows.append({**s, "alive": pid_alive(s.get("pid")), "age": age(s.get("start_epoch") or s.get("start_time"))})
    return rows


def task_claims(project: Path) -> list[dict[str, Any]]:
    data = prune_claims(project, normalize_claims(read_json(claims_path(project), {"claims": []})))
    return data.get("claims", [])


def active_tasks(project: Path) -> list[dict[str, Any]]:
    data = read_json(project / ".cognitive-os" / "tasks" / "active-tasks.json", {"tasks": []})
    return data.get("tasks", []) if isinstance(data, dict) and isinstance(data.get("tasks"), list) else []


def edit_locks(project: Path) -> list[dict[str, Any]]:
    rows = []
    for lock in sorted((project / ".cognitive-os" / "runtime" / "edit-locks").glob("*.json")):
        data = read_json(lock, {})
        if isinstance(data, dict):
            rows.append(data)
    return rows


def stashes(project: Path) -> list[str]:
    proc = run(project, ["stash", "list", "--date=local"])
    return [line for line in proc.stdout.splitlines() if line.strip()] if proc.returncode == 0 else []


def orphan_commits(project: Path) -> list[str]:
    proc = run(project, ["fsck", "--no-reflogs", "--unreachable", "--no-progress"])
    shas = []
    for line in (proc.stdout + proc.stderr).splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "unreachable" and parts[1] == "commit":
            shas.append(parts[2])
    rows = []
    for sha in shas[:20]:
        show = run(project, ["show", "-s", "--format=%h %cr %s", sha])
        rows.append(show.stdout.strip() or sha)
    return rows


def worktrees(project: Path) -> list[dict[str, str]]:
    proc = run(project, ["worktree", "list", "--porcelain"])
    rows = []
    cur: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if not line.strip():
            if cur:
                rows.append(cur); cur = {}
            continue
        key, _, val = line.partition(" ")
        cur[key] = val
    if cur:
        rows.append(cur)
    for row in rows:
        path = row.get("worktree")
        if path:
            status = subprocess.run(["git", "status", "--short"], cwd=path, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
            row["wip_count"] = str(len([l for l in status.stdout.splitlines() if l.strip()])) if status.returncode == 0 else "?"
    return rows


def race_risks(tasks: list[dict[str, Any]], claims: list[dict[str, Any]]) -> list[str]:
    risks: list[str] = []
    pending_by_fp: dict[str, list[str]] = {}
    from scripts.cos_task_claims import task_fingerprint
    for task in tasks:
        if task.get("status") == "pending":
            pending_by_fp.setdefault(task_fingerprint(task), []).append(str(task.get("id") or task.get("task_id") or "unknown"))
    for fp, ids in pending_by_fp.items():
        if len(ids) > 1:
            risks.append(f"duplicate pending fingerprint {fp}: {', '.join(ids)}")
    active_claims = [c for c in claims if c.get("status") == "active"]
    by_fp: dict[str, list[str]] = {}
    for claim in active_claims:
        by_fp.setdefault(str(claim.get("fingerprint")), []).append(str(claim.get("session_id")))
    for fp, sessions in by_fp.items():
        if fp and len(set(sessions)) > 1:
            risks.append(f"multiple live claims fingerprint {fp}: {', '.join(sorted(set(sessions)))}")
    return risks


def build_report(project: Path) -> dict[str, Any]:
    tasks = active_tasks(project)
    claims = task_claims(project)
    return {
        "project_dir": str(project),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "active_sessions": active_sessions(project),
        "claims": claims,
        "edit_locks": edit_locks(project),
        "stashes": stashes(project),
        "orphan_commits": orphan_commits(project),
        "worktrees": worktrees(project),
        "pending_tasks": [t for t in tasks if t.get("status") == "pending"],
        "race_risks": race_risks(tasks, claims),
    }


def print_human(report: dict[str, Any]) -> None:
    print(f"COS Coordination Status — {Path(report['project_dir']).name}")
    print("=" * 72)
    print(f"Generated: {report['generated_at']}")
    print(f"Active sessions: {len(report['active_sessions'])}")
    for s in report["active_sessions"]:
        print(f"  - {s.get('id') or s.get('session_id')} pid={s.get('pid')} alive={s.get('alive')} age={s.get('age')}")
    active_claims = [c for c in report["claims"] if c.get("status") == "active"]
    print(f"Claims: {len(active_claims)} active / {len(report['claims'])} total")
    for c in active_claims:
        print(f"  - {c.get('task_id')} session={c.get('session_id')} fp={c.get('fingerprint')} files={','.join(c.get('expected_files') or []) or '-'}")
    print(f"Pending tasks: {len(report['pending_tasks'])}")
    print(f"Edit locks: {len(report['edit_locks'])}")
    print(f"Stashes: {len(report['stashes'])}")
    for s in report["stashes"][:10]:
        print(f"  - {s}")
    print(f"Orphan commits: {len(report['orphan_commits'])}")
    for o in report["orphan_commits"][:10]:
        print(f"  - {o}")
    print(f"Worktrees: {len(report['worktrees'])}")
    for w in report["worktrees"]:
        print(f"  - {w.get('worktree')} {w.get('branch','')} wip={w.get('wip_count')}")
    print(f"Race risks: {len(report['race_risks'])}")
    for risk in report["race_risks"]:
        print(f"  - {risk}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(project_dir(args))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
