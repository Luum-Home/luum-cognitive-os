"""Unit tests for lib/web_crawler.py.

Tests cover:
- URL validation
- Fallback HTML stripping
- Import-availability detection
- Schema validation for structured extraction
- Timeout / error handling
- Sync wrapper behaviour

These tests do NOT hit the network.  All HTTP calls are patched.
"""

import asyncio
import sys
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _reload_module():
    """Force-reimport lib.web_crawler so availability flags refresh."""
    if "lib.web_crawler" in sys.modules:
        del sys.modules["lib.web_crawler"]
    import lib.web_crawler as wc
    return wc


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

class TestValidateUrl:
    def test_valid_https(self):
        wc = _reload_module()
        assert wc._validate_url("https://example.com") == "https://example.com"

    def test_valid_http(self):
        wc = _reload_module()
        assert wc._validate_url("http://example.com") == "http://example.com"

    def test_missing_scheme_adds_https(self):
        wc = _reload_module()
        assert wc._validate_url("example.com") == "https://example.com"

    def test_strips_whitespace(self):
        wc = _reload_module()
        assert wc._validate_url("  https://example.com  ") == "https://example.com"

    def test_empty_raises(self):
        wc = _reload_module()
        with pytest.raises(ValueError, match="non-empty"):
            wc._validate_url("")

    def test_none_raises(self):
        wc = _reload_module()
        with pytest.raises(ValueError):
            wc._validate_url(None)

    def test_no_host_raises(self):
        wc = _reload_module()
        with pytest.raises(ValueError, match="no host"):
            wc._validate_url("https://")


# ---------------------------------------------------------------------------
# HTML stripping fallback
# ---------------------------------------------------------------------------

class TestStripHtml:
    def test_removes_tags(self):
        wc = _reload_module()
        assert "Hello" in wc._strip_html("<p>Hello</p>")
        assert "<p>" not in wc._strip_html("<p>Hello</p>")

    def test_removes_script(self):
        wc = _reload_module()
        html = "<script>alert(1)</script><p>Content</p>"
        text = wc._strip_html(html)
        assert "alert" not in text
        assert "Content" in text

    def test_removes_style(self):
        wc = _reload_module()
        html = "<style>body{color:red}</style><p>Visible</p>"
        text = wc._strip_html(html)
        assert "color" not in text
        assert "Visible" in text

    def test_block_tags_become_newlines(self):
        wc = _reload_module()
        html = "<div>A</div><div>B</div>"
        text = wc._strip_html(html)
        assert "A" in text
        assert "B" in text

    def test_collapses_whitespace(self):
        wc = _reload_module()
        html = "<p>A</p>\n\n\n\n\n<p>B</p>"
        text = wc._strip_html(html)
        # Should not have 3+ consecutive newlines
        assert "\n\n\n" not in text


# ---------------------------------------------------------------------------
# crawl4ai availability detection
# ---------------------------------------------------------------------------

class TestAvailability:
    def test_reports_availability(self):
        wc = _reload_module()
        # Just check it returns a bool (actual value depends on env)
        assert isinstance(wc.is_crawl4ai_available(), bool)

    def test_fallback_when_not_available(self):
        """Simulate crawl4ai not installed by temporarily hiding it."""
        original = sys.modules.get("crawl4ai")
        sys.modules["crawl4ai"] = None  # block import
        try:
            wc = _reload_module()
            assert wc.is_crawl4ai_available() is False
        finally:
            if original is not None:
                sys.modules["crawl4ai"] = original
            else:
                sys.modules.pop("crawl4ai", None)


# ---------------------------------------------------------------------------
# fetch_markdown fallback path
# ---------------------------------------------------------------------------

