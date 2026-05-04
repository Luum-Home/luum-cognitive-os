"""Tests for ADR implementation ledger reconciliation."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "adr_implementation_ledger.py"

spec = importlib.util.spec_from_file_location("adr_implementation_ledger", SCRIPT)
assert spec and spec.loader
adr_implementation_ledger = importlib.util.module_from_spec(spec)
sys.modules["adr_implementation_ledger"] = adr_implementation_ledger
spec.loader.exec_module(adr_implementation_ledger)


def test_project_and_session_precedence_prefers_cognitive_then_codex_then_claude(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    canonical = tmp_path / "canonical"
    codex = tmp_path / "codex"
    claude = tmp_path / "claude"
    for path in (canonical, codex, claude):
        path.mkdir()
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(canonical))
    monkeypatch.setenv("CODEX_PROJECT_DIR", str(codex))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(claude))
    monkeypatch.setenv("COGNITIVE_OS_SESSION_ID", "cos")
    monkeypatch.setenv("CODEX_SESSION_ID", "codex")
    monkeypatch.setenv("CLAUDE_SESSION_ID", "claude")
    assert adr_implementation_ledger.resolve_project_dir() == canonical.resolve()
    assert adr_implementation_ledger.resolve_session_id() == "cos"
    monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR")
    monkeypatch.delenv("COGNITIVE_OS_SESSION_ID")
    assert adr_implementation_ledger.resolve_project_dir() == codex.resolve()
    assert adr_implementation_ledger.resolve_session_id() == "codex"


def test_scan_classifies_implemented_partial_and_pending_adrs(tmp_path: Path) -> None:
    project = tmp_path / "project"
    adrs = project / "docs" / "adrs"
    scripts = project / "scripts"
    adrs.mkdir(parents=True)
    scripts.mkdir(parents=True)
    (scripts / "implemented.py").write_text("print('ok')\n")
    (adrs / "ADR-001-implemented.md").write_text("# ADR-001 Implemented\n\n## Status\nAccepted — implemented.\n\nImplementation evidence: `scripts/implemented.py`\n")
    (adrs / "ADR-002-partial.md").write_text("# ADR-002 Partial\n\n## Status\nAccepted — partially implemented.\n\n## Open Questions\n- Wire startup check\n")
    (adrs / "ADR-003-pending.md").write_text("# ADR-003 Pending\n\n## Status\nAccepted.\n\nNo implementation section yet.\n")
    records = adr_implementation_ledger.scan_adrs(project)
    states = {record.adr_id: record.implementation_state for record in records}
    assert states["ADR-001-implemented"] == "implemented"
    assert states["ADR-002-partial"] == "partial"
    assert states["ADR-003-pending"] == "pending"


def test_closure_metadata_overrides_stale_heuristic_attention(tmp_path: Path) -> None:
    project = tmp_path / "project"
    adrs = project / "docs" / "adrs"
    manifests = project / "manifests"
    adrs.mkdir(parents=True)
    manifests.mkdir(parents=True)
    (adrs / "ADR-001-old.md").write_text(
        "# ADR-001 Old\n\n## Status\nProposed\n\n## Open Questions\n- Pending old wiring\n"
    )
    (adrs / "ADR-002-current.md").write_text(
        "# ADR-002 Current\n\n## Status\nAccepted\n"
    )
    (manifests / "adr-closure-metadata.yaml").write_text(
        """schema_version: 1
adrs:
  - adr_id: ADR-001-old
    closure_class: absorbed
    reason: Later ADR covers this old implementation shape.
"""
    )

    records = adr_implementation_ledger.scan_adrs(project)
    by_id = {record.adr_id: record for record in records}

    assert by_id["ADR-001-old"].implementation_state == "absorbed"
    assert by_id["ADR-001-old"].closure_class == "absorbed"
    assert by_id["ADR-002-current"].implementation_state == "pending"
    assert adr_implementation_ledger.summarize(records)["attention_count"] == 1


def test_closure_metadata_rejects_unknown_classes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    manifests = project / "manifests"
    manifests.mkdir(parents=True)
    (manifests / "adr-closure-metadata.yaml").write_text(
        """schema_version: 1
adrs:
  - adr_id: ADR-001
    closure_class: maybe
    reason: invalid
"""
    )

    with pytest.raises(ValueError, match="invalid closure_class"):
        adr_implementation_ledger.load_closure_metadata(project)


def test_write_outputs_creates_latest_json_jsonl_and_session_markdown(tmp_path: Path) -> None:
    project = tmp_path / "project"
    adrs = project / "docs" / "adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-001-pending.md").write_text("# ADR-001 Pending\n\n## Status\nAccepted.\n")
    records = adr_implementation_ledger.scan_adrs(project)
    now = adr_implementation_ledger.parse_now("2026-05-02T00:00:00Z")
    latest, jsonl, markdown = adr_implementation_ledger.write_outputs(project, "s1", now, records)
    assert latest.exists()
    assert jsonl.exists()
    assert markdown.exists()
    payload = json.loads(latest.read_text())
    assert payload["event"] == "adr_implementation_reconciled"
    assert payload["summary"]["attention_count"] == 1
    assert "ADR-001 Pending" in markdown.read_text()


def test_cli_json_reports_written_paths(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = tmp_path / "project"
    (project / "docs" / "adrs").mkdir(parents=True)
    code = adr_implementation_ledger.main(["--project-dir", str(project), "--session-id", "s1", "--write", "--json", "--now", "2026-05-02T00:00:00Z"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["latest_path"].endswith(".cognitive-os/metrics/adr-implementation-latest.json")
    assert payload["markdown_path"].endswith(".cognitive-os/sessions/s1/adr-implementation-ledger.md")
