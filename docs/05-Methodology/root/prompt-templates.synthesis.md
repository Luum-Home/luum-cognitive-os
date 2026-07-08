---
type: methodology-synthesis
source: docs/05-Methodology/root/prompt-templates.md
provenance: "Documents the reusable prompt-fragment library used to compose consistent sub-agent instructions instead of duplicating them across skills."
---

## What it is

A short reference for the Prompt Template Library: centralized, reusable prompt fragments in `.cognitive-os/templates/` that the orchestrator composes into sub-agent prompts, replacing per-skill duplicated instructions.

## Key mechanics

- **Problem solved**: each skill previously embedded its own architecture/testing/error-handling/quality instructions, causing duplication across 30+ skills and drift when standards changed.
- **6 templates** (each 50-100 words): `agent-preamble.md` (phase, architecture standards, memory protocol, ~80w), `quality-gates.md` (build/test/coverage/lint/architecture checks, ~80w), `error-recovery.md` (retry logic, diagnosis, Engram save, escalation, ~70w), `rebranding-checklist.md` (old-name->new-name rules, what to preserve, ~75w), `go-service-context.md` (example framework-specific context, ~90w, meant to be customized per project), `fintech-gates.md` (example industry-specific gates, ~70w, meant to be customized per project).
- **Usage**: via `/compose-prompt task="..."` skill (auto-selects templates by task keywords) or manual composition (read templates, concatenate in order: preamble, context, gates, task description).
- **Composition ordering rule** lives in `.cognitive-os/rules/prompt-composition.md`.
- **Adding a template**: create `.cognitive-os/templates/{name}.md` under 100 words, update the `/compose-prompt` auto-select table, add an entry to `prompt-composition.md`.

## Relations & where used

- The `/compose-prompt` skill and `prompt-composition.md` rule referenced here match `[prompt-composition]` in `RULES-COMPACT.md` under Prompt Engineering, and the global orchestrator instructions' "Sub-Agent Launch" section (`ADR-032`: "pipe draft through `scripts/compose_agent_prompt.py`... when task touches settings.json/lib/*.py/packages/efficiency-profile").
- `go-service-context.md` and `fintech-gates.md` are explicitly labeled as customization examples, connecting to the industry-preset framing in `configurable-quality-gates.md` (fintech/healthcare/ecommerce presets).

## Status / caveats

- Very short source document (47 lines) — essentially a pointer/reference page rather than a deep explainer; the actual composition logic lives in `.cognitive-os/rules/prompt-composition.md` and `scripts/compose_agent_prompt.py`, neither of which is included in this source.
- Not a pure index/stub (it explains the problem, the mechanism, and the extension procedure), so it was synthesized rather than skipped, but readers needing the full composition algorithm must follow the cross-reference.
