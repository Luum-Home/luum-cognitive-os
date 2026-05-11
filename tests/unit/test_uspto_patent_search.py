"""Unit tests for cos-uspto-patent-search (ADR-270 #1)."""
from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-uspto-patent-search"


def _load_module():
    name = SCRIPT.name.replace('-', '_')
    loader = SourceFileLoader(name, str(SCRIPT))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_classify_critical_when_multiple_keywords_overlap():
    mod = _load_module()
    patent = {"patent_title": "Agent runtime for LLM tools", "patent_abstract": "LLM agent runtime."}
    assert mod._classify(patent, ["agent runtime", "LLM agent"]) == "CRITICAL"


def test_classify_low_when_no_keyword_overlap():
    mod = _load_module()
    patent = {"patent_title": "Unrelated invention", "patent_abstract": "Mechanical widget."}
    assert mod._classify(patent, ["agent runtime"]) == "LOW"


def test_classify_high_when_one_keyword_overlap():
    mod = _load_module()
    patent = {"patent_title": "An agent runtime", "patent_abstract": ""}
    assert mod._classify(patent, ["agent runtime", "LLM agent"]) == "HIGH"


def test_build_report_envelope_summarizes():
    mod = _load_module()
    api_resp = {
        "patents": [
            {"patent_id": "US1", "patent_title": "LLM agent runtime", "patent_abstract": "An LLM agent.", "patent_date": "2024-01-01"},
            {"patent_id": "US2", "patent_title": "Coffee maker", "patent_abstract": "Beans.", "patent_date": "2023-01-01"},
        ]
    }
    report = mod.build_report("Holaboss", ["agent runtime", "LLM agent"], 50, api_resp)
    assert report["schema_version"] == "uspto-patent-report/v1"
    assert report["summary"]["total_returned"] == 2
    counts = report["summary"]["counts_by_relevance"]
    assert counts["CRITICAL"] + counts["HIGH"] + counts["LOW"] == 2


def test_build_report_handles_malformed_response():
    mod = _load_module()
    api_resp = {"error": "malformed-json", "raw": "<html>..."}
    report = mod.build_report("X", [], 10, api_resp)
    assert report["summary"]["total_returned"] == 0
    assert not report["summary"]["has_critical"]


def test_cli_offline_writes_file(tmp_path, monkeypatch):
    mod = _load_module()
    out = tmp_path / "rep.json"
    rc = mod.main(["--producer", "Holaboss", "--offline", "--output", str(out)])
    assert rc == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["query"]["producer"] == "Holaboss"
    assert data["raw_response"].get("_offline") is True


def test_render_markdown_smoke():
    mod = _load_module()
    api_resp = {"patents": []}
    report = mod.build_report("X", ["foo"], 5, api_resp)
    md = mod.render_markdown(report)
    assert "USPTO Patent Search" in md
