"""ADR-269 append-only contract for manifests/history-rewrite-ledger.yaml.

Asserts the current on-disk ledger entries are a STRICT-PREFIX SUPERSET of
the ledger entries committed at HEAD. New entries may be appended at the
bottom; previously-recorded entries must remain byte-equivalent for the
fields they declare (timestamp, operator, adr_ref, reason, bundle_path,
sha_before, sha_after, rewrite_scope, tool, invocation).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER_RELATIVE = "manifests/history-rewrite-ledger.yaml"


def _entries_from_yaml(text: str) -> list[dict[str, Any]]:
    data = yaml.safe_load(text) or {}
    entries = data.get("entries") or []
    return [dict(e) for e in entries]


def _head_blob(repo: Path, path: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", f"HEAD:{path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def test_ledger_file_exists() -> None:
    assert (REPO_ROOT / LEDGER_RELATIVE).exists(), (
        f"manifests/history-rewrite-ledger.yaml must exist (ADR-269 Primitive 1)."
    )


def test_ledger_yaml_well_formed() -> None:
    text = (REPO_ROOT / LEDGER_RELATIVE).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert isinstance(data, dict), "ledger must be a YAML mapping"
    assert data.get("schema_version", "").startswith("history-rewrite-ledger/"), (
        "schema_version must declare history-rewrite-ledger/v1"
    )
    entries = data.get("entries")
    assert isinstance(entries, list), "entries must be a list (may be empty)"


def test_ledger_entries_have_required_fields() -> None:
    text = (REPO_ROOT / LEDGER_RELATIVE).read_text(encoding="utf-8")
    entries = _entries_from_yaml(text)
    required = {
        "timestamp", "operator", "adr_ref", "reason",
        "bundle_path", "sha_before", "sha_after",
        "rewrite_scope", "tool", "invocation",
    }
    for i, entry in enumerate(entries):
        missing = required - set(entry.keys())
        assert not missing, f"entry[{i}] missing fields: {missing}"


def test_ledger_append_only_against_head() -> None:
    """New ledger entries may be appended; existing entries must not change."""
    current_text = (REPO_ROOT / LEDGER_RELATIVE).read_text(encoding="utf-8")
    head_text = _head_blob(REPO_ROOT, LEDGER_RELATIVE)
    if head_text is None:
        pytest.skip(
            "ledger not yet committed at HEAD; append-only contract activates after first commit."
        )
    head_entries = _entries_from_yaml(head_text)
    current_entries = _entries_from_yaml(current_text)
    assert len(current_entries) >= len(head_entries), (
        "ledger has fewer entries than HEAD — append-only violated (entry removed)."
    )
    for i, head_entry in enumerate(head_entries):
        cur = current_entries[i]
        for key, value in head_entry.items():
            assert cur.get(key) == value, (
                f"entry[{i}].{key} changed since HEAD: {head_entry.get(key)!r} -> {cur.get(key)!r} "
                "(append-only contract violated)."
            )
