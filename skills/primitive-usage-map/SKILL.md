<!-- SCOPE: os-only -->
---
name: primitive-usage-map
description: "Use when you need this Cognitive OS skill: Map which Cognitive OS skills, hooks, rules, tests, docs, workflows, and configs reference each primitive or script.; do not use when a narrower skill directly matches the task."
invoke: /primitive-usage-map
tag: os-only
model: haiku
audience: os-dev
effort: haiku
summary_line: Static primitive consumer map for scripts, hooks, skills, and rules.
version: "1.0.0"
platforms: ["claude-code", "codex"]
prerequisites: []
routing_patterns:
  - pattern: '\bprimitive[- ]?usage[- ]?map\b'
    confidence: 0.95
  - pattern: '\bmap\s+primitive\s+usage\b'
    confidence: 0.85
  - pattern: '\bwhich\s+skills\s+(reference|use)\s+primitive\b'
    confidence: 0.75
---

# Primitive Usage Map

## Purpose

Use this skill to answer questions such as:

- Which skills use each Python script?
- Which scripts are referenced only by tests or docs?
- Which primitives have no visible static consumer?
- Where should a missing skill, hook, rule, or workflow be added before a reducer archives anything?

The backing script is `scripts/primitive_usage_map.py`. It is static reachability,
not runtime execution coverage.

## Commands

Map Python scripts:

```bash
python3 scripts/primitive_usage_map.py --target-family scripts
```

Map other primitive families:

```bash
python3 scripts/primitive_usage_map.py --target-family hooks
python3 scripts/primitive_usage_map.py --target-family skills
python3 scripts/primitive_usage_map.py --target-family rules
```

Write custom report files:

```bash
python3 scripts/primitive_usage_map.py \
  --target-family scripts \
  --json-out docs/reports/primitive-usage-map-scripts.json \
  --md-out docs/reports/primitive-usage-map-scripts.md
```

## Interpretation

- `without_skill_consumer` means no `SKILL.md` mentions the target.
- `without_any_consumer` means no scanned skill, hook, rule, test, doc, workflow,
  config, or script mentions the target.
- A static consumer is not proof of runtime use. Pair this report with hook timing,
  row audit, claim proof audit, and behavior tests.

## Contextual Trigger

Use when the user says: qué skills usan scripts, primitive usage, coverage de primitivas, scripts sin skill, mapa de dependencias entre primitivas.
