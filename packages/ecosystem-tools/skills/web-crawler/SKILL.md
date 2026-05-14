---
name: web-crawler
description: 'Fetch and convert web pages to LLM-ready markdown using Crawl4AI. Supports
  single-page fetch, structured data extraction, and multi-page site crawling.

  '
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-26
license: MIT
metadata:
  author: luum
  tool: unclecode/crawl4ai
  tool-license: Apache-2.0
  tool-ring: ADOPT
  tool-score: null
audience: project
summary_line: Fetch and convert web pages to LLM-ready markdown using Crawl4AI.
platforms:
- claude-code
prerequisites: []
triggers:
- web-crawler
- /web-crawler
- Async -- single page
- Fetch and convert web pages to LLM-ready markdown using Crawl4AI
---
<!-- SCOPE: both -->
## Purpose

Provide standardized web crawling across Cognitive OS skills via `lib/web_crawler.py`.
Crawl4AI renders pages in a headless browser, strips boilerplate, and returns clean markdown
optimised for LLM consumption. When Crawl4AI is not installed the module falls back to
`urllib` with basic HTML stripping (no JS rendering).

## When to Use This vs WebFetch

| Scenario | Use |
|----------|-----|
| Quick read of a single public page | `WebFetch` tool (built-in, no deps) |
| Need full JS-rendered content | `web-crawler` (headless browser) |
| Structured data extraction (tables, lists, prices) | `web-crawler` with schema |
| Multi-page crawl of a documentation site | `web-crawler` `crawl_site()` |
| Authenticated / private pages | Neither -- use specialised MCP tools |

## Invocation

### From Python (skills, lib modules)

```python
from lib.web_crawler import fetch_markdown, fetch_structured, crawl_site, fetch_markdown_sync

# Async -- single page
md = await fetch_markdown("https://example.com/docs")

# Async -- structured extraction
data = await fetch_structured("https://example.com/pricing", schema={
    "name": "pricing",
    "baseSelector": ".pricing-card",
    "fields": [
        {"name": "plan", "selector": "h3", "type": "text"},
        {"name": "price", "selector": ".price", "type": "text"},
    ],
})

# Async -- multi-page crawl
pages = await crawl_site("https://docs.example.com", max_pages=15)

# Sync wrapper (for hooks / simple scripts)
md = fetch_markdown_sync("https://example.com/docs")
```

### From Claude Code session

Use `python -c` or invoke a skill that calls the library internally.

## Graceful Degradation

| crawl4ai installed? | `fetch_markdown` | `fetch_structured` | `crawl_site` |
|---------------------|------------------|---------------------|--------------|
| Yes | Full browser render + markdown | CSS/XPath extraction | Multi-page crawl |
| No | urllib + HTML strip (no JS) | RuntimeError raised | RuntimeError raised |

The fallback keeps single-page fetching functional in minimal environments.
Structured extraction and site crawling have no meaningful fallback and raise
`RuntimeError` with an install hint.

## Configuration

No configuration file needed. Timeouts are per-call parameters (default 30s for
single pages, 60s for site crawls). The hard cap for `crawl_site` is 50 pages.

## Dependencies

- `crawl4ai>=0.8.0` (Apache 2.0) -- listed in `requirements.txt`
- Falls back to Python stdlib (`urllib`, `re`) when crawl4ai is absent

## Files

- `lib/web_crawler.py` -- library module
- `tests/unit/test_web_crawler.py` -- unit tests
