# Self-Improvement Protocol

## When to Run `/self-improve`

| Trigger | Condition | Action |
|---------|-----------|--------|
| Scheduled | Weekly (Monday, after `/agent-kpis`) | Run `/self-improve` |
| KPI threshold | `first_pass_success_rate < 0.70` | `kpi-trigger.sh` flags it |
| High iteration count | `avg_iterations > 3` in a session | `kpi-trigger.sh` flags it |
| Session failures | 3+ failed tasks in one session | `session-learning.sh` flags it |
| Error recurrence | Same error pattern 5+ times across sessions | `/error-analyzer` recommends it |
| Manual | User invokes `/self-improve` | Always allowed |

## What Can Be Auto-Applied

### AUTO (no human approval needed)

These changes are safe to auto-apply because they are additive and do not modify core behavior:

| Category | Examples |
|----------|----------|
| Template updates | Add pre-count grep to rebranding checklist, add mandatory first step to migration template |
| Acceptance criteria additions | Add new criteria to `rules/acceptance-criteria.md` |
| Model routing changes | Update routing table in `rules/model-routing.md` based on performance data |
| Prompt template refinements | Add learned patterns to `templates/*.md` |
| KPI threshold adjustments | Minor threshold tuning (within 10% of current) |

### HUMAN APPROVAL REQUIRED

These changes modify core behavior and must be reviewed:

| Category | Why |
|----------|-----|
| Rule rewrites | Rules affect ALL agent behavior globally |
| Skill rewrites | Skills define agent capabilities; bad rewrites break workflows |
| Hook modifications | Hooks run on every tool use; bugs cause cascading failures |
| New rule creation | New rules add enforcement that may conflict with existing ones |
| Threshold changes > 10% | Large threshold changes may cause unexpected behavior |
| Removal of any check/gate | Removing safety checks is inherently risky |

## How Improvements Are Versioned

1. Each improvement is a separate git commit with a conventional message:
   ```
   improve(self-improve): {description of change}

   Pattern detected: {pattern description}
   Data source: {metrics file}
   Expected impact: {improvement description}
   ```

2. Commits are tagged with `self-improve/{date}` for easy rollback grouping

3. The improvement commit hash is logged in `metrics/kpi-history.jsonl` alongside the KPI snapshot

## How to Roll Back a Bad Improvement

### Automatic Rollback
If `/cognitive-os-test` fails after an auto-applied improvement:
1. The improvement is immediately reverted via `git revert`
2. The failed improvement is logged to `metrics/improvement-blocklist.jsonl`
3. Future `/self-improve` runs skip improvements matching the blocklisted pattern

### Manual Rollback
1. Find the improvement commit: `git log --oneline --grep="improve(self-improve)"`
2. Revert: `git revert {commit-hash}`
3. Add to blocklist: append pattern to `metrics/improvement-blocklist.jsonl`

### Blocklist Format
```json
{
  "timestamp": "2026-03-22T12:00:00Z",
  "pattern": "add pre-count to rebranding",
  "target_file": "templates/rebranding-checklist.md",
  "reason": "caused false positives in non-rebranding tasks",
  "reverted_commit": "abc1234"
}
```

## Safety Guards

1. **Max improvements per run**: Controlled by `self_improvement.max_auto_improvements` in `cognitive-os.yaml` (default: 5)
2. **Test gate**: After applying improvements, MUST run `/cognitive-os-test`. If tests fail, revert ALL changes from this run.
3. **No destructive changes**: Self-improve NEVER deletes rules, skills, or hooks. It only adds or modifies.
4. **Improvement cooldown**: At most 1 self-improve run per 24 hours (unless manually invoked)
5. **Data minimum**: Requires at least 10 data points before proposing improvements. With < 10 entries, only report patterns without proposing.

## Integration with Session Lifecycle

```
Session Start
    |
    v
[session-init.sh] -- Check for .self-improve-recommended flag
    |                  If flagged: inject "Consider running /self-improve" into context
    v
... (normal session work) ...
    |
    v
[session-learning.sh] -- Capture session errors, failed skills, iteration counts
    |
    v
[kpi-trigger.sh] -- Calculate KPI snapshot, check thresholds, write flag if needed
    |
    v
Session End
```

## Metrics Files

| File | Purpose | Written by |
|------|---------|------------|
| `metrics/kpi-history.jsonl` | KPI snapshots over time | `kpi-trigger.sh` |
| `metrics/session-learnings.jsonl` | Per-session error summaries | `session-learning.sh` |
| `metrics/improvement-blocklist.jsonl` | Failed improvements to skip | `/self-improve` rollback |
| `metrics/.self-improve-recommended` | Flag file for next session | `kpi-trigger.sh` |
