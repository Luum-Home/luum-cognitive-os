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
