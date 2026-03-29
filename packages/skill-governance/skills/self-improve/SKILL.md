---
name: self-improve
description: Analyze KPIs, error patterns, and skill metrics across sessions. Detect failure patterns, propose improvements to rules/skills/templates, optionally auto-apply. The closing piece of the self-improvement loop.
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-22
audience: os-dev
---

# Self-Improve Skill

Analyze accumulated execution data (errors, KPIs, skill metrics, auto-refine results) to detect recurring failure patterns and generate concrete improvements to rules, skills, and templates.

This is the **closing piece** of the self-improvement loop:
```
Execution -> Verification -> Error Capture -> Pattern Detection -> Self-Improve -> Better Rules/Skills -> Better Next Execution
```

## When to Use

- Weekly (recommended), or after `/agent-kpis` shows degraded metrics
- After 3+ failed tasks in a single session
- When `/error-analyzer` keeps finding the same patterns
- When the orchestrator detects KPI thresholds breached (via `kpi-trigger.sh`)
- Manually: `/self-improve` or `/self-improve --apply`

## Flags

| Flag | Effect |
|------|--------|
| (none) | Analyze and propose only (dry run) |
| `--apply` | Analyze, propose, AND auto-apply safe improvements |
| `--since YYYY-MM-DD` | Only analyze data since a specific date |
| `--focus TYPE` | Focus on a specific area: `rebranding`, `migration`, `compliance`, `testing`, `model-routing` |

## Instructions

### Step 1: Load All Error and Metrics Data

Read these files from `.cognitive-os/metrics/`:

1. **`error-learning.jsonl`** — Test/lint/build failures. Fields: `timestamp`, `type`, `service`, `framework`, `error`, `command`, `context`, `fingerprint`
2. **`skill-metrics.jsonl`** — Skill execution data. Fields: `timestamp`, `skill`, `model`, `tokens`, `duration_ms`, `success`
3. **`cost-events.jsonl`** (if exists) — Cost tracking per operation
4. **`auto-refine/`** directory (if exists) — Auto-refine iteration data

Also search Engram for:
- `mem_search(query: "cognitive-os/self-improvement", project: "{project}")` — previous self-improvement reports
- `mem_search(query: "cognitive-os/session-learnings", project: "{project}")` — session learning summaries
- `mem_search(query: "agent-kpis/latest", project: "{project}")` — latest KPI dashboard

If a file does not exist or is empty, note it as "no data" and continue.

### Step 2: Identify Failure Patterns

Group and analyze data across 5 dimensions:

#### 2a. Task Type Failures
Classify errors by task type (infer from command, skill name, or error context):
- **rebranding**: grep/sed/rename operations, string replacement failures
- **migration**: endpoint listing, schema changes, data migration errors
- **compliance**: architecture violations, lint errors matching patterns
- **testing**: test failures, mock configuration, assertion errors
- **implementation**: build errors, compilation failures, type mismatches

For each type, calculate:
- Total occurrences
- First-pass success rate (successes / total attempts)
- Average iterations needed (from auto-refine data if available)

#### 2b. Service Failures
Group errors by `service` field:
- Which services have the most failures?
- Which services have recurring patterns?
- Are failures concentrated or spread evenly?

#### 2c. Acceptance Criteria Failures
Search for patterns in error messages that indicate acceptance criteria gaps:
- "not complete" / "do it again" / "missed" patterns in session learnings
- Auto-refine iterations > 2 (indicates acceptance criteria were too loose)
- Verification failures (verification-before-completion skill failures)

#### 2d. Skill Quality
From `skill-metrics.jsonl`, calculate per-skill:
- Success rate
- Average tokens consumed
- Average duration
- Trend (improving or degrading over time)

Flag skills with:
- Success rate < 70%
- Token consumption > 2x average
- Degrading trend (last 5 invocations worse than previous 5)

#### 2e. Model Performance
Cross-reference skill metrics with model routing:
- Which model is used for which skills?
- Are some models performing worse for specific task types?
- Would a different model routing improve outcomes?

### Step 3: Generate Improvement Proposals

For each detected pattern, generate a concrete proposal:

#### Proposal Types

| Pattern | Proposal Type | Auto-Applicable |
|---------|--------------|-----------------|
| Task type fails > 75% | Template update (add pre-checks) | YES |
| Same acceptance criteria fails repeatedly | Acceptance criteria template update | YES |
| Compliance violations repeat | Add pattern to architecture-compliance.sh | YES |
| Skill success rate < 70% | Skill rewrite with specific instructions | HUMAN APPROVAL |
| Model mismatch detected | Model routing table update | YES |
| Service has 5+ recurring errors | New rule for service-specific patterns | HUMAN APPROVAL |
| Auto-refine needs > 3 iterations | Refine prompt template with learned patterns | YES |

#### Proposal Format

