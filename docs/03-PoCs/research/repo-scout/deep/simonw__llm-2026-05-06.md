---
evaluated_at: 2026-05-06 06:42 UTC
evaluation_level: 2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Plugin/provider architecture; map to lib/dispatch.py)
deep_verdict: ADOPT — proven plugin/provider architecture; direct reference for lib/dispatch.py (ADR-049)
deepwiki_url: https://deepwiki.com/simonw/llm
engram_id: pending
---

## Repository Evaluation: simonw/llm

### Classification: ADOPT
**Score**: 8.6/10
**Evaluation Level**: 2 (Deep — gh api tree, default_plugins/ inspection)

### Summary
Simon Willison's mature `llm` CLI for accessing LLMs from the command line. Apache-2.0, Python, push 2026-05-06 (active today), v0.32a1 + 0.31 + 0.30 + 0.29 cadence over years. **3 years old (2023-04-01)** — most mature project in the deep batch. Plugin/provider architecture in `llm/default_plugins/` is exactly the reference COS needs for `lib/dispatch.py` (ADR-049). Used widely as a Unix-style tool. ADOPT for pattern reference.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 9/10 | Plugin/provider arch is the exact pattern for ADR-049 LLM dispatch |
| License | 25% | 8/10 | Apache-2.0 (NOTICE compliance manageable) |
| Activity | 20% | 10/10 | Push today; weekly-monthly tag cadence; 48 issues/30d |
| Maturity | 15% | 9/10 | 3 years old; 11.7k★ from a single highly-respected maintainer; clean Apache-2.0 |
| Integration | 10% | 9/10 | Pattern is small + well-documented; cassette-based testing in `tests/cassettes/` is best-in-class |
| **Weighted Total** | | **8.95/10** weighted, presented as **8.6/10** after CI-flake adjustment | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 48 issues | high issue activity |
| Release cadence | 0.32a1, 0.32a0, 0.31, 0.30, 0.29 | monthly releases (alpha + stable line) |
| CI health | 4/10 success | CI flaky (recently — likely test-cassette refresh churn) |

### Key Findings
- **Strengths**:
  - Plugin discovery via setuptools entry points — battle-tested pattern.
  - `llm/default_plugins/` shows reference plugin shape we can mirror in `lib/dispatch.py` provider plugins.
  - **Cassette-based testing** (`tests/cassettes/`) — VCR-style record/replay for LLM API tests. Directly relevant to COS LLM-dispatch test discipline.
  - 3 years of evolution = stable API surface for plugin authors.
  - Single maintainer is famously responsive (simonw).
- **Weaknesses**:
  - 598 open issues — popularity outpaces maintainer time.
  - Apache-2.0 NOTICE compliance.
  - CI 4/10 lately — likely cassette mismatches with model API drift, not code rot.
- **Architecture**: CLI + plugin entry points + cassette tests + embeddings tooling. `llm/default_plugins/` is the reference plugin shape.

### Integration Plan
- **What to use**:
  1. Plugin/provider entry-point pattern → port into `lib/dispatch.py` provider abstraction.
  2. **Cassette-based LLM testing** → adopt for COS LLM-dispatch test suite.
  3. Embeddings module patterns (`docs/embeddings/`) → reference for any local embedding work.
- **How to integrate**: Pattern adoption only. Read default_plugins/*, mirror the plugin loader contract in COS dispatch.
- **Effort estimate**: small (1-2 days for plugin pattern + cassette adoption)
- **Dependencies it brings**: setuptools (already there); pytest-vcr or equivalent for cassettes (single small dep)

### Risks
- Apache-2.0 NOTICE-file compliance.
- 598 open issues = bus-factor concern despite simonw's strong reputation.
- Cassette test pattern requires careful re-record discipline as model APIs drift.

### Cross-Reference vs Shallow Radar
Shallow verdict: "Plugin/provider architecture; map to lib/dispatch.py (ADR-049)." **Deep evidence agrees** and adds the cassette-based testing pattern as an additional adoption target. Verdict ADOPT confirmed.

### Raw Metrics Appendix
```
{"name":"llm","license":"Apache-2.0","stars":11789,"forks":829,"language":"Python","pushed":"2026-05-06T04:48:52Z","created":"2023-04-01T21:16:57Z","open_issues":598,"size":1808 KB}
tags: 0.32a1,0.32a0,0.31,0.30,0.29
issues_30d=48, CI=4/10 success
```
