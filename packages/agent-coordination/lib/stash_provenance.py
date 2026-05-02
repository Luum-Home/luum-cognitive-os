"""Stash provenance registry for ADR-116 P4.3 — stash auto-reapply.

Records which git stash was taken in which session/agent context so that
a subsequent SessionStart for the same session can auto-reapply it.

Storage: .cognitive-os/runtime/stash-provenance.jsonl (one JSON object per line)
Lock:    .cognitive-os/runtime/stash-provenance.lock  (flock or mkdir CAS)

Stdlib-only. Atomic writes via tempfile + os.rename.
"""
from __future__ import annotations

import fcntl
import json
import os
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator, List, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ProvenanceRecord:
    stash_ref: str
    session_id: str
    agent_id: str
    original_files: List[str]
    created_at: str          # ISO-8601
    status: str = "pending"  # "pending" | "reapplied" | "pruned"
    reapplied_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ProvenanceRecord":
        return cls(
            stash_ref=d["stash_ref"],
            session_id=d["session_id"],
            agent_id=d["agent_id"],
            original_files=d.get("original_files", []),
            created_at=d["created_at"],
            status=d.get("status", "pending"),
            reapplied_at=d.get("reapplied_at"),
        )


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _project_dir() -> Path:
    for env_var in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        val = os.environ.get(env_var)
        if val:
            return Path(val).resolve()
    return Path.cwd().resolve()


def _runtime_dir(project_dir: Optional[Path] = None) -> Path:
    p = (project_dir or _project_dir()) / ".cognitive-os" / "runtime"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _provenance_file(project_dir: Optional[Path] = None) -> Path:
    return _runtime_dir(project_dir) / "stash-provenance.jsonl"


def _lock_file(project_dir: Optional[Path] = None) -> Path:
    return _runtime_dir(project_dir) / "stash-provenance.lock"


# ---------------------------------------------------------------------------
# Locking — flock preferred, mkdir fallback
# ---------------------------------------------------------------------------

@contextmanager
def _locked(project_dir: Optional[Path] = None) -> Iterator[None]:
    lf = _lock_file(project_dir)
    lf.parent.mkdir(parents=True, exist_ok=True)
    # Try flock first (Linux + macOS with Homebrew coreutils)
    try:
        with lf.open("a", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except (OSError, AttributeError):
        # Fallback: mkdir-based CAS lock
        lock_dir = Path(str(lf) + ".d")
        deadline = time.monotonic() + 10
        acquired = False
        while time.monotonic() < deadline:
            try:
                lock_dir.mkdir()
                acquired = True
                break
            except FileExistsError:
                time.sleep(0.05)
        if not acquired:
            raise TimeoutError(f"Could not acquire provenance lock: {lock_dir}")
        try:
            yield
        finally:
            try:
                lock_dir.rmdir()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def _read_all(project_dir: Optional[Path] = None) -> List[ProvenanceRecord]:
    pf = _provenance_file(project_dir)
    if not pf.exists():
        return []
    records: List[ProvenanceRecord] = []
    for line in pf.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(ProvenanceRecord.from_dict(json.loads(line)))
        except (json.JSONDecodeError, KeyError):
            pass
    return records


def _write_all(records: List[ProvenanceRecord], project_dir: Optional[Path] = None) -> None:
    """Atomic rewrite of the full provenance file."""
    pf = _provenance_file(project_dir)
    pf.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    fd, tmp_path = tempfile.mkstemp(dir=pf.parent, prefix=".stash-prov-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r.to_dict()) + "\n")
        os.rename(tmp_path, pf)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def record_provenance(
    stash_ref: str,
    session_id: str,
    agent_id: str,
    original_files: List[str],
    created_at: str,
    *,
    project_dir: Optional[Path] = None,
) -> ProvenanceRecord:
    """Append a new provenance record. Returns the stored record."""
    rec = ProvenanceRecord(
        stash_ref=stash_ref,
        session_id=session_id,
        agent_id=agent_id,
        original_files=original_files,
        created_at=created_at,
        status="pending",
    )
    pf = _provenance_file(project_dir)
    pf.parent.mkdir(parents=True, exist_ok=True)
    with _locked(project_dir):
        with pf.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec.to_dict()) + "\n")
    return rec


