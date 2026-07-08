---
type: concept-synthesis
source: docs/04-Concepts/architecture/token-savings-qa.md
status: "evidence-backed estimate, not a universal guarantee"
provenance: "Operator-facing answer to the recurring product/architecture question: how many tokens can Cognitive OS save vs legacy/vanilla agent governance, and how confident are we?"
---

## What it is

Q&A document giving the bounded, evidence-backed answer to "how many tokens does Cognitive OS save vs legacy/vanilla agent governance." Core claim: COS can plausibly save ~25%-85% of token usage per task/session depending on project size, governance style, subagent count, and context-rediscovery frequency — driven mainly by turning governance from a fixed prompt tax into progressive, on-demand context.

## Key mechanics

**Measured anchors** (chars/4 estimator): `AGENTS.md` ~2,508 tok; `rules/RULES-COMPACT.md` ~2,792; `skills/CATALOG-MICRO.md` ~3,585; `skills/CATALOG-COMPACT.md` ~4,775; `skills/CATALOG.md` ~11,982; `cognitive-os.yaml` ~17,893; all `rules/*.md` ~128,482; all `skills/*/SKILL.md` ~249,358. Preamble budgets: core ~2,865/3,200 (pass), team ~5,532/6,000, maintainer ~8,457/10,000, lab ~8,441/20,000.

**Savings tiers by scenario**:
- Conservative: ~14K tokens/session (legacy ~17.5K baseline vs compact COS ~3.5K)
- Typical medium/large project: ~50%-70% fewer tokens/task
- Legacy full-load baseline: ~150K+ tokens/session saved (~95% reduction)
- Extreme theoretical (all rules+skills+config+global instructions): ~390K tokens/session (~98% reduction, upper-bound only)
- By project type: small/one-agent 25%-45%; medium/several-files 45%-65%; large/multiagent 60%-75%; legacy manual governance 65%-85%; debug-heavy/chaotic 60%-80%

**8 savings sources**: progressive skill loading (CATALOG-MICRO first), compact rules (RULES-COMPACT.md), runtime config projection, subagent context diet, memory-first retrieval, result truncation, budget/accounting hooks, escalation discipline.

**Local paired-run evidence (2026-05-22)**: 3 anonymized projects, 9 task pairs (read-only, no provider API — estimates/proxies not telemetry). Context-bearing pairs (vanilla tool output >=1K est. tokens): 4 pairs, 46.0%-97.5% savings, avg 71.6%. Low-context pairs can show small absolute COS overhead. Checklist quality same-or-better in 9/9 pairs. Receipt: `docs/06-Daily/reports/token-savings-paired-live-anonymized-2026-05-22.md`.

**Operator answer card**: "~14K tokens/session conservative vs older full-load baselines; ~45%-70% typical in medium/large projects; ~75%-95%+ for legacy full-load setups. Evidence-backed estimates, not universal benchmark results."

**Bounded claim language** (Q10): use "commonly 45%-70% range... higher savings possible for legacy setups." Avoid "always saves 80%", "guaranteed", "zero overhead", "measured across all projects."

## Relations & where used

`docs/04-Concepts/architecture/context-rot-token-budget-controls.md`, `token-efficient-agent-messaging.md`, `docs/09-Quality/manual-tests/token-savings-paired-benchmark.md`, `rules/context-optimization.md`, `rules/token-economy.md`. Verification via `scripts/cos-token-savings-audit`, `scripts/cos-preamble-budget`, `scripts/cos-context-budget-report`.

## Status / caveats

Confidence is directional-high but exact-percentage-medium. Does NOT save tokens on tiny one-off tasks with no project history/subagents/governance burden (Q8). Token/context safety barriers are never removed for savings — moved from always-loaded prose to hooks/on-demand rules (Q9). Stronger claims require a controlled paired benchmark with real provider token usage (Q11) — not yet done beyond the anonymized read-only run above.