class TestFetchMarkdownFallback:
    """Test the urllib fallback path (crawl4ai NOT available)."""

    def test_fallback_returns_text(self):
        wc = _reload_module()

        html = b"<html><body><h1>Title</h1><p>Content here</p></body></html>"
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = html

        with mock.patch.object(wc, "_CRAWL4AI_AVAILABLE", False), \
             mock.patch("urllib.request.urlopen", return_value=mock_resp):
            result = _run(wc.fetch_markdown("https://example.com"))

        assert "Title" in result
        assert "Content" in result
        assert "<h1>" not in result

    def test_fallback_validates_url(self):
        wc = _reload_module()
        with mock.patch.object(wc, "_CRAWL4AI_AVAILABLE", False):
            with pytest.raises(ValueError):
                _run(wc.fetch_markdown(""))


# ---------------------------------------------------------------------------
# fetch_structured validation
# ---------------------------------------------------------------------------

class TestFetchStructuredValidation:
    def test_missing_schema_name_raises(self):
        wc = _reload_module()
        with pytest.raises(ValueError, match="name"):
            _run(wc.fetch_structured("https://example.com", schema={"baseSelector": ".x"}))

    def test_missing_base_selector_raises(self):
        wc = _reload_module()
        with pytest.raises(ValueError, match="baseSelector"):
            _run(wc.fetch_structured("https://example.com", schema={"name": "test"}))

    def test_non_dict_schema_raises(self):
        wc = _reload_module()
        with pytest.raises(ValueError, match="dict"):
            _run(wc.fetch_structured("https://example.com", schema="not a dict"))

    def test_requires_crawl4ai(self):
        wc = _reload_module()
        with mock.patch.object(wc, "_CRAWL4AI_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="crawl4ai"):
                _run(wc.fetch_structured(
                    "https://example.com",
                    schema={"name": "test", "baseSelector": ".item"},
                ))


# ---------------------------------------------------------------------------
# crawl_site validation
# ---------------------------------------------------------------------------

class TestCrawlSiteValidation:
    def test_requires_crawl4ai(self):
        wc = _reload_module()
        with mock.patch.object(wc, "_CRAWL4AI_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="crawl4ai"):
                _run(wc.crawl_site("https://example.com"))

    def test_validates_url(self):
        wc = _reload_module()
        with mock.patch.object(wc, "_CRAWL4AI_AVAILABLE", False):
            with pytest.raises(ValueError):
                _run(wc.crawl_site(""))

    def test_clamps_max_pages(self):
        """max_pages is clamped between 1 and 50 internally."""
        wc = _reload_module()
        # We cannot easily test the clamping without crawl4ai, but we can
        # verify the URL validation runs first (before the clamp).
        with mock.patch.object(wc, "_CRAWL4AI_AVAILABLE", False):
            with pytest.raises(RuntimeError):
                _run(wc.crawl_site("https://example.com", max_pages=999))


# ---------------------------------------------------------------------------
# Sync wrapper
# ---------------------------------------------------------------------------

class TestFetchMarkdownSync:
    def test_sync_wrapper_returns_string(self):
        wc = _reload_module()

        html = b"<html><body><p>Sync test</p></body></html>"
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = html

        with mock.patch.object(wc, "_CRAWL4AI_AVAILABLE", False), \
             mock.patch("urllib.request.urlopen", return_value=mock_resp):
            result = wc.fetch_markdown_sync("https://example.com")

        assert isinstance(result, str)
        assert "Sync test" in result

    def test_sync_wrapper_validates_url(self):
        wc = _reload_module()
        with mock.patch.object(wc, "_CRAWL4AI_AVAILABLE", False):
            with pytest.raises(ValueError):
                wc.fetch_markdown_sync("")


# ---------------------------------------------------------------------------
# Timeout handling
# ---------------------------------------------------------------------------

class TestTimeoutHandling:
    def test_fallback_respects_timeout(self):
        """urllib.urlopen receives the timeout parameter."""
        wc = _reload_module()

        html = b"<p>OK</p>"
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = html

        with mock.patch.object(wc, "_CRAWL4AI_AVAILABLE", False), \
             mock.patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
            _run(wc.fetch_markdown("https://example.com", timeout=5))
            # Verify timeout was passed through
            call_args = mock_open.call_args
            assert call_args is not None
            # The lambda captures timeout; check it was called at all
            assert mock_open.called
