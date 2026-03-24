# SRE Protocol

## Auto-Repair is ALWAYS ACTIVE

When the SRE agent detects an error, it follows this protocol:

1. **CLASSIFY** the error (crash, connection, OOM, timeout, logic error)
2. **SEARCH** Engram for known fixes: `mem_search(query: "sre-fix {type} {container}", project: "{project}")`
3. If known fix exists AND is safe -> APPLY automatically
4. If known fix exists AND is unsafe -> PROPOSE and wait for approval
5. If new error AND safe action available -> APPLY, then SAVE to Engram
6. If new error AND requires code change -> ANALYZE, PROPOSE, SAVE analysis to Engram
7. **NEVER** apply unsafe actions without explicit human approval
8. **ALWAYS** save the fix to Engram after resolution for future auto-repair

## What Counts as "Safe"

See `.cognitive-os/skills/sre-agent/references/auto-repair-actions.md` for the complete list.

Key principle: if the action is **reversible** and does **not touch data, code, or configuration files**, it is safe.

Safe examples:
- Container restart
- Dependency restart
- Cache service restart
- Disk cleanup (docker system prune)

Unsafe examples:
- Any source code modification
- Database queries or migrations
- Config file changes (.env, docker-compose)
- Environment variable changes
- Message queue operations

## Engram Topic Key Convention

All SRE fixes use this topic key format:
```
sre-fix/{container-name}/{error-type-slug}
```

Analysis reports (for unsafe fixes) use:
```
sre-analysis/{container-name}/{error-type-slug}
```

Incident reports use:
```
sre-incident/{timestamp}
```

## Metrics to Track

The SRE agent should track these metrics over time (saved to Engram):

| Metric | Description | Target |
|--------|-------------|--------|
| MTTD | Mean Time to Detect (from error to detection) | < 2 minutes |
| MTTR | Mean Time to Repair (from detection to fix) | < 5 minutes (safe), < 30 minutes (unsafe) |
| Auto-repair success rate | Fixes applied automatically that resolved the issue | > 90% |
| False positive rate | Errors detected that were not actual issues | < 10% |
| Escalation rate | Errors that required human approval | < 20% |
| Recurrence rate | Same error happening again within 24 hours | < 5% |

## Integration with Other Systems

- **error-learning rule**: SRE fixes feed into the error learning system
- **agent-kpis**: SRE metrics contribute to overall agent KPIs
- **fault-tolerance**: SRE agent is itself fault-tolerant (lock file prevents concurrent runs)
- **skill-adaptation**: SRE skill improves based on fix success/failure feedback
