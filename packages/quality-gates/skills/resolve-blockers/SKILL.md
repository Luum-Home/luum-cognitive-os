<!-- SCOPE: both -->
---
name: resolve-blockers
command: /resolve-blockers
description: >
  Automatically resolve blockers reported by readiness-check. Maps each blocker
  type to a resolution sub-agent, re-runs readiness-check after fixes, and
  escalates to human after 2 failed attempts.
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-26
trigger: After readiness-check returns FAIL
inputs:
  - change-name (required): SDD change whose blockers to resolve
outputs:
  - status: RESOLVED | PARTIAL | ESCALATED
  - resolved: list of blockers that were fixed
  - unresolved: list of blockers still open
  - attempts: number of resolution cycles used
  - recommendation: next action for orchestrator or human
metadata:
  author: luum
  pattern-source: .cognitive-os/Archive (3)/ai-workflow/ai_workflow_resolve_iso.py
audience: project
summary_line: Automatically resolve blockers reported by readiness-check.

platforms: ["claude-code"]
prerequisites: []
---

# Resolve Blockers

## Purpose

Closes the gap between readiness-check FAIL and sdd-apply. Instead of stopping at "these blockers exist," this skill dispatches resolution sub-agents for each blocker type, then re-validates. Inspired by the ai_workflow_resolve_iso pattern: resolve, re-validate, advance or escalate.

## When to Run

- **Automatic**: Orchestrator invokes after `/readiness-check` returns verdict `FAIL`
- **Manual**: User invokes `/resolve-blockers <change-name>`
- **SDD integration**: Sits between readiness-check and sdd-apply in the pipeline

```
proposal -> specs --> tasks -> [READINESS CHECK] -FAIL-> [RESOLVE BLOCKERS] -> [RE-CHECK] -> apply
             ^
             |
           design
```

## Invocation

```
/resolve-blockers <change-name>
```

## Blocker-to-Resolution Map

Each RED dimension from readiness-check maps to a specific resolution action.

| Blocker Type | Readiness Dimension | Resolution Action |
|---|---|---|
| Missing spec | `specs_complete: RED` | Launch `sdd-spec` for the change |
| Missing design | `design_reviewed: RED` | Launch `sdd-design` for the change |
| Missing API contract | `dependencies_identified: RED` (API drift) | Launch `/contract-drift` scan to identify and document contracts |
| Missing test plan | `tests_planned: RED` | Generate test plan from existing spec artifact |
| Missing dependencies | `dependencies_identified: RED` (imports) | Scan imports across affected services and document dependency map |
| Missing mocks | `mock_providers: RED` | Create mock stubs for identified external providers |

## Execution Steps

### Step 1: Load Readiness Report

1. Retrieve the readiness-check result. Accept it as input if passed by the orchestrator, or re-run `/readiness-check <change-name>` to get a fresh report.
2. If verdict is PASS or CONCERNS, return early:
   ```yaml
   status: RESOLVED
   resolved: []
   unresolved: []
   attempts: 0
   recommendation: "Readiness check already passing. Proceed to sdd-apply."
   ```
3. Extract the list of RED dimensions as `blockers_to_resolve`.

### Step 2: Check Prior Attempts

1. Search Engram for prior resolution state:
   ```
   mem_search(query: "planning/{change-name}/resolve-blockers", project: "{project}")
   ```
2. If found, retrieve full content via `mem_get_observation(id: {id})`.
3. Read `attempt_count` from the state. If `attempt_count >= 2`, skip to Step 6 (escalate).
4. Increment `attempt_count`. If no prior state, set `attempt_count = 1`.

### Step 3: Dispatch Resolution Sub-Agents

For each blocker in `blockers_to_resolve`, launch the appropriate resolution action. Process blockers in dependency order:

**Priority order** (resolve earlier dependencies first):
1. Missing spec (everything else depends on it)
2. Missing design (tasks and mocks depend on it)
3. Missing dependencies identified
4. Missing API contract
5. Missing test plan
6. Missing mocks

**For each blocker:**

#### Missing Spec (`specs_complete: RED`)
- Verify proposal exists: `mem_search(query: "planning/{change-name}/proposal")`
- If proposal exists: launch `sdd-spec` sub-agent with the change-name
- If proposal missing: report as unresolvable (proposal is a prerequisite for spec)

#### Missing Design (`design_reviewed: RED`)
- Verify proposal exists: `mem_search(query: "planning/{change-name}/proposal")`
- If proposal exists: launch `sdd-design` sub-agent with the change-name
- If proposal missing: report as unresolvable

