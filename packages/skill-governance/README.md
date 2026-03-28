# @luum/skill-governance

Skill lifecycle governance — tracking, KPI evaluation, agent bus monitoring, and auto-generation

## Install

```bash
cos install @luum/skill-governance
```

## Components

- `rules/skill-management.md` (rule) -- Unified skill management protocol — loading, adaptation, routing
- `rules/auto-skill-generation.md` (rule) -- Auto-generation of skills from complex agent completions
- `hooks/skill-tracker.sh` (hook) -- Tracks skill execution metrics and feedback
- `hooks/kpi-trigger.sh` (hook) -- Calculates KPI snapshots and triggers self-improvement
- `hooks/agent-bus-monitor.sh` (hook) -- Monitors agent communication bus on session start

## License

Apache-2.0
