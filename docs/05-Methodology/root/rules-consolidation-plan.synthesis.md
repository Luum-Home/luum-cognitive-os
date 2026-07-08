---
type: methodology-synthesis
source: docs/05-Methodology/root/rules-consolidation-plan.md
provenance: "P0 performance proposal to cut always-loaded rule tokens from ~73K to ~35K by shrinking the always-loaded core set from 73 to 14 rules, backed by token-budget math and a phased rollout."
---

## What it is

An implementation-ready (dated 2026-03-29) plan/proposal to reduce Cognitive OS's always-loaded rule footprint. Current state analyzed: 73 total rule files (~292KB, ~73,000 tokens) all loaded at session start, consuming 7.3% of a 1M-token window but 36.5% of a 200K window and 57% of a 128K window — flagged as approaching the >150-instruction degradation threshold cited from the "Evaluating AGENTS.md" paper (arXiv 2507.11538) once external project rules stack on top.

## Key mechanics

- **Proposed split**: 14 always-loaded "core" rules (~35,300 tokens total, including `RULES-COMPACT.md` itself) + 59 on-demand rules loaded via the Read tool when a trigger condition matches. The 14 are: RULES-COMPACT, adaptive-bypass, acceptance-criteria, agent-quality, trust-score, definition-of-done, phase-aware-agents, closed-loop-prompts, token-economy, responsiveness, agent-security, credential-management, content-policy, error-learning — selected by two tests: (1) relevant to >80% of sessions, (2) late-loading causes measurable quality degradation.
- **On-demand trigger taxonomy**: 6 mechanisms — `hook` (PostToolUse/PreToolUse detection, <200ms), `command` (slash command/skill invocation), `threshold` (metric crosses configured value), `env_var` (session-start env check), `keyword` (prompt/message pattern match), `config` (cognitive-os.yaml setting enabled) — each on-demand rule mapped to its trigger type/condition/regex pattern in a large table.
- **Chosen loading mechanism**: Option C ("RULES-COMPACT as bookmark + model self-serves via Read tool"), rejecting Option A (dynamic mid-session hook symlinking — rejected because Claude Code loads rules only at session start, not dynamically) and treating Option B (SessionStart config-driven loading) as a partial optimization only. No new hook required — existing infrastructure (RULES-COMPACT gateway + `cognitive-os.yaml` contextual_triggers + Read tool) already supports it.
- **Implementation**: add a `CORE_RULES` bash array to `hooks/self-install.sh` (lines 137-163 currently: `lean`/`standard` keep only RULES-COMPACT.md, `full` keeps everything); new behavior makes `standard` keep the 14 core rules instead of just the index.
- **Token/cost savings modeled**: system-prompt rules drop 73->14 files (80.8% reduction), ~73K->~35K tokens (52.1% reduction), freeing 18.8 percentage points of a 200K window; monthly savings at 100 sessions estimated at ~$57 (Opus), ~$11 (Sonnet), ~$1 (Haiku). For external projects stacking their own rules, savings range 26-47% depending on project size (small to enterprise).
- **5-phase migration**: Week 1 update self-install.sh + add `standard-core` profile flag; Week 1 document contextual-loading gateway pattern; Week 2 self-hosted validation (10 tasks, compare vs full profile, quality must not drop >5%, hallucination must not rise >10%); Week 2-3 external-project validation; Week 3 roll out `standard` as `cos init` default.
- **8-item risk table** — top risk (rule not loaded when needed) mitigated by RULES-COMPACT always containing a compressed summary + Read-tool fallback; explicitly notes self-hosted `full` profile is unaffected (Risk #4: NONE/NONE).

## Relations & where used

- Directly extends `rules/self-install.sh`'s existing efficiency-profile mechanism (`lean`/`standard`/`full`) described alongside in `rules.md`.
- Backed by `tests/behavior/test_rules_consolidation.py` (42 existing tests) plus a proposed new `test_rules_consolidation_plan.py`.
- Appendix A lists 13 rules with missing contextual triggers in `cognitive-os.yaml` that must be added as part of rollout: `broken-window-policy`, `component-classification`, `dogfooding`, `hook-security-profiles`, `infra-health`, `library-selection`, `model-compatibility`, `os-vs-project`, `plan-first`, `pre-commit-gate`, `prompt-composition`, `result-management`, `supply-chain-defense`.

## Status / caveats

- **Status: Proposed / "Implementation-ready"** — this is a plan, not a description of the currently-live rule-loading state. It should not be read as authoritative on the *current* rule count or loading behavior.
- **Direct numeric conflict with `rules.md`** (same batch, same directory): this plan's baseline states 73 total rule files with 14 proposed as always-loaded (~35K tokens after consolidation, ~73K before). `rules.md` instead describes the *current, already-implemented* state as 16 core rules always-loaded out of 150+ total rules, reducing tokens from ~93K to ~21K. The two documents disagree on total rule count (73 vs 150+), core-rule count (14 vs 16), and both the before-token figure (73K vs 93K) and after-token figure (35K vs 21K). This is flagged for operator triage rather than reconciled here — it is unclear whether `rules.md` describes a later/different state (post-plan, with more rules added and a different core set chosen) or whether the two documents are simply out of sync.
- The document self-corrects mid-text ("Wait -- the 14 includes RULES-COMPACT...") — left as-is per faithfulness requirement, but is a sign the source itself was not fully proofread.
- Section 3's table is explicitly acknowledged in-source as internally over-numbered ("shows 90 on-demand entries but the actual count... is 59") with a stated reconciliation note that the table lists package-sourced rules exhaustively beyond the 59 on-demand count.
