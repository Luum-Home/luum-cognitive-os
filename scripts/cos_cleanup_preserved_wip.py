#!/usr/bin/env python3
# SCOPE: both
"""Archive-first cleanup for preserved WIP stashes and temporary validation worktrees.

This is the action-layer companion to cos_work_inventory.py. It is deliberately
conservative: dry-run by default, writes an external backup before destructive
operations, and only targets explicitly requested cleanup classes.
"""
from __future__ import annotations
import os as _cos_os
import sys as _cos_sys
_cos_sys.path.insert(0, _cos_os.path.dirname(_cos_os.path.dirname(__file__)))
import sys
from lib.script_helpers import utc_stamp

import argparse
import json
import os
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from typing import Any


@dataclass(frozen=True)
class Worktree:
    path: Path
    head: str | None
    branch: str | None
    detached: bool


def run_git(repo: Path, args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
        timeout=60,
    )


def parse_worktrees(output: str) -> list[Worktree]:
    entries: list[Worktree] = []
    current: dict[str, str] = {}
    for line in [*output.splitlines(), ""]:
        if not line.strip():
            if current:
                branch = current.get("branch")
                entries.append(
                    Worktree(
                        path=Path(current["worktree"]).resolve(),
                        head=current.get("HEAD"),
                        branch=branch,
                        detached=branch is None,
                    )
                )
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    return entries


def list_worktrees(repo: Path) -> list[Worktree]:
    proc = run_git(repo, ["worktree", "list", "--porcelain"])
    if proc.returncode != 0:
        raise SystemExit(f"git worktree list failed: {proc.stderr.strip()}")
    return parse_worktrees(proc.stdout)


def stash_entries(repo: Path) -> list[dict[str, str]]:
    proc = run_git(repo, ["reflog", "show", "--format=%H%x09%gs", "refs/stash"])
    if proc.returncode != 0:
        return []
    entries: list[dict[str, str]] = []
    for index, line in enumerate(proc.stdout.splitlines()):
        if not line.strip():
            continue
        commit, _, subject = line.partition("\t")
        entries.append({"index": str(index), "commit": commit, "subject": subject})
    return entries


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def backup_stashes(repo: Path, backup_dir: Path, *, create_refs: bool) -> dict[str, Any]:
    entries = stash_entries(repo)
    stash_dir = backup_dir / "stashes"
    stash_dir.mkdir(parents=True, exist_ok=True)
    write_text(stash_dir / "list.tsv", "".join(f"{e['index']}\t{e['commit']}\t{e['subject']}\n" for e in entries))
    ref_prefix = f"refs/cos-backup/stashes/{backup_dir.name}"
    refs: list[str] = []
    for entry in entries:
        ordinal = int(entry["index"]) + 1
        name = f"stash-{ordinal:02d}"
        commit = entry["commit"]
        meta = run_git(repo, ["show", "--stat", "--oneline", "--decorate", commit])
        patch = run_git(repo, ["show", "--format=fuller", "--patch", "--stat", commit])
        write_text(stash_dir / f"{name}.meta.txt", f"commit={commit}\nsubject={entry['subject']}\n\n{meta.stdout}{meta.stderr}")
        write_text(stash_dir / f"{name}.show.patch", patch.stdout + patch.stderr)
        if create_refs:
            ref = f"{ref_prefix}/{name}"
            update = run_git(repo, ["update-ref", ref, commit])
            if update.returncode == 0:
                refs.append(ref)
    bundle_path = stash_dir / "stashes.bundle"
    if refs:
        bundle = run_git(repo, ["bundle", "create", str(bundle_path), *refs])
        if bundle.returncode != 0 and bundle_path.exists():
            bundle_path.unlink()
    return {"count": len(entries), "backup_dir": str(stash_dir), "backup_refs": refs, "bundle": str(bundle_path) if bundle_path.exists() else None}


def git_status(repo: Path) -> str:
    proc = run_git(repo, ["status", "--short", "--branch"])
    return proc.stdout + proc.stderr


