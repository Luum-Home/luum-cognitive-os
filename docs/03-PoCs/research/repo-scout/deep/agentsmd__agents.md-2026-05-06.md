---
evaluated_at: 2026-05-06 06:35 UTC
evaluation_level: 2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (AGENTS.md cross-harness spec primitive COS lacks)
deep_verdict: ADOPT (spec only — there is no library to vendor)
deepwiki_url: https://deepwiki.com/agentsmd/agents.md
engram_id: pending
---

## Repository Evaluation: agentsmd/agents.md

### Classification: ADOPT
**Score**: 8.0/10
**Evaluation Level**: 2 (Deep — gh api tree + repo metadata)

### Summary
Open spec + landing-site for `AGENTS.md` — a single Markdown file at the repo root that coding agents (Claude Code, Codex, Cursor, Aider, Goose, Factory, Gemini, OpenCode, Warp, Windsurf, Zed, Copilot, Junie, Jules, Kilo, Phoenix, Roo, Ona, Devin, Augment, etc.) read for project conventions. The repo IS a Next.js website — there is no library or runtime here. The "tech" we adopt is the spec format itself plus the cross-harness compatibility roster. Direct fit for COS `cognitive-os-init` to emit AGENTS.md alongside CLAUDE.md.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 9/10 | Cross-harness spec COS lacks; emit-target for `cognitive-os-init` and `radar-update` |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 7/10 | Push 2026-03-12 (~2 months stale); 31 issues/30d shows engagement |
| Maturity | 15% | 5/10 | No tags; community-driven spec; 21k stars + 1.5k forks indicate de-facto adoption |
| Integration | 10% | 9/10 | "Integration" is "write a markdown file at repo root" — trivial |
| **Weighted Total** | | **8.0/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 31 issues | high issue activity |
| Release cadence | no tags | no releases found |
| CI health | 2/2 success | CI green (small CI) |

### Key Findings
- **Strengths**:
  - 25+ harness logos in `public/logos/` — concrete cross-harness compatibility list COS can mirror in `lib/harness_adapter/`.
  - Spec itself is `AGENTS.md` at repo root — readable as a Markdown one-pager.
  - 21k stars on a 9-month-old spec site = real adoption.
- **Weaknesses**:
  - No library, no SDK, no runtime — spec only. Phase-2 deep audit confirms there is nothing to vendor.
  - 2 months since last push; spec evolution is slow (which may be a feature, not a bug).
- **Architecture**: Static Next.js marketing/spec site. Pages render the spec + compatibility table.

### Integration Plan
- **What to use**: The AGENTS.md spec format itself + the harness compatibility roster (logo set as ground-truth inventory of harnesses to support).
- **How to integrate**:
  1. Add an `AGENTS.md` emitter to the COS `cognitive-os-init` skill (sibling to `CLAUDE.md`).
  2. Cross-link the harness roster against `lib/harness_adapter/` to confirm coverage gaps.
  3. Reference AGENTS.md in COS docs as the canonical cross-harness spec.
- **Effort estimate**: small (half-day to add emitter + cross-link)
- **Dependencies it brings**: none

### Risks
- Spec is still evolving via PRs; pin to a referenced commit/section when emitting.
- "Single file at repo root" can collide with existing CLAUDE.md / .cursorrules / .codex-rules. Need clear precedence rules in the emitter.

### Cross-Reference vs Shallow Radar
Shallow verdict: "AGENTS.md cross-harness spec primitive COS lacks; emitter for `cognitive-os-init`." **Deep evidence agrees and refines.** The repo is not a code library — it is a spec + landing site. The "adopt" action is to (1) emit AGENTS.md from `cognitive-os-init`, (2) use the harness roster as the cross-harness target list. No vendored code is implied.

### Raw Metrics Appendix
```
{"name":"agents.md","license":"MIT","stars":21011,"forks":1536,"language":"TypeScript","archived":false,"pushed":"2026-03-12T14:26:14Z","created":"2025-08-19T17:22:54Z","open_issues":135,"size":1912 KB}
issues_30d=31, tags=[], CI=2/2 ok
```
