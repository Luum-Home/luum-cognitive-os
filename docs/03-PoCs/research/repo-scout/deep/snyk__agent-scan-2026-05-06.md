---
evaluated_at: 2026-05-06 06:58 UTC
evaluation_level: 2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Agent/MCP/skill-specific security scanner; clean delta vs Aguara)
deep_verdict: ADOPT — Snyk-backed, CI-perfect, skill-aware security scanning is a clean delta vs Aguara
deepwiki_url: https://deepwiki.com/snyk/agent-scan
engram_id: pending
---

## Repository Evaluation: snyk/agent-scan

### Classification: ADOPT
**Score**: 8.7/10
**Evaluation Level**: 2 (Deep — gh api recursive tree, tests/skills + tests/mcp_servers inspection)

### Summary
"Security scanner for AI agents, MCP servers and agent skills." Apache-2.0, Python, 2.3k★, push 2026-05-05 (today), v0.5.1 latest. **CI 10/10 green** (tied with token-savior + mempalace for top CI in batch). Backed by Snyk (commercial security vendor → real maintenance). Test corpus is the gem: realistic skill samples (`tests/skills/{algorithmic-art, brand-guidelines, canvas-design, doc-coauthoring, docx, frontend-design, internal-comms, malicious-skill, mcp-builder, pdf, pptx, skill-creator, slack-gif-creator, theme-factory, web-artifacts-builder, webapp-testing, xlsx}`) + MCP server samples + invalid-skill negative tests (`tests/mcp_servers/.test-client-invalid/skills/invalid-skill`). Direct fit for ADR-139..142 + the radar's mcp-extensions cluster.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 10/10 | Skill-aware security scanner is exactly the gap COS needs to close (clean delta vs Aguara per shallow) |
| License | 25% | 8/10 | Apache-2.0 |
| Activity | 20% | 10/10 | Push today; v0.4.18→v0.5.1 cadence; 62 issues/30d |
| Maturity | 15% | 7/10 | Pre-1.0 (v0.5.1); 1.1 years old; Snyk-backed = real maintenance |
| Integration | 10% | 9/10 | Python; clean src/agent_scan/{hooks,...}; demoserver/ for E2E; tests/skills/ for adoption-as-test-corpus |
| **Weighted Total** | | **8.95/10** weighted, presented as **8.7/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 62 issues | high issue activity |
| Release cadence | v0.5.1, v0.5.0, v0.4.18 + snapshot tags | weekly releases |
| CI health | 10/10 success | CI green |

### Key Findings
- **Strengths**:
  - **CI 10/10 green** — tied with token-savior + mempalace.
  - **`tests/skills/` corpus**: 17+ realistic skills covering productivity, creative, dev, security domains. Includes a deliberate `tests/skills/malicious-skill` for negative testing. Direct adoption candidate for COS skill-security-scan corpus.
  - **`tests/mcp_servers/.test-client-invalid/skills/invalid-skill/tricks`** — adversarial test fixtures specifically for MCP-server-skill scanning. Direct fit for ADR-141 air-gapped surface scanning.
  - Snyk-backed → commercial maintenance + supply-chain credibility.
  - Hooks subsystem (`src/agent_scan/hooks/`) — pluggable scan rules.
  - Tagged snapshot builds (`v0.5.0-snapshot-ea261e7-1043`) show CI/release discipline.
  - `demoserver/` for E2E integration testing.
- **Weaknesses**:
  - Pre-1.0 (v0.5.1) — API may shift.
  - Apache-2.0 NOTICE compliance.
  - 18 open issues is small but only because the project is young; Snyk's enterprise concerns may be private.
- **Architecture**: `src/agent_scan/` core + hooks subsystem; `tests/{e2e, mcp_servers, skills, unit, v4compatibility}` test split. Demoserver + circleci config.

### Integration Plan
- **What to use**:
  1. **agent-scan as a sidecar tool** in COS pre-commit / pre-skill-publish pipeline. It is purpose-built for our exact threat surface.
  2. **`tests/skills/malicious-skill`** + `tests/mcp_servers/.test-client-invalid/skills/invalid-skill` — adopt as canonical adversarial corpus for COS security tests.
  3. **Hook framework** in `src/agent_scan/hooks/` — add COS-specific hooks for our skill conventions.
  4. Combine with Aguara per the radar's "clean delta" verdict: agent-scan covers MCP/agent surface, Aguara covers prompt-injection runtime defense.
- **How to integrate**: Use as binary tool first; if patterns prove valuable, extend with COS-specific hooks.
- **Effort estimate**: small (1-2 days for first integration in pre-commit / CI)
- **Dependencies it brings**: agent-scan + transitively whatever Snyk pulls in

### Risks
- Apache-2.0 NOTICE compliance.
- Snyk is commercial — watch for license-tier walls or relicensing.
- Pre-1.0 — pin to v0.5.1.

### Cross-Reference vs Shallow Radar
Shallow verdict: "Agent/MCP/skill-specific security scanner; clean delta vs Aguara. Both Phase-2 to land before flow #1 promotion." **Deep evidence agrees and amplifies**: the skill + MCP-server test corpus (especially the deliberate malicious/invalid samples) is a direct artifact we can vendor under Apache-2.0 attribution. Verdict ADOPT confirmed; integration is near-term Phase-2 work per ADR-139..142.

### Raw Metrics Appendix
```
{"name":"agent-scan","license":"Apache-2.0","stars":2349,"forks":211,"language":"Python","pushed":"2026-05-05T06:18:06Z","created":"2025-04-07T14:31:26Z","open_issues":18,"size":3765 KB}
tags: v0.5.1, v0.5.0, v0.4.18 (+ snapshot variants)
issues_30d=62, CI=10/10 success
test skills count: 17+ (incl. deliberate malicious-skill)
```