For each proposal:
```
PROPOSAL #{N}:
  TYPE: {template_update | acceptance_criteria | compliance_hook | skill_rewrite | model_routing | new_rule | prompt_template}
  SEVERITY: {high | medium | low}
  AUTO_APPLICABLE: {yes | no (requires human approval)}
  TARGET_FILE: {relative path to file to modify}
  PATTERN_DETECTED: {description of the failure pattern}
  ROOT_CAUSE: {why this keeps happening}
  PROPOSED_CHANGE: {specific text/diff to add or modify}
  EXPECTED_IMPACT: {how this should improve metrics}
```

### Step 4: Apply Improvements (if `--apply` flag)

Only apply proposals where `AUTO_APPLICABLE = yes`. For human-approval items, list them in the report.

For each auto-applicable proposal:

1. **Template updates**: Edit the target template file in `templates/`
2. **Acceptance criteria**: Edit `rules/acceptance-criteria.md`
3. **Compliance hooks**: Edit `hooks/architecture-compliance.sh`
4. **Model routing**: Edit `rules/model-routing.md`
5. **Prompt templates**: Edit target in `templates/`

After applying:
- Cap at `max_auto_improvements` from cognitive-os.yaml (default: 5)
- Verify the Cognitive OS test suite still passes: run `/cognitive-os-test`
- If tests fail, revert the change and mark it as "failed to apply"

### Step 5: Save Learnings to Engram

Save the full analysis to Engram:

```
mem_save(
  title: "Self-Improvement Report {YYYY-MM-DD}",
  type: "discovery",
  project: "{project}",
  topic_key: "cognitive-os/self-improvement/{YYYY-MM-DD}",
  content: "{full report with patterns, proposals, and applied changes}"
)
```

### Step 6: Log KPI Snapshot

Append a KPI snapshot entry to `metrics/kpi-history.jsonl`:

```json
{
  "timestamp": "{ISO timestamp}",
  "first_pass_success_rate": {float 0-1},
  "avg_iterations": {float},
  "architecture_compliance": {float 0-1},
  "skill_success_rate": {float 0-1},
  "improvements_proposed": {int},
  "improvements_applied": {int},
  "error_patterns_detected": {int}
}
```

### Step 7: Generate Report

Output the following format:

```
=== SELF-IMPROVEMENT REPORT ===
Period: {earliest data timestamp} to {latest data timestamp}

DATA SOURCES:
- error-learning.jsonl: {N} entries
- skill-metrics.jsonl: {N} entries
- auto-refine data: {N} sessions
- session-learnings (Engram): {N} entries
- Previous self-improvement reports: {N}

PATTERNS DETECTED (from last {N} sessions):

1. {severity_emoji} {Pattern title}: {metric}
   ROOT CAUSE: {explanation}
   FIX: {what was/should be done}

2. ...

IMPROVEMENTS PROPOSED: {N}
- Auto-applicable: {N}
- Requires human approval: {N}

IMPROVEMENTS APPLIED: {N} (or "Dry run — use --apply to apply")
- {file} -> {change description}
- ...

PENDING HUMAN REVIEW: {N}
- {description of change needing approval}
- ...

METRICS SUMMARY:
- Error patterns analyzed: {N}
- Unique patterns found: {N}
- Improvements proposed: {N}
- Auto-applied: {N}
- Pending human review: {N}

KPI IMPACT (estimated):
- First-pass success rate: {current}% -> {projected}% (after improvements)
- Average iterations: {current} -> {projected}

NEXT RECOMMENDED:
- {action 1}
- {action 2}
```

Severity emojis: HIGH = red circle, MEDIUM = yellow circle, LOW = green circle.

## Rollback Protocol

If an auto-applied improvement causes regressions:

1. Check git log for the improvement commit
2. Revert the specific commit: `git revert {commit-hash}`
3. Log the failed improvement to Engram: `cognitive-os/self-improvement/rollbacks`
4. Add the pattern to a "do not auto-apply" list in `metrics/improvement-blocklist.jsonl`

## Configuration

Controlled by `self_improvement` section in `cognitive-os.yaml`:

```yaml
self_improvement:
  enabled: true
  auto_apply: false          # require human approval by default
  trigger_threshold:
    first_pass_success: 0.70  # below this -> suggest self-improve
    iteration_count: 3        # tasks needing >3 iterations -> flag
  schedule: session_end       # when to collect learnings
  max_auto_improvements: 5    # cap per self-improve run
```

## Integration Points

| Component | How it feeds self-improve |
|-----------|--------------------------|
| `hooks/error-learning.sh` | Captures raw error data |
| `hooks/auto-refine.sh` | Captures iteration data |
| `hooks/session-learning.sh` | Captures session-level learnings |
| `hooks/kpi-trigger.sh` | Detects when self-improve should run |
| `skills/error-analyzer/` | Detailed error pattern analysis |
| `skills/agent-kpis/` | KPI dashboard data |
| `skills/model-optimizer/` | Model routing recommendations |
| `rules/self-improvement-protocol.md` | Governance rules |
