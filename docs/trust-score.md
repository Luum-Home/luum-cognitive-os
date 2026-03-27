# Trust Score System

## The Problem: Why Agents Overclaim

AI agents have a completion bias -- they're optimized to say "done" and move on. This creates a trust deficit:

1. **The "LGTM" problem**: Agent says "I fixed it" without running tests. Human finds it broken.
2. **The confidence illusion**: Agent claims 100% confidence. Human knows that's impossible for non-trivial work.
3. **The missing context**: Agent doesn't mention what it DIDN'T check, leaving the human to discover gaps.
4. **The asymmetric cost**: Agent moves on to the next task. Human spends 30 minutes verifying.

After being burned a few times, humans stop trusting agent output entirely -- even when the agent DID do good work. This is the "boy who cried wolf" dynamic.

## How Trust Score Works

Every agent completion includes a Trust Report with:

1. **A numeric score (0-100)** calculated from four components
2. **Evidence list** showing what was verified and how
3. **Uncertainty list** (mandatory -- at least one item)
4. **Human verification checklist** with specific actions

### The Four Components

| Component | Weight | Measures |
|-----------|--------|----------|
| Verification Evidence | 40% | Did the agent run commands and show output? |
| Acceptance Criteria | 30% | Were measurable criteria defined and met? |
| Self-Awareness | 20% | Did the agent admit what it's unsure about? |
| Proportionality | 10% | Is the solution proportional to the problem? |

### Score Thresholds

| Range | Meaning | Human Action |
|-------|---------|--------------|
| 90-100 | High confidence | Minimal review needed |
| 70-89 | Medium confidence | Spot-check recommended |
| 50-69 | Low confidence | Thorough review required |
| 0-49 | Very low | Re-do or heavily verify |

## The Psychology: Why Doubt Builds Trust

Counterintuitively, agents that admit uncertainty are MORE trustworthy than agents that claim perfection:

- **"I tested all 5 endpoints and they pass, but I didn't test with invalid auth tokens"** -- the human knows exactly where to focus their review.
- **"Everything works perfectly"** -- the human has to check everything because they don't know what wasn't tested.

Mandatory self-doubt forces agents to think critically about their work. An agent that can't identify any uncertainty about a non-trivial task isn't being thorough -- it's being lazy.

## Integration with Existing Quality System

Trust Score is the REPORTING layer on top of existing quality gates:

```
Acceptance Criteria (what to check)
    |
    v
Auto-Verify / VBC (run the checks)
    |
    v
Definition of Done (gate the completion)
    |
    v
Trust Score (report the confidence)  <-- THIS
```

It doesn't replace any existing system. It makes the existing system's results visible and honest.

## How to Interpret Scores

### High scores (90+) that are trustworthy:
- Multiple command outputs shown (tests, compiles, greps)
- Specific uncertainties listed (not generic disclaimers)
- Human verification steps are minimal and targeted

### High scores (90+) that are suspicious:
- No command output, just "I read the code"
- Zero uncertainties listed
- Task was complex but agent claims everything is perfect

### Low scores (< 70) that are OK:
- Agent honestly couldn't verify (no test infrastructure, external dependency)
- Agent flagged exactly what needs human attention
- The score reflects reality, not agent failure

### Low scores (< 70) that are concerning:
- Agent did work but didn't bother verifying
- Agent skipped verification steps that were available
- No uncertainty list despite obvious gaps

## Metrics and Auditing

Trust scores are logged to `.cognitive-os/metrics/trust-scores.jsonl`.

Run `/trust-audit` to analyze:
- Which agents have lowest trust?
- Which task types consistently score low?
- Are any agents overclaiming (high scores but frequent errors)?
- Is trust improving over time?

## KPI Integration

Three trust-related KPIs are tracked:

| KPI | Target | Data Source |
|-----|--------|-------------|
| `average_trust_score` | > 75 | trust-scores.jsonl |
| `trust_accuracy` | > 80% | Cross-reference with error-learning.jsonl |
| `self_awareness_rate` | 100% | % of reports with uncertainties |
