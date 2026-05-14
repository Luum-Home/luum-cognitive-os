<!-- SCOPE: os-only -->
---
name: architecture-map-answer
version: 1.0.0
description: Use when you need a commercial-safe Cognitive OS architecture map from evidence-backed product-answer primitives, avoiding internal tool names and immature claims.
triggers:
  - architecture map
  - mapa del SO
  - mapa de arquitectura
  - commercial architecture
  - arquitectura comercial
user-invocable: true
audience: os-dev
tags:
  - product
  - architecture
  - commercial
  - evidence
  - claim-safety
summary_line: Produce a sanitized commercial architecture map through the ADR-313 architecture_map product answer.
platforms:
  - claude-code
  - codex
  - shell
prerequisites: []
routing_patterns:
  - pattern: "\\b(architecture|arquitectura).{0,40}(map|mapa|commercial|comercial)\\b"
    confidence: 0.95
  - pattern: "\\b(mapa del SO|mapa reducido|agent OS map|cognitive os map)\\b"
    confidence: 0.95
routing_intents:
  - intent: commercial_architecture_map
    description: User wants a concise buyer-safe map of Cognitive OS architecture and how it grows without leaking implementation inventory.
    confidence: 0.92
---

# Architecture Map Answer

## Purpose

Generate a compact, commercial-safe architecture map for Cognitive OS from the
ADR-313 `architecture_map` product-answer primitive.

Use this when the user wants to explain the SO's architecture externally or to a
commercial/product audience without exposing internal tool names, implementation
counts, provider names, or immature runtime claims.

## Fast path

From the SO repository root:

```bash
scripts/cos-product-answer --question-id architecture_map --format markdown
```

If the card is stale or missing:

```bash
scripts/cos-product-answer-refresh --question-id architecture_map
scripts/cos-product-answer --question-id architecture_map --format markdown
```

## Output discipline

- Keep the value-chain structure: team → coding agents → Cognitive OS →
  guardrails/policies/playbooks/memory/evidence → operational trust.
- Use generic labels such as "development tools" or "existing agent tools" in
  public/commercial mode.
- Do not lead with counts of hooks, rules, skills, scripts, manifests, or tests.
- Do not name internal providers, private tools, or immature service surfaces
  unless the user explicitly asks for technical due diligence.
- Keep Mermaid simple: prefer `graph TD` and single-line labels for broad
  renderer compatibility.
- Include unsafe claims and gaps when the answer is used for external copy.

## Adaptation rule

When the SO grows, update these evidence surfaces instead of rewriting chat copy:

1. `manifests/product-question-bank.yaml` — public wording and aliases.
2. `manifests/product-claim-evidence.yaml` — maturity, evidence, and boundaries.
3. Architecture/product docs referenced by the claim evidence.
4. Product-answer cards via `scripts/cos-product-answer-refresh`.

The public categories should stay stable unless product positioning changes.
Implementation details can move underneath those categories.

## Validation

```bash
python3 -m pytest tests/behavior/test_product_answer_cli.py -q
scripts/cos-product-answer --question-id architecture_map --format markdown --no-cache
```
