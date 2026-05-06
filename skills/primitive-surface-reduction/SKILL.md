<!-- SCOPE: os-only -->
---
name: primitive-surface-reduction
description: Plan or apply conservative surface reduction for Cognitive OS agentic primitives; OS source repo only, plan by default.
invoke: /primitive-surface-reduction
tag: os-only
model: sonnet
audience: os-dev
effort: sonnet
summary_line: Plan/apply safe reduction of unused Cognitive OS primitive surface.
version: "1.0.0"
platforms: ["claude-code", "codex"]
prerequisites: []
routing_patterns:
  - pattern: '\bprimitive[- ]?surface[- ]?reduction\b'
    confidence: 0.95
  - pattern: '\breduce\s+primitive\s+surface\b'
    confidence: 0.85
  - pattern: '\bconservative\s+surface\s+reduction\b'
    confidence: 0.75
---

# Primitive Surface Reduction

## Purpose

Use this skill to reduce Cognitive OS primitive surface without surprising a user
project. It wraps `scripts/primitive_surface_reduce.py`, which refuses to run
outside the Cognitive OS source repository.

This is maintainer-only. Do not run this against an installed target project.

## Default command

Plan only:

```bash
python3 scripts/primitive_surface_reduce.py --family hooks --plan
```

Apply only mechanically safe actions:

```bash
python3 scripts/primitive_surface_reduce.py --family hooks --apply-safe
```

## Guardrails

1. Run from the Cognitive OS source repo root.
2. Prefer `--plan` first and inspect `docs/reports/primitive-surface-reduction-latest.md`.
3. Use `--apply-safe` only when the generated action is marked safe.
4. Never delete implementation files manually; the reducer archives safe items under `archive/primitive-surface/`.
5. After applying, run the focused tests:

```bash
python3 -m pytest tests/unit/test_primitive_surface_reduce.py -q
python3 -m pytest tests/unit/test_primitive_gap_workflow.py -q
```

## Related audit

Before reducing a family, inspect static consumers with:

```bash
python3 scripts/primitive_usage_map.py --target-family scripts
```

## Contextual Trigger

Use when the user says: primitive surface reduction, reduce hook surface, archive unused primitives, shrink COS primitive surface, remove dead hooks.
