"""Unit tests for lib.wiki_ingester.

All tests run real code against a temporary vault directory.
No network calls — ingest_url is tested with a local HTTP server thread.
"""

from __future__ import annotations

import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.wiki_ingester import (
    IngestResult,
    WikiIngester,
    _redact_secrets,
    _slugify,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ingester(tmp_path: Path) -> WikiIngester:
    """Return a WikiIngester rooted at *tmp_path*."""
    return WikiIngester(vault_root=tmp_path, project="test-project")


def _read_index(tmp_path: Path) -> list[dict]:
    index_path = tmp_path / "docs" / "08-References" / "raw" / "index.jsonl"
    if not index_path.exists():
        return []
    lines = [ln.strip() for ln in index_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_basic(self):
        assert _slugify("Hello World") == "hello-world"

    def test_deterministic(self):
        assert _slugify("Meeting Notes 2026-05-13") == _slugify("Meeting Notes 2026-05-13")

    def test_special_chars_stripped(self):
        slug = _slugify("Foo & Bar (2026)")
        assert slug == "foo-bar-2026"

    def test_empty_string_returns_untitled(self):
        assert _slugify("") == "untitled"

    def test_unicode_normalised(self):
        # Accent chars are NFKD-decomposed then ASCII-encoded; accented letters
        # whose base char IS ASCII (e → e, é → e) survive, others are dropped.
        slug = _slugify("Résumé")
        # "Résumé" → NFKD "Résumé" → ascii-encode drops combining
        # accents → "Resume" → lower → "resume"
        assert slug == "resume"


# ---------------------------------------------------------------------------
# _redact_secrets
# ---------------------------------------------------------------------------

class TestRedactSecrets:
    def test_detects_api_key_pattern(self):
        text = "api_key = abcdefghijklmnopqrstuvwxyz123456"
        result, count = _redact_secrets(text)
        assert count == 1
        assert "[REDACTED]" in result
        assert "abcdefghijklmnopqrstuvwxyz123456" not in result

    def test_detects_token_pattern(self):
        text = "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9abcdef"
        result, count = _redact_secrets(text)
        assert count >= 1
        assert "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9abcdef" not in result

    def test_no_false_positive_on_short_value(self):
        text = "key = short"
        result, count = _redact_secrets(text)
        # "short" is only 5 chars — below the 20-char threshold
        assert count == 0
        assert result == text

    def test_no_redaction_without_context_word(self):
        text = "abcdefghijklmnopqrstuvwxyz1234567890"
        result, count = _redact_secrets(text)
        assert count == 0
        assert result == text

    def test_count_multiple_secrets(self):
        text = (
            "api_key = abcdefghijklmnopqrstuvwxyz1\n"
            "secret = zyxwvutsrqponmlkjihgfedcba1\n"
        )
        _, count = _redact_secrets(text)
        assert count == 2


# ---------------------------------------------------------------------------
# ingest_text — happy path
# ---------------------------------------------------------------------------

class TestIngestText:
    def test_creates_vault_page(self, tmp_path):
        ingester = _ingester(tmp_path)
        result = ingester.ingest_text("Hello vault", "Test Title", locator="test")

        assert isinstance(result, IngestResult)
        assert result.source_id.startswith("sha256-")
        assert result.page_path.exists()
        assert result.already_existed is False

    def test_source_id_contains_hash_prefix(self, tmp_path):
        ingester = _ingester(tmp_path)
        text = "deterministic content"
        result = ingester.ingest_text(text, "Deterministic", locator="inline")
        expected_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        assert result.source_id == f"sha256-{expected_hash}"

    def test_index_entry_written(self, tmp_path):
        ingester = _ingester(tmp_path)
        result = ingester.ingest_text("some content", "Index Test", locator="x")

        entries = _read_index(tmp_path)
        assert len(entries) == 1
        entry = entries[0]
        assert entry["source_id"] == result.source_id
        assert entry["type"] == "text"
        assert entry["locator"] == "x"
        assert len(entry["sha256_hash"]) == 64

    def test_page_has_valid_frontmatter(self, tmp_path):
        ingester = _ingester(tmp_path)
        result = ingester.ingest_text("body text", "FM Test", locator="fm")

        content = result.page_path.read_text(encoding="utf-8")
        assert "---" in content
        assert "source_id:" in content
        assert "source_hash:" in content
        assert "ingested_at:" in content
        assert "source_locator:" in content

    def test_page_body_present(self, tmp_path):
        ingester = _ingester(tmp_path)
        result = ingester.ingest_text("unique body content here", "Body Test", locator="b")
        content = result.page_path.read_text(encoding="utf-8")
        assert "unique body content here" in content

    def test_slug_deterministic_for_same_title(self, tmp_path):
        ingester = _ingester(tmp_path)
        r1 = ingester.ingest_text("content A", "Same Title", locator="a")
        # Change content so it is a new source
        r2 = ingester.ingest_text("content B", "Same Title", locator="b")
        # Both slugs derive from "Same Title"
        assert r1.page_path.stem == r2.page_path.stem

    def test_redacted_count_reported(self, tmp_path):
        ingester = _ingester(tmp_path)
        text = "api_key = abcdefghijklmnopqrstuvwxyz1234"
        result = ingester.ingest_text(text, "Secret Test", locator="s")
        assert result.redacted_secrets_count == 1

    def test_redacted_secret_not_in_vault_page(self, tmp_path):
        ingester = _ingester(tmp_path)
        secret = "abcdefghijklmnopqrstuvwxyz1234"
        text = f"api_key = {secret}"
        result = ingester.ingest_text(text, "Redact Check", locator="r")
        content = result.page_path.read_text(encoding="utf-8")
        assert secret not in content
        assert "[REDACTED]" in content


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_same_content_returns_existing_source_id(self, tmp_path):
        ingester = _ingester(tmp_path)
        text = "identical content"
        r1 = ingester.ingest_text(text, "Dup Title", locator="first")
        r2 = ingester.ingest_text(text, "Dup Title Again", locator="second")

        assert r2.source_id == r1.source_id
        assert r2.already_existed is True

    def test_same_content_no_duplicate_index_entry(self, tmp_path):
        ingester = _ingester(tmp_path)
        text = "no duplicate"
        ingester.ingest_text(text, "Dup", locator="a")
        ingester.ingest_text(text, "Dup", locator="b")

        entries = _read_index(tmp_path)
        assert len(entries) == 1

    def test_different_content_creates_new_entry(self, tmp_path):
        ingester = _ingester(tmp_path)
        ingester.ingest_text("first", "Title A", locator="a")
        ingester.ingest_text("second", "Title B", locator="b")

        entries = _read_index(tmp_path)
        assert len(entries) == 2


# ---------------------------------------------------------------------------
# ingest_file
# ---------------------------------------------------------------------------

class TestIngestFile:
    def test_text_file_hash_matches(self, tmp_path):
        content = "file content for hashing"
        src = tmp_path / "test.txt"
        src.write_text(content, encoding="utf-8")

        ingester = _ingester(tmp_path)
        result = ingester.ingest_file(src, title="Text File")

        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        entry = _read_index(tmp_path)[0]
        assert entry["sha256_hash"] == expected_hash
        assert result.source_id == f"sha256-{expected_hash[:16]}"

    def test_file_type_recorded_as_file(self, tmp_path):
        src = tmp_path / "doc.md"
        src.write_text("# Markdown doc", encoding="utf-8")

        ingester = _ingester(tmp_path)
        ingester.ingest_file(src, title="Markdown Doc")

        entry = _read_index(tmp_path)[0]
        assert entry["type"] == "file"

    def test_pdf_like_bytes_ingested(self, tmp_path):
        # Simulate a minimal PDF-like binary payload (no real PDF parser needed)
        fake_pdf = b"%PDF-1.4\nsome readable text content\n%%EOF"
        src = tmp_path / "document.pdf"
        src.write_bytes(fake_pdf)

        ingester = _ingester(tmp_path)
        result = ingester.ingest_file(src)

        assert result.source_id.startswith("sha256-")
        assert result.page_path.exists()

    def test_title_inferred_from_filename(self, tmp_path):
        src = tmp_path / "my_report_2026.txt"
        src.write_text("report body", encoding="utf-8")

        ingester = _ingester(tmp_path)
        result = ingester.ingest_file(src)  # no explicit title

        # Slug should be derived from filename stem
        assert "my" in result.page_path.stem or "report" in result.page_path.stem


# ---------------------------------------------------------------------------
# ingest_url — local HTTP server mock
# ---------------------------------------------------------------------------

class _MockHTTPHandler(BaseHTTPRequestHandler):
    """Minimal handler that serves a fixed HTML page."""

    HTML = b"<html><head><title>Mock Page</title></head><body>Mock content here.</body></html>"

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(self.HTML)))
        self.end_headers()
        self.wfile.write(self.HTML)

    def log_message(self, *args):  # suppress server log noise
        pass


