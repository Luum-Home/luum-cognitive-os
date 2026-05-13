# SCOPE: both
"""Engram write gate — dry-run preview + approval check (ADR-287, capability 2).

Wraps any ``save_fn`` (e.g. ``lib.engram_client.save_observation``) with two
controls:

- ``dry_run=True`` returns a :class:`WriteGatePreview` of the payload that
  WOULD be written. No DB mutation occurs.
- ``approved=False`` rejects the call with :class:`ApprovalRequiredError`
  when ``ENGRAM_REQUIRE_APPROVAL=1`` is set in the environment.

Every gated call appends a JSONL record to
``.cognitive-os/metrics/engram-write-gate.jsonl`` for audit.

The gate is transport-agnostic: it does not import the HTTP client or
subprocess CLI. Callers inject the underlying save function.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from lib.engram_wave3_schema import (
    CLAIM_TYPES_REQUIRING_EVIDENCE,
    EvidenceRequiredError,
    validate_claim_evidence,
)

DEFAULT_AUDIT_PATH = Path(".cognitive-os/metrics/engram-write-gate.jsonl")

ENV_REQUIRE_APPROVAL = "ENGRAM_REQUIRE_APPROVAL"
ENV_REQUIRE_EVIDENCE_TYPES = "ENGRAM_REQUIRE_EVIDENCE_FOR_TYPES"


class ApprovalRequiredError(PermissionError):
    """Raised when ``approved=False`` is passed in strict-approval mode."""


@dataclass
class WriteGatePreview:
    """The payload that would be written, plus resolution metadata."""

    action: str  # 'dry_run'
    title: str
    content: str
    type: str
    project: str
    topic_key: str
    evidence: list[str] = field(default_factory=list)
    evidence_hashes: dict[str, str] = field(default_factory=dict)
    would_upsert: bool = False  # True if a row with topic_key already exists

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(
    audit_path: Path,
    *,
    action: str,
    title: str,
    type_: str,
    topic_key: str,
    project: str,
    evidence_count: int,
    actor: str,
) -> None:
    record = {
        "ts": _now_iso(),
        "action": action,
        "title": title[:200],
        "type": type_,
        "topic_key": topic_key,
        "project": project,
        "evidence_count": evidence_count,
        "actor": actor,
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# Strict-mode helpers
# ---------------------------------------------------------------------------


def _strict_approval_required() -> bool:
    return os.environ.get(ENV_REQUIRE_APPROVAL, "").strip() == "1"


def _strict_evidence_types() -> frozenset[str]:
    raw = os.environ.get(ENV_REQUIRE_EVIDENCE_TYPES, "").strip()
    if not raw:
        return frozenset()
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def gated_save(
    save_fn: Callable[..., dict[str, Any] | None],
    title: str,
    content: str,
    *,
    type_: str = "manual",
    topic_key: str = "",
    project: str = "",
    evidence: list[str] | None = None,
    evidence_hashes: dict[str, str] | None = None,
    dry_run: bool = False,
    approved: bool = True,
    actor: str = "unknown",
    existing_lookup_fn: Callable[[str, str], dict[str, Any] | None] | None = None,
    audit_path: Path | str = DEFAULT_AUDIT_PATH,
    **save_kwargs: Any,
) -> dict[str, Any] | WriteGatePreview | None:
    """Gate a save call.

    Returns:
      - :class:`WriteGatePreview` when ``dry_run=True``.
      - The underlying ``save_fn`` result on commit.
      - Raises :class:`ApprovalRequiredError` when strict approval is on and
        ``approved=False``.
      - Raises :class:`EvidenceRequiredError` when strict evidence types are
        configured and a claim-bearing type lacks evidence.
    """
    audit = Path(audit_path)
    evidence_list = list(evidence or [])

    # Strict evidence enforcement (opt-in via env).
    strict_types = _strict_evidence_types()
    if strict_types:
        try:
            validate_claim_evidence(type_, evidence_list, strict_types=strict_types)
        except EvidenceRequiredError:
            _audit(
                audit,
                action="rejected:no-evidence",
                title=title,
                type_=type_,
                topic_key=topic_key,
                project=project,
                evidence_count=0,
                actor=actor,
            )
            raise

    # Strict approval enforcement (opt-in via env).
    if _strict_approval_required() and not approved:
        _audit(
            audit,
            action="rejected:not-approved",
            title=title,
            type_=type_,
            topic_key=topic_key,
            project=project,
            evidence_count=len(evidence_list),
            actor=actor,
        )
        raise ApprovalRequiredError(
            "ENGRAM_REQUIRE_APPROVAL=1 but call did not pass approved=True"
        )

    would_upsert = False
    if topic_key and existing_lookup_fn is not None:
        try:
            would_upsert = existing_lookup_fn(topic_key, project) is not None
        except Exception:
            would_upsert = False

    if dry_run:
        preview = WriteGatePreview(
            action="dry_run",
            title=title,
            content=content,
            type=type_,
            project=project,
            topic_key=topic_key,
            evidence=evidence_list,
            evidence_hashes=dict(evidence_hashes or {}),
            would_upsert=would_upsert,
        )
        _audit(
            audit,
            action="dry_run",
            title=title,
            type_=type_,
            topic_key=topic_key,
            project=project,
            evidence_count=len(evidence_list),
            actor=actor,
        )
        return preview

    # Commit path.
    result = save_fn(
        title,
        content,
        type_=type_,
        topic_key=topic_key,
        project=project,
        **save_kwargs,
    )
    _audit(
        audit,
        action="approved",
        title=title,
        type_=type_,
        topic_key=topic_key,
        project=project,
        evidence_count=len(evidence_list),
        actor=actor,
    )
    return result


def is_claim_type(obs_type: str) -> bool:
    """Convenience: is this an observation type that semantically carries claims?"""
    return obs_type in CLAIM_TYPES_REQUIRING_EVIDENCE
