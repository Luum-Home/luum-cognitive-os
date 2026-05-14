---
name: catalog-full
description: 'Use when the compact Level-1 catalog does not have enough detail. Purpose:
  Load and display the full skills catalog (skills/CATALOG.md) with invocations, sections,
  and audience columns.'
version: 1.0.0
command: /catalog-full
last-updated: 2026-04-16
audience: both
tags:
- catalog
- skills
- context-optimization
summary_line: Load and display the full skills catalog (skills/CATALOG.md) with invocations…
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bcatalog[- ]?full\b
  confidence: 0.95
- pattern: \bfull\s+skills?\s+catalog\b
  confidence: 0.85
- pattern: \bshow\s+(full\s+)?catalog\b
  confidence: 0.75
triggers:
- catalog-full
- /catalog-full
- Catalog Full
- Load and display the full skills catalog (skills/CATALOG
---
<!-- SCOPE: both -->
# Catalog Full

## Purpose

Session-start only loads the compact catalog (`skills/CATALOG-COMPACT.md`, ~2K tokens,
name + 1-line description). When you need the full catalog — invocations, audience
columns, section groupings, loading protocol notes, project-specific skill examples —
invoke this skill to load `skills/CATALOG.md` on demand.

## Trigger

- User asks for the full skills catalog, invocation syntax, or where a skill is grouped.
- The compact catalog does not have enough detail to answer the question.
- User invokes `/catalog-full` directly.

## Inputs

None. The catalog is a static file.

## Protocol

1. Read `skills/CATALOG.md` from the project root.
2. Render the relevant section, or if the user asked a targeted question, extract only
   the rows and notes that match.
3. Do NOT keep the full catalog loaded after the request is answered — unload once the
   specific question is resolved. This keeps Level-1 overhead low.

## Outputs

- The requested section(s) of `skills/CATALOG.md`, or
- A brief answer citing the catalog entries that match the user's question.

## Notes

- The full catalog is ~7K tokens. Only load it when needed.
- If the skill the user is asking about is missing from both `CATALOG.md` and
  `CATALOG-COMPACT.md`, run `python3 scripts/generate_compact_catalog.py` to
  regenerate the compact catalog from SKILL.md frontmatter.
- The compact catalog groups skills by audience (`os`, `os-dev`, `both`, `project`).
  The full catalog groups by theme (Universal, Pre-Development, Caveman, Trail of Bits,
  Project Skills, etc.). Use whichever grouping is more useful for the question.

## Related

- `skills/CATALOG-COMPACT.md` — Level-1, always loaded at session start
- `skills/CATALOG.md` — full catalog with invocations and examples
- `rules/context-optimization.md` — progressive skill loading protocol
- `scripts/generate_compact_catalog.py` — regenerator
