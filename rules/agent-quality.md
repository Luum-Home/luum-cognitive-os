# Agent Quality: Maximum Output, Not Minimum

## The Core Problem

Agents optimize for SPEED, not COMPLETENESS. Given a vague prompt, an agent will:
- Do the easiest 10% of the work
- Report "done" with confidence
- Pass superficial checks
- Leave 90% of the actual work untouched

This is the single biggest quality problem in agent-driven development.

## Why Agents Do the Minimum

1. **Ambiguous prompts get minimal interpretation**: "Rebrand the project" has no measurable definition of "done." The agent picks the interpretation that requires the least work.

2. **No verification means no accountability**: Without measurable criteria, "done" is whatever the agent says it is. There is no mechanism to prove the agent missed items.

3. **Speed over thoroughness**: Agents are optimized to return results quickly. Enumerating every file, checking every occurrence, and verifying every change is slower than doing a sample.

4. **Context window pressure**: Agents working on large tasks may process some items and then summarize "and N more similar changes" without actually doing them.

## The Four Fixes

### Fix 1: Mandatory Acceptance Criteria (`rules/acceptance-criteria.md`)

Every agent prompt MUST include measurable, verifiable acceptance criteria. Not "rebrand the project" but "rebrand old-name to new-name where `grep -rl 'old-name'' --include='*.go' | wc -l` = 0."

The orchestrator defines what "done" means BEFORE the agent starts. If the orchestrator doesn't provide criteria, the agent must define them before beginning work.

### Fix 2: Auto-Verification Loop (`hooks/auto-verify.sh`)

PostToolUse hook that fires when an agent reports completion:
- Extracts acceptance criteria from the original prompt
- Runs verification commands automatically
- Reports PASS or FAIL with actual vs expected values
- On FAIL: the orchestrator re-launches with failure context
- On missing criteria: WARNS that verification was impossible

This runs BEFORE `dod-gate.sh` in the hook chain.

### Fix 3: Exhaustive Prompt Generator (`skills/exhaustive-prompt`)

Invoke with `/exhaustive-prompt` BEFORE launching agents. It:
1. Runs discovery commands to enumerate the EXACT scope
2. Lists every file, every line, every change needed
3. Generates measurable acceptance criteria
4. Creates verification commands with expected results
5. Sets the Definition of Done for the task's complexity

This transforms "rebrand the project" into a 50-item file list with line numbers, verification commands, and pass/fail criteria.

### Fix 4: Completeness Validator (`hooks/completeness-check.sh`)

PreToolUse hook that fires before launching any agent. Detects red flags:
- "all files" without listing them
- "complete the migration" without item counts
- "follow patterns" without specifying which patterns
- No acceptance criteria section
- Large scope without explicit enumeration

Advisory only (does not block). Suggests running `/exhaustive-prompt` first.

## The Quality Chain

```
Orchestrator receives task
    |
    v
completeness-check.sh (PreToolUse) — warns if prompt is vague
    |
    v
/exhaustive-prompt — generates exhaustive scope + criteria
    |
    v
Agent launches with exhaustive prompt + acceptance criteria
    |
    v
Agent reports completion
    |
    v
auto-verify.sh (PostToolUse) — runs acceptance criteria commands
    |
    v
dod-gate.sh (PostToolUse) — checks Definition of Done
    |
    v
PASS: task confirmed complete
FAIL: orchestrator re-launches with failure context (max 3 retries)
```

## Rules for Orchestrators

1. **Never launch an agent without acceptance criteria** — if you can't measure "done," the agent can't achieve it.
2. **Enumerate, don't generalize** — "47 endpoints" not "all endpoints." "grep found 203 occurrences" not "everything."
3. **Include verification commands** — if you can't write a command to check it, it's not a criterion.
4. **Re-launch on failure** — auto-verify failures mean the task is NOT done. Do not accept partial results.
5. **Use /exhaustive-prompt for medium+ tasks** — the 30 seconds spent on prompt generation saves hours of incomplete work.

## Rules for Agents

