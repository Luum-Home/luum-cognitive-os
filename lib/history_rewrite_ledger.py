"""ADR-269 history-rewrite ledger primitives.

Append-only registry of every git history rewrite performed against this
repository. Each entry pairs a recovery bundle (`.cognitive-os/recovery/
pre-history-sanitization-*.bundle`) with the ADR documenting why the rewrite
was authorized.

The ledger is YAML for human readability and lives in `manifests/` so it is
git-tracked. Append-only is enforced by:

1. A contract test that compares the on-disk file against the previous git
   blob and fails if existing entries change byte-for-byte.
2. Convention: write paths only via `append_entry()` which preserves prior
   entries verbatim.

Public API
----------
- `LedgerEntry` — dataclass mirroring the YAML schema.
- `load_ledger(project_dir)` — parse manifests/history-rewrite-ledger.yaml.
- `append_entry(project_dir, entry)` — append a new entry (idempotent on
  bundle_path; refuses to overwrite existing entries).
- `list_entries(project_dir)` — list all entries.
- `find_orphan_bundles(project_dir)` — bundles without ledger entries.
- `find_orphan_entries(project_dir)` — ledger entries without bundles on disk.
- `find_missing_bundles(project_dir)` — alias of find_orphan_entries.
- `validate_adr_accepted(project_dir, adr_ref)` — confirm ADR exists and is
  Accepted (not Proposed, not Superseded).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


SCHEMA_VERSION = "history-rewrite-ledger/v1"
DEFAULT_LEDGER_PATH = Path("manifests/history-rewrite-ledger.yaml")
RECOVERY_DIR = Path(".cognitive-os/recovery")
BUNDLE_GLOB = "pre-history-sanitization-*.bundle"
ADR_DIR = Path("docs/02-Decisions/adrs")
ADR_RE = re.compile(r"^ADR-\d{3,4}$")


@dataclass
class LedgerEntry:
    timestamp: str  # ISO-8601 UTC
    operator: str
    adr_ref: str  # e.g. ADR-268
    reason: str
    bundle_path: str  # relative to project root
    sha_before: str
    sha_after: str
    rewrite_scope: str  # commit-messages-only | blob-content | metadata | all
    tool: str  # git-filter-repo | bfg | custom
    invocation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LedgerEntry":
        return cls(
            timestamp=str(data.get("timestamp", "")),
            operator=str(data.get("operator", "")),
            adr_ref=str(data.get("adr_ref", "")),
            reason=str(data.get("reason", "")),
            bundle_path=str(data.get("bundle_path", "")),
            sha_before=str(data.get("sha_before", "")),
            sha_after=str(data.get("sha_after", "")),
            rewrite_scope=str(data.get("rewrite_scope", "")),
            tool=str(data.get("tool", "")),
            invocation=str(data.get("invocation", "")),
        )


class LedgerError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _ledger_path(project_dir: Path) -> Path:
    return Path(project_dir) / DEFAULT_LEDGER_PATH


def load_ledger(project_dir: Path) -> dict[str, Any]:
    """Return the raw parsed ledger (schema_version + entries list)."""
    path = _ledger_path(project_dir)
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "entries": []}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if "entries" not in data or data["entries"] is None:
        data["entries"] = []
    data.setdefault("schema_version", SCHEMA_VERSION)
    return data


def list_entries(project_dir: Path) -> list[LedgerEntry]:
    data = load_ledger(project_dir)
    return [LedgerEntry.from_dict(e) for e in (data.get("entries") or [])]


def _bundle_paths(project_dir: Path) -> list[Path]:
    recovery = Path(project_dir) / RECOVERY_DIR
    if not recovery.exists():
        return []
    return sorted(recovery.glob(BUNDLE_GLOB))


def find_orphan_bundles(project_dir: Path) -> list[Path]:
    """Bundles present on disk without a matching ledger entry."""
    registered = {e.bundle_path for e in list_entries(project_dir)}
    out: list[Path] = []
    for path in _bundle_paths(project_dir):
        rel = path.relative_to(Path(project_dir)).as_posix()
        if rel not in registered:
            out.append(path)
    return out


def find_orphan_entries(project_dir: Path) -> list[LedgerEntry]:
    """Ledger entries whose declared bundle is missing on disk."""
    out: list[LedgerEntry] = []
    for entry in list_entries(project_dir):
        bundle = Path(project_dir) / entry.bundle_path
        if not bundle.exists():
            out.append(entry)
    return out


def find_missing_bundles(project_dir: Path) -> list[LedgerEntry]:
    """Alias of find_orphan_entries (ADR-269 §Primitive 3 naming)."""
    return find_orphan_entries(project_dir)


def find_entries_with_missing_adr(project_dir: Path) -> list[LedgerEntry]:
    """Entries whose adr_ref does not point at an accepted ADR."""
    out: list[LedgerEntry] = []
    for entry in list_entries(project_dir):
        ok, _reason = validate_adr_accepted(project_dir, entry.adr_ref)
        if not ok:
            out.append(entry)
    return out


def _find_adr_file(project_dir: Path, adr_ref: str) -> Path | None:
    """Locate the file for a given ADR-NNN reference under docs/02-Decisions/adrs/."""
    adr_dir = Path(project_dir) / ADR_DIR
    if not adr_dir.exists():
        return None
    # ADRs follow ADR-NNN-... .md pattern. Match by prefix.
    number = adr_ref.replace("ADR-", "").lstrip("0") or "0"
    padded = f"ADR-{number.zfill(3)}"
    for candidate in adr_dir.glob(f"{padded}-*.md"):
        return candidate
    # Try four-digit form as well
    padded4 = f"ADR-{number.zfill(4)}"
    for candidate in adr_dir.glob(f"{padded4}-*.md"):
        return candidate
    return None


def validate_adr_accepted(project_dir: Path, adr_ref: str) -> tuple[bool, str]:
    """Return (ok, reason). ok=True iff ADR file exists AND status is accepted."""
    if not ADR_RE.match(adr_ref):
        return False, f"adr_ref '{adr_ref}' does not match ADR-NNN format"
    path = _find_adr_file(project_dir, adr_ref)
    if path is None:
        return False, f"no ADR file matching '{adr_ref}' under {ADR_DIR}"
    text = path.read_text(encoding="utf-8", errors="replace")
    # Look in YAML front matter for status: accepted (case insensitive).
    head = text[:2000]
    m = re.search(r"^status:\s*([a-zA-Z_-]+)", head, flags=re.MULTILINE | re.IGNORECASE)
    if m:
        status = m.group(1).strip().lower()
        if status in {"accepted", "active"}:
            return True, f"{path.name}: status={status}"
        return False, f"{path.name}: status={status} (need accepted)"
    # Fall back to "## Status" section, look for "Accepted"
    body = text[:6000]
    m2 = re.search(r"^##\s+Status\s*\n+(.+?)(?:\n##|\Z)", body, flags=re.MULTILINE | re.DOTALL)
    if m2:
        status_block = m2.group(1).lower()
        if "accepted" in status_block or "active" in status_block:
            return True, f"{path.name}: status section accepted"
        return False, f"{path.name}: status section did not match 'accepted'"
    return False, f"{path.name}: no status field found"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_entry(
    project_dir: Path,
    entry: LedgerEntry,
    *,
    validate_adr: bool = True,
) -> Path:
    """Append a new entry to the ledger.

    Raises `LedgerError` if:
      - bundle_path is already registered (append-only / no duplicates)
      - validate_adr=True and the ADR is not accepted

    The ledger is read, the entry appended (last position), and re-serialized
    via yaml.safe_dump with preserve-key-order. Existing entries are NEVER
    rewritten in semantic content; only their YAML representation may
    canonically reformat (the contract test allows representational drift but
    enforces that the entries list is a strict-prefix superset of the previous
    ledger state).

    Returns the ledger path written.
    """
    if not entry.bundle_path:
        raise LedgerError("bundle-path-required", "bundle_path must be set on the entry.")
    if not entry.adr_ref:
        raise LedgerError("adr-ref-required", "adr_ref must be set on the entry (ADR-269 mandate).")
    if not entry.reason or not entry.reason.strip():
        raise LedgerError("reason-required", "reason must be non-empty.")
    if validate_adr:
        ok, why = validate_adr_accepted(Path(project_dir), entry.adr_ref)
        if not ok:
            raise LedgerError("adr-not-accepted", f"adr_ref {entry.adr_ref} not accepted: {why}")
    if not entry.timestamp:
        entry.timestamp = _utc_now_iso()

    data = load_ledger(project_dir)
    existing = data.get("entries") or []
    for e in existing:
        if str(e.get("bundle_path")) == entry.bundle_path:
            raise LedgerError(
                "bundle-already-registered",
                f"bundle_path {entry.bundle_path} already has ledger entry (append-only).",
            )
    existing.append(entry.to_dict())
    data["entries"] = existing
    data["schema_version"] = SCHEMA_VERSION
    path = _ledger_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


__all__ = [
    "SCHEMA_VERSION",
    "DEFAULT_LEDGER_PATH",
    "LedgerEntry",
    "LedgerError",
    "append_entry",
    "find_missing_bundles",
    "find_orphan_bundles",
    "find_orphan_entries",
    "find_entries_with_missing_adr",
    "list_entries",
    "load_ledger",
    "validate_adr_accepted",
]
