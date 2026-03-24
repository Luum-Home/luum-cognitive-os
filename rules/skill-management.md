# Skill Management — Unified Protocol

## Loading Priority

1. **Project skills** (`.claude/skills/`) — highest priority, project-specific
2. **Global skills** (`~/.claude/skills/`) — shared across projects
3. **Auto-generated skills** — created when coverage is missing

## Skill Registry

- `/skill-registry` scans all skills and creates `.atl/skill-registry.md`
- Registry saved to Engram for cross-session access
- Sub-agents consult registry to know which skills to load
- Version tracked in frontmatter (`name`, `version`, `last-updated`, `auto-generated`, `tech`)
- Refresh when Context7 shows breaking changes; auto-generated skills can be regenerated safely; manual skills NEVER auto-overwritten

## Auto-Loader (session start)

1. Read `.claude/detected-stack.json` (from stack-detector.sh)
2. Verify skills exist per detected technology
3. If missing: suggest generation (do NOT auto-generate without user confirmation)
4. Auto-generated skills marked with `auto-generated: true` in frontmatter
5. After generation, run `/skill-registry` to update index

## Skill Adaptation (always active)

### Before executing any skill
1. Search feedback: `mem_search(query: "skill-feedback/{skill-name}", project: "{project}")`
2. If feedback exists, read full content and adapt execution

### After skill failure
Save feedback to Engram immediately:
```
mem_save(title: "Skill feedback: {name} failed", type: "discovery",
  project: "{project}", topic_key: "skill-feedback/{skill-name}",
  content: "**Skill**: {name}\n**Context**: ...\n**Error**: ...\n**Correction**: ...")
```

### After recovery (with prior failures)
Update feedback to note the successful approach.

### Auto-improvement trigger (3+ failures)
1. Announce: "Skill {name} has failed {N} times. Proposing improvements."
2. Read ALL failure observations
3. Invoke `/skill-creator` with failure context
4. Run `/skill-registry` to update index

## System Layers

```
Registry (knows what exists) -> Engram (remembers what worked)
  -> Hooks (detect failures in real-time) -> skill-creator (applies improvements)
```
