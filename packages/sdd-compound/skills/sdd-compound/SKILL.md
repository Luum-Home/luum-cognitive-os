---
name: sdd-compound
description: "Extract learnings and compound knowledge after completing an SDD change. Run after sdd-archive to crystallize patterns, update skill routing, and improve future iterations."
allowed-tools:
  - Read
  - Grep
  - Bash
  - mcp__plugin_engram_engram__mem_save
  - mcp__plugin_engram_engram__mem_search
  - mcp__plugin_engram_engram__mem_get_observation
audience: project
---

# SDD Compound — Post-Archive Learning Extraction

## When to Use
After `sdd-archive` completes for any change. The orchestrator should suggest this automatically.

## Steps

1. **Read the archive report**: Search Engram for `planning/{change}/archive-report`
2. **Extract patterns**: Identify what worked well, what failed, what was unexpected
3. **Update skill routing**: If a skill consistently succeeded or failed, note in skill feedback
4. **Save compound knowledge**: Save to Engram under `implementation/{change}/compound`
5. **Suggest improvements**: If process improvements are identified, suggest `/self-improve`

## Output Format

```
COMPOUND REPORT: {change-name}

PATTERNS EXTRACTED:
- [pattern description + where it applies]

SKILL FEEDBACK:
- [skill-name]: [worked well / needs improvement] because [reason]

PROCESS IMPROVEMENTS:
- [suggestion for future iterations]

KNOWLEDGE SAVED:
- [engram topic key]: [what was saved]
```

## Integration with SDD Pipeline

The compound phase extends the SDD dependency graph:

```
proposal -> specs -> tasks -> apply <-> verify -> archive -> compound
```

Each compound report feeds into future SDD cycles, making each iteration more effective than the last.
