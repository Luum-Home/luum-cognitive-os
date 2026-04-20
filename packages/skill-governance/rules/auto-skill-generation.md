<!-- SCOPE: both -->
# Auto-Skill Generation Protocol

## What It Does

When a sub-agent completes a complex task successfully, the `auto-skill-generator.sh` PostToolUse hook
automatically creates a reusable SKILL.md from the task description and result summary.

## Complexity Detection

A task is considered "complex enough" for skill generation when:

1. **Structured detection**: `num_tool_uses >= 10` in the agent response
2. **Heuristic detection** (fallback): Response text > 8000 characters, OR > 3000 characters with
   evidence of file creation or bug fixing

AND the task completed successfully (no error in response).

## Generated Skill Location

All auto-generated skills are saved to:
```
.claude/skills/auto-generated/{skill-slug}/SKILL.md
```

## Skill Quality

Auto-generated skills are **drafts**. They capture the procedure but may need refinement.

| Quality Level | Action |
|---------------|--------|
| Draft (auto-generated) | Usable as reference, may need editing |
| Refined (after /optimize-skill) | Production-ready with user feedback incorporated |
| Manual (hand-written) | Highest quality, created by /skill-creator |

## Lifecycle

```
Complex agent task completes successfully
    |
    v
auto-skill-generator.sh detects complexity
    |
    v
SKILL.md created in .claude/skills/auto-generated/{slug}/
    |
    v (user reviews or skill is invoked)
Feedback captured by skill-feedback-tracker.sh
    |
    v (if 3+ failures or user runs /optimize-skill)
Skill refined by skill-creator
```

## Frontmatter

Auto-generated skills always include:
```yaml
auto-generated: true
generated-from: {original task description}
generated-at: {ISO timestamp}
version: 0.1.0
```

## Integration Points

| System | Interaction |
|--------|-------------|
| Skill Registry | Auto-generated skills are discoverable via /skill-registry |
| Skill Adaptation | Feedback is tracked; skill improves over time |
| Skill Metrics | Execution metrics tracked like any other skill |
| Error Learning | Failures feed into error-learning.jsonl |

## Opt-Out

To prevent skill generation for a specific task, set `NO_AUTO_SKILL=true` in the environment.
The hook checks this variable and exits early if set.

## Agent Experts Pattern: Act, Learn, Reuse

> Source: "Tactical Agentic Coding" by IndyDevDan (agenticengineer.com)

Auto-skill generation implements the **Agent Experts** three-step workflow:

### Act
The agent executes a task using available tools and context. This is normal sub-agent execution — no special handling needed.

### Learn
After successful completion, the system evaluates whether the task was complex enough to extract reusable knowledge:
- **Complexity threshold**: 10+ tool uses OR 8000+ character response
- **Success requirement**: task completed without errors
- If both conditions met: extract the procedure into a structured SKILL.md

### Reuse
The generated skill becomes available for future similar tasks:
- Discoverable via CATALOG.md and skill registry
- Loaded on-demand when a matching task appears
- Improves over time via skill-adaptation protocol (feedback from failures)

### The Virtuous Cycle

```
Agent executes complex task successfully (ACT)
    |
    v
Procedure extracted into SKILL.md (LEARN)
    |
    v
Future similar task loads the skill (REUSE)
    |
    v
Skill guides faster, more accurate execution (ACT — improved)
    |
    v
Feedback refines the skill (LEARN — improved)
    |
    v
Next execution is even better (REUSE — improved)
```

Each cycle through Act/Learn/Reuse makes the agent more capable. This is leverage point 11 (self-improving systems) in action.

### Relationship to PITER

The Agent Experts cycle operates at the **skill level** (improving reusable capabilities over time), while PITER operates at the **task level** (self-correcting within a single task execution). They are complementary:

- PITER ensures the current task succeeds (refine until done)
- Agent Experts ensures future similar tasks succeed faster (extract and reuse)

## Cleanup

Auto-generated skills that are never used can be safely deleted:
```bash
rm -rf .claude/skills/auto-generated/{skill-slug}/
```

Skills with `auto-generated: true` are never prioritized over manually created skills
with the same purpose.
