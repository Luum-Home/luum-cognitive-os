#!/usr/bin/env python3
"""cos-sprint — Sprint orchestration CLI (ADR-036 MVP).

Subcommands:
  run <spec.yaml>   Load spec, validate, create manifest + launch script.
  status <id>       Render sprint manifest + live state (from canonical JSONL).
  list              List all sprint manifests under .cognitive-os/sprints/.
  cancel <id>       Mark sprint cancelled + emit SprintCancelled event.

MVP note: ``run`` does NOT launch agents from this script (no API access from
a shell-invoked process in all harnesses). It writes the manifest + a launch
script that the orchestrator/user executes. Canonical events still flow through
the standard ADR-033 pipeline when the orchestrator runs the tasks.

Exit codes:
  0  success
  1  user error (bad args, spec missing)
  2  validation error (bad spec schema)
  3  state error (illegal transition, manifest not found)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

# Allow both "installed" (lib/ on sys.path) and "in-repo" execution.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.sprint_orchestrator import (  # noqa: E402
    CommitStrategy,
    SprintCancelled,
    SprintManifest,
    SprintSpecError,
    SprintStarted,
    SprintStatus,
    default_sprints_dir,
    list_manifests,
    load_manifest,
    load_spec,
    manifest_path,
    now_epoch,
    render_sprint_status_stub,
    save_manifest,
    transition,
)
from lib.harness_adapter.base import CanonicalEvent  # noqa: E402


CANONICAL_LIVE = ".cognitive-os/metrics/canonical-live.jsonl"
CANONICAL_EVENTS = ".cognitive-os/metrics/canonical-events.jsonl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _project_dir() -> Path:
    import os

    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())


def _emit(event: CanonicalEvent, project_dir: Path) -> None:
    """Append the event to canonical-events.jsonl (and canonical-live.jsonl)."""
    for rel in (CANONICAL_EVENTS, CANONICAL_LIVE):
        target = project_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(event.to_json() + "\n")


def _read_live_events(project_dir: Path, sprint_id: str) -> List[dict]:
    """Return canonical-live events matching this sprint_id."""
    p = project_dir / CANONICAL_LIVE
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("sprint_id") == sprint_id:
            out.append(obj)
    return out


def _write_launch_script(manifest: SprintManifest, project_dir: Path) -> Path:
    """Generate a launch script the orchestrator can execute to run tasks.

    The script is a plain Markdown prompt file the orchestrator reads; actual
    agent launch happens via the harness. This is the MVP hand-off.
    """
    d = default_sprints_dir(project_dir) / "launch"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{manifest.id}.md"
    lines = [
        f"# Sprint launch: {manifest.name}",
        f"Sprint ID: `{manifest.id}`",
        f"Commit strategy: `{manifest.commit_strategy}`",
        f"Tasks: {len(manifest.tasks)}",
        "",
        "## Tasks to launch (in parallel unless noted)",
        "",
    ]
    for t in manifest.tasks:
        lines.extend(
            [
                f"### {t.id} — {t.title}",
                f"- Model: `{t.model}`",
                f"- File scope: {', '.join(f'`{p}`' for p in t.file_scope) or '(unscoped)'}",
                "",
                "Prompt:",
                "",
                "```",
                t.prompt,
                "```",
                "",
            ]
        )
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    project_dir = _project_dir()
    try:
        manifest = load_spec(args.spec)
    except SprintSpecError as exc:
        print(f"cos sprint: spec invalid: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError:
        print(f"cos sprint: spec not found: {args.spec}", file=sys.stderr)
        return 1

    # Persist manifest (state remains PENDING until orchestrator transitions).
    mpath = save_manifest(manifest, manifest_path(manifest.id, project_dir))
    launch_md = _write_launch_script(manifest, project_dir)

    # Emit SprintStarted — the orchestrator interprets this as "ready to dispatch".
    _emit(
        SprintStarted(
            sprint_id=manifest.id,
            sprint_name=manifest.name,
            task_count=len(manifest.tasks),
            started_at=now_epoch(),
            commit_strategy=manifest.commit_strategy,
        ),
        project_dir,
    )

    print(f"sprint: {manifest.id}")
    print(f"manifest: {mpath}")
    print(f"launch:   {launch_md}")
    print(f"tasks:    {len(manifest.tasks)}")
    print("status:   pending (awaiting orchestrator dispatch)")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    project_dir = _project_dir()
    p = manifest_path(args.sprint_id, project_dir)
    if not p.exists():
        print(f"cos sprint: manifest not found: {p}", file=sys.stderr)
        return 3
    manifest = load_manifest(p)

    if args.json:
        out = manifest.to_dict()
        out["live_events"] = _read_live_events(project_dir, manifest.id)
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0

    print(render_sprint_status_stub(manifest))
    live = _read_live_events(project_dir, manifest.id)
    if live:
        print(f"\nLive events: {len(live)}")
        for ev in live[-5:]:
            print(f"  - {ev.get('event_type', '?')} @ {ev.get('started_at') or ev.get('ts') or '?'}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    project_dir = _project_dir()
    manifests = list_manifests(project_dir)
    if not manifests:
        print("(no sprints)")
        return 0
    if args.json:
        print(json.dumps([m.to_dict() for m in manifests], indent=2, sort_keys=True))
        return 0
    print(f"{'ID':<20} {'STATUS':<12} {'TASKS':<6} NAME")
    for m in manifests:
        print(f"{m.id:<20} {m.status:<12} {len(m.tasks):<6} {m.name}")
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    project_dir = _project_dir()
    p = manifest_path(args.sprint_id, project_dir)
    if not p.exists():
        print(f"cos sprint: manifest not found: {p}", file=sys.stderr)
        return 3
    manifest = load_manifest(p)
    try:
        transition(manifest, SprintStatus.CANCELLED.value)
    except ValueError as exc:
        print(f"cos sprint: {exc}", file=sys.stderr)
        return 3
    save_manifest(manifest, p)
    _emit(
        SprintCancelled(
            sprint_id=manifest.id,
            cancelled_at=now_epoch(),
            reason=args.reason or "user-requested",
        ),
        project_dir,
    )
    print(f"sprint {manifest.id}: cancelled ({args.reason or 'user-requested'})")
    return 0


# ---------------------------------------------------------------------------
# Argparse entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cos-sprint",
        description="Sprint orchestration CLI (ADR-036 MVP)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="Create a sprint from a YAML spec")
    pr.add_argument("spec", help="Path to sprint YAML spec")
    pr.set_defaults(func=cmd_run)

    ps = sub.add_parser("status", help="Show a sprint's status")
    ps.add_argument("sprint_id")
    ps.add_argument("--json", action="store_true", help="Emit JSON")
    ps.set_defaults(func=cmd_status)

    pl = sub.add_parser("list", help="List all sprint manifests")
    pl.add_argument("--json", action="store_true", help="Emit JSON")
    pl.set_defaults(func=cmd_list)

    pc = sub.add_parser("cancel", help="Cancel a running or pending sprint")
    pc.add_argument("sprint_id")
    pc.add_argument("--reason", default=None, help="Cancellation reason")
    pc.set_defaults(func=cmd_cancel)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
