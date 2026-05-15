# SCOPE: os-only
"""ADR-184 intent arbitration for cosd critical-surface ownership.

The arbiter is intentionally narrow in v1: it owns ADR identity intents
(`adr-number-request` and `adr-tombstone-request`) and persists results under
`.cognitive-os/cosd/results/`. It does not author ADR prose.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from lib.session_coordination import adr_tombstone_findings


COSD_DIR = Path(".cognitive-os") / "cosd"
INTENTS_DIR = COSD_DIR / "intents"
RESULTS_DIR = COSD_DIR / "results"
RUNTIME_DIR = COSD_DIR / "runtime"
ARBITRATIONS_LOG = COSD_DIR / "arbitrations.jsonl"

ADR_FILE_RE = re.compile(r"^ADR-(\d{3,})-.+\.md$")
INTENT_KINDS = {"adr-number-request", "adr-tombstone-request"}


@dataclass(frozen=True)
class Intent:
    """Cosd intent payload."""

    id: str
    kind: str
    session_id: str
    submitted_at: str
    context: dict[str, Any]


@dataclass(frozen=True)
class ArbitrationResult:
    """Cosd result payload."""

    id: str
    status: str
    decision: dict[str, Any]
    decided_at: str
    reason: str = ""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def project_path(project_dir: str | Path, relative: Path) -> Path:
    return Path(project_dir).resolve() / relative


def intents_dir(project_dir: str | Path) -> Path:
    return project_path(project_dir, INTENTS_DIR)


def results_dir(project_dir: str | Path) -> Path:
    return project_path(project_dir, RESULTS_DIR)


def runtime_dir(project_dir: str | Path) -> Path:
    return project_path(project_dir, RUNTIME_DIR)


def lock_path(project_dir: str | Path) -> Path:
    return runtime_dir(project_dir) / "intent-arbiter.lock"


def pid_path(project_dir: str | Path) -> Path:
    return runtime_dir(project_dir) / "cosd.pid"


def stop_path(project_dir: str | Path) -> Path:
    return runtime_dir(project_dir) / "cosd.stop"


def started_path(project_dir: str | Path) -> Path:
    return runtime_dir(project_dir) / "cosd.started.json"


def result_path(project_dir: str | Path, intent_id: str) -> Path:
    return results_dir(project_dir) / f"{safe_id(intent_id)}.json"


def safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in value).strip(".-")
    return cleaned or f"intent-{uuid.uuid4().hex[:12]}"


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "untitled"


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True))
        handle.write("\n")


def parse_intent(payload: dict[str, Any]) -> Intent:
    intent_id = str(payload.get("id") or "").strip()
    kind = str(payload.get("kind") or "").strip().replace("_", "-")
    session_id = str(payload.get("session_id") or "unknown").strip() or "unknown"
    submitted_at = str(payload.get("submitted_at") or utc_now_iso())
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    if not intent_id:
        raise ValueError("intent.id is required")
    if kind not in INTENT_KINDS:
        raise ValueError(f"unsupported intent kind: {kind}")
    return Intent(id=safe_id(intent_id), kind=kind, session_id=session_id, submitted_at=submitted_at, context=context)


def submit_intent(
    project_dir: str | Path,
    *,
    kind: str,
    session_id: str,
    context: dict[str, Any],
    intent_id: str | None = None,
    submitted_at: str | None = None,
) -> dict[str, Any]:
    """Persist an intent for cosd arbitration."""

    intent_id = safe_id(intent_id or f"intent-{uuid.uuid4().hex[:12]}")
    intent = Intent(
        id=intent_id,
        kind=kind.strip().replace("_", "-"),
        session_id=session_id or "unknown",
        submitted_at=submitted_at or utc_now_iso(),
        context=context,
    )
    if intent.kind not in INTENT_KINDS:
        raise ValueError(f"unsupported intent kind: {intent.kind}")
    path = intents_dir(project_dir) / f"{intent.id}.json"
    if result_path(project_dir, intent.id).exists():
        return {"ok": True, "status": "already-decided", "intent": asdict(intent), "intent_path": str(path)}
    if path.exists():
        stored = read_json(path) or {}
        return {
            "ok": True,
            "status": "already-submitted",
            "intent": stored if stored else asdict(intent),
            "intent_path": str(path),
        }
    atomic_write_json(path, asdict(intent))
    return {"ok": True, "status": "submitted", "intent": asdict(intent), "intent_path": str(path)}


def iter_adr_numbers(project_dir: str | Path) -> Iterable[int]:
    adrs_dir = Path(project_dir).resolve() / "docs" / "02-Decisions" / "adrs"
    if not adrs_dir.is_dir():
        return []
    numbers: list[int] = []
    for path in adrs_dir.iterdir():
        match = ADR_FILE_RE.match(path.name)
        if match:
            numbers.append(int(match.group(1)))
    return numbers


def iter_reserved_numbers(project_dir: str | Path) -> Iterable[int]:
    numbers: list[int] = []
    for path in results_dir(project_dir).glob("*.json"):
        payload = read_json(path)
        if not payload or payload.get("status") != "granted":
            continue
        decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
        number = decision.get("adr_number")
        if isinstance(number, int):
            numbers.append(number)
    return numbers


def next_adr_number(project_dir: str | Path) -> int:
    used = [*iter_adr_numbers(project_dir), *iter_reserved_numbers(project_dir)]
    return (max(used) if used else 0) + 1


def result_payload(result: ArbitrationResult) -> dict[str, Any]:
    payload = asdict(result)
    if not payload["reason"]:
        payload.pop("reason")
    return payload


def grant_adr_number(project_dir: str | Path, intent: Intent) -> ArbitrationResult:
    topic = str(intent.context.get("topic") or intent.context.get("title") or "Untitled ADR")
    stem = slugify(str(intent.context.get("filename_stem") or topic))
    number = next_adr_number(project_dir)
    aid = f"ADR-{number:03d}"
    filename = f"{aid}-{stem}.md"
    return ArbitrationResult(
        id=intent.id,
        status="granted",
        decision={
            "adr_number": number,
            "reserved_filename": filename,
            "claim_subject": aid,
            "session_id": intent.session_id,
        },
        decided_at=utc_now_iso(),
    )


def decide_tombstone(project_dir: str | Path, intent: Intent) -> ArbitrationResult:
    raw_number = intent.context.get("adr_number")
    try:
        if not isinstance(raw_number, (int, str)):
            raise ValueError("invalid adr_number")
        number = int(raw_number)
    except Exception:
        return ArbitrationResult(
            id=intent.id,
            status="rejected",
            decision={},
            decided_at=utc_now_iso(),
            reason="context.adr_number must be an integer",
        )
    findings = adr_tombstone_findings(project_dir, number=number, session_id=intent.session_id)
    if findings:
        return ArbitrationResult(
            id=intent.id,
            status="rejected",
            decision={
                "adr_number": number,
                "findings": [asdict(finding) for finding in findings],
            },
            decided_at=utc_now_iso(),
            reason="active ADR file or live claim owns this number",
        )
    aid = f"ADR-{number:03d}"
    filename = str(intent.context.get("candidate_filename") or f"{aid}-tombstone.md")
    if not filename.startswith(f"{aid}-") or not filename.endswith(".md"):
        return ArbitrationResult(
            id=intent.id,
            status="rejected",
            decision={"adr_number": number, "candidate_filename": filename},
            decided_at=utc_now_iso(),
            reason="candidate filename must preserve ADR number and .md suffix",
        )
    return ArbitrationResult(
        id=intent.id,
        status="granted",
        decision={
            "adr_number": number,
            "authorized_filename": filename,
            "session_id": intent.session_id,
        },
        decided_at=utc_now_iso(),
    )


def arbitrate_intent(project_dir: str | Path, intent: Intent) -> ArbitrationResult:
    if intent.kind == "adr-number-request":
        return grant_adr_number(project_dir, intent)
    if intent.kind == "adr-tombstone-request":
        return decide_tombstone(project_dir, intent)
    return ArbitrationResult(id=intent.id, status="rejected", decision={}, decided_at=utc_now_iso(), reason=f"unsupported intent kind: {intent.kind}")


def pending_intent_paths(project_dir: str | Path) -> list[Path]:
    paths = sorted(intents_dir(project_dir).glob("*.json"), key=lambda path: path.name)
    return [path for path in paths if not result_path(project_dir, path.stem).exists()]


def process_once(project_dir: str | Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    """Process pending intents once under an exclusive arbiter lock."""

    root = Path(project_dir).resolve()
    lock = lock_path(root)
    lock.parent.mkdir(parents=True, exist_ok=True)
    processed: list[dict[str, Any]] = []
    with lock.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        for path in pending_intent_paths(root):
            if limit is not None and len(processed) >= limit:
                break
            payload = read_json(path)
            if not payload:
                continue
            try:
                intent = parse_intent(payload)
                result = arbitrate_intent(root, intent)
            except Exception as exc:
                intent_id = safe_id(str(payload.get("id") or path.stem))
                result = ArbitrationResult(id=intent_id, status="rejected", decision={}, decided_at=utc_now_iso(), reason=str(exc))
            stored = result_payload(result)
            atomic_write_json(result_path(root, result.id), stored)
            append_jsonl(project_path(root, ARBITRATIONS_LOG), stored)
            processed.append(stored)
    return processed


def queue_depth(project_dir: str | Path) -> int:
    return len(pending_intent_paths(project_dir))


def last_arbitrations(project_dir: str | Path, *, limit: int = 10) -> list[dict[str, Any]]:
    path = project_path(project_dir, ARBITRATIONS_LOG)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def status(project_dir: str | Path) -> dict[str, Any]:
    root = Path(project_dir).resolve()
    pid_payload = read_json(pid_path(root)) or {}
    started_payload = read_json(started_path(root)) or {}
    pid = int(pid_payload.get("pid") or 0)
    alive = pid_alive(pid)
    started_epoch = float(started_payload.get("started_epoch") or 0)
    uptime = max(0.0, time.time() - started_epoch) if alive and started_epoch else 0.0
    return {
        "ok": True,
        "status": "running" if alive else "stopped",
        "pid": pid if alive else None,
        "uptime_seconds": round(uptime, 3),
        "intent_queue_depth": queue_depth(root),
        "last_arbitrations": last_arbitrations(root, limit=10),
    }
