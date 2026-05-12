---
evaluated_at: 2026-05-06 06:35 UTC
evaluation_level: 2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Skills/instincts/memory model + cross-harness abstraction)
deep_verdict: ADOPT (with caveats — confirm anomalous fork count is real)
deepwiki_url: https://deepwiki.com/affaan-m/everything-claude-code
engram_id: pending
---

## Repository Evaluation: affaan-m/everything-claude-code

### Classification: ADOPT
**Score**: 8.5/10
**Evaluation Level**: 2 (Deep — gh api tree, 455 SKILL.md count)

### Summary
"The agent harness performance optimization system." JavaScript-led, MIT, with **455 SKILL.md files** organized under `.agents/skills/` and per-skill `agents/openai.yaml` companions. Tags v1.6.0–v1.10.0 indicate active semver releases. Self-described domain matches COS exactly: skills, instincts, memory, security, research-first development. Clear ADOPT for pattern study; the breadth of skill catalog is a forcing-function comparison set for COS's own `skills/` tree.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 10/10 | Direct domain peer (skills/instincts/memory/security/research-first); 455 skills as forcing comparison set |
| License | 25% | 10/10 | MIT confirmed (shallow radar already verified) |
| Activity | 20% | 10/10 | Push 2026-05-03 (3 days ago); 100+ issues/30d; 5 tagged releases |
| Maturity | 15% | 7/10 | v1.10.0 + semver; 4 months old; large skill catalog but unknown internal QA depth |
| Integration | 10% | 7/10 | Per-skill `openai.yaml` shows multi-provider intent; SKILL.md format compatible with COS |
| **Weighted Total** | | **9.05/10** weighted, presented as **8.5/10** after fork-anomaly adjustment | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 100+ (paged out) | high issue activity |
| Release cadence | v1.6.0 → v1.10.0 visible | weekly-to-biweekly releases |
| CI health | 2/10 success | CI mostly red (8/10 not success — likely many cancelled/skipped) |

### Key Findings
- **Strengths**:
  - **455 SKILL.md files** — largest skill catalog in the deep batch by an order of magnitude. Forcing-function for COS skill-coverage gaps.
  - Per-skill `agents/openai.yaml` companion — interesting cross-provider abstraction we don't have.
  - Active semver release cadence (v1.6 → v1.10 in a few months).
  - Domain alignment is unusually tight: skills / instincts / memory / security / research-first all match COS Phase-2 and ADR-049/059.
- **Weaknesses**:
  - **Fork count 26,970** on a 4-month-old repo is anomalous (similar profile to obra/superpowers). Likely automated forking.
  - 174k stars vs 27k forks vs single primary maintainer = bus factor 1 with metric-pump.
  - CI not consistently green. 8/10 runs are non-success — if "cancelled" rather than "failed" this is fine, but worth verifying before vendoring any one skill.
  - 159 open issues — triage health unknown.
- **Architecture**: Skills under `.agents/skills/<name>/SKILL.md` + per-skill agent YAMLs. Mirrors COS layout closely.

### Integration Plan
- **What to use**:
  1. **Skill catalog as gap analysis**: diff the 455 skills against COS skill registry to find under-covered domains (e.g. `agent-introspection-debugging`, `eval-harness`, `brand-voice`, `crosspost`, `dmux-workflows` are visible from the tree).
  2. **`.agents/skills/agents/openai.yaml` pattern**: per-skill provider override is a primitive COS lacks. Worth adopting.
  3. Specific skills worth diffing first: `agent-introspection-debugging`, `eval-harness`, `deep-research`, `coding-standards`, `documentation-lookup`.
- **How to integrate**: Pattern adoption only (read + selectively port skill bodies). Do NOT vendor wholesale — the catalog has high duplication risk with our existing skills.
- **Effort estimate**: medium (1-2 days for catalog diff; ad-hoc for per-skill ports)
- **Dependencies it brings**: JavaScript (Node) toolchain if we adopt runtime pieces, but skills themselves are MD/YAML

### Risks
- Star/fork inflation makes community signal unreliable; judge purely on content.
- 455-skill catalog depth uneven; sample skills before bulk porting.
- Single maintainer; bus factor 1.
- License re-verify per radar Phase-2 note (shallow already confirmed MIT but radar called it out).

### Cross-Reference vs Shallow Radar
Shallow verdict: "Skills/instincts/memory model + cross-harness abstraction; compare to skill registry + ADR-033." **Deep evidence agrees and amplifies**: the catalog scale (455 skills) makes this a higher-priority gap-analysis target than the shallow radar suggested. Caveat added: fork-count and star-count are likely metric-pump artifacts; treat community signals with skepticism.

### Raw Metrics Appendix
```
{"name":"everything-claude-code","license":"MIT","stars":174147,"forks":26970,"language":"JavaScript","pushed":"2026-05-03T04:53:48Z","created":"2026-01-18T00:51:51Z","size":31473 KB,"open_issues":159}
SKILL.md count: 455
tags: v1.10.0,v1.9.0,v1.8.0,v1.7.0,v1.6.0
issues_30d=100+, CI 2/10 success
```
