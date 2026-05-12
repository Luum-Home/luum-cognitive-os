---
evaluated_at: 2026-05-06 06:30 UTC
evaluation_level: 2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (highest-priority Phase-2 target — direct peer to COS skills)
deep_verdict: ADOPT (with caveats — see Risks)
deepwiki_url: https://deepwiki.com/obra/superpowers
engram_id: pending
---

## Repository Evaluation: obra/superpowers

### Classification: ADOPT
**Score**: 8.4/10
**Evaluation Level**: 2 (Deep — gh api tree+file inspection of 63-path skills/ subtree, plus README, plugin manifests, CI history)

### Summary
Cross-harness agentic-engineering plugin (Claude Code, Codex CLI/App, Gemini, OpenCode, Cursor, Copilot CLI, Factory Droid) shipping 16 SKILL.md-based skills plus a documented agentic methodology (brainstorm → worktree → plan → subagent-driven dev → TDD → review → finish). MIT, Shell-first, very low porting cost. The skill schema, trigger philosophy ("skills trigger automatically"), and worktree+TDD methodology all map directly onto COS rules/skills/`RULES-COMPACT.md`. Highest-leverage target for cross-pollination in the Phase-2 batch.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 10/10 | Direct peer to COS skill system + agentic methodology; 7 harness adapters answer ADR-033/cross-harness-authoring directly |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | Push 2026-05-06 (today); 5 tags v5.0.4→v5.1.0 visible; 273 open issues |
| Maturity | 15% | 7/10 | v5.1.0 + semver; ~7 months old; 16 skills covering core SDD lifecycle. Plans/specs subdirectory shows real internal SDD discipline. Low test ratio (no `tests/` tree visible, only systematic-debugging/find-polluter.sh) |
| Integration | 10% | 7/10 | Each skill is one MD file with optional sibling scripts — trivial to read+adapt. No formal API/types. CLI install per harness. |
| **Weighted Total** | | **8.95/10** weighted, presented as **8.4/10** after CI-failure adjustment | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 100+ issues (paged out at 100) | high issue activity |
| Release cadence | 5 tags visible v5.0.4→v5.1.0; rapid minor cadence | weekly-to-biweekly releases |
| CI health | 0/10 success in last 10 runs | CI red |

### Key Findings
- **Strengths**:
  - Skill schema is YAML-frontmatter + MD body — virtually identical to COS `skills/*/SKILL.md`. Direct compare/adopt patterns possible.
  - Cross-harness packaging is the most mature in the radar (`.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `.opencode/`, `gemini-extension.json`, hooks-cursor.json + hooks.json) — concrete reference for COS's own AGENTS.md ambitions and ADR-033 harness adapter work.
  - The 7-step methodology (brainstorm, worktree, plan, subagent dev, TDD, review, finish) is the same arc COS expresses as SDD; we can compare phase definitions and skill triggers directly.
  - "Skills trigger automatically" — useful for tightening our `skill-router.best_match` confidence thresholds (RULES §11).
  - Internal `docs/superpowers/plans` and `docs/superpowers/specs` directories indicate dogfooded SDD-like discipline.
- **Weaknesses**:
  - **CI is fully red**: 10/10 last runs failed. Either intentional (failing tests as documentation) or a real quality regression. Worth one issue triage before adopting any specific skill verbatim.
  - **Star-count anomaly**: 179,720★ on a 7-month-old MIT shell project with 1 maintainer is implausible. The shallow radar flagged this. Stars do NOT validate quality here — patterns must be judged on substance.
  - 273 open issues with no visible triage labels in the tree.
  - No `tests/` directory at the top level — Shell-first projects test in-skill, but verification of skill correctness is informal.
- **Architecture**: Plugin manifests per harness + `skills/<name>/SKILL.md` + `hooks/run-hook.cmd` for cross-platform shell entry. Each skill self-contained; no central skill registry analog to COS `skill-registry`.

### Integration Plan (TRIAL+ only)
- **What to use**:
  1. `skills/test-driven-development/SKILL.md` — compare against COS `test-driven-development` skill; adopt RED-GREEN-REFACTOR phrasing if it reads cleaner.
  2. `skills/writing-skills/anthropic-best-practices.md` + `skills/writing-skills/persuasion-principles.md` — feed into our `skill-creator` skill template.
  3. `skills/subagent-driven-development/{implementer,spec-reviewer,code-quality-reviewer}-prompt.md` — three-prompt pattern is novel vs our orchestrator/sub-agent split. Worth lifting the prompts.
  4. `.claude-plugin/marketplace.json` + `.codex-plugin/plugin.json` schemas — reference for cross-harness plugin export from COS.
  5. `hooks/run-hook.cmd` + `docs/windows/polyglot-hooks.md` — concrete polyglot hook pattern (Windows .cmd + bash fallback) directly relevant to COS hooks system.
- **How to integrate**: Pattern adoption only (read-as-reference, do not vendor). Compare pattern-by-pattern with our existing skills, lift specific prompt wording or method sequencing where superior.
- **Effort estimate**: medium (1-2 days of skill-by-skill diff and selective merge).
- **Dependencies it brings**: none — Shell + MD only.

### Risks
- CI red flag must be investigated before mirroring specific shell scripts. Plugin manifests are safer to lift than active scripts.
- High mindshare + active fork tree = pattern drift risk; pin to a specific tag (v5.1.0) when referencing.
- Single maintainer; bus factor 1.
- Star count is suspect — do not use it as a signal of community vetting. Judge purely on the content.

### Alternatives
- `obra/superpowers-marketplace` — sibling marketplace registry, also worth scouting if we ever publish a COS plugin.
- `affaan-m/everything-claude-code` (deep target #3) — also targets cross-harness skills/instincts; complementary perspective.
- Our own `skills/` tree is more battle-tested in production-OS settings; superpowers is more end-user dev-loop oriented.

### Cross-Reference vs Shallow Radar
Shallow verdict (`docs/06-Daily/reports/external-tools-radar-2026-05-06.md`): "highest learn-rate target; shell-first means low porting cost." **Deep evidence agrees.** The ADOPT classification is upheld, but with two caveats the shallow scout did not surface: (1) CI red across the last 10 runs, (2) the 179k★ count is an outlier we should not weight. Both lower confidence in code-level adoption (use as pattern reference, not vendored shell), but do not change the radar ring.

### Raw Metrics Appendix
<details>
<summary>gh api summary</summary>

```
{"name":"superpowers","full_name":"obra/superpowers","description":"An agentic skills framework & software development methodology that works.","language":"Shell","license":"MIT","stars":179720,"forks":15982,"archived":false,"disabled":false,"pushed_at":"2026-05-06T04:58:07Z","created_at":"2025-10-09T19:45:18Z","open_issues":273,"size":2604,"topics":[]}
```

Tags: v5.1.0, v5.0.7, v5.0.6, v5.0.5, v5.0.4
CI runs: total=10, success=0, failure=10, null=0
Skills tree: 16 SKILL.md files, ~63 skill-tree paths total
</details>
