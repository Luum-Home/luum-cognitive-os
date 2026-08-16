#!/usr/bin/env python3
# SCOPE: both
"""Census of processes this repo leaves running, partitioned by BEHAVIOUR.

Answers "which primitives leave processes hanging" without grepping source for
names. It reads the live process table, rebuilds the parent tree, and puts every
repo-owned process into exactly one of four classes:

  daemon              — born detached on purpose (declared daemon marker in argv).
                        ``ppid=1`` is expected here and is NOT evidence of a leak.
  live-child          — its ancestor chain reaches a process that is still alive
                        and is not itself an orphan (typically the agent harness).
  orphan-root         — ``ppid=1`` and no daemon marker: reparented to init
                        because whoever spawned it died first.
  orphan-descendant   — still has a live parent, but the top of its chain is an
                        orphan-root, so nobody owns the tree any more.

The distinction between ``daemon`` and ``orphan-root`` is the whole point: both
show ``ppid=1``, and conflating them either invents leaks or hides them.

Two invocations separated in time are required to tell accumulation from churn:
a single photo cannot distinguish "30 orphans piling up forever" from "30
orphans that live six minutes". Use ``--snapshot FILE`` to persist a sample and
``--compare FILE`` to diff against it.

Exit codes: 0 no orphans, 1 orphans found, 2 error.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# argv markers that mean "this process was born detached on purpose".
# Canonical definition lives in cos_lib so the census, the ADR-279 audit and
# the reaper's detector cannot drift apart on what counts as a daemon.
from cos_lib.orphan_process_audit import DAEMON_MARKERS  # noqa: E402

_ETIME = re.compile(r"^(?:(?:(\d+)-)?(\d+):)?(\d+):(\d+)$")


def etime_seconds(raw: str) -> int:
    """Parse ps etime. ``04:51`` is 4m51s, not 4h51m — a trap worth a function."""
    m = _ETIME.match(raw.strip())
    if not m:
        return 0
    days, hours, minutes, seconds = m.groups()
    return (
        int(days or 0) * 86400
        + int(hours or 0) * 3600
        + int(minutes) * 60
        + int(seconds)
    )


def read_table() -> list[dict]:
    out = subprocess.run(
        ["ps", "-eo", "pid,ppid,etime,pcpu,stat,command"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if out.returncode != 0:
        raise RuntimeError(f"ps failed: {out.stderr.strip()[:200]}")
    rows = []
    for line in out.stdout.splitlines()[1:]:
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        try:
            pid, ppid = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        rows.append(
            {
                "pid": pid,
                "ppid": ppid,
                "etime_s": etime_seconds(parts[2]),
                "pcpu": float(parts[3]) if parts[3].replace(".", "").isdigit() else 0.0,
                "stat": parts[4],
                "command": parts[5],
            }
        )
    return rows


def owning_script(command: str, root_name: str) -> str:
    """Best-effort: the repo-relative path of the script this process is running."""
    for token in command.split():
        idx = token.find(root_name + "/")
        if idx >= 0:
            return token[idx + len(root_name) + 1 :]
    return "<unattributed>"


def classify(rows: list[dict], root: Path) -> list[dict]:
    root_str = str(root)
    root_name = root.name
    by_pid = {r["pid"]: r for r in rows}
    alive = set(by_pid)

    mine = [r for r in rows if root_str in r["command"]]
    for r in mine:
        r["script"] = owning_script(r["command"], root_name)
        r["is_daemon"] = any(m in r["command"] for m in DAEMON_MARKERS)

    mine_pids = {r["pid"] for r in mine}

    def chain_root(row: dict) -> dict:
        """Walk up until ppid leaves the repo, hits init, or the parent is gone."""
        seen = set()
        cur = row
        while True:
            if cur["pid"] in seen:
                return cur
            seen.add(cur["pid"])
            parent = by_pid.get(cur["ppid"])
            if cur["ppid"] == 1 or parent is None or cur["ppid"] not in mine_pids:
                return cur
            cur = parent

    for r in mine:
        top = chain_root(r)
        if r["is_daemon"]:
            r["class"] = "daemon"
        elif top["ppid"] == 1 and not top["is_daemon"]:
            r["class"] = "orphan-root" if r is top else "orphan-descendant"
        elif top["ppid"] in alive:
            r["class"] = "live-child"
        else:
            r["class"] = "orphan-root"
        r["chain_root_pid"] = top["pid"]
    return mine


def summarize(mine: list[dict]) -> dict:
    per_class: dict[str, int] = {}
    per_script: dict[str, dict[str, int]] = {}
    for r in mine:
        per_class[r["class"]] = per_class.get(r["class"], 0) + 1
        bucket = per_script.setdefault(r["script"], {})
        bucket[r["class"]] = bucket.get(r["class"], 0) + 1
    orphans = [r for r in mine if r["class"].startswith("orphan")]
    return {
        "total_repo_processes": len(mine),
        "by_class": per_class,
        "by_script": per_script,
        "orphan_pids": sorted(r["pid"] for r in orphans),
        "oldest_orphan_seconds": max((r["etime_s"] for r in orphans), default=0),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project-dir", default=str(PROJECT_ROOT))
    ap.add_argument("--json", action="store_true", help="emit the full row list too")
    ap.add_argument("--snapshot", help="write orphan PIDs to FILE for a later --compare")
    ap.add_argument("--compare", help="diff current orphan PIDs against FILE")
    args = ap.parse_args(argv)

    root = Path(args.project_dir).resolve()
    try:
        mine = classify(read_table(), root)
    except Exception as exc:  # noqa: BLE001 — audit must report, not crash
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report = summarize(mine)
    if args.json:
        report["rows"] = [
            {k: v for k, v in r.items() if k != "command"} | {"command": r["command"][:160]}
            for r in mine
        ]

    if args.compare:
        try:
            previous = set(json.loads(Path(args.compare).read_text()))
        except Exception:  # noqa: BLE001
            previous = set()
        current = set(report["orphan_pids"])
        report["delta"] = {
            "previous_count": len(previous),
            "current_count": len(current),
            "survived": sorted(previous & current),
            "collected": sorted(previous - current),
            "new": sorted(current - previous),
            "verdict": (
                "accumulating" if previous and not (previous - current) and len(current) > len(previous)
                else "churn" if previous and (previous - current)
                else "steady"
            ),
        }

    if args.snapshot:
        Path(args.snapshot).write_text(json.dumps(report["orphan_pids"]))

    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["orphan_pids"] else 0


if __name__ == "__main__":
    sys.exit(main())
