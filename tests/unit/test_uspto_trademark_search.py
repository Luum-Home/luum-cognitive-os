"""Unit tests for cos-uspto-trademark-search (ADR-270 #2)."""
from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-uspto-trademark-search"


def _load_module():
    name = SCRIPT.name.replace('-', '_')
    loader = SourceFileLoader(name, str(SCRIPT))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_normalize_mark_lowercase_alnum():
    mod = _load_module()
    assert mod._normalize_mark("holaOS") == "holaos"
    assert mod._normalize_mark("Hola-Boss!") == "holaboss"


def test_fuzzy_score_self_is_one():
    mod = _load_module()
    assert mod._fuzzy_score("holaOS", "holaOS") == 1.0


def test_build_report_envelope_with_empty_results():
    mod = _load_module()
    results = {"holaOS": {"marks": []}}
    report = mod.build_report(["holaOS"], "042", results)
    assert report["schema_version"] == "uspto-trademark-report/v1"
    assert report["summary"]["marks_queried"] == 1
    assert report["summary"]["any_live_match"] is False


def test_build_report_with_live_match():
    mod = _load_module()
    results = {
        "holaOS": {
            "marks": [
                {"wordmark": "HOLAOS", "status": "live", "owner": "ACME", "filing_date": "2024-01-01"}
            ]
        }
    }
    report = mod.build_report(["holaOS"], "042", results)
    assert report["summary"]["any_live_match"] is True
    assert report["classified"][0]["similar_marks"][0]["status"] == "LIVE"


def test_cli_offline_writes_file(tmp_path):
    mod = _load_module()
    out = tmp_path / "tm.json"
    rc = mod.main(["--mark", "holaOS", "--mark", "Holaboss", "--offline", "--output", str(out)])
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["summary"]["marks_queried"] == 2


def test_render_markdown_smoke():
    mod = _load_module()
    report = mod.build_report(["holaOS"], "", {"holaOS": {"marks": []}})
    md = mod.render_markdown(report)
    assert "Trademark" in md
