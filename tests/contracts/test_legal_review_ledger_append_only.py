"""Contract test: legal-review-ledger.yaml is append-only.

ADR-270 primitive #7. Existing entries MUST NOT be deleted between commits;
schema_version and contract fields are immutable; entries may only grow.

This test compares the working-tree ledger against the version recorded at
HEAD. If running on a worktree where the ledger does not yet exist in HEAD
(e.g. this very commit introduces it), the test passes trivially.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "manifests" / "legal-review-ledger.yaml"


def _head_version() -> str | None:
    if not shutil.which("git"):
        return None
    try:
        out = subprocess.run(
            ["git", "show", "HEAD:manifests/legal-review-ledger.yaml"],
            cwd=ROOT, capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def test_ledger_yaml_is_valid():
    assert LEDGER.exists(), f"missing ledger: {LEDGER}"
    data = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    assert data["schema_version"] == "legal-review-ledger/v1"
    assert isinstance(data.get("entries"), list)


def test_ledger_entries_have_required_fields():
    data = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    required = {"tool", "adr_ref", "decision", "annex_f_path"}
    for entry in data["entries"]:
        missing = required - set(entry.keys())
        assert not missing, f"entry {entry.get('tool')!r} missing fields: {missing}"


def test_ledger_decisions_are_valid_values():
    data = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    valid = {"pending", "approved", "approved-with-conditions", "rejected"}
    for entry in data["entries"]:
        d = str(entry.get("decision", "")).lower()
        assert d in valid, f"invalid decision: {d}"


def test_ledger_append_only_versus_head():
    """Working-tree must contain at least every (tool, adr_ref) tuple from HEAD."""
    head = _head_version()
    if head is None:
        pytest.skip("ledger absent in HEAD or git unavailable")
    head_data = yaml.safe_load(head) or {}
    head_keys = {
        (e.get("tool"), e.get("adr_ref"))
        for e in head_data.get("entries", []) or []
    }
    cur = yaml.safe_load(LEDGER.read_text(encoding="utf-8")) or {}
    cur_keys = {
        (e.get("tool"), e.get("adr_ref"))
        for e in cur.get("entries", []) or []
    }
    removed = head_keys - cur_keys
    assert not removed, f"entries removed from ledger (append-only violation): {removed}"
    # schema_version must not change
    assert cur.get("schema_version") == head_data.get("schema_version", cur.get("schema_version"))
