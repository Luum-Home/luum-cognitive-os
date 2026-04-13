# BMAD v6 Patterns — Implementation Status

> Tracking the implementation of BMAD (Build Measure Analyze Decide) v6 patterns in Cognitive OS.

## Implemented Patterns

### Pattern 7: HALT-and-WAIT for Ambiguous Tasks

**Status**: Implemented
**File**: `.cognitive-os/rules/closed-loop-prompts.md` (HALT-and-WAIT Protocol section)
**Also in**: `.cognitive-os/rules/RULES-COMPACT.md` (compact reference)

Agents MUST present their plan and WAIT before executing ambiguous or high-risk tasks. HALT triggers include: multi-service changes, data migration, API contract changes, auth/security modifications. Phase-dependent behavior: reconstruction only halts for data-destructive ops; production halts for all ambiguous tasks.

### Pattern 8: Path Segregation in Engram

**Status**: Implemented
**File**: `.cognitive-os/rules/engram-organization.md`
**Also in**: `.cognitive-os/rules/RULES-COMPACT.md` (compact reference)

Structured topic key prefixes: `planning/`, `implementation/`, `docs/`, `agent/`, `sre/`, `architecture/`, `sprint/`, `config/`, `bugfix/`. Includes migration guide from legacy `sdd/` flat keys. Gradual migration strategy (re-save on read).

### Pattern 9: Agent Customization via Override Files

**Status**: Implemented
**Files**:
- `.cognitive-os/rules/agent-customization.md` (rule definition)
- `.cognitive-os/customizations/example.yaml` (example override)
**Also in**: `.cognitive-os/rules/RULES-COMPACT.md` (compact reference)

Per-agent behavioral overrides in `customizations/{agent-name}.yaml`. Deep merge semantics. Override fields: model, temperature, max_tokens, tools, skills, budget, phase behavior, custom instructions. Customizations directory survives Cognitive OS updates.

### Pattern 10: Sprint Tracking

**Status**: Implemented
**Files**:
- `.cognitive-os/skills/sprint/SKILL.md` (skill definition)
- `.cognitive-os/workflows/state/sprint-status.yaml` (state file)
**Also in**: `.cognitive-os/skills/CATALOG.md` (catalog entry)

Lightweight agent-managed sprint tracking. Sub-commands: `/sprint plan`, `/sprint status`, `/sprint retro`, `/sprint correct`. Integrates with Engram (persists goals/retros), Agent KPIs (completion rate), and resume-tasks (incomplete stories).

### Pattern 11: Dual-Search Protocol for Artifacts

**Status**: Implemented
**File**: `.cognitive-os/rules/context-optimization.md` (Dual-Search Protocol section)
**Also in**: `.cognitive-os/rules/RULES-COMPACT.md` (compact reference)

Three-step search: (1) complete file, (2) sharded version (index + sections), (3) Engram (topic key -> legacy key -> keyword). Handles both small projects (single files) and large projects (sharded docs). Respects token budgets.

### Pattern 12: Schema Validation for Skills and Agents

**Status**: Implemented
**Files**:
- `.cognitive-os/skills/validate-config/SKILL.md` (skill definition)
**Also in**: `.cognitive-os/skills/CATALOG.md` (catalog entry)

Validates: `cognitive-os.yaml` (required fields, valid phase, valid budget), `squads/*.yaml` (valid agent refs, no circular reporting), `CATALOG.md` (all skills exist on disk), `RULES-COMPACT.md` (all rules exist), skill frontmatter (name, description required), hooks (exist and executable), customizations (valid overrides). Returns PASS/WARNINGS/ERRORS.

## `.cognitive-os/` vs `_cognitive-os/` Naming

**Finding**: The `.cognitive-os/` directory is NOT filtered by any standard IDE or LLM tool:
- `.gitignore` in the project does not exclude `.cognitive-os/`
- No `.vscode/settings.json` or `.idea/` configuration exists that would hide it
- Claude Code reads dotfiles without issue
- Git tracks the directory normally

**Decision**: Keep `.cognitive-os/` naming. No rename needed. If future IDE/LLM filtering is discovered, document it here and evaluate renaming at that point.

## Patterns 1-6 (Reconstructed)

Patterns 1-6 were reconstructed with full implementations. Prior placeholder descriptions replaced with actual BMAD v6 implementations.

### Pattern 1: Adversarial Review

**Status**: Implemented
**File**: `.cognitive-os/rules/adversarial-review.md`

Every review MUST produce at least one finding. "Looks good" / "no issues found" is PROHIBITED and triggers a HALT with re-launch. Four severity tiers: BLOCKER, CONCERN, SUGGESTION, QUESTION. Applies to sdd-verify, code-reviewer, /evaluate-plan. Structured finding format with location, what, why, recommendation.

### Pattern 2: Implementation Readiness Gate

**Status**: Implemented
**Files**:
- `.cognitive-os/skills/readiness-check/SKILL.md` (gate skill, invocable as `/readiness-check`)
- `.cognitive-os/rules/phase-aware-agents.md` (updated with readiness gate in SDD flow)

Six-dimension checklist: specs complete, design reviewed, tasks broken down, dependencies identified, mocks configured, tests planned. Three verdicts: PASS, CONCERNS, FAIL. Mandatory gate between sdd-tasks and sdd-apply.

### Pattern 3: Project-Context Auto-Loading in Sub-Agents

**Status**: Implemented
**File**: `hooks/inject-phase-context.sh` (rewritten)

Hook now injects full project context into every sub-agent: current phase from cognitive-os.yaml, architecture standards (declared framework, clean arch, naming), all 7 constitutional gates, active squad assignment, project type. Prevents sub-agents from violating conventions they were never told about.

### Pattern 4: Per-Agent Sidecars via Engram

**Status**: Implemented
**File**: `.cognitive-os/rules/agent-sidecars.md`

Engram topic key convention: `agent/{agent-name}/sidecar`. Sidecars store learnings, preferences, frequent patterns, known issues, performance notes. Orchestrator searches for sidecar on agent launch and injects relevant context. Agents save discoveries to sidecar after tasks. Upsert via same topic_key.

### Pattern 5: Step-File Architecture for Long Phases

**Status**: Implemented
**Files**:
- `.cognitive-os/rules/step-files.md` (protocol definition)
- `.cognitive-os/workflows/steps/example-new-endpoint/` (6-step reference implementation)

Step files for phases > 30 min or > 5 actions. Naming: `step-01-{desc}.md` through `step-XX-complete.md`. Each step: objective, inputs, actions, outputs, success criteria. Resumption protocol: scan, find last completed, resume. Engram persistence for cross-session recovery.

### Pattern 6: Enhanced sdd-continue with State Inspection

**Status**: Implemented
**File**: `.cognitive-os/skills/sdd-continue/SKILL.md`

Before recommending next phase, inspects 4 state sources: Engram artifacts (all SDD topic keys), plan files in `.cognitive-os/plans/`, workflow state in `.cognitive-os/workflows/state/`, active tasks in `active-tasks.json`. Decision logic covers all possible states. Returns recommended action, alternatives ranked by impact, full state summary with reasoning. Without change-name, scans all in-progress changes.
