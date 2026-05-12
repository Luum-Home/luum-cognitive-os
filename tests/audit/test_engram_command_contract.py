from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.audit


def test_engram_command_contract_audit_passes() -> None:
    result = subprocess.run(
        [str(ROOT / "scripts" / "cos-engram-command-audit"), "--fail-on-findings"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_engram_command_contract_doc_exists() -> None:
    doc = ROOT / "docs" / "04-Concepts" / "architecture" / "engram-command-contract.md"
    text = doc.read_text(encoding="utf-8")

    assert "engram save <title> <content>" in text
    assert "engram sync --cloud --project PROJECT" in text
    assert "engram search --json" in text
