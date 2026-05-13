<!-- SCOPE: both -->
<!-- TIER: 0 -->
---
enforcement: agent-instruction
trigger_priority: high
routing_patterns:
- pattern: \breconstruction phase\b
  confidence: 0.95
- pattern: \bphase[- ]aware\b
  confidence: 0.92
- pattern: \brewrite\s*(>|over|vs\.?|instead of)\s*patch\b
  confidence: 0.9
- pattern: \b(rewrite|reconstruct).*(legacy|broken|stub)\b
  confidence: 0.8
summary_line: Apply reconstruction/stabilization/production/maintenance phase behavior to agent work.
routing_intents:
- intent: phase_aware_agents_request
  description: User asks about project phase behavior, rewrite-versus-patch choices, or reconstruction policy.
  confidence: 0.85
---
# Phase-Aware Agent Protocol

## Current Phase: RECONSTRUCTION

Read the current phase from `cognitive-os.yaml` -> `project.phase`.

### Phase: reconstruction
When in reconstruction phase, ALL agents MUST:
- Follow the project's declared framework STRICTLY (per `cognitive-os.yaml -> project.architecture.frameworks`)
- REWRITE code that doesn't follow standards (don't patch, don't document as "future work")
- Break existing patterns if they're wrong
- Not worry about backwards compatibility
- If something doesn't compile after rewriting, FIX IT in the same session

### Phase: stabilization
When in stabilization phase, ALL agents MUST:
- Follow the standard STRICTLY
- REWRITE code that doesn't follow standards
- Maintain backwards compatibility where possible
- Fix remaining issues before they accumulate

### Phase: production
When in production phase, ALL agents MUST:
- NOT break existing functionality
- Use feature flags for changes
- Document risky changes as proposals, not implementations
- Maintain backwards compatibility

### Phase: maintenance
When in maintenance phase, ALL agents MUST:
- Only fix bugs and security issues
- Minimal changes, maximum stability
- Document everything as future work unless critical

### Architecture Standards (always enforced)

Read architecture standards from `cognitive-os.yaml -> project.architecture`. These typically include:
- HTTP framework: per `project.architecture.frameworks` (use the project's declared framework only)
- Controllers: implement the project's controller interface
- Use cases: implement the project's use case interface
- Entities: follow the project's entity conventions
- Repositories: implement the project's repository interface
- DTOs: in the application layer, NOT in the domain layer
- All app code under the project's declared source root
- One use case per file
- Mappers: Map{Input}To{Output} naming

### Implementation Readiness Gate (BMAD v6)

Before any `sdd-apply` phase, the orchestrator MUST run `/readiness-check`:
- Validates: specs complete, design reviewed, tasks broken down, dependencies identified, mocks configured, tests planned
- Verdicts: PASS (proceed), CONCERNS (proceed with caution), FAIL (must fix first)
- On FAIL: orchestrator MUST NOT launch sdd-apply. Report blockers to user.
- See: `.cognitive-os/skills/readiness-check/SKILL.md` for full checklist

SDD dependency graph with readiness gate:
```
proposal -> specs --> tasks -> [READINESS CHECK] -> apply -> verify -> archive
             ^
             |
           design
```

**`/sdd-ff` fast-forward pipeline**: `propose → spec + design (parallel) → tasks`
Runs all planning phases automatically in sequence. Does NOT include explore/apply/verify/archive.
Phase sequence defined in `sdd.fast_path.phases` in `cognitive-os.yaml`.
Model assignments per phase: propose=opus, spec=sonnet, design=opus, tasks=sonnet (from `sdd.phases`).

**Model-tier fast path** (Opus only): `explore → propose → apply → verify → archive`
Skips spec/design/tasks entirely. Controlled by `sdd.fast_path.model_threshold` in `cognitive-os.yaml`.
Use `SDDPipeline.get_phases(model, config)` from `lib/sdd_pipeline.py` to resolve the correct phase list.

### Auto-Refinement (PITER Loop)
When an agent task fails (test/build/lint errors detected by auto-refine hook):
1. If phase is reconstruction: auto-retry ALWAYS enabled — agents fix their own work, up to 3 attempts
2. If phase is stabilization: auto-retry ALWAYS enabled — agents fix their own work, up to 3 attempts
3. If phase is production: detect failure and SUGGEST retry, but require human approval before re-launch
4. If phase is maintenance: detect failure and SUGGEST retry, but require human approval before re-launch

The auto-refine hook (`auto-refine.sh`) enforces this automatically. The orchestrator must respond
to `ORCHESTRATOR ACTION REQUIRED` messages by re-launching the agent with error context.

### Auto-Remediation
When architecture-compliance hook detects violations:
1. If phase is reconstruction: suggest immediate fix — violations are BLOCKERS
2. If phase is stabilization: create task for fix
3. If phase is production: log warning only
4. If phase is maintenance: log warning only

### Scale-Adaptive Intelligence + Definition of Done

Task complexity determines BOTH the workflow AND the completion criteria:

| Complexity | Signal | Workflow | DoD Level |
|------------|--------|----------|-----------|
| Trivial | < 20 lines, 1 file | Do it directly | `code_compiles` + `no_lint_errors` |
| Small | 1-3 files, single service | Do it, DoD checked | + `unit_tests_pass` |
| Medium | Multi-file, new feature | `/plan-feature` first | + `unit_tests_added` + `coverage_maintained` + `docs_updated` |
| Large | Multi-service, integration | SDD required | + `readiness_check` + `80% coverage` + `integration_tests` + `adversarial_review` |
| Critical | Security, payments, migration | SDD + security review | + `security_review` + `idempotency` + `audit_trail` + `rollback_tested` |

Agents MUST classify complexity BEFORE starting and CANNOT mark done without passing ALL DoD criteria for that level. Run `/dod-check` to verify.

Phase modifies enforcement:
- `reconstruction` / `stabilization`: Missing criteria = WARNING
- `production` / `maintenance`: Missing criteria = BLOCK

### Phase Transition
To change phases, edit `cognitive-os.yaml` -> `project.phase`. Valid values:
- `reconstruction` — Full rebuild mode
- `stabilization` — Standards established, fixing remaining issues
- `production` — Live system, incremental changes only
- `maintenance` — Bug fixes and security patches only
