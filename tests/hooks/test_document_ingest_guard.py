from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "hooks" / "document-ingest-guard.sh"


def _run(payload: dict, project_dir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )


def test_document_ingest_guard_blocks_pdf_read(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    proc = _run({"tool_name": "Read", "tool_input": {"file_path": str(pdf)}}, tmp_path)
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["decision"] == "block"
    assert "cos-document-ingest" in payload["reason"]
    assert str(pdf) in payload["reason"]


def test_document_ingest_guard_allows_markdown_read(tmp_path: Path) -> None:
    md = tmp_path / "sample.md"
    md.write_text("# ok\n", encoding="utf-8")
    proc = _run({"tool_name": "Read", "tool_input": {"file_path": str(md)}}, tmp_path)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
