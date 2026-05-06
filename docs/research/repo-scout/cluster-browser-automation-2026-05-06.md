---
cluster: browser-automation
date: 2026-05-06
phase: shallow
total: 5
pass: 3
patterns_only: 1
reject: 1
deferred: 0
---

# Cluster: browser-automation (shallow audit)

Theme: browser automation + scraping (anti-detect browsers, AI-friendly crawlers, headless engines, security spidering).

Note: cluster theme mentioned `xcrawl` — not present in input file. Audited only the 5 repos in `cluster-browser-automation.txt`.

## Repos

### 1. D4Vinci/Scrapling
- URL: https://github.com/D4Vinci/Scrapling
- License: BSD-3-Clause
- Stars: 45,313
- Last commit: 2026-05-05
- Primary language: Python
- Purpose: Adaptive Python web-scraping framework spanning single-request fetches up to full-scale crawls with auto-healing selectors.
- Verdict: PASS (Phase 2 candidate)
- Rationale: Permissive BSD-3, very actively maintained, large community, Python-native (matches our stack), broad scraping surface (HTTP + browser fallback) directly relevant to agent web-research workflows. High signal for code/pattern adoption.

### 2. daijro/camoufox
- URL: https://github.com/daijro/camoufox
- License: MPL-2.0
- Stars: 7,991
- Last commit: 2026-04-29
- Primary language: C++
- Purpose: Anti-detect Firefox-based headless browser for stealth automation (fingerprint spoofing at the engine level).
- Verdict: PASS (Phase 2 candidate)
- Rationale: MPL-2.0 is file-level copyleft — acceptable for tool integration without infecting our codebase. Engine-level (not patched JS) anti-detect is unique vs Playwright stealth shims; useful for high-friction scraping targets. C++ binary used as external tool — no source ingestion needed.

### 3. lightpanda-io/browser
- URL: https://github.com/lightpanda-io/browser
- License: AGPL-3.0
- Stars: 30,038
- Last commit: 2026-05-06
- Primary language: Zig
- Purpose: Lightweight headless browser engine purpose-built for AI agents and automation (low-memory, fast cold-start).
- Verdict: REJECT (license-blocked) — patterns only
- Rationale: AGPL-3.0 is on the project block-list (`license-policy`). Cannot adopt source or invoke as a service over network without copyleft contagion concerns. Architectural patterns (minimal-DOM headless design for agents) may be studied but no code/binary integration. Skip Phase 2.

### 4. projectdiscovery/katana
- URL: https://github.com/projectdiscovery/katana
- License: MIT
- Stars: 16,653
- Last commit: 2026-05-05
- Primary language: Go
- Purpose: Next-gen crawling/spidering framework with headless and standard modes, built for security recon and asset discovery.
- Verdict: PASS (Phase 2 candidate)
- Rationale: MIT permissive, Go binary integrates cleanly as CLI sidecar, mature ProjectDiscovery ecosystem. Strong fit for repo-scout / pentesting-readiness / web-asset-discovery flows. Headless mode covers JS-heavy sites where pure-HTTP crawlers fail.

### 5. unclecode/crawl4ai
- URL: https://github.com/unclecode/crawl4ai
- License: Apache-2.0
- Stars: 65,073
- Last commit: 2026-05-05
- Primary language: Python
- Purpose: LLM-friendly open-source web crawler/scraper that produces clean markdown + structured extraction tuned for RAG and agent ingestion.
- Verdict: PASS (Phase 2 candidate)
- Rationale: Apache-2.0 (most permissive of the set, includes patent grant), highest star count in cluster, Python-native, output format aligns with agent/LLM consumption (markdown + JSON schema extraction). Direct fit for agent web-research and knowledge-ingestion pipelines.

## Phase 2 candidates

1. unclecode/crawl4ai — primary candidate (Apache-2.0, LLM-native output, highest community signal).
2. D4Vinci/Scrapling — secondary (BSD-3, adaptive selectors, Python parity).
3. projectdiscovery/katana — Go sidecar for security/recon crawling.
4. daijro/camoufox — anti-detect engine for stealth-required targets (tool integration only, MPL-2.0 isolation).

Excluded: lightpanda-io/browser (AGPL-3.0, patterns-only).
