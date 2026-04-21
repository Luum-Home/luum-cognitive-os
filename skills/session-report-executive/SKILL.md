<!-- SCOPE: both -->
---
name: session-report-executive
description: Generate an executive-level session report translating technical metrics into business language. For non-technical leaders who need to know what the Cognitive OS did during a session.
user-invocable: true
version: 0.1.0
last-updated: 2026-04-09
audience: human
effort: haiku
tags: [governance, transparency, reporting]
triggers:
  - session report
  - executive report
  - what did the OS do
  - qué hizo el SO
  - audit report
  - reporte ejecutivo
summary_line: Generate an executive-level session report translating technical metrics into…

---

# Session Report — Executive View

Translate technical JSONL metrics into a business-readable session report. Plain language. Actual numbers. Honest about what was and was not verified.

## Instructions

### Step 1: Identify the Current Session

1. Check for `COGNITIVE_OS_SESSION_ID` environment variable
2. If not set, list `.cognitive-os/sessions/` and pick the directory with the most recent `meta.json` `start_time`
3. Read that session's `meta.json` to get: `session_id`, `start_time`, `working_directory`
4. Read `.cognitive-os/sessions/{id}/tasks.json` (if it exists) for task lifecycle data

If no session directory exists, proceed with global metrics files only and note "session isolation unavailable."

### Step 2: Set the Time Window

Determine the session time window:
- If `meta.json` has `start_time`: use `start_time` to now
- Otherwise: use the last 24 hours as the window

All JSONL reads below filter to entries within this window using the `timestamp` field.

### Step 3: Read Metrics Files

For each file, check existence first. If the file is missing or empty, record "No data collected this session" for that section — never omit the section.

All files are under `.cognitive-os/metrics/` unless otherwise noted.

#### 3a. `auto-verify.jsonl`
Each line: `{ "timestamp", "result": "PASS"|"FAIL"|"NO_CRITERIA"|"NO_PARSEABLE", "agent", ... }`

Collect within window:
- `pass_count` = lines where `result == "PASS"`
- `fail_count` = lines where `result == "FAIL"`
- `no_criteria_count` = lines where `result == "NO_CRITERIA"`
- `no_parseable_count` = lines where `result == "NO_PARSEABLE"`

#### 3b. `trust-scores.jsonl`
Each line: `{ "timestamp", "score": 0-100, "agent", "components": {...}, "uncertainties_count" }`

Collect within window:
- `avg_trust` = mean of all `score` values (round to 1 decimal)
- `min_trust` = lowest score and its `agent` description (first 60 chars)
- `total_uncertainties` = sum of all `uncertainties_count`
- `agents_without_uncertainty` = count of entries where `uncertainties_count == 0`

#### 3c. `cost-events.jsonl`
Each line: `{ "timestamp", "agent", "model", "input_tokens", "output_tokens", "estimated_cost_usd" }`

Collect within window:
- `total_cost` = sum of `estimated_cost_usd`
- Per model: count of agents and sum of cost for `opus`, `sonnet`, `haiku`, others
- `total_agents_tracked` = total line count in window

#### 3d. `error-learning.jsonl`
Each line: `{ "timestamp", "error_type", "service", "message", "fingerprint" }`

Collect within window:
- `errors_detected` = total line count
- `error_types` = unique values of `error_type` with their counts
- `services_affected` = unique values of `service`

#### 3e. `assumptions.jsonl`
Each line: `{ "timestamp", "assumption_count", "agent", "assumptions" }`

Collect within window:
- `total_assumptions` = sum of `assumption_count`
- `high_assumption_agents` = entries where `assumption_count >= 3` (list their `agent` first 60 chars)

#### 3f. `consequence-history.jsonl`
Each line: `{ "timestamp", "skill", "consequence": "PROMOTE"|"DEGRADE"|"DISABLE"|"MAINTAIN"|"WARN", "reason" }`

Collect within window:
- `promotions` = lines where `consequence == "PROMOTE"` with `skill` names
- `degradations` = lines where `consequence == "DEGRADE"` with `skill` names and `reason`
- `disables` = lines where `consequence == "DISABLE"` with `skill` names and `reason`

#### 3g. `escalation-events.jsonl`
Each line: `{ "timestamp", "escalation_count", "tool_calls_total", "escalation_types", ... }`

