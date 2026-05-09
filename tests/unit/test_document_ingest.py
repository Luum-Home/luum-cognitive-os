from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lib.document_ingest import html_to_markdown, ingest_document, pdf_to_markdown

REPO = Path(__file__).resolve().parents[2]


def _simple_pdf(path: Path) -> None:
    path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length 44 >> stream\n"
        b"BT /F1 12 Tf 72 720 Td (Hello PDF context) Tj ET\n"
        b"endstream endobj\n"
        b"trailer << /Root 1 0 R >>\n%%EOF\n"
    )


def test_pdf_to_markdown_extracts_simple_text(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    _simple_pdf(pdf)
    markdown = pdf_to_markdown(pdf)
    assert markdown.startswith("# Extracted PDF: sample.pdf")
    assert "Hello PDF context" in markdown


def test_ingest_document_writes_markdown_and_metric(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    out = tmp_path / "sample.md"
    project = tmp_path / "project"
    _simple_pdf(pdf)

    result = ingest_document(pdf, out, project_dir=project)

    assert out.exists()
    assert result.kind == "pdf"
    assert result.output_tokens_estimate > 0
    metric = project / ".cognitive-os" / "metrics" / "document-ingest.jsonl"
    rows = [json.loads(line) for line in metric.read_text().splitlines()]
    assert rows[-1]["kind"] == "pdf"
    assert rows[-1]["output_path"] == str(out.resolve())


def test_html_to_markdown_removes_script_noise() -> None:
    markdown = html_to_markdown("<h1>Title</h1><script>bad()</script><p>Hello <b>world</b></p>")
    assert "# Title" in markdown
    assert "Hello" in markdown and "world" in markdown
    assert "bad" not in markdown


def test_cos_document_ingest_cli_json(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    out = tmp_path / "sample.md"
    _simple_pdf(pdf)
    proc = subprocess.run(
        [str(REPO / "scripts" / "cos-document-ingest"), str(pdf), "--output", str(out), "--project-dir", str(tmp_path), "--json"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["kind"] == "pdf"
    assert Path(payload["output_path"]).read_text(encoding="utf-8").startswith("# Extracted PDF")
