---
name: primitive-harvester
description: 'Use when you need this Cognitive OS skill: Classify whether a conversation
  should become a reusable agentic primitive, improve an existing primitive, use an
  existing primitive, become documentation only, or be discarded.; do not use when
  a narrower skill directly matches the task.'
user-invocable: true
version: 1.0.0
last-updated: 2026-05-02
audience: both
tags:
- meta
- primitives
- skills
- automation
- governance
summary_line: Turn repeatable high-value conversation recipes into governed primitive
  proposals.
platforms:
- codex
- claude-code
- generic-cli
prerequisites:
- python3
routing_patterns:
- pattern: \bprimitive[- ]?harvester\b
  confidence: 0.95
- pattern: \bclassify\s+conversation\s+(as\s+)?primitive\b
  confidence: 0.8
- pattern: \bharvest\s+primitive\b
  confidence: 0.75
triggers:
- primitive-harvester
- /primitive-harvester
- Primitive Harvester
- Turn repeatable high-value conversation recipes into governed primitive proposals
---
<!-- SCOPE: both -->
# Primitive Harvester

Use this skill when a conversation starts producing a repeatable workflow,
operator checklist, scriptable safety sequence, or reusable governance pattern.
The harvester is advisory: it classifies and plans, but it does not mutate the
repo by itself.

## Decision classes

- `CREATE_PRIMITIVE`: create a new skill/script/hook/docs/tests bundle.
- `IMPROVE_EXISTING`: extend an existing primitive instead of duplicating it.
- `USE_EXISTING`: invoke the existing primitive; do not create a new artifact.
- `DOCUMENT_ONLY`: preserve the decision/tradeoff as ADR/docs, no executable.
- `DISCARD`: keep as ordinary conversation or Engram learning.

## Run

```bash
python3 scripts/cos_primitive_harvester.py \
  --repo "$PWD" \
  --conversation-file /path/to/conversation.txt \
  --json
```

For a short excerpt:

```bash
python3 scripts/cos_primitive_harvester.py --repo "$PWD" --text "..." --json
```

## Promotion rule

Promote only when the workflow is:

```text
repeatable + risky/valuable + verifiable + portable
```

If the repo already has a matching primitive, improve or use that primitive
instead of creating a duplicate.

## Required follow-up for CREATE/IMPROVE

1. Write or update the listed artifacts.
2. Before promoting any emitted primitive, run `/primitive-authoring` and the classifier on each exact artifact:

   ```bash
   python3 scripts/primitive_scope_classifier.py \
     --project-dir . \
     --paths <artifact> \
     --fail-contradictions \
     --fail-low-confidence
   ```
3. Add or update `manifests/primitive-consumer-availability.yaml` and `manifests/primitive-behavior-evidence.yaml` for every persistent primitive.
4. For every `SCOPE: both` artifact in the plan, run `scripts/cos-portability-proof-scaffold --artifact <artifact>` instead of inventing a portability filename.
5. Add behavior tests and specialize each scaffolded red-team portability test with a falsification probe.
6. Run `scripts/cos-scope-both-portability-audit --strict --no-write` and `scripts/cos-scope-projection-audit --strict --no-write`.
7. For consumer-visible primitives, run `scripts/cos-scope-projection-audit --run-install-smoke --strict --no-write`, `scripts/cos-install-projection-audit --json`, and check `scripts/cos status --portability`.
8. Validate with the emitted validation plan.
9. Land through the governed merge queue.
10. Save the decision/discovery to Engram.

## Contextual Trigger

Keywords: convert conversation to primitive, this should be automatic,
crear skill, crear primitiva, no receta manual, harvester, classify primitive,
descartar conversación, mejorar skill existente, usar primitiva existente.
