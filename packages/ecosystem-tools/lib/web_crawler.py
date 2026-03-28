"""Cognitive OS Web Crawler -- Crawl4AI wrapper for LLM-ready web content.

Provides standardized crawling across skills with graceful degradation:
if crawl4ai is not installed, falls back to urllib + basic HTML stripping.

License: Apache 2.0 (Crawl4AI by UncleCode)
"""

from typing import Optional, List, Dict
from urllib.parse import urlparse
import asyncio
import re

# ---------------------------------------------------------------------------
# Crawl4AI availability detection
# ---------------------------------------------------------------------------

_CRAWL4AI_AVAILABLE = False

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
    _CRAWL4AI_AVAILABLE = True
except ImportError:
    pass


def is_crawl4ai_available() -> bool:
    """Return True if the crawl4ai package is importable."""
    return _CRAWL4AI_AVAILABLE


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

def _validate_url(url: str) -> str:
    """Validate and normalise a URL. Raises ValueError on bad input."""
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError(f"Invalid URL (no host): {url}")
    return url


# ---------------------------------------------------------------------------
# Fallback: stdlib-only HTML -> text
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\n{3,}")


def _strip_html(html: str) -> str:
    """Crude HTML-to-text via regex. Used when crawl4ai is absent."""
    # Remove script / style blocks
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Replace block-level tags with newlines
    text = re.sub(r"<(br|p|div|h[1-6]|li|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = _TAG_RE.sub("", text)
    # Collapse whitespace
    text = _WS_RE.sub("\n\n", text).strip()
    return text


async def _fallback_fetch(url: str, timeout: int) -> str:
    """Fetch via urllib and return stripped text (no browser rendering)."""
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "CognitiveOS-Crawler/1.0"})
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None,
        lambda: urllib.request.urlopen(req, timeout=timeout),  # noqa: S310
    )
    html = response.read().decode("utf-8", errors="replace")
    return _strip_html(html)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fetch_markdown(url: str, timeout: int = 30) -> str:
    """Fetch *url* and return clean markdown.

    When crawl4ai is installed the page is rendered in a headless browser and
    converted to markdown automatically.  Otherwise falls back to urllib with
    basic HTML stripping (no JS rendering, no markdown formatting).

    Parameters
    ----------
    url:
        The web page to fetch.  ``https://`` is prepended when missing.
    timeout:
        Maximum seconds to wait for the page.

    Returns
    -------
    str
        Markdown (crawl4ai) or plain text (fallback) of the page content.

    Raises
    ------
    ValueError
        If *url* is invalid.
    TimeoutError
        If the page does not load within *timeout* seconds.
    """
    url = _validate_url(url)

    if not _CRAWL4AI_AVAILABLE:
        return await _fallback_fetch(url, timeout)

    browser_cfg = BrowserConfig(headless=True)
    run_cfg = CrawlerRunConfig(
        wait_until="domcontentloaded",
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await asyncio.wait_for(
            crawler.arun(url=url, config=run_cfg),
            timeout=timeout,
        )
        if not result.success:
            raise RuntimeError(f"Crawl4AI failed for {url}: {result.error_message}")
        return result.markdown or ""


async def fetch_structured(
    url: str,
    schema: dict,
    timeout: int = 30,
) -> dict:
    """Fetch *url* and extract structured data using a JSON-CSS extraction schema.

    Parameters
    ----------
    url:
        The web page to scrape.
    schema:
        A Crawl4AI ``JsonCssExtractionStrategy``-compatible schema dict.
        Must contain at least ``name`` (str) and ``baseSelector`` (str) keys.
    timeout:
        Maximum seconds to wait.

    Returns
    -------
    dict
        ``{"url": str, "data": list[dict]}`` with extracted records.

    Raises
    ------
    ValueError
        If *url* is invalid or *schema* is missing required keys.
    RuntimeError
        If crawl4ai is not installed (no fallback for structured extraction).
    """
    url = _validate_url(url)

    if not isinstance(schema, dict):
        raise ValueError("schema must be a dict")
    for key in ("name", "baseSelector"):
        if key not in schema:
            raise ValueError(f"schema missing required key: {key}")

    if not _CRAWL4AI_AVAILABLE:
        raise RuntimeError(
            "Structured extraction requires crawl4ai.  "
            "Install it with: pip install 'crawl4ai>=0.8.0'"
        )

    from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
    import json

    strategy = JsonCssExtractionStrategy(schema)
    browser_cfg = BrowserConfig(headless=True)
    run_cfg = CrawlerRunConfig(
        extraction_strategy=strategy,
        wait_until="domcontentloaded",
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await asyncio.wait_for(
            crawler.arun(url=url, config=run_cfg),
            timeout=timeout,
        )
        if not result.success:
            raise RuntimeError(f"Crawl4AI failed for {url}: {result.error_message}")

        data = json.loads(result.extracted_content) if result.extracted_content else []
        return {"url": url, "data": data}


async def crawl_site(
    base_url: str,
    max_pages: int = 10,
    timeout: int = 60,
) -> List[dict]:
    """Deep-crawl *base_url* up to *max_pages* pages.

    Returns a list of ``{"url": str, "markdown": str, "title": str}`` dicts.

    Parameters
    ----------
    base_url:
        Starting URL for the crawl.
    max_pages:
        Maximum number of pages to visit (default 10, hard cap 50).
    timeout:
        Per-page timeout in seconds.

    Raises
    ------
    RuntimeError
        If crawl4ai is not installed (no fallback for site crawling).
    """
    base_url = _validate_url(base_url)
    max_pages = min(max(1, max_pages), 50)  # clamp 1..50

    if not _CRAWL4AI_AVAILABLE:
        raise RuntimeError(
            "Site crawling requires crawl4ai.  "
            "Install it with: pip install 'crawl4ai>=0.8.0'"
        )

    browser_cfg = BrowserConfig(headless=True)
    run_cfg = CrawlerRunConfig(
        wait_until="domcontentloaded",
    )

    results: List[dict] = []
    visited: set = set()
    queue: list = [base_url]
    base_domain = urlparse(base_url).netloc

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        while queue and len(results) < max_pages:
            current_url = queue.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)

            try:
                result = await asyncio.wait_for(
                    crawler.arun(url=current_url, config=run_cfg),
                    timeout=timeout,
                )
            except (asyncio.TimeoutError, Exception):
                continue

            if not result.success:
                continue

            title = ""
            if result.metadata and isinstance(result.metadata, dict):
                title = result.metadata.get("title", "")

            results.append({
                "url": current_url,
                "markdown": result.markdown or "",
                "title": title,
            })

            # Enqueue same-domain links
            if result.links and isinstance(result.links, dict):
                for link_list in result.links.values():
                    if isinstance(link_list, list):
                        for link_info in link_list:
                            href = link_info if isinstance(link_info, str) else getattr(link_info, "href", None)
                            if href and isinstance(href, str):
                                href = _validate_url(href) if not href.startswith("http") else href
                                if urlparse(href).netloc == base_domain and href not in visited:
                                    queue.append(href)

    return results


def fetch_markdown_sync(url: str, timeout: int = 30) -> str:
    """Synchronous wrapper for :func:`fetch_markdown`.

    Creates a new event loop if none is running.  Intended for simple
    scripting and hook integration where ``async/await`` is not available.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already inside an async context -- create a new thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, fetch_markdown(url, timeout)).result()
    else:
        return asyncio.run(fetch_markdown(url, timeout))
