<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Cost-Aware Decomposition

## Rule: Break Down Before Spending

Tasks with estimated cost >$1.00 MUST be decomposed before execution. Each sub-task
should cost <$0.50 individually. The orchestrator chooses the cheapest model per sub-task.

## Cost Estimation Before Starting

Use Planning Poker or `CostDashboard.estimate_action_cost()` to estimate before starting:

| Model | ~10K tokens cost | ~50K tokens cost |
|-------|-----------------|-----------------|
| haiku | $0.003 | $0.015 |
| sonnet | $0.036 | $0.18 |
| opus | $0.18 | $0.90 |

## Decomposition Strategies

| Task Type | Decomposition |
|-----------|---------------|
| Complex research | Break into focused queries, not one massive prompt |
| Implementation | One file at a time, not "implement everything" |
| Migration | Batch by service or entity type |
| Refactoring | One pattern at a time |
| Code review | Split by service or module |
| Testing | One test suite or feature at a time |

## Model Selection Per Sub-Task

| Sub-Task | Model |
|----------|-------|
| Architecture decisions, root cause analysis | opus |
| Implementation, specs, testing, verification | sonnet |
| Archiving, formatting, documentation, renaming | haiku |

## The SDD Pipeline IS Decomposition

For medium+ tasks, the SDD pipeline (propose, spec, design, tasks, apply, verify)
naturally decomposes work. Each phase uses its own optimal model per the routing table.
Do not bypass SDD for tasks that would cost >$1.00 as a single agent call.

## Integration

- **Token Economy**: `rules/token-economy.md` defines the 5 principles
- **Model Routing**: `rules/model-routing.md` has the task-to-model mapping
- **Resource Governance**: `rules/resource-governance.md` enforces budget limits
