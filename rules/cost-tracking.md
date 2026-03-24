# Cost Tracking Protocol

## Per-Agent Cost Awareness
After each sub-agent completes, the skill-metrics-tracker captures:
- Input/output tokens
- Model used
- Duration
- Estimated cost

## Cost Optimization Rules
- Use haiku for simple tasks (archive, document)
- Use sonnet for implementation (apply, test)
- Use opus for reasoning (propose, design, debug)
- If a skill consistently costs >$0.50/run, flag for optimization
- Weekly cost review via /agent-kpis

## Model Selection Matrix

| Task Type | Recommended Model | Max Budget |
|-----------|------------------|------------|
| Documentation, formatting | haiku | $0.05 |
| Code generation, test writing | sonnet | $0.30 |
| Architecture, design, complex debug | opus | $1.00 |
| SDD phases (propose, spec, design) | opus | $1.50 |
| SDD phases (apply, verify) | sonnet | $0.50 |
| SRE auto-repair | sonnet | $0.20 |

## Budget Alerts

When skill-metrics-tracker detects:
- Single run > $1.00: Log warning to Engram
- Single run > $2.00: Flag for immediate review
- Cumulative daily spend > $10.00: Alert user
- Same skill > $0.50 three times in a row: Suggest optimization

## Optimization Strategies

1. **Reduce context**: Only pass necessary artifacts to sub-agents
2. **Model downgrade**: Use sonnet instead of opus for mechanical tasks
3. **Batch operations**: Combine related small tasks into one agent call
4. **Cache results**: Save reusable analysis to Engram instead of re-computing
5. **Progressive detail**: Start with haiku for classification, escalate only if needed
