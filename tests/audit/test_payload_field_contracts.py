"""Guard the payload-contract auditor and pin BLIND payload reads at 3.

A BLIND read is a hook reading a harness-owned *verdict* field with a default
that is itself a legal reading of that field — the hook cannot tell "the tool
succeeded" from "the field is not there".  See
docs/06-Daily/reports/payload-contract-architecture-2026-08-15.md.

The count is a ratchet: it may go down, never up.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_payload_field_contracts.py"

# Known BLIND reads as of 2026-08-15.  Shrinking this set is the point; growing
# it means a new hook was written with the defect the auditor exists to stop.
KNOWN_BLIND = {
    ("hooks/error-learning.sh", ".exit_code"),
    ("hooks/error-pipeline.sh", ".exit_code"),
    ("packages/skill-governance/hooks/skill-tracker.sh", ".exit_code"),
}


@pytest.fixture(scope="module")
def audit():
    spec = importlib.util.spec_from_file_location("_payload_audit", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_payload_audit"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_script_exists_and_is_executable():
    assert SCRIPT.is_file(), f"missing {SCRIPT.name}"
    assert SCRIPT.stat().st_mode & 0o111, f"{SCRIPT.name} must be executable"


def test_scan_finds_payload_reads(audit):
    findings = audit.scan()
    assert len(findings) > 100, "auditor stopped seeing payload reads — regex rot?"


def test_blind_reads_do_not_grow(audit):
    blind = {(r["file"], r["field"]) for r in audit.scan() if r["verdict"] == "BLIND"}
    new = blind - KNOWN_BLIND
    assert not new, (
        "new BLIND payload read(s) — a verdict field is being read with a "
        f"permissive default: {sorted(new)}"
    )


def test_scan_is_deterministic(audit):
    assert audit.scan() == audit.scan()


@pytest.mark.parametrize(
    ("field", "default", "expected"),
    [
        (".exit_code", "0", "BLIND"),
        (".tool_response.is_error", "false", "BLIND"),
        (".tool_response.status", "ok", "BLIND"),
        (".tool_name", "unknown", "GUARDED"),
        (".tool_input.command", "", "INERT"),
        (".tool_response.stdout", "empty", "INERT"),
    ],
)
def test_default_classification(audit, field, default, expected):
    assert audit._classify(field, default) == expected


def test_only_harness_owned_roots_are_audited(audit):
    roots = {audit._root_of(r["field"]) for r in audit.scan()}
    assert roots <= audit.HARNESS_OWNED_ROOTS, (
        "auditor drifted into OS-owned state files; it must only cover fields "
        "the harness controls"
    )