#### Missing API Contract (`dependencies_identified: RED` with API drift indicators)
- Launch `/contract-drift` scan against the affected services
- Document discovered endpoints and mismatches
- Save contract analysis to Engram: `planning/{change-name}/contract-analysis`

#### Missing Test Plan (`tests_planned: RED`)
- Retrieve spec from Engram: `planning/{change-name}/spec`
- Generate test plan covering:
  - Unit tests for each requirement in the spec
  - Integration tests for cross-service flows
  - Edge cases from spec acceptance criteria
  - Coverage target (minimum from project config or 80% default)
- Save test plan to Engram: `planning/{change-name}/test-plan`

#### Missing Dependencies (`dependencies_identified: RED` without API drift)
- Scan source files for import statements across affected services
- Identify inter-service dependencies and infrastructure requirements
- Document: which services communicate, required infra (DB, queue, cache)
- Save dependency map to Engram: `planning/{change-name}/dependency-map`

#### Missing Mocks (`mock_providers: RED`)
- Read design artifact for external provider list
- For each external provider without a mock:
  - Create a mock stub interface following the project's mock pattern
  - Add mock flag to env documentation (`PROVIDER_MOCK=true`)
- Save mock inventory to Engram: `planning/{change-name}/mock-inventory`

### Step 4: Record Resolution Results

Track which blockers were resolved and which remain:

```yaml
resolved:
  - type: "missing_spec"
    action: "Launched sdd-spec, spec artifact created"
  - type: "missing_test_plan"
    action: "Generated test plan from spec"
unresolved:
  - type: "missing_design"
    reason: "Proposal artifact not found, cannot generate design"
```

### Step 5: Re-Run Readiness Check

1. Invoke `/readiness-check <change-name>` to re-validate.
2. Evaluate new verdict:
   - **PASS**: All blockers resolved. Proceed.
   - **CONCERNS**: No RED remaining. Proceed with noted concerns.
   - **FAIL**: Some blockers remain. Check attempt count.

If verdict is still FAIL and `attempt_count < 2`:
- Save state to Engram and return to Step 3 with remaining blockers only.

If verdict is PASS or CONCERNS:
- Save final state to Engram and return success.

### Step 6: Escalate to Human

When `attempt_count >= 2` and blockers remain:

1. Compile escalation report with:
   - Original blockers from first readiness-check
   - What was resolved across all attempts
   - What remains unresolved and why
   - Specific recommended human actions
2. Save escalation report to Engram: `planning/{change-name}/resolve-escalation`
3. Return structured result with `status: ESCALATED`

## State Persistence

After every step transition, save state to Engram:

```
mem_save(
  title: "Resolve blockers: {change-name} - attempt {N}",
  type: "pattern",
  scope: "project",
  project: "{project}",
  topic_key: "planning/{change-name}/resolve-blockers",
  content: |
    change: {change-name}
    attempt_count: {N}
    max_attempts: 2
    blockers_original: [{list}]
    blockers_resolved: [{list with actions taken}]
    blockers_remaining: [{list with reasons}]
    last_readiness_verdict: {PASS|CONCERNS|FAIL}
    timestamp: {ISO}
)
```

## Result Format

```yaml
status: RESOLVED | PARTIAL | ESCALATED
change: {change-name}
attempts: {1 or 2}
resolved:
  - type: "{blocker_type}"
    action: "{what was done}"
    artifact: "{engram topic key or file path}"
unresolved:
  - type: "{blocker_type}"
    reason: "{why it could not be resolved}"
    human_action: "{what the human should do}"
recommendation: "Proceed to sdd-apply" | "Address remaining concerns" | "Human intervention required"
```

## Constraints

- **Max 2 resolution attempts** before escalating. Do not loop indefinitely.
- **Dependency order matters**: resolve specs before design, design before mocks.
- **Do not create artifacts that already exist**: check Engram before launching sub-agents.
- **Do not modify existing specs or designs**: only create missing ones. If an existing artifact is incomplete, flag it as unresolvable for human review.
- **Respect phase behavior**: in production/maintenance phases, resolution sub-agents require human approval before launching.

## Integration

| System | How it integrates |
|---|---|
| readiness-check | Consumes its FAIL verdict, re-runs it after resolution |
| sdd-spec / sdd-design | Launched as resolution sub-agents for missing planning artifacts |
| contract-drift | Launched to resolve missing API contract documentation |
| Engram | State persistence for cross-session resumption and attempt tracking |
| Orchestrator | Orchestrator calls this skill automatically on readiness FAIL; respects the RESOLVED/ESCALATED status to decide next action |
| Phase protocol | Phase-aware: reconstruction auto-resolves, production requires approval |
