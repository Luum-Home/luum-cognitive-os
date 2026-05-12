---
evaluated_at: 2026-05-06 06:42 UTC
evaluation_level: 2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Provider routing transforms; same harness)
deep_verdict: TRIAL — strong patterns but pre-1.0 + 2-month staleness; adopt patterns, not the code
deepwiki_url: https://deepwiki.com/musistudio/claude-code-router
engram_id: pending
---

## Repository Evaluation: musistudio/claude-code-router

### Classification: TRIAL
**Score**: 7.5/10
**Evaluation Level**: 2 (Deep — gh api tree, packages/ structure)

### Summary
TypeScript monorepo (packages/cli, core, server, shared, ui) that routes Claude Code traffic through alternative providers. MIT, 33k★, push 2026-03-04 (~2 months stale), single tag v2.0.0. Same harness as ours — patterns directly applicable to ADR-049 LLM dispatch. Solid surface for transformer/preset patterns and provider auth flows. Downgrade ADOPT-implied → TRIAL on stagnation + huge open-issue count (915).

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 9/10 | Same-harness provider routing is exactly the ADR-049 pattern |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 6/10 | 2 months since push; only 1 tag; 93 issues/30d shows ongoing community demand |
| Maturity | 15% | 5/10 | Single v2.0.0 tag; pre-stable; no semver patch line |
| Integration | 10% | 7/10 | TypeScript monorepo; clean packages/ split; reading patterns out of TS into Python takes effort |
| **Weighted Total** | | **8.0/10** weighted, presented as **7.5/10** after staleness + open-issue adjustment | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 93 issues | high issue activity |
| Release cadence | 1 tag (v2.0.0) | infrequent releases |
| CI health | 7/9 success | CI green-ish |

### Key Findings
- **Strengths**:
  - Clean monorepo split: `packages/{cli, core, server, shared, ui}` mirrors a sensible provider-router architecture.
  - `packages/core/src/{api, plugins, services, tokenizer, transformer, types}` is a complete reference for transformer chains and preset systems.
  - i18n + docusaurus docs (en + zh-CN) — broad community.
  - Same harness (Claude Code) means semantics are 1:1 portable.
- **Weaknesses**:
  - **915 open issues + 2 months without push** = maintenance debt.
  - Single v2.0.0 tag with no patch line.
  - Backup directories committed (`docs/i18n/zh-CN/...backup.20260101_205603/`) suggest housekeeping issues.
  - TypeScript ports to COS Python need translation effort.
- **Architecture**: Monorepo. CLI invokes Server which uses Core (transformer + plugins + services). UI is React. Server agents in `packages/server/src/agents/` route per-provider.

### Integration Plan (TRIAL+)
- **What to use**:
  1. **Transformer chain pattern** in `packages/core/src/transformer` — port concept into `lib/dispatch.py` request/response transform pipeline.
  2. **Preset system** (`packages/cli/src/utils/preset/`) — pattern for COS dispatch preset selection.
  3. **Provider plugin registry** in `packages/core/src/plugins/` — mirror as Python plugins for dispatch.
- **How to integrate**: Pattern adoption only — read TS, reimplement in Python.
- **Effort estimate**: medium (3-5 days to extract transformer + preset patterns)
- **Dependencies it brings**: none if we port patterns

### Risks
- 2-month staleness + 915 issues = real maintenance risk; do not depend on upstream fixes.
- TypeScript-to-Python translation is friction.
- Backup-dirs committed suggest the repo's hygiene is shaky.

### Cross-Reference vs Shallow Radar
Shallow verdict: "Provider routing transforms + auth handling; same harness as ours." **Deep evidence partially overturns**: the patterns are real and worth lifting, but the project is staler than the shallow radar implied (2 months since push, 915 open issues, single tag). **Downgrade implied-ADOPT → TRIAL.** Action stays: adopt transformer + preset + plugin patterns from a pinned commit.

### Raw Metrics Appendix
```
{"name":"claude-code-router","license":"MIT","stars":33487,"forks":2711,"language":"TypeScript","pushed":"2026-03-04T05:48:17Z","created":"2025-02-25T02:17:18Z","open_issues":915,"size":13894 KB}
tags: v2.0.0
issues_30d=93, CI=7/9 success
```
