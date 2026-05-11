"""Unit tests for cos-counsel-outreach-draft (ADR-270 #4)."""
from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-counsel-outreach-draft"


def _load_module():
    name = SCRIPT.name.replace('-', '_')
    loader = SourceFileLoader(name, str(SCRIPT))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_fill_template_replaces_known_keys_and_preserves_unknown():
    mod = _load_module()
    raw = "Hello {{TOOL}}, dear {{COUNSEL_CONTACT}}."
    out = mod.fill_template(raw, {"TOOL": "Holaboss"})
    assert "Holaboss" in out
    assert "{{COUNSEL_CONTACT}}" in out


def test_build_draft_clean_room_permission(tmp_path):
    mod = _load_module()
    draft = mod.build_draft(
        tool="Holaboss",
        to="admin@holaboss.ai",
        template="clean-room-permission",
        counsel_packet=None,
        operator_name="Mat",
        operator_email="m@example.com",
    )
    assert "Holaboss" in draft
    assert "admin@holaboss.ai" in draft
    assert "NOT auto-sent" in draft


def test_build_draft_review_request_packet_name(tmp_path):
    mod = _load_module()
    draft = mod.build_draft(
        tool="holaOS",
        to="ip-counsel@acme.example",
        template="review-request",
        counsel_packet="/tmp/counsel-holaOS-2026-05-11.zip",
        operator_name="Mat",
        operator_email="m@example.com",
    )
    assert "counsel-holaOS-2026-05-11.zip" in draft


def test_main_writes_draft_file(tmp_path):
    mod = _load_module()
    out = tmp_path / "draft.md"
    rc = mod.main([
        "--tool", "Holaboss",
        "--to", "admin@holaboss.ai",
        "--template", "clean-room-permission",
        "--operator-name", "Mat",
        "--operator-email", "m@example.com",
        "--output", str(out),
    ])
    assert rc == 0
    assert out.exists()
    assert "Holaboss" in out.read_text()


def test_invalid_template_rejected(tmp_path):
    mod = _load_module()
    import pytest
    with pytest.raises(SystemExit):
        mod.main([
            "--tool", "X", "--to", "a@b", "--template", "bogus",
            "--output", str(tmp_path / "x.md"),
        ])
