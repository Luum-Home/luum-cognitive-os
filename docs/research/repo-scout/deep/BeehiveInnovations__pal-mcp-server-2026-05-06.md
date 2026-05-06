---
evaluated_at: 2026-05-06 06:50 UTC
evaluation_level: 2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Multi-model MCP bridge; cross-provider routing)
deep_verdict: ADOPT — confirmed Apache-2.0, multi-provider MCP server with cassette tests
deepwiki_url: https://deepwiki.com/BeehiveInnovations/pal-mcp-server
engram_id: pending
license_verification: confirmed Apache-2.0 via LICENSE file (gh api returned NOASSERTION; manual fetch confirms Apache-2.0)
---

## Repository Evaluation: BeehiveInnovations/pal-mcp-server

### Classification: ADOPT
**Score**: 7.9/10
**Evaluation Level**: 2 (Deep — gh api tree, LICENSE file fetch, cassettes inspection)

### Summary
"The power of Claude Code / GeminiCLI / CodexCLI + multiple providers working as one." Python MCP server, 11.5k★, push 2025-12-15 (5 months stale — concerning). v9.x cadence (v9.6.0 → v9.8.2). License surface: GitHub API returns NOASSERTION; manual `gh api .../contents/LICENSE` fetch confirms **Apache-2.0** (consistent with shallow radar Phase-2 note). Strong test discipline — `tests/gemini_cassettes/`, `tests/openai_cassettes/`, `simulator_tests/`. Provider registries + clink (CLI-link) abstractions are direct ADR-049 references.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 9/10 | Multi-provider MCP bridge with provider registries = ADR-049 reference |
| License | 25% | 8/10 | Apache-2.0 (manual verification required; GH classifier returned NOASSERTION) |
| Activity | 20% | 6/10 | Push 2025-12-15 (~5 months stale); v9.8.2 latest |
| Maturity | 15% | 7/10 | v9.x cadence; cassette-based tests; 11.5k★ |
| Integration | 10% | 8/10 | Python MCP server; conf/cli_clients/ + providers/registries/ = pluggable |
| **Weighted Total** | | **7.9/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 27 issues | moderate-high issue activity |
| Release cadence | v9.6.0-v9.8.2 | weekly-to-biweekly cadence (when active) |
| CI health | 8/10 success | CI green-ish |

### Key Findings
- **Strengths**:
  - **Cassette-based provider tests** in `tests/gemini_cassettes/` + `tests/openai_cassettes/` — same pattern as simonw/llm; both repos validate this as best-practice for LLM testing.
  - `providers/registries/` + `providers/shared/` = clean multi-provider abstraction. Direct fit for `lib/dispatch.py`.
  - `clink/agents/` + `clink/parsers/` + `conf/cli_clients/` = harness adapter primitives (parallel to coder/agentapi).
  - `tools/{shared, simple, workflow}` split is a useful taxonomy COS could adopt for skill organization.
  - `simulator_tests/` for end-to-end validation.
- **Weaknesses**:
  - 5-month staleness — pre-HOLD threshold but trending toward inactivity.
  - License NOASSERTION on GH classifier; requires manual verification (done; Apache-2.0).
  - 992 forks on 11.5k stars feels reasonable (no metric-pump signals here).
  - 126 open issues with the maintenance gap is concerning.
- **Architecture**: MCP server core + `tools/` directory of capabilities + `providers/` (registries + shared) + `clink/` (CLI-link adapters) + `conf/cli_clients/` per-client config + cassette tests.

### Integration Plan
- **What to use**:
  1. Provider registry pattern from `providers/registries/` → ADR-049 dispatch reference.
  2. `clink/parsers/` for harness output parsing (compare against coder/agentapi msgfmt).
  3. **Cassette test infrastructure** — second confirmation of this pattern (after simonw/llm). Adopt for COS dispatch tests.
  4. `tools/{shared, simple, workflow}` skill taxonomy.
- **How to integrate**: Pattern adoption only.
- **Effort estimate**: small-medium (2-3 days)
- **Dependencies it brings**: none (pattern adoption)

### Risks
- 5-month staleness — pin to v9.8.2; do not expect upstream maintenance.
- License re-verify before vendoring: **Apache-2.0 confirmed** via direct LICENSE file fetch.
- Apache-2.0 NOTICE compliance.

### Cross-Reference vs Shallow Radar
Shallow verdict: "Multi-model MCP bridge; cross-provider routing patterns. License confirmed Apache-2.0." **Deep evidence agrees and adds**: cassette-based testing infrastructure (parallel to simonw/llm) is a second adoption target on top of provider registries. Verdict ADOPT confirmed.

### Raw Metrics Appendix
```
{"name":"pal-mcp-server","license_API":"NOASSERTION","license_FILE":"Apache-2.0","stars":11513,"forks":992,"language":"Python","pushed":"2025-12-15T17:07:31Z","created":"2025-06-08T15:36:50Z","open_issues":126,"size":4096 KB}
tags: v9.8.2,v9.8.1,v9.8.0,v9.7.0,v9.6.0
issues_30d=27, CI=8/10 success
```
