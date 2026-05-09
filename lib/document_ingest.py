# SCOPE: both
"""Document ingestion helpers for converting noisy artifacts into Markdown.

The first-class use case is PDF-to-Markdown before an agent reads the content
into model context. The module is dependency-light: it uses optional local PDF
extractors when available, then falls back to a conservative parser for simple
text PDFs.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from lib.context_budget import count_tokens


class DocumentIngestError(RuntimeError):
    """Raised when a document cannot be converted into useful Markdown."""


@dataclass(frozen=True)
class IngestResult:
    input_path: str
    output_path: str
    kind: str
    input_bytes: int
    input_tokens_estimate: int
    output_tokens_estimate: int
    token_savings_estimate: int
    token_savings_pct: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_BLOCK_TAGS = {"p", "div", "section", "article", "header", "footer", "br", "li", "tr"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class _MarkdownHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if tag in _HEADING_TAGS:
            level = int(tag[1])
            self.parts.append("\n\n" + "#" * level + " ")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag in _HEADING_TAGS or tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        stripped = data.strip()
        if stripped:
            self.parts.append(stripped + " ")


def _collapse_ws(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def html_to_markdown(text: str) -> str:
    """Convert HTML into simple Markdown/plain text without external services."""
    parser = _MarkdownHTMLParser()
    parser.feed(text)
    return _collapse_ws(html.unescape("".join(parser.parts)))


def _decode_pdf_literal(raw: bytes) -> str:
    out = bytearray()
    i = 0
    while i < len(raw):
        b = raw[i]
        if b == 92 and i + 1 < len(raw):  # backslash escape
            nxt = raw[i + 1]
            mapping = {ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12, ord("("): 40, ord(")"): 41, ord("\\"): 92}
            if nxt in mapping:
                out.append(mapping[nxt])
                i += 2
                continue
            if 48 <= nxt <= 55:
                octal = bytes([nxt])
                j = i + 2
                while j < min(i + 4, len(raw)) and 48 <= raw[j] <= 55:
                    octal += bytes([raw[j]])
                    j += 1
                out.append(int(octal, 8) & 0xFF)
                i = j
                continue
            i += 1
            b = nxt
        out.append(b)
        i += 1
    return out.decode("utf-8", errors="replace")


def _naive_pdf_text(path: Path) -> str:
    data = path.read_bytes()
    literal_parts = [_decode_pdf_literal(m.group(1)) for m in re.finditer(rb"\(((?:\\.|[^\\)])*)\)", data)]
    hex_parts: list[str] = []
    for match in re.finditer(rb"(?<!<)<([0-9A-Fa-f\s]{4,})>(?!>)", data):
        compact = re.sub(rb"\s+", b"", match.group(1))
        if len(compact) % 2:
            compact += b"0"
        try:
            decoded = bytes.fromhex(compact.decode("ascii")).decode("utf-8", errors="replace")
        except ValueError:
            continue
        if decoded.strip():
            hex_parts.append(decoded)
    text = _collapse_ws("\n".join(literal_parts + hex_parts))
    # Filter obvious PDF operators when a binary stream produced noise.
    lines = [line for line in text.splitlines() if not re.fullmatch(r"[A-Za-z0-9./_ -]{0,3}", line.strip())]
    return _collapse_ws("\n".join(lines) or text)


def _extract_pdf_with_optional_lib(path: Path) -> str | None:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        return _collapse_ws("\n\n".join(page.extract_text() or "" for page in reader.pages))
    except Exception:
        pass
    try:
        from PyPDF2 import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        return _collapse_ws("\n\n".join(page.extract_text() or "" for page in reader.pages))
    except Exception:
        pass
    try:
        from pdfminer.high_level import extract_text  # type: ignore

        return _collapse_ws(extract_text(str(path)) or "")
    except Exception:
        pass
    if shutil.which("pdftotext"):
        proc = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return _collapse_ws(proc.stdout)
    return None


def pdf_to_markdown(path: str | Path) -> str:
    """Extract text from a PDF and wrap it as Markdown."""
    pdf = Path(path)
    text = _extract_pdf_with_optional_lib(pdf) or _naive_pdf_text(pdf)
    if not text.strip():
        raise DocumentIngestError(f"No extractable text found in PDF: {pdf}")
    return f"# Extracted PDF: {pdf.name}\n\n{text}\n"


def convert_to_markdown(input_path: str | Path) -> tuple[str, str]:
    """Return (kind, markdown) for a supported document path."""
    path = Path(input_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf", pdf_to_markdown(path)
    if suffix in {".html", ".htm"}:
        return "html", html_to_markdown(path.read_text(encoding="utf-8", errors="replace"))
    if suffix in {".md", ".markdown"}:
        return "markdown", path.read_text(encoding="utf-8", errors="replace")
    if suffix in {".txt", ".text"}:
        return "text", path.read_text(encoding="utf-8", errors="replace")
    raise DocumentIngestError(f"Unsupported document type: {path.suffix or '<none>'}")


def ingest_document(input_path: str | Path, output_path: str | Path, project_dir: str | Path | None = None) -> IngestResult:
    """Convert a supported document to Markdown and write an ingest metric."""
    source = Path(input_path).resolve()
    target = Path(output_path).resolve()
    if not source.is_file():
        raise DocumentIngestError(f"Input file does not exist: {source}")
    kind, markdown = convert_to_markdown(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(markdown, encoding="utf-8")

    raw = source.read_bytes()
    input_tokens = count_tokens(raw.decode("utf-8", errors="ignore")) if kind != "pdf" else max(1, len(raw) // 4)
    output_tokens = count_tokens(markdown)
    savings = input_tokens - output_tokens
    savings_pct = round((savings / input_tokens) * 100, 2) if input_tokens else 0.0
    result = IngestResult(
        input_path=str(source),
        output_path=str(target),
        kind=kind,
        input_bytes=len(raw),
        input_tokens_estimate=input_tokens,
        output_tokens_estimate=output_tokens,
        token_savings_estimate=savings,
        token_savings_pct=savings_pct,
    )
    if project_dir is not None:
        metrics = Path(project_dir) / ".cognitive-os" / "metrics" / "document-ingest.jsonl"
        metrics.parent.mkdir(parents=True, exist_ok=True)
        row = {"timestamp_epoch": time.time(), **result.to_dict()}
        with metrics.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return result