Collect within window:
- `total_escalations` = sum of `escalation_count` across all entries
- `escalation_types_seen` = union of all `escalation_types` keys

#### 3h. `scope-proportionality.jsonl`
Each line: `{ "timestamp", "severity": "WARN"|"BLOCK", "task_type", "message" }`

Collect within window:
- `scope_warnings` = count where `severity == "WARN"`
- `scope_blocks` = count where `severity == "BLOCK"`

#### 3i. `clarification-events.jsonl`
Each line: `{ "timestamp", "score", "verdict": "PASS"|"WARN"|"BLOCK", "questions" }`

Collect within window:
- `clarification_blocks` = count where `verdict == "BLOCK"`
- `clarification_warns` = count where `verdict == "WARN"`

#### 3j. `blast-radius.jsonl`
Each line: `{ "timestamp", "radius": "LOW"|"MEDIUM"|"HIGH"|"CRITICAL", "infra", "security" }`

Collect within window:
- `high_radius` = count where `radius == "HIGH"`
- `critical_radius` = count where `radius == "CRITICAL"`
- `security_flagged` = count where `security == true`
- `infra_flagged` = count where `infra == true`

#### 3k. `skill-metrics.jsonl`
Each line: `{ "timestamp", "skill", "model", "tokens", "duration_ms", "success" }`

Collect within window:
- `skills_executed` = count of all entries
- `skills_succeeded` = count where `success == true`
- `top_skills` = top 3 by frequency (skill name + count)

#### 3l. Session tasks (`.cognitive-os/sessions/{id}/tasks.json`)
If it exists, read the JSON array:
- `tasks_started` = total count
- `tasks_completed` = count where `status == "completed"`
- `tasks_failed` = count where `status == "failed"`
- `tasks_in_progress` = count where `status == "in_progress"`

If no session tasks file, note "Task tracking not available for this session."

### Step 4: Calculate Session Duration

If `meta.json` has `start_time` (ISO-8601), calculate:
- `duration_minutes` = (now - start_time) in minutes
- Format as "{H}h {M}m" if >= 60 minutes, else "{M}m"

If not available: "Duration unknown."

### Step 5: Determine Overall Confidence Level

Based on `avg_trust`:
- >= 85: **HIGH**
- 70–84: **MEDIUM**
- < 70: **LOW**
- No data: **UNKNOWN**

### Step 6: Build the Report

Produce the following Markdown report. Use the collected values. Write every number as an actual number. Use plain English throughout — no technical jargon unless explained inline.

