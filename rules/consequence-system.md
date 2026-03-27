# Consequence System — OKR-Driven Feedback Loop

## Purpose

Closes the loop between measurement and action. Every agent completion is evaluated for consequences based on trust score performance over time.

## Thresholds

| Score Range | Streak | Consequence | Action |
|-------------|--------|-------------|--------|
| >= 85% | 5 consecutive | PROMOTE | Save best-version snapshot, prefer model, log promotion |
| 60-84% | any | MAINTAIN | No change, log only |
| < 60% | 1st occurrence | WARN | Flag for attention, log warning |
| < 60% | 2nd consecutive | DEGRADE | Downgrade model (opus->sonnet->haiku), require human review |
| < 60% | 3rd consecutive | DISABLE | Temporarily disable skill, suggest `/optimize-skill` rewrite |

## How It Works

1. `consequence-evaluator.sh` PostToolUse hook fires after every Agent completion
2. Extracts trust score from Trust Report in agent output
3. Records performance to `.cognitive-os/metrics/consequence-history.jsonl`
4. Evaluates consequence using streak detection
5. Applies action (promote/degrade/disable) and logs result

## OKR Integration

Consequence history feeds into three OKRs:
- **Quality**: Average trust score target >90%
- **Efficiency**: Month-over-month cost reduction target -20%
- **Self-improvement**: Target 0 disabled skills (recurring errors eliminated)

## Re-enabling Disabled Skills

Disabled skills are temporary. After running `/optimize-skill` or manual rewrite, call `ConsequenceEngine.re_enable_skill(name)` to restore the skill.

## Metrics

All events logged to `.cognitive-os/metrics/consequence-history.jsonl`. Use `ConsequenceEngine.format_consequence_report()` for a summary dashboard.

## Integration

| Component | Role |
|-----------|------|
| `lib/consequence_engine.py` | Core logic: evaluate, apply, query |
| `hooks/consequence-evaluator.sh` | PostToolUse hook on Agent |
| `lib/skill_archive.py` | Snapshot storage for promoted skills |
| `lib/model_router.py` | Model selection affected by degradation |
| `rules/trust-score.md` | Trust Report that provides the input score |
| `rules/agent-kpis.md` | OKR targets that define thresholds |
