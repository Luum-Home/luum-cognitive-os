# SCOPE: both
"""Cross-session coordination ledger for agentic primitive ownership.

Git coordinates bytes. This module coordinates intent: task subjects, ADR
numbers, path ownership, disposition policies, and worktree intake records that
must be visible across IDEs, harnesses, and parallel sessions.
"""

from __future__ import annotations

import fcntl
import json
import os
import socket
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


DEFAULT_TTL_SECONDS = 24 * 60 * 60
CLAIM_KINDS = {"task", "adr-number", "path", "policy", "skill", "primitive"}


@dataclass(frozen=True)
class CoordinationFinding:
    """Machine-readable finding emitted by coordination guards."""

    status: str
    source: str
    message: str
    evidence: str = ""


@dataclass(frozen=True)
class ClaimResult:
    """Result from acquiring a cross-session claim."""

    status: str
    claim: dict[str, Any] | None = None
    held_by: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"status": self.status}
        if self.claim is not None:
            payload["claim"] = self.claim
        if self.held_by is not None:
            payload["held_by"] = self.held_by
        return payload


def now_iso() -> str:
    """Return an RFC3339-ish UTC timestamp."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_epoch(value: Any) -> float | None:
    """Parse an ISO timestamp to epoch seconds."""

    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def project_coordination_dir(project_dir: str | Path) -> Path:
    """Return the runtime coordination directory."""

    path = Path(project_dir) / ".cognitive-os" / "coordination"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ledger_path(project_dir: str | Path) -> Path:
    """Return the cross-session claim ledger path."""

    return project_coordination_dir(project_dir) / "session-claims.json"


def intake_path(project_dir: str | Path) -> Path:
    """Return the worktree intake ledger path."""

    return project_coordination_dir(project_dir) / "worktree-intake.json"


def _lock_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".lock")


def read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    """Read a JSON document, tolerating absence and corruption."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    return data if isinstance(data, dict) else fallback


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Atomically write a JSON document."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def normalize_subject(kind: str, subject: str) -> str:
    """Normalize claim subjects so independent sessions collide deterministically."""

    cleaned = " ".join(subject.strip().split())
    if kind == "adr-number":
        digits = "".join(ch for ch in cleaned if ch.isdigit())
        if digits:
            return f"ADR-{int(digits):03d}"
    if kind == "path":
        return cleaned.strip("./")
    return cleaned.lower()


