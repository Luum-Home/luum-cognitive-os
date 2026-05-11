"""Unit tests for cos-legal-approve (ADR-270 #5)."""
from __future__ import annotations

import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-legal-approve"


def _load_module():
    name = SCRIPT.name.replace('-', '_')
    loader = SourceFileLoader(name, str(SCRIPT))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_sha256_matches_known(tmp_path):
    mod = _load_module()
    p = tmp_path / "memo.pdf"
    p.write_bytes(b"hello")
    expected = hashlib.sha256(b"hello").hexdigest()
    assert mod.sha256_of(p) == expected


def test_find_adr_path_returns_existing_adr():
    mod = _load_module()
    p = mod.find_adr_path("ADR-270")
    assert p is not None and p.exists()
    assert "ADR-270" in p.name


def test_adr_is_accepted_true_for_270():
    mod = _load_module()
    p = mod.find_adr_path("ADR-270")
    assert mod.adr_is_accepted(p) is True


def test_update_annex_f_frontmatter_round_trip(tmp_path):
    mod = _load_module()
    annex = tmp_path / "annex.md"
    annex.write_text(
        "---\ntitle: T\nreviewed-by-legal: no\n---\n# body\n"
    )
    mod.update_annex_f_frontmatter(annex, {"reviewed-by-legal": "yes", "legal-decision": "approved"})
    text = annex.read_text()
    import re
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    fm = yaml.safe_load(m.group(1))
    assert fm["reviewed-by-legal"] == "yes"
    assert fm["legal-decision"] == "approved"


def test_derive_tool_slug_from_filename():
    mod = _load_module()
    assert mod.derive_tool_slug(Path("hermes-annex-f-compliance-cleanroom-2026-05-11.md")).startswith("hermes")
    assert mod.derive_tool_slug(Path("holaos-annex-f.md")).startswith("holaos")


def test_main_writes_ledger_and_frontmatter(tmp_path, monkeypatch):
    """Full smoke: create a temp annex + memo, point ledger to a temp file, run main."""
    mod = _load_module()
    # Build temp annex
    annex = tmp_path / "tmpkit-annex-f.md"
    annex.write_text("---\ntitle: T\nreviewed-by-legal: no\nannex: F\n---\n# tmpkit\n")
    memo = tmp_path / "memo.pdf"
    memo.write_bytes(b"counsel review content")
    # Redirect ledger
    ledger = tmp_path / "legal-review-ledger.yaml"
    ledger.write_text(
        "schema_version: legal-review-ledger/v1\nentries:\n  - tool: tmpkit\n    adr_ref: ADR-270\n    decision: pending\n    annex_f_path: " + str(annex) + "\n"
    )
    monkeypatch.setattr(mod, "LEDGER_PATH", ledger)
    rc = mod.main([
        "--adr", "ADR-270",
        "--annex-f", str(annex),
        "--counsel", "Jane Doe, Acme IP LLP",
        "--memo", str(memo),
        "--decision", "approved",
        "--tool", "tmpkit",
    ])
    assert rc == 0
    # Annex frontmatter mutated
    import re
    text = annex.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    fm = yaml.safe_load(m.group(1))
    assert fm["reviewed-by-legal"] == "yes"
    assert fm["legal-decision"] == "approved"
    assert fm["legal-counsel"] == "Jane Doe, Acme IP LLP"
    # Ledger entry filled
    data = yaml.safe_load(ledger.read_text())
    entry = [e for e in data["entries"] if e["tool"] == "tmpkit"][0]
    assert entry["decision"] == "approved"
    assert entry["memo_sha256"] == hashlib.sha256(b"counsel review content").hexdigest()


def test_main_rejects_missing_memo(tmp_path):
    mod = _load_module()
    annex = tmp_path / "x-annex-f.md"
    annex.write_text("---\ntitle: T\n---\n")
    rc = mod.main([
        "--adr", "ADR-270",
        "--annex-f", str(annex),
        "--counsel", "X",
        "--memo", str(tmp_path / "missing.pdf"),
        "--decision", "approved",
    ])
    assert rc == 1


def test_main_rejects_conditions_missing_when_required(tmp_path, monkeypatch):
    mod = _load_module()
    annex = tmp_path / "y-annex-f.md"
    annex.write_text("---\ntitle: T\n---\n")
    memo = tmp_path / "m.pdf"
    memo.write_bytes(b"x")
    rc = mod.main([
        "--adr", "ADR-270",
        "--annex-f", str(annex),
        "--counsel", "X",
        "--memo", str(memo),
        "--decision", "approved-with-conditions",
    ])
    assert rc == 1
