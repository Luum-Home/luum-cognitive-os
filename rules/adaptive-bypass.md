<!-- TIER: 2 -->
<!-- SCOPE: both -->
# Adaptive Bypass — Smart Orchestration

## Purpose

The orchestrator should apply governance proportional to task complexity. Orchestrating a typo fix is like hiring a project manager to change a lightbulb.

## The Rule

Before choosing a workflow, the orchestrator MUST:
1. Read `cognitive-os.yaml` for the CURRENT project's `phase` and `efficiency.profile`
2. Classify the CURRENT task's complexity
3. Apply the bypass decision based on BOTH

| Complexity | Signal | Workflow | Orchestration |
|-----------|--------|----------|---------------|
| Trivial | < 3 files, < 20 lines, single obvious fix | Do it directly | None — no delegation, no SDD |
| Small | 1-3 files, single service, clear scope | Delegate if beneficial | Minimal — one sub-agent if needed |
| Medium | Multi-file, new feature, refactor | Plan first, then delegate | Standard — plan + delegation |
| Large | Multi-service, integration, cross-cutting | SDD pipeline required | Full — SDD + squads |
| Critical | Security, payments, data migration | SDD + security review | Maximum — all gates active |

### Phase Modifies the Bypass Threshold

The project phase shifts what counts as "safe to bypass":

| Phase | Bypass Bias | Effect |
|-------|------------|--------|
| reconstruction | Aggressive — bias toward speed | Even small tasks can be done directly |
| stabilization | Moderate | Follow the table above as-is |
| production | Conservative — bias toward governance | Small tasks may still need delegation |
| maintenance | Very conservative | Only trivial tasks bypass; everything else gets review |

### Dynamic Context (per task, not per session)

The bypass decision is evaluated PER TASK, not once at session start. In the same session:
- "Fix the typo on line 42" → trivial, do it directly
- "Add JWT auth to all endpoints" → critical, full SDD

If connected to a ticketing system processing tasks across multiple projects, each task reads its OWN project's `cognitive-os.yaml` to determine phase and profile. The bypass is never global — it is always project-scoped and task-scoped.

### Research Backing

The paper "Evaluating AGENTS.md" (arxiv.org/abs/2602.11988) found that context files REDUCE task success rates and increase costs by 20%+. This validates the adaptive bypass: for trivial tasks, governance context hurts more than it helps. The bypass isn't just about saving tokens -- it's about IMPROVING task success by reducing cognitive noise.

See `docs/research/minimal-context-principle.md` for full analysis.

## Self-Check (mandatory before every task)

> "Is this task so simple that orchestrating it would cost more than doing it?"

If the answer is yes:
1. Skip delegation
2. Skip SDD
3. Do the work directly
4. Apply the Definition of Done criteria for the appropriate complexity level

## What "Trivial" Means

A task is trivial when ALL of these are true:
- Touches fewer than 3 files
- Changes fewer than 20 lines total
- The fix is obvious from the user's description
- No architectural decisions needed
- No cross-service impact
- No security implications

## What "Trivial" Does NOT Mean

- "I think it's simple" (assumption, not evidence)
- "It's just one function" (one function can have blast radius)
- "Quick refactor" (refactors are never trivial)

If in doubt, classify UP (small, not trivial).

## Integration with Existing Rules

| Rule | Integration |
|------|-------------|
| Definition of Done | Trivial DoD: code_compiles + no_lint_errors. That's it. |
| Phase-Aware Agents | Scale-Adaptive Intelligence table already maps complexity to workflow |
| Agent Quality | Adaptive bypass prevents the opposite anti-pattern: over-orchestrating simple tasks |
| Token Economy | Bypassing delegation for trivial tasks saves 2,000-5,000 tokens per task |
| Closed-Loop Prompts | Trivial tasks don't need closed-loop verification — the edit IS the verification |

## Cost Savings

| Task Type | With Full Orchestration | With Adaptive Bypass | Savings |
|-----------|------------------------|---------------------|---------|
| Fix typo | ~3,000 tokens (delegate + verify) | ~200 tokens (direct edit) | 93% |
| Rename variable | ~5,000 tokens (delegate + grep + verify) | ~500 tokens (direct) | 90% |
| Add config value | ~3,000 tokens (delegate) | ~300 tokens (direct edit) | 90% |
| New endpoint | ~15,000 tokens (SDD pipeline) | Same (SDD appropriate) | 0% |

## Contextual Trigger

This rule is always active. It is the FIRST rule evaluated before any task.
