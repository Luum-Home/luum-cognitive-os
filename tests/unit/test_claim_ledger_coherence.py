"""Coherence test: claims written via lib.task_claim_ledger shim must be
readable/listable by scripts.cos_task_claims, proving both APIs write to the
same canonical store (.cognitive-os/tasks/active-claims.json).

ADR-116 §P1.1 mandates a single canonical path and API.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lib.task_claim_ledger import acquire_claim, list_claims, release_claim
from scripts.cos_task_claims import (
    claim_task as ctc_claim_task,
    claim_is_stale,
    claims_path,
    list_claims as ctc_list_claims,
    normalize_claims,
    read_json,
)

pytestmark = pytest.mark.unit


def test_tcl_acquire_visible_via_ctc_list(tmp_path: Path) -> None:
    """Claim acquired through TCL shim appears in CTC list (same file)."""
    result = acquire_claim(
        tmp_path,
        task_id="coherence-task-1",
        session_id="s-coherence",
        agent_id="a-coherence",
        scope="test-scope",
        ttl_seconds=3600,
    )
    assert result.status == "acquired"

    # CTC's canonical path must contain the claim.
    path = claims_path(tmp_path)
    assert path.exists(), "Canonical CTC path must exist after TCL acquire"

    data = normalize_claims(read_json(path, {"claims": []}))
    task_ids = [c.get("task_id") for c in data["claims"]]
    assert "coherence-task-1" in task_ids, "TCL claim must appear in CTC store"

    # ctc_list_claims must also see it.
    active = ctc_list_claims(tmp_path)
    assert any(c.get("task_id") == "coherence-task-1" for c in active)


def test_ctc_claim_visible_via_tcl_list(tmp_path: Path) -> None:
    """Claim acquired through CTC appears in TCL list_claims (same file)."""
    task = {"id": "coherence-task-2", "description": "test", "deliverable": "docs/out.md"}
    ok, _ = ctc_claim_task(tmp_path, task, session="s-coherence-2")
    assert ok is True

    # TCL list_claims must see it.
    active = list_claims(tmp_path)
    assert any(c.get("task_id") == "coherence-task-2" for c in active)


def test_tcl_release_visible_via_ctc(tmp_path: Path) -> None:
    """Claim released through TCL shim is reflected in CTC store."""
    acquire_claim(
        tmp_path,
        task_id="coherence-task-3",
        session_id="s-rel",
        agent_id="a-rel",
    )
    rel = release_claim(tmp_path, task_id="coherence-task-3", session_id="s-rel")
    assert rel.status == "released"

    # CTC store should show the claim as released (not active).
    data = normalize_claims(read_json(claims_path(tmp_path), {"claims": []}))
    for c in data["claims"]:
        if c.get("task_id") == "coherence-task-3":
            assert c.get("status") == "released", "CTC store must reflect TCL release"
            break


def test_tcl_blocks_duplicate_claim_via_shared_store(tmp_path: Path) -> None:
    """TCL shim blocks a second acquirer using the same CTC backing store."""
    # First claim via CTC directly.
    task = {"id": "coherence-task-4", "description": "block test", "deliverable": "lib/foo.py"}
    ok, _ = ctc_claim_task(tmp_path, task, session="s-first")
    assert ok is True

    # Second claim attempt via TCL shim from a different session — must be blocked.
    second = acquire_claim(
        tmp_path,
        task_id="coherence-task-4",
        session_id="s-second",
        agent_id="a-second",
    )
    assert second.status == "blocked", "TCL must see CTC claim and block duplicate"
    assert second.held_by is not None


def test_extended_fields_persisted_via_tcl(tmp_path: Path) -> None:
    """TCL-specific fields (agent_id, scope, ttl_seconds, pid, host) survive in CTC store."""
    result = acquire_claim(
        tmp_path,
        task_id="coherence-task-5",
        session_id="s-fields",
        agent_id="agent-xyz",
        scope="ADR-116/P1.1",
        ttl_seconds=900,
    )
    assert result.status == "acquired"

    data = normalize_claims(read_json(claims_path(tmp_path), {"claims": []}))
    claim = next(c for c in data["claims"] if c.get("task_id") == "coherence-task-5")

    assert claim.get("agent_id") == "agent-xyz"
    assert claim.get("scope") == "ADR-116/P1.1"
    assert claim.get("ttl_seconds") == 900
    assert "expires_at" in claim
    assert "pid" in claim
    assert "host" in claim


def test_ctc_staleness_honors_per_claim_ttl_and_expires_at(tmp_path: Path) -> None:
    """TTL fields added for TCL-compatible consumers must affect pruning semantics."""
    result = acquire_claim(
        tmp_path,
        task_id="coherence-task-ttl",
        session_id="s-ttl",
        agent_id="agent-ttl",
        ttl_seconds=1,
    )
    assert result.status == "acquired"

    data = normalize_claims(read_json(claims_path(tmp_path), {"claims": []}))
    claim = next(c for c in data["claims"] if c.get("task_id") == "coherence-task-ttl")

    now_epoch = float(claim["expires_at"]) + 0.1
    assert claim_is_stale(claim, {}, now_epoch) is True
