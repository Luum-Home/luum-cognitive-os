---
adr: 325
title: AI Resource Economy, Budget Preflight, and Graceful Degradation
status: accepted
implementation_status: partial
date: '2026-05-15'
supersedes: []
superseded_by: null
implementation_files:
- manifests/ai-resource-economy.yaml
- scripts/ai_resource_economy_audit.py
- scripts/ai-resource-economy-audit
- scripts/ai_budget_preflight.py
- scripts/ai-budget-preflight
- rules/language-token-economy.md
- lib/taximeter.py
- hooks/context-budget-meter.sh
- hooks/token-budget-monitor.sh
- tests/unit/test_ai_resource_economy.py
- tests/unit/test_taximeter.py
- tests/unit/test_rate_limit_protection.py
- tests/contracts/test_context_budget_enforcement.py
- tests/red_team/portability/test_ai_budget_preflight.py
- tests/red_team/portability/test_ai-budget-preflight.py
- tests/red_team/portability/test_ai_resource_economy_audit.py
- tests/red_team/portability/test_ai-resource-economy-audit.py
- tests/red_team/portability/test_language-token-economy.py
tier: project
classification_basis: resource scarcity, model rate limits, language token overhead, public history hygiene, and repeated validation loops require explicit budget ledgers, preflight estimates, local fallback, and degradation rules instead of relying on agent discipline.
partial_remaining: 'partial ADR-325 implementation: manifest/audit/preflight/language-token rule and Phase 2 taximeter exist; Phase 3 has initial context-budget resource-ledger emission and token-budget ledger reads. Remaining scope is subagent-budget ledger integration, provider actual-cost ingestion, ledger normalization/deduplication, preflight threshold enforcement, local fallback routing, and CI ratchets.'
partial_remaining_basis: manual Wave 5 slice reconciliation
tags:

- ai-resource-economy
- token-budget
- budget-preflight
- language-token-economy
- anti-loop
- degradation
---

# ADR-325 — AI Resource Economy, Budget Preflight, and Graceful Degradation

## Status

Accepted. Partial implementation starts with a manifest, audit, preflight CLI, and language-token-economy rule. Phase 3 now has an initial bounded hook path: `context-budget-meter` emits ADR-325 resource ledger rows and `token-budget-monitor` consults that ledger for hourly token enforcement. Provider-specific actual-cost ingestion and broader hook coverage remain follow-up phases.

## Context

Agentic AI work consumes scarce model capacity. Long sessions, repeated full-suite validation, unnecessary frontier-model calls, and multilingual duplication can turn normal maintenance into expensive or rate-limited work. The risk is not only monetary: when providers ration capacity, agents may degrade quality, stop mid-task, or loop across retries without noticing the economic failure mode.

The SO already has context budgets, efficiency profiles, model routing, result truncation, and token/rate hooks. Those controls are necessary but not sufficient. Budgets are partly declarative, cost ledgers are not uniform across session/agent/task, and preflight estimation is not mandatory before expensive work.

Spanish remains the user's language for collaboration. Cost optimization must not force the user into English. The correct optimization layer is internal representation: compact fields, memory-first retrieval, summaries, deterministic scripts, and avoiding duplicate Spanish/English prose unless requested.

## Decision

Introduce an explicit **AI Resource Economy** control plane with five phases:

1. **Taximeter ledger** — every AI-consuming work unit should be representable as JSONL with `session_id`, `agent_id`, `task_id`, `model`, `tokens_in`, `tokens_out`, `estimated_cost_usd`, `actual_cost_usd`, `retry_count`, `tool_calls`, and `reasoning_effort`.
2. **Budget preflight** — before expensive tasks, estimate context size, file count, expected agents, expected tests, cost, and loop risk. If the estimate is high, degrade: split, use cheaper models, search locally first, ask for confirmation, or plan without execution.
3. **Language token economy** — preserve Spanish for the user while keeping internal artifacts compact and structured. Long transcripts are summarized before analysis; memory/local search precedes re-reading large histories.
4. **Local/open-source fallback** — grep, parsing, classification, inventories, report generation, mechanical audits, and preliminary summaries should use scripts, deterministic rules, or local models when available before spending frontier-model calls.
5. **Anti-loop / anti-slop** — cap iterations per front, stop after the same failure repeats, regenerate stale artifacts once, classify repeat failures as real contracts, and avoid full-suite reruns until the cause is narrowed.

The canonical machine-readable policy is `manifests/ai-resource-economy.yaml`. Enforcement begins as audit/preflight and can graduate to hooks once the ledger is stable.

## Consequences

### Positive

- Resource controls become inspectable and testable instead of conversational advice.
- Spanish collaboration remains first-class without wasting tokens internally.
- Expensive tasks get an explicit preflight and degradation path.
- Repeated validation loops become diagnosable economic incidents.
- Public-facing work can distinguish product-quality artifacts from internal churn.

### Negative / trade-offs

- More metadata must be maintained.
- Early estimates are approximate until provider actual-cost APIs/events are normalized.
- Strict blocking must be phased in carefully to avoid stopping urgent repairs.
- Local fallback can be less semantically rich than frontier reasoning and must not be used for judgments that require architectural review.

## Alternatives rejected

- Rely only on provider rate limits: rejected because provider limits trigger after waste has already occurred and do not explain what to degrade.
- Force English-only work to reduce tokens: rejected because it harms the user's workflow and solves the wrong layer; internal compactness is the appropriate optimization.
- Use only frontier models for classification and summaries: rejected because mechanical tasks are cheaper, more reproducible, and more auditable as local scripts.
- Run full validation repeatedly until green: rejected because repeated full-suite runs hide stale-artifact loops and waste scarce capacity.

## Verification

```bash
scripts/ai-resource-economy-audit --strict --json
scripts/ai-budget-preflight --task "classify primitive scope debt" --paths manifests/ai-resource-economy.yaml --expected-agents 1 --expected-tests 2 --json --fail-block
.venv/bin/python -m pytest tests/unit/test_ai_resource_economy.py -q
```

## Phased implementation plan

1. **Phase 1 — documented control plane**: ADR, manifest, audit, preflight CLI, and language-token-economy rule.
2. **Phase 2 — ledger unification**: normalize existing cost events into `.cognitive-os/metrics/ai-resource-ledger.jsonl` and backfill session/agent/task identifiers where available.
3. **Phase 3 — hook enforcement**: connect preflight and ledger thresholds to `token-budget-monitor`, `context-budget-meter`, and `subagent-budget-enforcer`. Initial slice complete: context-budget events now emit resource ledger rows, and token-budget monitoring counts recent resource-ledger tokens alongside legacy cost events.
4. **Phase 4 — local fallback routing**: route mechanical audits and summaries to deterministic scripts/local models before frontier models.
5. **Phase 5 — ratchets**: fail CI on missing ledger fields, repeated unbounded loops, and public-history hygiene violations before public release.