class TestIngestUrl:
    @pytest.fixture(autouse=True)
    def _local_server(self):
        server = HTTPServer(("127.0.0.1", 0), _MockHTTPHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.base_url = f"http://127.0.0.1:{port}"
        yield
        server.shutdown()

    def test_fetches_and_creates_page(self, tmp_path):
        ingester = _ingester(tmp_path)
        result = ingester.ingest_url(self.base_url + "/test", title="Mock Page")

        assert result.source_id.startswith("sha256-")
        assert result.page_path.exists()

    def test_type_recorded_as_url(self, tmp_path):
        ingester = _ingester(tmp_path)
        ingester.ingest_url(self.base_url + "/", title="URL Type Test")

        entry = _read_index(tmp_path)[0]
        assert entry["type"] == "url"

    def test_title_extracted_from_html(self, tmp_path):
        ingester = _ingester(tmp_path)
        result = ingester.ingest_url(self.base_url + "/")  # no explicit title

        # Should detect "Mock Page" from <title>
        content = result.page_path.read_text(encoding="utf-8")
        assert "Mock Page" in content or "mock" in result.page_path.stem

    def test_url_deduplication(self, tmp_path):
        ingester = _ingester(tmp_path)
        r1 = ingester.ingest_url(self.base_url + "/same", title="Same")
        r2 = ingester.ingest_url(self.base_url + "/same", title="Same Again")
        assert r2.already_existed is True
        assert r2.source_id == r1.source_id


# ---------------------------------------------------------------------------
# Engram integration (graceful degradation)
# ---------------------------------------------------------------------------

class TestEngramIntegration:
    """Tests for engram integration inside _emit_engram_claim.

    The method does a lazy ``from lib import engram_client`` inside the function
    body, so we patch ``WikiIngester._emit_engram_claim`` directly to control its
    return value without depending on the real engram daemon.
    """

    def test_no_engram_claim_id_is_none(self, tmp_path):
        """When _emit_engram_claim returns None, IngestResult.claim_id is None."""
        ingester = _ingester(tmp_path)

        with patch.object(ingester, "_emit_engram_claim", return_value=None):
            result = ingester.ingest_text("engram absent", "No Engram", locator="test")

        assert result.claim_id is None
        assert isinstance(result, IngestResult)

    def test_engram_save_failure_does_not_raise(self, tmp_path):
        """If _emit_engram_claim returns None, claim_id is None — no exception."""
        ingester = _ingester(tmp_path)

        with patch.object(ingester, "_emit_engram_claim", return_value=None):
            result = ingester.ingest_text("engram failure", "Engram Fail", locator="f")

        assert result.claim_id is None

    def test_engram_save_success_returns_claim_id(self, tmp_path):
        """When _emit_engram_claim returns 99, claim_id is 99."""
        ingester = _ingester(tmp_path)

        with patch.object(ingester, "_emit_engram_claim", return_value=99):
            result = ingester.ingest_text("engram success", "Engram OK", locator="ok")

        assert result.claim_id == 99

    def test_engram_exception_does_not_propagate(self, tmp_path):
        """Exceptions inside _emit_engram_claim are swallowed by the method itself."""
        ingester = _ingester(tmp_path)

        # Simulate engram_client.save_observation raising inside _emit_engram_claim
        # by patching it at the source the lazy import will resolve to.
        with patch("lib.engram_client.save_observation", side_effect=RuntimeError("crash")):
            result = ingester.ingest_text("boom", "Crash Test", locator="crash")

        # claim_id may be None or a real ID depending on whether engram is running;
        # the key invariant is that NO exception propagated.
        assert isinstance(result, IngestResult)


# ---------------------------------------------------------------------------
# Index integrity
# ---------------------------------------------------------------------------

class TestIndexIntegrity:
    def test_index_is_valid_jsonl(self, tmp_path):
        ingester = _ingester(tmp_path)
        ingester.ingest_text("alpha", "A", locator="a")
        ingester.ingest_text("beta", "B", locator="b")
        ingester.ingest_text("gamma", "C", locator="c")

        index_path = tmp_path / "docs" / "08-References" / "raw" / "index.jsonl"
        for line in index_path.read_text().splitlines():
            obj = json.loads(line)
            assert "source_id" in obj
            assert "sha256_hash" in obj
            assert "page_path" in obj
            assert "ingested_at" in obj

    def test_index_entries_have_correct_page_path_prefix(self, tmp_path):
        ingester = _ingester(tmp_path)
        ingester.ingest_text("body", "Prefix Test", locator="p")

        entry = _read_index(tmp_path)[0]
        assert entry["page_path"].startswith("docs/04-Concepts/ingested/")
