---
name: adr-tombstone
description: 'Use when you need this Cognitive OS skill: Create or repair neutral
  tombstones for removed ADR numbers; use when an ADR is deleted, purged, superseded
  without replacement text, or ADR numbering has gaps that must stay auditable without
  reusing numbers.; do not use when a narrower skill directly matches the task.'
version: 1.0.0
last-updated: 2026-05-05
user-invocable: true
auto-generated: false
audience: os-dev
tags:
- adr
- tombstone
- governance
- numbering
summary_line: Agentic primitive for creating neutral ADR tombstones while preserving
  ADR numbering integrity.
platforms:
- claude-code
- codex
prerequisites: []
routing_patterns:
- pattern: \badr[- ]?tombstone\b
  confidence: 0.95
- pattern: \b(tombstone|neutraliz\w*)\s+(an?\s+)?ADR\b
  confidence: 0.9
- pattern: \bADR\s*(gap|hole|numbering)\b
  confidence: 0.85
routing_intents:
- intent: adr_tombstone_request
  description: User asks to create or repair neutral tombstones for removed ADR numbers;
    use when an ADR is deleted, purged, superseded without replacement text, or ADR
    numbering has gaps that must stay auditable without reusing numbers.
  confidence: 0.85
triggers:
- adr-tombstone
- /adr-tombstone
- ADR Tombstone
- Agentic primitive for creating neutral ADR tombstones while preserving ADR numbering
  integrity
---
<!-- SCOPE: os-only -->
# ADR Tombstone

This is an **agentic primitive**: the reusable procedure and deterministic tooling for tombstoning ADR records. The ADR files it creates are documentation records, not the primitive itself.

Use this skill when an ADR number must remain reserved but the original decision
text should no longer live in active first-party documentation.

## Boundary

- Primitive: `skills/adr-tombstone/`, `scripts/adr_tombstone.py`, `scripts/cos-adr-tombstone`, and their tests.
- ADR record: `docs/02-Decisions/adrs/ADR-NNN-tombstone.md`, generated or repaired by the primitive.
- Do not confuse the existence of a tombstone ADR with the primitive that manages tombstones.

## Rules

- Never reuse an ADR number for a different decision.
- Prefer a neutral file name: `docs/02-Decisions/adrs/ADR-NNN-tombstone.md`.
- The first heading must match the filename number.
- The tombstone must include the same required ADR sections as normal ADRs.
- Do not include removed integration names or other purged terms in tombstone text.
- Update links from the removed ADR filename to the neutral tombstone filename.
- Validate the full ADR sequence after creating or repairing tombstones.

## Workflow

1. Identify the ADR number and any forbidden terms that must not reappear.
2. Run the deterministic helper:

```bash
scripts/cos-adr-tombstone \
  --number NNN \
  --title "Removed architecture decision" \
  --reason "The original decision content was removed from the active architecture surface." \
  --forbidden-token "term-to-keep-out" \
  --validate-forbidden-tokens
```

3. If only filling a numbering gap, omit `--forbidden-token` and use a reason like:

```text
This ADR number is intentionally reserved so the ADR sequence remains contiguous.
```

4. Validate:

```bash
python3 -m pytest tests/unit/test_adr_tombstone.py tests/contracts/test_adr_numbering_integrity.py -q
```

5. If the task is a full purge, also run the repository-specific no-reference
   contract for the removed surface.

## Output expectations

Report the tombstone path, removed ADR files, updated references, and validation
commands. Do not commit or push unless explicitly asked.