def current_session_id(default: str = "manual") -> str:
    """Return the best available harness/session identifier."""

    return (
        os.environ.get("COGNITIVE_OS_SESSION_ID")
        or os.environ.get("CODEX_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
        or default
    )


def current_branch(project_dir: Path) -> str:
    """Return the current branch name when git is available."""

    proc = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=str(project_dir),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=60,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def is_expired(claim: dict[str, Any], now: float | None = None) -> bool:
    """Return whether a claim is no longer live."""

    expires = parse_epoch(claim.get("expires_at"))
    return expires is not None and (now or time.time()) >= expires


def read_claims(project_dir: str | Path, *, include_expired: bool = False) -> list[dict[str, Any]]:
    """Read live claims from the coordination ledger."""

    data = read_json(ledger_path(project_dir), {"version": 1, "claims": []})
    rows = [row for row in data.get("claims", []) if isinstance(row, dict)]
    if include_expired:
        return rows
    now = time.time()
    return [row for row in rows if row.get("status", "active") == "active" and not is_expired(row, now)]


def acquire_claim(
    project_dir: str | Path,
    *,
    kind: str,
    subject: str,
    session_id: str | None = None,
    owner: str | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    metadata: dict[str, Any] | None = None,
) -> ClaimResult:
    """Acquire an intent claim, blocking conflicting active claims."""

    if kind not in CLAIM_KINDS:
        raise ValueError(f"unknown claim kind: {kind}")
    project = Path(project_dir).resolve()
    session = session_id or current_session_id()
    normalized = normalize_subject(kind, subject)
    created = now_iso()
    expires_at = datetime.fromtimestamp(time.time() + max(60, ttl_seconds), tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    claim = {
        "kind": kind,
        "subject": normalized,
        "raw_subject": subject,
        "session_id": session,
        "owner": owner or os.environ.get("USER") or "unknown",
        "branch": current_branch(project),
        "worktree": str(project),
        "host": socket.gethostname(),
        "pid": os.getpid(),
        "status": "active",
        "claimed_at": created,
        "expires_at": expires_at,
        "metadata": metadata or {},
    }
    path = ledger_path(project)
    with _lock_path(path).open("w", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        data = read_json(path, {"version": 1, "claims": []})
        claims = [row for row in data.get("claims", []) if isinstance(row, dict)]
        live_claims = [row for row in claims if row.get("status", "active") == "active" and not is_expired(row)]
        for existing in live_claims:
            same_subject = existing.get("kind") == kind and existing.get("subject") == normalized
            same_owner = existing.get("session_id") == session
            if same_subject and not same_owner:
                return ClaimResult(status="blocked", held_by=existing)
        replaced = [
            row
            for row in claims
            if not (
                row.get("kind") == kind
                and row.get("subject") == normalized
                and row.get("session_id") == session
                and row.get("status", "active") == "active"
            )
        ]
        data["claims"] = [*replaced, claim]
        data["updated_at"] = created
        atomic_write_json(path, data)
    return ClaimResult(status="acquired", claim=claim)


def release_claim(project_dir: str | Path, *, kind: str, subject: str, session_id: str | None = None) -> ClaimResult:
    """Release an owned claim."""

    project = Path(project_dir).resolve()
    session = session_id or current_session_id()
    normalized = normalize_subject(kind, subject)
    path = ledger_path(project)
    with _lock_path(path).open("w", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        data = read_json(path, {"version": 1, "claims": []})
        claims = [row for row in data.get("claims", []) if isinstance(row, dict)]
        kept: list[dict[str, Any]] = []
        released: dict[str, Any] | None = None
        for row in claims:
            if row.get("kind") == kind and row.get("subject") == normalized and row.get("session_id") == session and row.get("status", "active") == "active":
                released = {**row, "status": "released", "released_at": now_iso()}
                kept.append(released)
            else:
                kept.append(row)
        data["claims"] = kept
        data["updated_at"] = now_iso()
        atomic_write_json(path, data)
    return ClaimResult(status="released" if released else "absent", claim=released)


def adr_files_for_number(project_dir: str | Path, number: int) -> list[Path]:
    """Return ADR files that use a given number."""

    adrs = Path(project_dir) / "docs" / "02-Decisions" / "adrs"
    if not adrs.exists():
        return []
    prefix = f"ADR-{number:03d}"
    return sorted(path for path in adrs.glob("ADR-*.md") if path.name.startswith(prefix))


def is_tombstone_file(path: Path) -> bool:
    """Return whether an ADR file is a tombstone."""

    if "tombstone" in path.name.lower():
        return True
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:1000].lower()
    except OSError:
        return False
    return "status: tombstone" in head


def adr_tombstone_findings(project_dir: str | Path, *, number: int, session_id: str | None = None) -> list[CoordinationFinding]:
    """Return findings that should block tombstoning an owned ADR number."""

    project = Path(project_dir).resolve()
    aid = f"ADR-{number:03d}"
    findings: list[CoordinationFinding] = []
    active_files = [path for path in adr_files_for_number(project, number) if not is_tombstone_file(path)]
    if active_files:
        rels = ", ".join(path.relative_to(project).as_posix() for path in active_files)
        findings.append(
            CoordinationFinding(
                status="FAIL",
                source=aid,
                message=f"cannot tombstone {aid}; active ADR file(s) already own this number",
                evidence=rels,
            )
        )
    session = session_id or current_session_id()
    for claim in read_claims(project):
        if claim.get("kind") == "adr-number" and claim.get("subject") == aid and claim.get("session_id") != session:
            findings.append(
                CoordinationFinding(
                    status="FAIL",
                    source=aid,
                    message=f"cannot tombstone {aid}; number is claimed by another live session",
                    evidence=json.dumps(claim, sort_keys=True),
                )
            )
    return findings


def parse_git_worktrees(project_dir: str | Path) -> list[dict[str, str]]:
    """Return git worktree rows from ``git worktree list --porcelain``."""

    proc = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=str(project_dir),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=60,
    )
    if proc.returncode != 0:
        return []
    rows: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if not line:
            if current:
                rows.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current["path"] = value
        elif key == "HEAD":
            current["head"] = value
        elif key == "branch":
            current["branch"] = value.removeprefix("refs/heads/")
    if current:
        rows.append(current)
    return rows


def record_worktree_intake(
    project_dir: str | Path,
    *,
    other_worktree: str,
    policy: str,
    summary: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Record that another worktree was reviewed before importing or ignoring it."""

    if policy not in {"read-only", "import-approved", "ignore-approved"}:
        raise ValueError("policy must be read-only, import-approved, or ignore-approved")
    project = Path(project_dir).resolve()
    record = {
        "session_id": session_id or current_session_id(),
        "current_worktree": str(project),
        "other_worktree": str(Path(other_worktree).resolve()),
        "policy": policy,
        "summary": summary,
        "recorded_at": now_iso(),
    }
    path = intake_path(project)
    with _lock_path(path).open("w", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        data = read_json(path, {"version": 1, "records": []})
        records = [row for row in data.get("records", []) if isinstance(row, dict)]
        data["records"] = [*records, record]
        data["updated_at"] = record["recorded_at"]
        atomic_write_json(path, data)
    return record


def read_intake_records(project_dir: str | Path) -> list[dict[str, Any]]:
    """Read worktree intake records."""

    data = read_json(intake_path(project_dir), {"version": 1, "records": []})
    return [row for row in data.get("records", []) if isinstance(row, dict)]


def worktree_intake_findings(project_dir: str | Path, *, require_for_all: bool = True) -> list[CoordinationFinding]:
    """Return findings for active worktrees that lack an intake record."""

    project = Path(project_dir).resolve()
    rows = parse_git_worktrees(project)
    if len(rows) <= 1:
        return []
    current = str(project)
    others = [row for row in rows if str(Path(row.get("path", "")).resolve()) != current]
    records = read_intake_records(project)
    covered = {str(Path(str(row.get("other_worktree", ""))).resolve()) for row in records}
    findings: list[CoordinationFinding] = []
    for row in others:
        other = str(Path(row.get("path", "")).resolve())
        if other in covered:
            continue
        findings.append(
            CoordinationFinding(
                status="FAIL" if require_for_all else "WARN",
                source="worktree-intake",
                message="active sibling worktree has no intake record for this session branch",
                evidence=f"{row.get('branch', '')} {other}",
            )
        )
    return findings


def findings_to_dict(findings: Sequence[CoordinationFinding]) -> list[dict[str, str]]:
    """Serialize coordination findings."""

    return [asdict(finding) for finding in findings]
