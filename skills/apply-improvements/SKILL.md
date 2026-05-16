---
name: apply-improvements
description: 'Use when you need this Cognitive OS skill: Apply approved self-improvement
  changes from an analyze-improvements report. Applies AUTO changes immediately; presents
  HUMAN-APPROVAL changes for explicit confirmation before touching files.; do not
  use when a narrower skill directly matches the task.'
version: 0.1.0
user-invocable: true
auto-generated: false
last-updated: 2026-04-10
audience: both
tags:
- self-improvement
- apply
- verification
disable-model-invocation: true
effort: sonnet
summary_line: Apply approved self-improvement changes from an analyze-improvements
  report.
platforms:
- claude-code
prerequisites: []
routing_intents:
- intent: apply_approved_self_improvements
  description: User wants to apply a completed analyze-improvements report, executing
    AUTO changes and pausing for explicit approval before HUMAN-APPROVAL changes.
  confidence: 0.87
- intent: implement_self_improvement_plan
  description: User has already chosen or approved Cognitive OS self-improvement
    changes and needs the repository updated, not another analysis-only report.
  confidence: 0.84
triggers:
- apply-improvements
- /apply-improvements
- Apply Improvements Skill
- Apply approved self-improvement changes from an analyze-improvements report
---
<!-- SCOPE: both -->
# Apply Improvements Skill

Takes the structured output from `/analyze-improvements` and applies changes to rules, skills, and templates.

**Prerequisite**: You MUST have an analysis report from `/analyze-improvements` before invoking this skill. If you do not have one, run `/analyze-improvements` first and review the output.

## Human Gate (Critical)

Before applying any change, the human must have reviewed and approved the analysis report. This skill:

1. Applies **AUTO** changes immediately (up to `max_auto_improvements` per run)
2. **Halts and asks for explicit confirmation** before each HUMAN-APPROVAL change
3. Runs `/cognitive-os-test` after all changes and rolls back if tests fail

This separation exists precisely to enforce the human gate. Do not skip it.

## Input

Paste the PROPOSAL BLOCK from `/analyze-improvements` as context when invoking this skill. The expected format is:

```
PROPOSAL #N:
  TYPE: ...
  SEVERITY: ...
  AUTO_APPLICABLE: yes | no
  TARGET_FILE: ...
  PATTERN_DETECTED: ...
  ROOT_CAUSE: ...
  PROPOSED_CHANGE: ...
  EXPECTED_IMPACT: ...
```

If no PROPOSAL BLOCK is provided, this skill MUST stop and say:
> "No analysis input found. Run /analyze-improvements first and paste its PROPOSAL BLOCK here."

## Instructions

### Step 1: Parse Proposals

Read the provided PROPOSAL BLOCK. Split proposals into two groups:

- **auto_queue**: proposals where `AUTO_APPLICABLE: yes`
- **manual_queue**: proposals where `AUTO_APPLICABLE: no` (requires human approval)

Print a summary:
```
APPLY PLAN:
  Auto-applicable ({N}): will apply without further confirmation
  Requires approval ({N}): will halt and ask before each

Auto queue:
  - PROPOSAL #X: {type} → {target_file}
  ...

Manual queue (will ask before each):
  - PROPOSAL #Y: {type} → {target_file}
  ...
```

### Step 2: Read max_auto_improvements from Config

```python
import yaml
with open('cognitive-os.yaml') as f:
    cfg = yaml.safe_load(f)
max_auto = cfg.get('self_improvement', {}).get('max_auto_improvements', 5)
```

Cap the auto_queue at `max_auto_improvements`. If the queue exceeds the cap, defer lowest-severity proposals to next run and note this in the report.

### Step 3: Apply AUTO Changes

For each proposal in auto_queue (up to `max_auto_improvements`):

1. Read the current content of `TARGET_FILE`
2. Apply `PROPOSED_CHANGE` (edit, append, or replace as specified)
3. Confirm the file was modified
4. Log the change: `"Applied PROPOSAL #N: {type} → {target_file}"`

**File type → edit action mapping:**

| `TYPE` | Target | Edit Action |
|--------|--------|-------------|
| `template_update` | `templates/*.md` | Append or replace specified section |
| `acceptance_criteria` | `rules/acceptance-criteria.md` | Append new criterion to the relevant template |
| `compliance_hook` | `hooks/architecture-compliance.sh` | Add pattern to the detection list |
| `model_routing` | `rules/model-routing.md` | Update the routing table row |
| `prompt_template` | `templates/*.md` | Append learned pattern |