```markdown
# Session Report — {YYYY-MM-DD} {HH:MM}

## Summary

| Metric | Value |
|--------|-------|
| Duration | {duration} |
| Skills executed | {skills_executed} |
| Tasks completed | {tasks_completed} of {tasks_started} |
| Errors detected | {errors_detected} |
| Estimated cost | ${total_cost:.2f} |
| Overall confidence | {HIGH/MEDIUM/LOW/UNKNOWN} (avg trust: {avg_trust}/100) |

## Autonomous Decisions

The Cognitive OS made the following decisions without human input:

{For each consequence action (PROMOTE/DEGRADE/DISABLE), list as bullet:}
- Promoted [{skill}]: performance consistently high — will prefer this tool going forward
- Degraded [{skill}]: performance below threshold — switched to a cheaper/safer model ({reason})
- Disabled [{skill}]: too many failures — blocked until rewritten ({reason})

{For each clarification BLOCK:}
- Blocked an agent launch because the task description was too vague (score too high for autonomous execution)

{For each scope BLOCK:}
- Blocked an agent from deleting files during a bug-fix task (scope violation in production phase)

{If no autonomous decisions: "No significant autonomous decisions recorded this session."}

## Human Approvals Required

{If escalations > 0:}
The OS raised {total_escalations} escalation(s) during this session, meaning it detected a situation it could not resolve autonomously:
{List escalation_types_seen in plain English:}
- loop_detected → Agent was making the same changes repeatedly with no progress
- error_repeat → Same error appeared multiple times — root cause not identified
- no_progress → Agent worked for many steps without measurable forward progress

{If clarification_blocks > 0:}
- {clarification_blocks} agent launch(es) were held pending clearer task descriptions

{If scope_blocks > 0:}
- {scope_blocks} operation(s) were blocked due to scope violations (changes outside the approved task boundary)

{If blast-radius critical_radius > 0 or security_flagged > 0:}
- {critical_radius} task(s) were flagged as HIGH IMPACT (touching infrastructure or security-sensitive code)

{If nothing to list: "No human approvals were required this session."}

## Quality Metrics

### Acceptance Criteria Verification
| Result | Count | Meaning |
|--------|-------|---------|
| Verified (PASS) | {pass_count} | Criteria checked and met |
| Failed (FAIL) | {fail_count} | Criteria checked and NOT met |
| Not parseable | {no_parseable_count} | Criteria present but could not be auto-checked |
| No criteria | {no_criteria_count} | Agent completed with no measurable criteria defined |

### Agent Confidence (Trust Scores)
- Average confidence: **{avg_trust}/100** — {HIGH/MEDIUM/LOW}
- Lowest confidence: **{min_trust}/100** (agent: "{min_trust_agent}")
- Total uncertainties acknowledged: {total_uncertainties} (agents are expected to report what they are unsure about)
- Agents that reported zero uncertainty: {agents_without_uncertainty} ⚠️ (zero uncertainty is a red flag — it usually means the agent did not think critically)

### Assumptions Made
- Total assumptions detected: {total_assumptions}
{If high_assumption_agents not empty:}
- Agents with 3+ assumptions (need attention):
{For each: "  - {agent description}"}

## Errors & Issues

{If errors_detected == 0: "No errors detected this session."}
{Otherwise:}
- **{errors_detected}** error(s) detected across {len(services_affected)} service(s)
- Error types: {error_types formatted as "TYPE (N occurrences)"}
- Services affected: {services_affected joined by ", "}

## Cost Breakdown

| Model | Agents | Est. Cost |
|-------|--------|-----------|
| opus (deep reasoning) | {opus_agents} | ${opus_cost:.2f} |
| sonnet (general tasks) | {sonnet_agents} | ${sonnet_cost:.2f} |
| haiku (simple tasks) | {haiku_agents} | ${haiku_cost:.2f} |
| **Total** | **{total_agents_tracked}** | **${total_cost:.2f}** |

Note: Costs are estimates based on token counts. Actual billing may differ.

## What Was NOT Verified

This section is critical for understanding where human review may be needed.

- **{no_parseable_count}** acceptance criteria were present but could not be automatically verified — a human should spot-check these results
- **{no_criteria_count}** agents completed work with no measurable success criteria defined — outcomes are based on agent self-reporting only
- **{agents_without_uncertainty}** agents reported 100% confidence — treat their outputs with extra scrutiny
{If fail_count > 0:}
- **{fail_count}** acceptance criteria checks FAILED — these items require immediate human review before the results are considered done
{If total_assumptions > 0:}
- **{total_assumptions}** assumption(s) were made by agents where requirements were unclear — verify those decisions match intent

---
*Generated by /session-report-executive | Cognitive OS {date}*
```

### Step 7: Save the Report (Optional)

If the user asks to save the report, write it to:
`.cognitive-os/reports/{YYYY-MM-DD}-executive-report.md`

Create the `reports/` directory if it does not exist.

### Step 8: Save Discovery to Engram

After generating the report, save a brief summary:

```
mem_save(
  title: "Executive session report generated — {date}",
  type: "discovery",
  scope: "project",
  topic_key: "implementation/session-report-executive/last-run",
  content: "Generated executive report for session {session_id}. Cost: ${total_cost:.2f}. Avg trust: {avg_trust}. Tasks: {tasks_completed}/{tasks_started}. Key issues: {fail_count} criteria failed, {total_escalations} escalations."
)
```

## Important Rules

- **Plain language only.** If you use a technical term, explain it in parentheses the first time. A VP with no engineering background must understand every line.
- **Actual numbers, not vague statements.** Write "3 of 7 criteria verified" — never "most criteria verified."
- **Never hide gaps.** If a metrics file is missing, say so explicitly in the relevant section. Do not silently omit a section.
- **The "What Was NOT Verified" section is the most important for trust.** Populate it honestly even if it makes the session look less successful.
- **Zero uncertainty agents are a red flag, not a success indicator.** Always call them out.
- **Costs are always labeled as estimates.** Never present them as exact billing figures.
