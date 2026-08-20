#!/usr/bin/env python3
# SCOPE: os-only
"""cos_lineage — operator surface for session lineage and the recursion fuses.

Subcommands
-----------
  record   append a lineage row for a session (used by the SessionStart hook)
  chain    print the root-to-session chain reconstructed from disk
  status   arm state, counters, last decisions
  arm      write the arm file for one goal (this is the ON switch)
  disarm   remove the arm file
  decide   run evaluate_relaunch and print the verdict — launches nothing
  probe    force each fuse and report whether it actually cut

``probe`` exists because of the hole the survey left: across ~50 sources, no
harness was found that periodically exercises its own fuses. A fuse nobody has
seen cut is a promise.

Exit codes: 0 = ok / decision allowed, 1 = decision refused or probe failed,
2 = usage or runtime error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from cos_lib.session_lineage import (  # noqa: E402
    ENV_DISABLE,
    FuseLimits,
    LineageRecord,
    LineageStore,
    child_env,
    current_depth,
    default_store,
    evaluate_relaunch,
    resolve_parent,
    resolve_root,
)


def _project_dir(args) -> Path:
    return Path(
        args.project_dir
        or os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or _ROOT
    )


def _limits(args) -> FuseLimits:
    lim = FuseLimits()
    for name in ("max_depth", "max_total", "max_width", "max_no_progress"):
        val = getattr(args, name, None)
        if val is not None:
            setattr(lim, name, int(val))
    return lim


def cmd_record(args) -> int:
    store = default_store(_project_dir(args))
    session_id = args.session_id or os.environ.get("CLAUDE_SESSION_ID") or ""
    if not session_id:
        print("cos_lineage: no session id available; refusing to invent one", file=sys.stderr)
        return 2
    parent = resolve_parent()
    rec = LineageRecord(
        session_id=session_id,
        parent_session_id=parent,          # None when unknown. Never fabricated.
        depth=current_depth(),
        root_id=resolve_root(session_id),
        recorded_at=__import__("cos_lib.session_lineage", fromlist=["_now"])._now(),
        source=args.source,
        pid=os.getpid(),
        goal_id=os.environ.get("COS_LINEAGE_GOAL_ID", ""),
    )
    store.record_session(rec)
    if not args.quiet:
        print(json.dumps(rec.to_dict(), sort_keys=True))
    return 0


def cmd_chain(args) -> int:
    store = default_store(_project_dir(args))
    chain = store.chain(args.session_id)
    if not chain:
        print(f"no lineage recorded for {args.session_id}", file=sys.stderr)
        return 1
    for i, rec in enumerate(chain):
        arrow = "" if i == 0 else " -> "
        print(f"{arrow}gen{rec.depth} {rec.session_id} (parent={rec.parent_session_id}, source={rec.source})")
    return 0


def cmd_status(args) -> int:
    store = default_store(_project_dir(args))
    armed, reason = store.is_armed()
    print(f"arm file : {store.arm_path}")
    print(f"armed    : {armed} — {reason}")
    print(f"mode     : {store.arm_mode()}")
    print(f"killswitch {ENV_DISABLE}={os.environ.get(ENV_DISABLE, '<unset>')}")
    recs = store.records()
    print(f"sessions : {len(recs)} recorded")
    roots = sorted({r.root_id for r in recs})
    for root in roots:
        c = store.read_counters(root)
        print(f"  root {root}: total={c['total']} children={c['children']}")
    decs = store.decisions()
    print(f"decisions: {len(decs)}")
    for d in decs[-args.tail:]:
        print(f"  {d.get('decided_at')} allowed={d.get('allowed')} fuse={d.get('fuse')} — {d.get('reason')}")
    return 0


def cmd_arm(args) -> int:
    store = default_store(_project_dir(args))
    mode = "spawn" if args.spawn else "dry-run"
    path = store.arm(args.goal_id, ttl_seconds=args.ttl, mode=mode)
    print(f"armed for goal {args.goal_id!r} in mode {mode!r} until +{args.ttl}s: {path}")
    if mode == "dry-run":
        print("dry-run: the gate will decide and record, and will spawn nothing.")
        print("Add --spawn only after reading the double-continuation note in")
        print("the Stop gate hook.")
    else:
        print("SPAWN MODE: a successor session can now be started without you watching.")
    print("`cos_lineage.py disarm` turns it off.")
    return 0


def cmd_disarm(args) -> int:
    store = default_store(_project_dir(args))
    removed = store.disarm()
    print("disarmed" if removed else "already disarmed (no arm file)")
    return 0


def cmd_decide(args) -> int:
    store = default_store(_project_dir(args))
    dec = evaluate_relaunch(
        store,
        session_id=args.session_id,
        goal_id=args.goal_id,
        consecutive_no_progress=args.no_progress,
        limits=_limits(args),
    )
    print(json.dumps(dec.to_dict(), indent=2, sort_keys=True))
    return 0 if dec.allowed else 1


def _probe_case(name: str, fn) -> tuple[str, bool, str]:
    try:
        cut, detail = fn()
    except Exception as exc:  # noqa: BLE001
        return name, False, f"probe raised: {exc}"
    return name, cut, detail


def cmd_probe(args) -> int:
    """Force each fuse condition in a throwaway directory and see it cut."""
    results = []
    with tempfile.TemporaryDirectory(prefix="cos-lineage-probe-") as td:
        base = Path(td) / "lineage"

        def disarmed():
            s = LineageStore(base / "disarmed")
            d = evaluate_relaunch(s, session_id="s0", goal_id="g", env={})
            return (not d.allowed and d.fuse == "disarmed"), d.reason

        def killswitch():
            s = LineageStore(base / "ks")
            s.arm("g")
            d = evaluate_relaunch(s, session_id="s0", goal_id="g", env={ENV_DISABLE: "1"})
            return (not d.allowed and d.fuse == "kill-switch"), d.reason

        def stall():
            s = LineageStore(base / "stall")
            s.arm("g")
            d = evaluate_relaunch(s, session_id="s0", goal_id="g", consecutive_no_progress=2, env={})
            return (not d.allowed and d.fuse == "stall"), d.reason

        def depth():
            s = LineageStore(base / "depth")
            s.arm("g")
            d = evaluate_relaunch(s, session_id="s0", goal_id="g", env={"COS_SESSION_DEPTH": "3"})
            return (not d.allowed and d.fuse == "depth"), d.reason

        def total():
            s = LineageStore(base / "total")
            s.arm("g")
            lim = FuseLimits(max_total=2, max_width=99)
            ok = []
            for i in range(5):
                d = evaluate_relaunch(s, session_id=f"s{i}", goal_id="g", limits=lim, env={"COS_LINEAGE_ROOT_ID": "R"})
                if d.allowed:
                    s.reserve_slot("R", f"s{i}", lim)
                ok.append(d.allowed)
            return (ok[:2] == [True, True] and not any(ok[2:])), f"allowed sequence={ok} (cap 2)"

        def width():
            s = LineageStore(base / "width")
            s.arm("g")
            lim = FuseLimits(max_total=99, max_width=2)
            ok = []
            for _ in range(4):
                d = evaluate_relaunch(s, session_id="P", goal_id="g", limits=lim, env={"COS_LINEAGE_ROOT_ID": "R"})
                if d.allowed:
                    s.reserve_slot("R", "P", lim)
                ok.append(d.allowed)
            return (ok[:2] == [True, True] and not any(ok[2:])), f"allowed sequence={ok} (width cap 2)"

        for name, fn in [
            ("disarmed", disarmed), ("kill-switch", killswitch), ("stall", stall),
            ("total", total), ("width", width), ("depth", depth),
        ]:
            results.append(_probe_case(name, fn))

    failed = 0
    for name, cut, detail in results:
        mark = "CUT " if cut else "FAIL"
        if not cut:
            failed += 1
        print(f"[{mark}] {name}: {detail}")
    print(f"\n{len(results) - failed}/{len(results)} fuses cut when forced")
    return 1 if failed else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="cos_lineage")
    p.add_argument("--project-dir", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("record"); r.add_argument("--session-id"); r.add_argument("--source", default="unknown"); r.add_argument("--quiet", action="store_true"); r.set_defaults(fn=cmd_record)
    c = sub.add_parser("chain"); c.add_argument("session_id"); c.set_defaults(fn=cmd_chain)
    s = sub.add_parser("status"); s.add_argument("--tail", type=int, default=5); s.set_defaults(fn=cmd_status)
    a = sub.add_parser("arm"); a.add_argument("--goal-id", required=True); a.add_argument("--ttl", type=int, default=3600)
    a.add_argument("--spawn", action="store_true", help="allow a real process spawn (default: dry-run)")
    a.set_defaults(fn=cmd_arm)
    d = sub.add_parser("disarm"); d.set_defaults(fn=cmd_disarm)
    de = sub.add_parser("decide")
    de.add_argument("--session-id", required=True); de.add_argument("--goal-id", default="")
    de.add_argument("--no-progress", type=int, default=0)
    for name in ("max-depth", "max-total", "max-width", "max-no-progress"):
        de.add_argument(f"--{name}", type=int, default=None)
    de.set_defaults(fn=cmd_decide)
    pr = sub.add_parser("probe"); pr.set_defaults(fn=cmd_probe)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
