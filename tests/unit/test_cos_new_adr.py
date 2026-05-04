from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos_new_adr.py"

spec = importlib.util.spec_from_file_location("cos_new_adr", SCRIPT)
assert spec and spec.loader
cos_new_adr = importlib.util.module_from_spec(spec)
sys.modules["cos_new_adr"] = cos_new_adr
spec.loader.exec_module(cos_new_adr)


def test_create_adr_writes_contract_compliant_draft(tmp_path: Path) -> None:
    draft = cos_new_adr.create_adr(
        project_dir=tmp_path,
        title="Contract Authoring",
        session_id="test-session",
        owner="test",
        context="Need a new decision without drifting from the ADR contract.",
        decision="Use the ADR authoring primitive.",
    )

    path = tmp_path / draft.path
    text = path.read_text(encoding="utf-8")

    assert draft.adr_id == "ADR-001"
    assert path.name == "ADR-001-contract-authoring.md"
    for section in cos_new_adr.REQUIRED_SECTIONS:
        assert f"## {section}" in text
    assert "| Alternative | Why rejected |" in text
    assert "```bash" in text
    assert "implementation_files:" in text


def test_create_adr_dry_run_reserves_without_writing_file(tmp_path: Path) -> None:
    draft = cos_new_adr.create_adr(project_dir=tmp_path, title="Dry Run", dry_run=True, session_id="s1", owner="test")

    assert draft.wrote is False
    assert not (tmp_path / draft.path).exists()
    assert (tmp_path / ".cognitive-os" / "locks" / "adr-reservations.json").exists()


def test_cli_json_reports_created_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = cos_new_adr.main(["--project-dir", str(tmp_path), "--title", "CLI ADR", "--session-id", "s1", "--owner", "test", "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["path"] == "docs/adrs/ADR-001-cli-adr.md"
    assert payload["wrote"] is True
