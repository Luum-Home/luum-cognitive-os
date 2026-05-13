"""Unit tests for lib.engram_write_gate (ADR-287 capability 2)."""
from __future__ import annotations

import json

import pytest

from lib.engram_write_gate import (
    ApprovalRequiredError,
    WriteGatePreview,
    gated_save,
    is_claim_type,
)
from lib.engram_wave3_schema import EvidenceRequiredError


class _RecordingSave:
    def __init__(self):
        self.calls = []

    def __call__(self, title, content, *, type_, topic_key, project, **kw):
        self.calls.append(
            {
                "title": title,
                "content": content,
                "type_": type_,
                "topic_key": topic_key,
                "project": project,
            }
        )
        return {
            "id": 1,
            "title": title,
            "content": content,
            "type": type_,
            "topic_key": topic_key,
            "project": project,
        }


def test_dry_run_returns_preview_and_skips_save(tmp_path):
    rec = _RecordingSave()
    audit = tmp_path / "audit.jsonl"
    out = gated_save(
        rec,
        "title",
        "content",
        type_="decision",
        topic_key="adr/test",
        project="p",
        evidence=["src-1"],
        evidence_hashes={"src-1": "h" * 64},
        dry_run=True,
        actor="tester",
        audit_path=audit,
    )
    assert isinstance(out, WriteGatePreview)
    assert out.action == "dry_run"
    assert out.evidence == ["src-1"]
    assert out.evidence_hashes == {"src-1": "h" * 64}
    assert rec.calls == []  # No save executed.

    # Audit record exists and is JSONL.
    assert audit.exists()
    lines = audit.read_text().strip().splitlines()
    assert len(lines) == 1
    rec_line = json.loads(lines[0])
    assert rec_line["action"] == "dry_run"
    assert rec_line["evidence_count"] == 1


def test_commit_path_invokes_save(tmp_path):
    rec = _RecordingSave()
    audit = tmp_path / "audit.jsonl"
    result = gated_save(
        rec,
        "t",
        "c",
        type_="manual",
        topic_key="k",
        project="p",
        dry_run=False,
        approved=True,
        actor="tester",
        audit_path=audit,
    )
    assert result is not None
    assert result["id"] == 1
    assert len(rec.calls) == 1

    line = json.loads(audit.read_text().strip().splitlines()[-1])
    assert line["action"] == "approved"


def test_strict_approval_rejects_when_not_approved(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_REQUIRE_APPROVAL", "1")
    rec = _RecordingSave()
    audit = tmp_path / "audit.jsonl"
    with pytest.raises(ApprovalRequiredError):
        gated_save(
            rec,
            "t",
            "c",
            type_="manual",
            approved=False,
            audit_path=audit,
        )
    assert rec.calls == []
    line = json.loads(audit.read_text().strip().splitlines()[-1])
    assert line["action"].startswith("rejected")


def test_strict_approval_off_allows_unapproved(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_REQUIRE_APPROVAL", raising=False)
    rec = _RecordingSave()
    audit = tmp_path / "audit.jsonl"
    result = gated_save(
        rec,
        "t",
        "c",
        type_="manual",
        approved=False,
        audit_path=audit,
    )
    assert result is not None
    assert len(rec.calls) == 1


def test_strict_evidence_blocks_claim_without_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "ENGRAM_REQUIRE_EVIDENCE_FOR_TYPES", "fact,decision,workflow"
    )
    rec = _RecordingSave()
    audit = tmp_path / "audit.jsonl"
    with pytest.raises(EvidenceRequiredError):
        gated_save(
            rec,
            "t",
            "c",
            type_="decision",
            evidence=None,
            audit_path=audit,
        )
    assert rec.calls == []


def test_strict_evidence_allows_non_claim_types(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "ENGRAM_REQUIRE_EVIDENCE_FOR_TYPES", "fact,decision,workflow"
    )
    rec = _RecordingSave()
    audit = tmp_path / "audit.jsonl"
    # 'discovery' is not in the strict list -> allowed without evidence.
    result = gated_save(
        rec,
        "t",
        "c",
        type_="discovery",
        evidence=None,
        audit_path=audit,
    )
    assert result is not None


def test_would_upsert_set_when_existing_lookup_returns_row(tmp_path):
    rec = _RecordingSave()

    def lookup(topic_key, project):
        return {"id": 99} if topic_key == "exists" else None

    out = gated_save(
        rec,
        "t",
        "c",
        type_="manual",
        topic_key="exists",
        project="p",
        dry_run=True,
        existing_lookup_fn=lookup,
        audit_path=tmp_path / "a.jsonl",
    )
    assert isinstance(out, WriteGatePreview)
    assert out.would_upsert is True


def test_is_claim_type():
    assert is_claim_type("decision")
    assert is_claim_type("fact")
    assert is_claim_type("workflow")
    assert not is_claim_type("discovery")
    assert not is_claim_type("manual")
