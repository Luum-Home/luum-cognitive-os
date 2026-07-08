---
type: concept-synthesis
source: docs/04-Concepts/root/ux-principles.md
provenance: "Documents the invisible-OS philosophy so the AI knows how and when to surface information, avoiding both silent failures and noisy over-explanation."
---

## What it is
Seven UX principles governing how Cognitive OS communicates with users — analogous to a car's ABS/ESP: safety runs invisibly and only surfaces when it needs to intervene.

## Key mechanics
- **Principle 1 Invisible Safety**: 4 visibility tiers — Silent (no output), Informative (1-line ack), Intervention (explanation + action needed), Block (prevents damage, explains + alternative). Maps to the 12-layer safety mesh: Silent (blast radius, assumption tracker, trust score validator), Informative (clarification interceptor, scope proportionality), Intervention (clarification gate, confidence gate, rate limiter), Block (dry-run preview, auto-rollback trigger).
- **Principle 2 Progressive Disclosure**: Level 0 just works (`install.sh` -> done), Level 1 discovers SDD (`/sdd-new` suggested for complex asks), Level 2 discovers quality gates (trust report visible), Level 3 power user (`cos map`, `cos perf`, `/planning-poker`).
- **Principle 3 The AI Is the Driver**: user only knows what they asked and what they got; AI internally manages 55+ rules, 12 safety layers, model routing, Engram memory, quality gates. Documentation split: `faq.md`/`getting-started.md` (user), rules/skills/hooks (AI-consumed), `how-to-extend.md`/`architecture-principles.md` (contributors).
- **Principle 4 Speak Only When Valuable**: 3-question test (does the user need to know? does it help a decision? is it actionable?). Communication budget: routine success = 0 tokens, noteworthy = 1 line, intervention = 2-3 lines, block = 5+ lines.
- **Principle 5 Cost Transparency Without Noise**: costs tracked silently; surfaced at session end (summary line), at 80% budget threshold (model-switch note), at 95% (critical warning), at 100% (block + recovery options), or on demand (`cos perf`).
- **Principle 6 Error Messages Are Teaching Moments**: translation table maps internal jargon (`clarification-gate BLOCK, score 72`, `blast-radius CRITICAL`, `confidence-gate BLOCK, trust score 35`, `scope-proportionality violation`, `rate-limiter BLOCK, 31/30`, `assumption-tracker WARNING`) to plain-language user-facing explanations.
- **Principle 7 The Hood Is Always Available**: on-demand introspection — `cos perf` (cost/tokens/routing), `cos map <component>` (dependency tree across 5 layers), `/cognitive-os-status` (hooks/rules/skills/metrics health), Engram search (past decisions), `cos test` (TUI pass/fail dashboard).
- Anti-patterns table: 8 examples of noise to avoid (e.g. "12 hooks executed successfully", showing the full safety mesh every task, dumping metrics in normal output, unprompted architecture explanations).
- 5-layer visibility mapping: Rules = invisible, Skills = contextual, Hooks = silent-unless-intervening, Libs = on-demand CLI, Externals = invisible.

## Relations & where used
Maps to `docs/04-Concepts/root/safety-mesh.md` (12-layer mesh), `docs/04-Concepts/architecture-principles.md` (5-layer architecture), `rules/responsiveness.md` (proactive-but-not-verbose communication protocol).

## Status / caveats
No explicit status stated. North-star framing: the user should feel they are working with a capable colleague who handles complexity quietly and interrupts only when something genuinely needs attention.
