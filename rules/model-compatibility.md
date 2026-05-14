<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Model Compatibility — Baseline Expectations

## Baseline Model

The Cognitive OS is developed and tested against `claude-opus-4-6` (1M context).
All skills, rules, and hooks assume this model's capabilities as the baseline.

## Minimum Model Requirements

For the Cognitive OS to function correctly, the model must:

1. **Follow multi-step procedural instructions** — Skills are step-by-step. The model must execute them in order without skipping.
2. **Parse YAML configuration** — cognitive-os.yaml drives behavior. The model must read and apply YAML values.
3. **Respect conditional rules** — Phase-aware behavior, contextual triggers, and quality gates depend on if/then reasoning.
4. **Maintain tool-call discipline** — Skills require specific tool sequences (read file, then edit, then test). The model must not shortcut.
5. **Handle structured output** — Test reports, KPI dashboards, and status reports require formatted output.
6. **Context window >= 200K tokens** — Progressive loading assumes at least 200K usable context.

## Model Switch Checklist

When switching from one model to another, run `/cognitive-os-compat-test` and verify:

- [ ] All 8 compatibility tests pass
- [ ] Skill trigger accuracy >= 90% (model correctly identifies which skill to load)
- [ ] Rule compliance >= 95% (model follows rules without prompting)
- [ ] Memory retrieval works (Engram mem_search returns results)
- [ ] Phase-aware behavior is correct (reconstruction vs production rules applied)
- [ ] YAML parsing is accurate (budget values, thresholds read correctly)
- [ ] Auto-refine loop works (failure -> analysis -> retry)
- [ ] Progressive loading stays within token budgets

## Known Model-Specific Behavior

### Claude Opus 4.6 (baseline)
- Handles complex multi-file skills well
- Follows phase-conditional rules reliably
- Good at maintaining tool-call sequences across long contexts
- Occasionally over-delegates when orchestrator rules are strict

### Claude Sonnet 4
- Faster, cheaper — good for implementation and documentation tasks
- May simplify multi-step skills (skip optional steps)
- Skill trigger accuracy slightly lower for ambiguous triggers
- Works well with explicit, short skills (< 50 lines)

### Claude Haiku 3.5
- Best for simple, single-purpose tasks (archiving, doc generation)
- Does NOT reliably follow complex skills (> 30 steps)
- May ignore conditional rules or phase-specific behavior
- Not recommended for: debugging, architecture decisions, multi-file edits
- Skill trigger accuracy drops significantly for auto-triggered skills

## Degradation Signals

Watch for these signs that the current model is struggling:

| Signal | Likely Cause | Action |
|--------|-------------|--------|
| Skills not triggering on matching files | Model ignores CATALOG.md triggers | Simplify trigger descriptions |
| Rules violated without acknowledgment | Model doesn't load contextual rules | Switch to `full` rule loading |
| Wrong phase behavior | Model misreads cognitive-os.yaml | Add phase to system prompt explicitly |
| Budget values ignored | YAML parsing failure | Hardcode limits in rules |
| Auto-refine loops forever | Model can't analyze failures | Reduce max_retries, add human gate |
| Sub-agents ignore instructions | Prompt too complex for model tier | Simplify skill, use higher-tier model |

## Remediation

If a model fails compatibility tests:

1. **Score 6-7/8 (DEGRADED)**: Identify failing tests, add explicit instructions to compensate
2. **Score < 6/8 (BROKEN)**: Do not use this model for orchestration. Consider:
   - Downgrade skill complexity
   - Switch to `full` loading (no progressive optimization)
   - Use the model only for simple tasks (implementation, docs)
   - Route complex work to a higher-tier model via model-routing rules

## Contextual Trigger

- When work relates to Model Compatibility — Baseline Expectations.
