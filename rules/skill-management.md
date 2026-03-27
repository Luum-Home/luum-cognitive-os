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

## Skill Routing Table

When the orchestrator receives a task, consult this routing table to select the most appropriate skill:

| Task Type | Primary Skill | Fallback |
|---|---|---|
| New feature | `/sdd-new` (full pipeline) | `/plan-feature` (plan only) |
| Bug fix | `/plan-bug` then implement | `/systematic-debugging` |
| Research/investigation | `/deep-research` | `/eval-repo` (for repos) |
| Code review | `/self-review` | `/sdd-verify` (formal) |
| Security scan | `/semgrep-scan` | `/secret-audit` |
| Performance issue | `/systematic-debugging` | -- |
| Documentation | `/document-feature` | `/doc-sync` |
| Architecture decision | `/sdd-new` with explore | -- |
| Dependency evaluation | `/eval-repo` | `/recommend-library` |
| Test writing | `/test-driven-development` | -- |
| Refactoring | `/sdd-new` (if >5 files) | direct (if <5 files) |
| Infrastructure | `/sre-agent` | -- |
| Skill creation | `/skill-creator` | -- |
| Quality check | `/confidence-check` (pre) | `/self-review` (post) |

Note: This table COMPLEMENTS model-routing (which picks the MODEL). Skill routing picks the SKILL/WORKFLOW.

## System Layers

```
Registry (knows what exists) -> Engram (remembers what worked)
  -> Hooks (detect failures in real-time) -> skill-creator (applies improvements)
```