After each edit, confirm the change is syntactically valid:
- Shell scripts: `bash -n {file}`
- Markdown: file is non-empty and opens without error
- YAML: `python3 -c "import yaml; yaml.safe_load(open('{file}'))"` (if applicable)

If a syntax check fails: revert the specific change, mark it as "failed to apply", continue to next proposal.

### Step 4: Present HUMAN-APPROVAL Changes

For each proposal in manual_queue:

Print the full proposal and ask:

```
--- HUMAN APPROVAL REQUIRED
---
PROPOSAL #{N}: {short description}

Target: {TARGET_FILE}
Pattern: {PATTERN_DETECTED}
Root cause: {ROOT_CAUSE}

Proposed change:
{PROPOSED_CHANGE}

Expected impact: {EXPECTED_IMPACT}

Apply this change? [yes / no / skip-all-manual]
```

Wait for the user's response before proceeding.

- **yes**: apply the change as described in Step 3
- **no**: skip this proposal, note it as "skipped by user"
- **skip-all-manual**: skip this and all remaining manual proposals

### Step 5: Run Verification

After all changes are applied, run:

```bash
python3 -m pytest tests/ -q --tb=short 2>&1 | tail -20
```

Or, if a Cognitive OS test suite exists:
```
/cognitive-os-test
```

If tests **pass**: proceed to Step 6.

If tests **fail**:
1. Identify which change introduced the failure (binary search: revert one at a time)
2. Revert the offending change via `git revert` (or direct file restoration)
3. Log it to `.cognitive-os/metrics/improvement-blocklist.jsonl`:
   ```json
   {"timestamp": "{ISO}", "proposal_type": "{type}", "target_file": "{file}", "reason": "caused test failure", "pattern": "{PATTERN_DETECTED}"}
   ```
4. Note it in the report as "reverted"
5. Re-run tests after reversion to confirm the suite is green

### Step 6: Log KPI Snapshot

Append the KPI snapshot from the analysis report to `.cognitive-os/metrics/kpi-history.jsonl`:

```json
{
  "timestamp": "{ISO timestamp}",
  "first_pass_success_rate": {from analysis},
  "avg_iterations": {from analysis},
  "architecture_compliance": {from analysis},
  "skill_success_rate": {from analysis},
  "improvements_proposed": {total from analysis},
  "improvements_applied": {N actually applied this run},
  "improvements_skipped": {N skipped},
  "error_patterns_detected": {from analysis}
}
```

### Step 7: Save Apply Report to Engram

```
mem_save(
  title: "Improvements Applied {YYYY-MM-DD}",
  type: "bugfix",
  project: "{project}",
  topic_key: "cognitive-os/self-improvement/applied/{YYYY-MM-DD}",
  content: "{summary of what was applied, what was skipped, test outcome}"
)
```

### Step 8: Output Summary Report

```
=== APPLY IMPROVEMENTS REPORT ===
Timestamp: {ISO}

CHANGES APPLIED ({N}):
  {emoji} PROPOSAL #N: {type} → {target_file}
    Change: {brief description}
    Verification: PASS | FAIL (reverted)
  ...

CHANGES SKIPPED ({N}):
  - PROPOSAL #N: {reason — user skipped / exceeded cap / failed verification}
  ...

VERIFICATION:
  Test suite: {PASS | FAIL}
  Reverted: {N changes}

KPI SNAPSHOT LOGGED: metrics/kpi-history.jsonl

NEXT RECOMMENDED:
  - Run /analyze-improvements again in {N} sessions to measure impact
  - Pending manual proposals: {N} (run /apply-improvements --include-manual to address)
```

## Flags

| Flag | Effect |
|------|--------|
| (none) | Apply AUTO proposals only; halt for HUMAN-APPROVAL |
| `--include-manual` | Also process HUMAN-APPROVAL proposals (still asks per proposal) |
| `--dry-run` | Show what would be applied without making changes |

## Rollback Protocol

If an applied change causes regressions after the session ends:

1. Find the improvement commit: `git log --oneline --grep="improve(self-improve)"`
2. Revert: `git revert {commit-hash}`
3. Add to blocklist: `metrics/improvement-blocklist.jsonl`

## Configuration

Reads `self_improvement` section from `cognitive-os.yaml`:

```yaml
self_improvement:
  enabled: true
  auto_apply: false          # if false, treat all proposals as HUMAN-APPROVAL
  max_auto_improvements: 5   # cap per run
```

If `auto_apply: false`, all proposals are moved to the manual_queue regardless of their `AUTO_APPLICABLE` field.
