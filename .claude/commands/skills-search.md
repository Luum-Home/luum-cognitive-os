---
description: Search skills by keyword — returns matching SKILL.md with full description
argument-hint: <query>
---

# Skills Search: $ARGUMENTS

Search the skill catalog for entries matching the query.

Run:
```bash
grep -l -i "$ARGUMENTS" skills/*/SKILL.md packages/*/skills/*/SKILL.md 2>/dev/null
```

For each match, display:
1. Skill name + path
2. Full `description` field from frontmatter
3. `summary_line` if present
4. Trigger conditions (from body, if documented)

Also consult:
- `skills/CATALOG-COMPACT.md` — for compact one-line summaries
- `skills/CATALOG.md` — for full catalog if present

If no matches, suggest synonyms or broader terms. Do NOT invent skills that don't exist.

**Why this exists**: `CATALOG-COMPACT.md` only has summary_line per skill (~80 chars). Full descriptions are in the individual SKILL.md files. This command expands on-demand so every session doesn't pay the full-catalog token cost.
