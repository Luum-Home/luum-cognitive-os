---
name: adr-tombstone
description: 'Use when you need this Cognitive OS skill: Create or repair neutral
  tombstones for removed ADR numbers; use when an ADR is deleted, purged, superseded
  without replacement text, or ADR numbering gaps should stay auditable without
  number reuse. Prefer a narrower skill when it directly matches the task.'
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
    numbering gaps should stay auditable without number reuse.
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

Use this skill when an ADR number remains reserved but the original decision
text should no longer live in active first-party documentation.

## Boundary

- Primitive: `skills/adr-tombstone/`, `scripts/adr_tombstone.py`, `scripts/cos-adr-tombstone`, and their tests.
- ADR record: `docs/02-Decisions/adrs/ADR-NNN-tombstone.md`, generated or repaired by the primitive.
- Distinguish the tombstone ADR record from the primitive that manages tombstones.

## Rules

- Keep each ADR number bound to one decision lineage.
- Prefer a neutral file name: `docs/02-Decisions/adrs/ADR-NNN-tombstone.md`.
- The first heading matches the filename number.
- The tombstone includes the same required ADR sections as normal ADRs.
- Keep removed integration names and other purged terms out of tombstone text.
- Update links from the removed ADR filename to the neutral tombstone filename.
- Validate the full ADR sequence after creating or repairing tombstones.

## Workflow

1. Identify the ADR number and any forbidden terms to keep out of the tombstone.
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
commands. Commit or push only when explicitly asked.
