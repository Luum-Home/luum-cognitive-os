# Health Monitoring

## Overview

Cognitive OS health monitoring has two layers:

1. **`/cognitive-os-status`** — Full interactive health report (skill, on-demand)
2. **`cognitive-os-health.sh`** — 1-line summary (SessionStart hook, automatic)

## Full Report: `/cognitive-os-status`

Invoke with `/cognitive-os-status`, `/aos-status`, or `/health`.

Checks 17 components and outputs an ASCII table:

| Component | What it checks |
|-----------|---------------|
| Hooks | All .sh files in settings.json exist and are executable |
| Rules | Rule files in `.cognitive-os/rules/` and `.claude/rules/`, RULES-COMPACT.md |
| Skills | Skill dirs in `.cognitive-os/skills/`, CATALOG.md |
| Squads | YAML files in `.cognitive-os/squads/` |
| Agents | Persona .md files in `.cognitive-os/agents/` and `~/.claude/agents/` |
| Metrics | .jsonl files in `.cognitive-os/metrics/`, which have data |
| Phase | Current phase from `cognitive-os.yaml` |
| Budget | Monthly limit from `cognitive-os.yaml` |
| Langfuse | Docker container status |
| LiteLLM | Docker container status |
| NeMo Guardrails | Docker container status |
| Paperclip | Docker container status |
| Engram | Memory system accessibility via `mem_context` |
| Progressive Load | CATALOG.md + RULES-COMPACT.md token counts |
| Templates | Template files in `.cognitive-os/templates/` |
| Workflows | `run.py` + pipeline files in `.cognitive-os/workflows/` |
| Plans | Active plans in `.cognitive-os/plans/` |

Statuses: **OK**, **WARN** (degraded but functional), **FAIL** (broken).

**Skill file:** `.cognitive-os/skills/cognitive-os-status/SKILL.md`

## Quick Check: SessionStart Hook

Runs automatically at session start. Outputs a single line:

```
Cognitive OS: 14/17 OK | Phase: reconstruction | Budget: $0/$200 | Down: langfuse-web, paperclip
```

**Hook file:** `hooks/cognitive-os-health.sh`
**Registered in:** `.claude/settings.json` under `SessionStart`

## Adding New Checks

1. Add the check logic to both `SKILL.md` (as a new step) and `cognitive-os-health.sh` (as a new `check()` call)
2. Increment the total expected in the summary
3. Update this doc with the new component
