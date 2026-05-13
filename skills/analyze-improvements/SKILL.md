<!-- SCOPE: both -->
---
name: analyze-improvements
description: 'Use when you need this Cognitive OS skill: Analyze KPIs, error patterns, and skill metrics to identify improvement
  opportunities. Produces a ranked list of proposed changes with AUTO vs HUMAN-APPROVAL classification. Output only — makes
  NO file changes.; do not use when a narrower skill directly matches the task.'
version: 0.1.0
user-invocable: true
auto-generated: false
last-updated: 2026-04-10
audience: both
effort: opus
tags:
- self-improvement
- analysis
- kpis
summary_line: Analyze KPIs, error patterns, and skill metrics to identify improvement…
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \banalyze[- ]?improvements?\b
  confidence: 0.95
- pattern: \b(kpi|error\s+patterns?|skill\s+metrics)\s+analysis\b
  confidence: 0.8
- pattern: \bimprovement\s+opportunities?\b
  confidence: 0.75
routing_intents:
- intent: analyze_improvements_request
  description: User asks to analyze KPIs, error patterns, and skill metrics to identify improvement opportunities. Produces
    a ranked list of proposed changes with AUTO vs HUMAN-APPROVAL classification.
  confidence: 0.85
---

# Analyze Improvements Skill

Read-only analysis of accumulated execution data. Identifies recurring failure patterns and generates concrete, ranked improvement proposals.

**This skill makes NO file changes.** It produces a structured proposal document that a human reviews before `apply-improvements` is invoked.

## When to Use

- Before running `/apply-improvements` (always precedes it)
- After `/agent-kpis` shows degraded metrics
- After 3+ failed tasks in a session
- When `/error-analyzer` keeps finding the same patterns
- Weekly health check

## Output Contract

Produces a structured analysis report with:
1. Data source summary (what was found, what was missing)
2. Ranked failure patterns (CRITICAL > HIGH > MEDIUM > LOW)
3. Per-pattern proposals with `AUTO_APPLICABLE: yes/no`
4. KPI snapshot for the metrics log

The report is designed to be pasted directly into `/apply-improvements` as input.

## Instructions

### Step 0: Quick Analysis via lib/self_improvement.py + lib/feedback_consumer.py

Run the pre-built analysis first to get a baseline:

```python
import sys, os
sys.path.insert(0, os.environ.get('CLAUDE_PROJECT_DIR', '.'))
from lib.self_improvement import analyze_kpi_history, suggest_improvements, format_improvement_report

analysis = analyze_kpi_history('.cognitive-os/metrics')
suggestions = suggest_improvements(analysis)
print(format_improvement_report(analysis, suggestions))
```

Then surface recent user feedback signals that should inform the proposals.
`feedback_consumer` reads `.cognitive-os/metrics/prompt-captures.jsonl`, groups
entries by classification, and returns the actionable signals (category: feedback,
correction, escalation):

```python
from lib.feedback_consumer import summarise_for_skill_improvement

feedback_summary = summarise_for_skill_improvement(limit=50)
print(f"Feedback window: {feedback_summary['total_entries']} entries, "
      f"{feedback_summary['actionable_count']} actionable signals")
for signal in feedback_summary['actionable_signals'][:10]:
    print(f"  [{signal['recency_rank']}] {signal['signal_category']} "
          f"(confidence={signal['confidence']:.2f}, ts={signal['timestamp']})")
```

If `actionable_count > 0`, include the top signals as an additional data source
in Step 2 (Identify Failure Patterns). Each actionable signal indicates a moment
where the user corrected, escalated, or gave negative feedback — these are
high-value inputs for skill repair proposals.

Use both outputs as context for the deeper analysis below.

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

### Step 4: Build KPI Snapshot

Compute a KPI snapshot (for later logging by apply-improvements):

```json
{
  "timestamp": "{ISO timestamp}",
  "first_pass_success_rate": {float 0-1},
  "avg_iterations": {float},
  "architecture_compliance": {float 0-1},
  "skill_success_rate": {float 0-1},
  "improvements_proposed": {int},
  "auto_applicable_count": {int},
  "human_approval_count": {int},
  "error_patterns_detected": {int}
}
```

Include this block verbatim at the end of the report so `apply-improvements` can log it.

### Step 5: Save Analysis to Engram

Save the full analysis:

```
mem_save(
  title: "Improvement Analysis {YYYY-MM-DD}",
  type: "discovery",
  project: "{project}",
  topic_key: "cognitive-os/self-improvement/{YYYY-MM-DD}",
  content: "{full report with patterns and proposals}"
)
```

### Step 6: Output the Analysis Report

```
=== IMPROVEMENT ANALYSIS REPORT ===
Period: {earliest data timestamp} to {latest data timestamp}
Run at: {ISO timestamp}

DATA SOURCES:
- error-learning.jsonl: {N} entries ({date range})
- skill-metrics.jsonl: {N} entries ({date range})
- auto-refine data: {N} sessions
- session-learnings (Engram): {N} entries
- Previous self-improvement reports: {N}

PATTERNS DETECTED ({N} total):

{severity_emoji} PATTERN 1: {title} [{CRITICAL|HIGH|MEDIUM|LOW}]
   Occurrences: {N}
   Root cause: {explanation}
   Proposal: see PROPOSAL #1

... (one entry per pattern, ranked by severity)

PROPOSALS ({N} total):
  Auto-applicable: {N}
  Requires human approval: {N}

--- PROPOSAL BLOCK (paste into apply-improvements)
---

{full PROPOSAL #1 through #N blocks}

--- END PROPOSAL BLOCK
---

KPI SNAPSHOT (for metrics/kpi-history.jsonl):
{JSON block}

NEXT STEP:
  Review proposals above.
  Auto-applicable ({N}): safe to apply immediately via /apply-improvements
  Human-approval ({N}): review each before invoking /apply-improvements --include-manual
```

Severity emojis: CRITICAL = 🔴, HIGH = 🟠, MEDIUM = 🟡, LOW = 🟢

## Flags

| Flag | Effect |
|------|--------|
| (none) | Full analysis of all available data |
| `--since YYYY-MM-DD` | Only analyze data since a specific date |
| `--focus TYPE` | Focus: `rebranding`, `migration`, `compliance`, `testing`, `model-routing` |

## Configuration

Reads `self_improvement` section from `cognitive-os.yaml`:

```yaml
self_improvement:
  enabled: true
  trigger_threshold:
    first_pass_success: 0.70
    iteration_count: 3
```
