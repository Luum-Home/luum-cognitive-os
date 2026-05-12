---

adr: 179
title: Auto-Derived Rule Routing for Agent-Instruction Rules
status: accepted
implementation_status: partial
classification_basis: 'initial PoC migrates five high-value rules while rule frontmatter migration remains incomplete'
date: 2026-05-05
supersedes: []
superseded_by: null
extends: [ADR-174]
implementation_files:
  - lib/rule_router.py
  - hooks/rule-router-prompt-suggest.sh
  - hooks/rule-md-routing-validator.sh
  - manifests/rule-routing-coverage.yaml
  - tests/unit/test_rule_router.py
  - tests/contracts/test_rule_router_invariant.py
  - tests/unit/test_rule_md_routing_validator_hook.py
tier: maintainer
tags: [rules, routing, agentic-primitives, hooks, user-prompt-submit, governance]
---

# ADR-179: Auto-Derived Rule Routing for Agent-Instruction Rules

## Status

**Accepted** — 2026-05-05

## Context

ADR-174 closed the skill-router gap by making SKILL.md frontmatter the source
for runtime routing. The same prevention problem exists for rules: COS has many
rule documents under `rules/` and `packages/*/rules/`, but the orchestrator must
usually remember manually which rule to load for a prompt.

Rules are not homogeneous. Some are already enforced by hooks and should not be
suggested as reading context. Others are agent-instruction rules and only help
when the orchestrator loads them before responding. A rule router must therefore
respect the rule's enforcement mode instead of treating every Markdown file as a
candidate.

The 2026-05-05 cross-session collision showed the cost of implicit routing and
implicit ownership. New agentic primitives need declared metadata, runtime
routing, and tests that prevent future hidden backlog growth.

## Decision

Add a rule-routing layer analogous to ADR-174, with rule-specific semantics:

1. `lib/rule_router.py` indexes `rules/*.md` and `packages/*/rules/*.md`.
2. YAML frontmatter defines:
   - `enforcement: hook | agent-instruction | hybrid`
   - `routing_patterns:` for `agent-instruction` and `hybrid` rules
   - `trigger_priority: low | medium | high`
3. `enforcement: hook` rules are deliberately excluded from prompt suggestions
   because their backing hooks already fire automatically.
4. `hooks/rule-router-prompt-suggest.sh` runs on `UserPromptSubmit`, evaluates
   the prompt, logs to `.cognitive-os/metrics/rule-suggestion.jsonl`, and emits
   `additionalContext` only for high-confidence matches.
5. `hooks/rule-md-routing-validator.sh` runs on rule edits and warns when an
   agent-instruction/hybrid rule lacks `routing_patterns:` or when a hook rule
   has a stale hook reference.
6. `manifests/rule-routing-coverage.yaml` records the baseline backlog and acts
   as a ratchet: migrated rules leave the allowlist; new agent-instruction rules
   should not silently increase it.

The initial landing is a PoC migration for five high-value rules:

- `acceptance-criteria`
- `trust-score`
- `adversarial-review`
- `definition-of-done`
- `phase-aware-agents`

## Consequences

### Positive

- The orchestrator receives compact, prompt-specific rule suggestions instead
  of loading the full rules corpus.
- Hook-enforced rules are not double-counted as prompt context.
- New or edited rules have a declared routing contract.
- The rule-routing backlog is explicit and testable.

### Negative

- Rule frontmatter migration remains incomplete; the initial coverage is a PoC,
  not full corpus completion.
- `additionalContext` emitters increase prompt overhead, so ADR-186 should be
  used to cap aggregate context budget before adding many more routers.
- Low-confidence or poorly written patterns can create noisy suggestions.

## Operational Guide

### What changes for the operator

Before this ADR, the orchestrator had to manually recall which rules were relevant for a given prompt, loading the full rules corpus or relying on `[ref-key]` references in `RULES-COMPACT.md`. Hook-enforced rules and agent-instruction rules were not distinguished, leading to duplicate noise when hook-backed rules were loaded as prompt context.

After this ADR:

| Surface | Before | After |
|---|---|---|
| Rule selection | Manual recall or full corpus load | `hooks/rule-router-prompt-suggest.sh` fires on `UserPromptSubmit`; emits `additionalContext` for high-confidence matches only |
| Rule enforcement classification | Implicit | YAML frontmatter `enforcement: hook \| agent-instruction \| hybrid` declared per rule |
| Hook-enforced rules | May appear as prompt context (duplicate) | Excluded from suggestions; their backing hooks already fire automatically |
| Rule migration backlog | Not tracked | `manifests/rule-routing-coverage.yaml` records the baseline and acts as a ratchet |

### What this answers (and what it doesn't)

**Answers:**
- "Which rules are relevant for this prompt?" — The hook emits context for high-confidence matches only; suggestions are logged to `.cognitive-os/metrics/rule-suggestion.jsonl`.
- "Is this rule hook-enforced or agent-instruction?" — Check the `enforcement:` field in the rule's YAML frontmatter.
- "How many rules still need routing frontmatter?" — Read `manifests/rule-routing-coverage.yaml` for the current backlog and ratchet state.

**Does not answer:**
- "Is the routing correct?" — The initial PoC migrates 5 rules; coverage is partial. Low-confidence or poorly written `routing_patterns:` can produce noisy suggestions — check the metrics log for calibration.
- "Are all hook-enforced rules correctly classified?" — `hooks/rule-md-routing-validator.sh` warns on rule edits when a hook rule has a stale hook reference, but does not scan the full corpus.

### Daily operational pattern

1. Normal operation: the hook fires automatically on prompt submission — no manual action needed.
2. When writing a new rule: add YAML frontmatter with `enforcement:` and `routing_patterns:` (for `agent-instruction` and `hybrid` rules). The validator hook warns if these are missing.
3. To migrate an existing rule: add frontmatter; remove its slug from `manifests/rule-routing-coverage.yaml` allowlist to advance the ratchet.
4. To disable suggestions: `DISABLE_HOOK_RULE_ROUTER_PROMPT_SUGGEST=1` (if applicable) or check the hook killswitch.

### Reading guide for cold readers

1. Read `manifests/rule-routing-coverage.yaml` for the current migration state — it shows which rules have been migrated and what the backlog is.
2. The five initially migrated rules (`acceptance-criteria`, `trust-score`, `adversarial-review`, `definition-of-done`, `phase-aware-agents`) in `rules/` are the best examples of correctly structured routing frontmatter.
3. `lib/rule_router.py` is the authoritative routing implementation; `tests/contracts/test_rule_router_invariant.py` defines the invariants.
4. This ADR is deliberately partial (PoC, not full corpus). The ratchet in `manifests/rule-routing-coverage.yaml` is the tool for tracking progress toward full coverage.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Load every rule all the time | Defeats the token-compression goal and creates irrelevant context. |
| Treat all rules as routeable | Hook-enforced rules already execute; routing them as context is duplicate noise. |
| Keep manual references only | The session collision proved manual recall does not scale across agents/sessions. |
| Block rule writes immediately | Too risky while the backlog is large; start advisory and promote after evidence. |

## Verification

```bash
python3 -m pytest \
  tests/unit/test_rule_router.py \
  tests/contracts/test_rule_router_invariant.py \
  tests/unit/test_rule_md_routing_validator_hook.py \
  -q
```
