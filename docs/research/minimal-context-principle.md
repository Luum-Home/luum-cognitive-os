# Minimal Context Principle

> Based on: "Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?"
> Paper: https://arxiv.org/abs/2602.11988
> Authors: Gloaguen, Mundler, Muller, Raychev, Vechev (ETH Zurich)
> Documented: 2026-03-27

## Research Findings

The paper evaluated whether repository-level context files (.claude/CLAUDE.md, AGENTS.md, etc.) improve AI coding agent performance. The conclusion is counterintuitive:

**Context files reduce task success rates and increase costs by 20%+.**

Key findings:
1. Task success rates DECLINE when context files are provided vs no context
2. Inference costs increase by over 20%
3. Agents perform broader but less effective exploration with context files
4. Root cause: unnecessary requirements make tasks harder, not simpler
5. Both human-written and AI-generated context files show this effect
6. Recommendation: "human-written context files should describe only minimal requirements"

## Impact on Cognitive OS

### Where the paper applies (individual tasks)

For simple, single-task agent work (fix a bug, implement a feature), the paper is correct: loading 71 rules, architecture descriptions, and workflow instructions makes the agent WORSE, not better. The agent knows how to fix bugs -- adding governance overhead confuses it.

### Where the paper does NOT apply (orchestration)

For multi-agent orchestration, SDD pipelines, and governance across complex workflows, context IS necessary because:
- Without SDD phase definitions, the agent doesn't know the workflow exists
- Without Engram protocol, memory doesn't persist across sessions
- Without cost governance, budgets aren't tracked
- Without phase-aware behavior, production safeguards don't activate

### The nuance

| Task Type | Context Value | Optimal Loading |
|-----------|--------------|-----------------|
| Trivial (fix typo, rename) | Negative -- hurts performance | Zero context preferred |
| Small (single file feature) | Neutral to slightly negative | Minimal (just phase) |
| Medium (multi-file, new feature) | Positive -- prevents errors | Phase + relevant rules |
| Large (multi-service, SDD) | Strongly positive -- orchestration required | Full governance |
| Critical (security, payments) | Essential -- safety gates required | Full + security review |

## Design Directive for Cognitive OS

### The Minimal Context Principle

**Load the MINIMUM context that adds value for the CURRENT task's complexity.**

This means:
1. RULES-COMPACT.md (~2,890 tokens) is the MAXIMUM always-loaded governance context
2. Individual rules load ONLY when contextual triggers match (via contextual-rule-loader.sh)
3. Skills load ONLY when invoked or when the model detects a matching task
4. For trivial tasks, even RULES-COMPACT adds overhead -- the adaptive bypass gives the model permission to ignore governance for trivial work
5. CLAUDE.md should contain ONLY behavioral instructions that cannot be discovered from the codebase (Engram protocol, adaptive bypass permission, phase awareness)

### What NEVER belongs in always-loaded context

Based on the paper's findings, these should NEVER be in CLAUDE.md or RULES-COMPACT.md:
- Project file structure (the model can `find`/`ls` in real time)
- Available commands (the model reads package.json, Makefile, etc.)
- Technology stack description (the model reads source files)
- Architecture diagrams (belong in docs/, loaded on demand)
- Database schema (the model reads schema files directly)
- Deployment instructions (belong in docs/, loaded on demand)
- API documentation (belong in docs/, loaded on demand)

### What DOES belong in always-loaded context

- Behavioral protocols the model can't discover (Engram save triggers, session close protocol)
- Permission grants the model needs (adaptive bypass, delegation rules)
- Phase-awareness (which phase determines which governance level)
- Efficiency profile awareness (so the model knows its own constraints)

### Validation

The efficiency profiles we implemented align with this principle:
- **lean** (~6,000 tokens total): Near-zero context. For experienced users on capable models.
- **standard** (~8,000 tokens total): Minimal governance. Recommended for most users.
- **full** (~142,000 tokens total): Maximum context. For OS development and complex orchestration.

The paper would predict that `lean` users have HIGHER task success rates on simple tasks than `full` users -- which is exactly why the profiles exist.

## Implementation Status

| Principle | Implemented? | How |
|-----------|-------------|-----|
| Minimal always-loaded context | Yes | RULES-COMPACT.md (~2,890 tokens) |
| On-demand rule loading | Yes | contextual-rule-loader.sh |
| On-demand skill loading | Yes | Skills loaded when triggered |
| Adaptive bypass for trivial tasks | Yes | adaptive-bypass rule + hook |
| Efficiency profiles | Yes | lean/standard/full in cognitive-os.yaml |
| Capability-level auto-disable | Yes | 15 hooks with check_capability_level |
| Zero-context option | Partial | lean profile still loads RULES-COMPACT |

## Future Consideration

A true "zero context" mode (capability level 6?) could disable even RULES-COMPACT.md, relying entirely on the model's built-in capabilities. This would match the paper's finding that NO context outperforms context for simple tasks. The trade-off: no Engram memory protocol, no phase awareness, no adaptive bypass permission. Essentially vanilla Claude Code.

## Sources

- [Paper: Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988) -- ETH Zurich, 2025
- [Anthropic Agent Skills Standard](https://docs.anthropic.com/en/docs/claude-code/skills) -- December 2025
- [Skills.sh](https://skild.sh/) -- On-demand skill loading model
