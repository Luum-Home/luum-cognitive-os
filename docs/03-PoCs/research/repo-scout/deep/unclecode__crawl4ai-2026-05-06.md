---
evaluated_at: 2026-05-06 06:58 UTC
evaluation_level: 2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (LLM-native crawler — markdown + structured extraction — for agent web-research/RAG ingestion)
deep_verdict: ADOPT — production-ready, CI-perfect, drop-in for COS web-research / RAG ingestion
deepwiki_url: https://deepwiki.com/unclecode/crawl4ai
engram_id: pending
---

## Repository Evaluation: unclecode/crawl4ai

### Classification: ADOPT
**Score**: 8.8/10
**Evaluation Level**: 2 (Deep — gh api recursive tree, crawl4ai/ + tests/ + deploy/docker inspection)

### Summary
"Open-source LLM Friendly Web Crawler & Scraper." Apache-2.0, Python, **65k★** (genuinely well-known), push 2026-05-05 (today), v0.6.3 / v0.8.6 release tracks. **CI 10/10 green** (tied for top with snyk/agent-scan, token-savior, mempalace). Comprehensive: core crawler + deep-crawling + PDF processor + dedicated crawlers for amazon_product + google_search + html2text + js_snippet + Docker deployment + MCP integration tests. Best-of-class web-acquisition primitive in the deep batch.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 9/10 | Drop-in solution for COS web-research + RAG ingestion + research-protocol skill input |
| License | 25% | 8/10 | Apache-2.0 |
| Activity | 20% | 10/10 | Push today; 2 active release lines (vr0.6.x + v0.8.x); 60 issues/30d |
| Maturity | 15% | 9/10 | 2 years old; 65k★; Docker deploy; 20+ test suites; mcp tests; production posture |
| Integration | 10% | 9/10 | Python pip install OR Docker sidecar; clear module boundaries |
| **Weighted Total** | | **8.95/10** weighted, presented as **8.8/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 60 issues | high issue activity |
| Release cadence | vr0.6.3, vr0.6.0, vr0.6.0rc1, v.3.72, v0.8.6 (2 release lines) | weekly releases |
| CI health | 10/10 success | CI green |

### Key Findings
- **Strengths**:
  - **CI 10/10 green** — best-in-class CI health.
  - 65k★ + 6.6k forks = strong community signal (no metric-pump pattern detected here — ratios are healthy).
  - Modular: `crawl4ai/{cloud, components, crawlers/{amazon_product, google_search}, deep_crawling, html2text, js_snippet, processors/pdf, script}`.
  - **MCP integration tests** in `tests/mcp/` — direct fit for COS MCP-extension cluster.
  - **Memory + profiler tests** in `tests/{memory, profiler}/` — performance discipline.
  - Docker deploy ready (`deploy/docker/` with static + monitor + playground + tests).
  - `prompts/` directory — exposes the LLM-extraction prompts for inspection/customization.
  - `.claude/commands/` shows internal Claude-Code dogfooding.
  - SBOM directory (`sbom/`) — supply-chain transparency.
- **Weaknesses**:
  - Apache-2.0 NOTICE compliance.
  - 80 open issues — manageable for a 65k★ project.
  - 150MB repo size (mostly docs/examples).
  - Two release lines (vr0.6.x and v0.8.x) — pin carefully; understand which is canonical.
- **Architecture**: Python core (`crawl4ai/`) + Docker deploy (`deploy/docker/`) + comprehensive tests (`tests/{adaptive, async, async_assistant, browser, cache_validation, cli, deep_crawling, docker, general, hub, loggers, mcp, memory, profiler, proxy, regression, releases, unit}`) + extensive docs + MCP-server-tested.

### Integration Plan
- **What to use**:
  1. **crawl4ai as a dependency** for any COS web-research/RAG ingestion skill. Direct adoption, not pattern lifting.
  2. **MCP integration** for any COS skill that needs web acquisition over MCP.
  3. **PDF processor** in `crawl4ai/processors/pdf` — covers a known agent-research gap.
  4. **Specialized crawlers** (`amazon_product`, `google_search`) — drop-in for product/search-research workflows.
  5. **Prompts catalog** in `prompts/` — reference for LLM-extraction prompt patterns.
- **How to integrate**: pip install crawl4ai OR Docker sidecar. Wrap in a COS skill (`research-protocol` extension or new `web-acquire` skill).
- **Effort estimate**: small (1-2 days for first integration in a research skill)
- **Dependencies it brings**: playwright (for headless browser), beautifulsoup, httpx + transitive

### Risks
- Apache-2.0 NOTICE compliance.
- Playwright browser dependency adds install weight.
- Two release tracks → understand release-line semantics before pinning.
- Some specialized crawlers (amazon_product, google_search) may break with TOS / CAPTCHA churn.

### Cross-Reference vs Shallow Radar
Shallow verdict: "LLM-native crawler (markdown + structured extraction) for agent web-research/RAG ingestion." **Deep evidence agrees and amplifies**: this is one of the cleanest ADOPTs in the deep batch — CI green, Apache-2.0, healthy community ratios, real Docker + MCP + PDF coverage, SBOM published. Verdict ADOPT confirmed at 8.8/10.

### Raw Metrics Appendix
```
{"name":"crawl4ai","license":"Apache-2.0","stars":65076,"forks":6656,"language":"Python","pushed":"2026-05-05T06:41:44Z","created":"2024-05-09T09:48:50Z","open_issues":80,"size":150501 KB}
tags: vr0.6.3,vr0.6.0,vr0.6.0rc1,v.3.72,v0.8.6
issues_30d=60, CI=10/10 success
test suites: 20+ (incl. mcp, memory, profiler, deep_crawling)
specialized crawlers: amazon_product, google_search
```