def backup_worktree(path: Path, backup_dir: Path) -> dict[str, Any]:
    name = path.name.replace(os.sep, "_")
    wt_dir = backup_dir / "worktrees" / name
    wt_dir.mkdir(parents=True, exist_ok=True)
    status = subprocess.run(["git", "-C", str(path), "status", "--short", "--branch"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)
    diff = subprocess.run(["git", "-C", str(path), "diff"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)
    write_text(wt_dir / "status.txt", status.stdout + status.stderr)
    write_text(wt_dir / "diff.patch", diff.stdout + diff.stderr)
    untracked = subprocess.run(["git", "-C", str(path), "ls-files", "--others", "--exclude-standard"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)
    files = [item for item in untracked.stdout.splitlines() if item]
    write_text(wt_dir / "untracked.txt", "\n".join(files) + ("\n" if files else ""))
    tar_path = wt_dir / "untracked.tgz"
    if files:
        with tarfile.open(tar_path, "w:gz") as archive:
            for rel in files:
                candidate = path / rel
                if candidate.exists():
                    archive.add(candidate, arcname=rel, recursive=True)
    return {"path": str(path), "backup_dir": str(wt_dir), "untracked_count": len(files)}


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def validation_lock_active_for(repo: Path, path: Path) -> tuple[bool, str]:
    lock = repo / ".cognitive-os" / "runtime" / "validation-capsule.lock"
    if not lock.exists():
        return False, "no validation capsule lock"
    try:
        data = json.loads(lock.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return True, "validation capsule lock is corrupt; fail closed"
    capsule_dir = data.get("capsule_dir")
    if not capsule_dir:
        return True, "validation capsule lock has no capsule_dir; fail closed"
    try:
        if Path(capsule_dir).resolve() != path.resolve():
            return False, "validation capsule lock points elsewhere"
    except OSError:
        return True, "validation capsule lock path is not resolvable; fail closed"

    now = int(datetime.now(timezone.utc).timestamp())
    expires_at = int(data.get("expires_at_epoch") or 0)
    if expires_at and expires_at < now:
        return False, "validation capsule lock expired"
    pid = int(data.get("pid") or 0)
    if pid and not pid_alive(pid):
        return False, "validation capsule lock pid is dead"
    heartbeat = int(data.get("last_heartbeat_epoch") or 0)
    interval = int(data.get("heartbeat_interval_seconds") or 0)
    if heartbeat and interval and (now - heartbeat) > (3 * interval):
        return False, "validation capsule heartbeat is stale"
    return True, "validation capsule lock is active"


def process_activity_for_path(path: Path) -> tuple[bool, str]:
    needle = str(path.resolve())
    proc = subprocess.run(
        ["ps", "-axo", "pid=,command="],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,  # timeout per ADR-278 (default - review)
    )
    if proc.returncode == 0 and any(needle in line and "cos_cleanup_preserved_wip.py" not in line for line in proc.stdout.splitlines()):
        return True, "process command references validation capsule path"
    lsof = next((Path(item) / "lsof" for item in os.environ.get("PATH", "").split(os.pathsep) if (Path(item) / "lsof").is_file()), None)
    if lsof is None:
        return False, "no active process detected; lsof unavailable"
    lsof_proc = subprocess.run(
        [str(lsof), "+D", needle],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,  # timeout per ADR-278 (default - review)
    )
    if lsof_proc.returncode == 0 and lsof_proc.stdout.strip():
        return True, "open file detected under validation capsule path"
    return False, "no active process detected"


def validation_capsule_removal_blocker(repo: Path, path: Path) -> str | None:
    lock_active, lock_reason = validation_lock_active_for(repo, path)
    if lock_active:
        return lock_reason
    process_active, process_reason = process_activity_for_path(path)
    if process_active:
        return process_reason
    return None


def validation_capsule_worktrees(repo: Path) -> list[Worktree]:
    primary = repo.resolve()
    return [
        wt
        for wt in list_worktrees(repo)
        if wt.path != primary and "cos-validation-capsules" in str(wt.path)
    ]


def cleanup_zombie_registry(repo: Path, backup_dir: Path, *, apply: bool) -> dict[str, Any]:
    registry = repo / ".cognitive-os" / "sessions" / "active-sessions.json"
    if not registry.exists():
        return {"registry": str(registry), "removed": 0, "kept": 0, "exists": False}
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"registry": str(registry), "error": str(exc), "removed": 0, "kept": 0, "exists": True}
    sessions = data.get("sessions", [])
    kept: list[dict[str, Any]] = []
    for session in sessions:
        pid = session.get("pid")
        alive = False
        if isinstance(pid, int) and pid > 0:
            try:
                os.kill(pid, 0)
                alive = True
            except ProcessLookupError:
                alive = False
            except PermissionError:
                alive = True
        if alive:
            kept.append(session)
    removed = len(sessions) - len(kept)
    if apply and removed:
        backup = backup_dir / "active-sessions.before-clean.json"
        write_text(backup, registry.read_text(encoding="utf-8"))
        fd, tmp = tempfile.mkstemp(prefix=registry.name + ".", dir=str(registry.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"sessions": kept}, handle)
            handle.write("\n")
        os.replace(tmp, registry)
    return {"registry": str(registry), "removed": removed, "kept": len(kept), "exists": True}


def default_backup_root(repo: Path) -> Path:
    return Path.home() / ".codex" / "backups" / repo.name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.getcwd())
    parser.add_argument("--backup-root", help="Directory under which a timestamped cleanup backup is created.")
    parser.add_argument("--apply", action="store_true", help="Perform cleanup. Default is dry-run.")
    parser.add_argument("--all", action="store_true", help="Enable all cleanup classes.")
    parser.add_argument("--drop-stashes", action="store_true", help="Backup and clear git stash stack.")
    parser.add_argument("--remove-validation-capsules", action="store_true", help="Backup and remove cos-validation-capsules worktrees.")
    parser.add_argument("--clean-zombie-registry", action="store_true", help="Remove dead PIDs from .cognitive-os/sessions/active-sessions.json.")
    parser.add_argument("--no-backup-refs", action="store_true", help="Do not create local refs/cos-backup refs for stashes.")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = Path(args.repo).resolve()
    backup_parent = Path(args.backup_root).resolve() if args.backup_root else default_backup_root(repo)
    backup_dir = backup_parent / f"cleanup-{utc_stamp()}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    requested = {
        "drop_stashes": args.all or args.drop_stashes,
        "remove_validation_capsules": args.all or args.remove_validation_capsules,
        "clean_zombie_registry": args.all or args.clean_zombie_registry,
    }
    report: dict[str, Any] = {
        "mode": "apply" if args.apply else "dry-run",
        "repo": str(repo),
        "backup_dir": str(backup_dir),
        "requested": requested,
        "before_status": git_status(repo),
    }
    write_text(backup_dir / "manifest.json", json.dumps(report, indent=2, sort_keys=True) + "\n")
    if requested["drop_stashes"]:
        report["stashes"] = backup_stashes(repo, backup_dir, create_refs=not args.no_backup_refs)
        if args.apply and report["stashes"]["count"]:
            clear = run_git(repo, ["stash", "clear"])
            report["stashes"]["clear_returncode"] = clear.returncode
            report["stashes"]["clear_stderr"] = clear.stderr
    if requested["remove_validation_capsules"]:
        capsules = validation_capsule_worktrees(repo)
        removed: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        for wt in capsules:
            blocker = validation_capsule_removal_blocker(repo, wt.path)
            if blocker:
                skipped.append({"path": str(wt.path), "reason": blocker, "skipped": True})
                continue
            item = backup_worktree(wt.path, backup_dir)
            if args.apply:
                proc = run_git(repo, ["worktree", "remove", "--force", str(wt.path)])
                item["remove_returncode"] = proc.returncode
                item["remove_stderr"] = proc.stderr
            removed.append(item)
        if args.apply:
            run_git(repo, ["worktree", "prune"])
        report["validation_capsules"] = removed
        report["skipped_validation_capsules"] = skipped
    if requested["clean_zombie_registry"]:
        report["zombie_registry"] = cleanup_zombie_registry(repo, backup_dir, apply=args.apply)
    report["after_status"] = git_status(repo)
    write_text(backup_dir / "result.json", json.dumps(report, indent=2, sort_keys=True) + "\n")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"mode={report['mode']}")
        print(f"backup_dir={backup_dir}")
        if "stashes" in report:
            print(f"stashes_backed_up={report['stashes']['count']}")
        if "validation_capsules" in report:
            print(f"validation_capsules={len(report['validation_capsules'])}")
        if "zombie_registry" in report:
            print(f"zombie_registry_removed={report['zombie_registry'].get('removed', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