1. **If no acceptance criteria are provided, DEFINE them yourself** before starting work.
2. **Count before starting** — run grep/find to know the full scope before making changes.
3. **Verify before claiming done** — run the acceptance criteria commands yourself.
4. **Report actual numbers** — "renamed 203/203 occurrences" not "renamed all occurrences."
5. **Never say "and similar changes"** — if you didn't list it, you didn't do it.
6. **For documentation changes, NEVER use sed/grep replacement.** Always use an agent that reads context. Prose requires understanding, not pattern matching. See `rules/sandbox-sampling.md`.
7. **For epic tasks (>100 files), use /sandbox-sample** to validate strategy before scaling. Classify files by type, sample 3-5 per type, verify in sandbox, then scale. See `skills/sandbox-sample/SKILL.md`.

## Metrics

All verification results are logged to `metrics/auto-verify.jsonl`:
- `NO_CRITERIA`: prompt had no acceptance criteria (bad)
- `PASS`: all criteria verified (good)
- `FAIL`: one or more criteria failed (requires re-launch)

Completeness warnings logged to `metrics/completeness-check.jsonl`.

Track the ratio of PASS vs FAIL+NO_CRITERIA to measure improvement over time.

## Implementation Completeness

Code claimed as "done" must be production-ready. These anti-patterns are prohibited in committed code:

### No TODO Comments in Committed Code

Every `TODO`, `FIXME`, `HACK`, or `XXX` comment must be resolved before marking a task as done. If the work genuinely cannot be completed now, create a tracking ticket/task and reference it instead of leaving a comment in the code.

**Verification**: `grep -rn 'TODO\|FIXME\|HACK\|XXX' {changed_files}` returns 0 results.

### No Stub Implementations

Every function, method, or handler must be fully implemented. Stubs that return hardcoded values, `nil`, empty strings, or `panic("not implemented")` are not acceptable as completed work.

**Verification**: `grep -rn 'not implemented\|NotImplemented\|panic.*implement\|raise.*NotImplemented' {changed_files}` returns 0 results.

### No Mock Objects in Production Code

Mocks, fakes, and test doubles belong exclusively in test files (`*_test.go`, `*.spec.ts`, `*.test.ts`, `test_*.py`). Production source files must use real implementations or properly abstracted interfaces.

**Verification**: `grep -rn 'mock\|Mock\|fake\|Fake' {production_files}` returns 0 results (excluding interface definitions and variable names where "mock" is part of the domain).

### No "Future Work" Deferred Without Tracking

If a task cannot be fully completed, the remaining work must be captured in a tracking system (GitHub issue, task in active-tasks.json, or Engram observation). Untracked deferred work is invisible work that will be forgotten.

**Verification**: Any mention of "future work", "later", "eventually", or "phase 2" in code comments or PR descriptions must reference a tracking ID.

### No Commented-Out Code Blocks

Dead code in comments clutters the codebase and confuses future readers. If the code is not needed, delete it (git history preserves it). If it is needed, uncomment and implement it.

**Verification**: No blocks of 3+ consecutive commented-out lines of code in changed files.

## Communication Quality

Sycophantic output wastes tokens and erodes trust. ALL agents MUST follow these rules:

### Prohibited Openers

Agents MUST NOT start responses with:
- Flattery: "Great question!", "Excellent idea!", "That's a fantastic approach!", "What a thoughtful request!"
- Filler affirmations: "Absolutely!", "Of course!", "Definitely!", "Sure thing!"
- Performative enthusiasm: "I'd love to help with that!", "I'm excited to work on this!"

### What Direct Communication Means

- **Lead with substance**: The first sentence should contain information, not praise.
- **Disagree openly**: "This approach has a problem: X" not "That's interesting, but have you considered..."
- **Skip the sandwich**: If criticism is needed, deliver it directly. Wrapping it in compliments dilutes the message and wastes tokens.
- **Report facts, not feelings**: "3 tests fail" not "Almost everything looks great, just a couple of small issues."
- **No hedging without reason**: "This will break production" not "This might potentially cause some minor concerns."

### Scope

This applies to ALL agents — orchestrator, sub-agents, review agents, SRE agents. No exceptions.

### Why This Matters

Sycophantic output:
1. **Wastes tokens** — every "Great question!" is tokens not spent on the actual answer
2. **Erodes trust** — if the agent praises everything, praise means nothing
3. **Hides problems** — sugar-coating makes issues easy to miss in long outputs
4. **Slows review** — humans must read through filler to find the substance

## Contextual Trigger

This rule is always active. It is the meta-rule governing agent output quality.