def find_by_session(
    session_id: str,
    *,
    project_dir: Optional[Path] = None,
) -> List[ProvenanceRecord]:
    """Return unconsumed (status != 'reapplied') records matching session_id."""
    with _locked(project_dir):
        records = _read_all(project_dir)
    return [
        r for r in records
        if r.session_id == session_id and r.status != "reapplied"
    ]


def mark_reapplied(
    stash_ref: str,
    *,
    project_dir: Optional[Path] = None,
) -> bool:
    """Mark a stash_ref as reapplied. Returns True if found and updated."""
    with _locked(project_dir):
        records = _read_all(project_dir)
        updated = False
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for r in records:
            if r.stash_ref == stash_ref and r.status != "reapplied":
                r.status = "reapplied"
                r.reapplied_at = ts
                updated = True
        if updated:
            _write_all(records, project_dir)
    return updated


def prune_stale(
    max_age_seconds: float,
    *,
    project_dir: Optional[Path] = None,
) -> int:
    """Remove entries older than max_age_seconds. Returns number pruned."""
    now = time.time()
    pruned = 0
    with _locked(project_dir):
        records = _read_all(project_dir)
        kept: List[ProvenanceRecord] = []
        for r in records:
            try:
                import datetime as dt
                ts_str = r.created_at.rstrip("Z")
                t = dt.datetime.fromisoformat(ts_str).replace(tzinfo=dt.timezone.utc).timestamp()
                age = now - t
            except (ValueError, AttributeError):
                age = 0
            if age > max_age_seconds:
                pruned += 1
            else:
                kept.append(r)
        if pruned:
            _write_all(kept, project_dir)
    return pruned


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli_record(args: list) -> None:
    """record --stash-ref REF --session-id SID --agent-id AID --original-files FILES --created-at TS"""
    import argparse
    p = argparse.ArgumentParser(prog="stash_provenance record")
    p.add_argument("--stash-ref", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--agent-id", required=True)
    p.add_argument("--original-files", default="")
    p.add_argument("--created-at", required=True)
    ns = p.parse_args(args)
    files = [f for f in ns.original_files.split("\n") if f.strip()]
    rec = record_provenance(
        stash_ref=ns.stash_ref,
        session_id=ns.session_id,
        agent_id=ns.agent_id,
        original_files=files,
        created_at=ns.created_at,
    )
    print(json.dumps(rec.to_dict()))


def _cli_find_by_session(args: list) -> None:
    """find-by-session SESSION_ID [--json]"""
    import argparse
    p = argparse.ArgumentParser(prog="stash_provenance find-by-session")
    p.add_argument("session_id")
    p.add_argument("--json", action="store_true", dest="as_json")
    ns = p.parse_args(args)
    records = find_by_session(ns.session_id)
    if ns.as_json:
        print(json.dumps([r.to_dict() for r in records]))
    else:
        for r in records:
            print(f"{r.stash_ref}\t{r.session_id}\t{r.status}")


def _cli_mark_reapplied(args: list) -> None:
    """mark-reapplied STASH_REF"""
    import argparse
    p = argparse.ArgumentParser(prog="stash_provenance mark-reapplied")
    p.add_argument("stash_ref")
    ns = p.parse_args(args)
    ok = mark_reapplied(ns.stash_ref)
    print("updated" if ok else "not_found")


def _cli_prune_stale(args: list) -> None:
    """prune-stale MAX_AGE_SECONDS"""
    import argparse
    p = argparse.ArgumentParser(prog="stash_provenance prune-stale")
    p.add_argument("max_age_seconds", type=float)
    ns = p.parse_args(args)
    n = prune_stale(ns.max_age_seconds)
    print(f"pruned {n}")


def main(argv: Optional[list] = None) -> None:
    import sys
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("Usage: python3 -m stash_provenance {record|find-by-session|mark-reapplied|prune-stale} ...", file=sys.stderr)
        sys.exit(1)
    subcmd = argv[0]
    rest = argv[1:]
    dispatch = {
        "record": _cli_record,
        "find-by-session": _cli_find_by_session,
        "mark-reapplied": _cli_mark_reapplied,
        "prune-stale": _cli_prune_stale,
    }
    if subcmd not in dispatch:
        print(f"Unknown subcommand: {subcmd}", file=sys.stderr)
        sys.exit(1)
    dispatch[subcmd](rest)


if __name__ == "__main__":
    main()
