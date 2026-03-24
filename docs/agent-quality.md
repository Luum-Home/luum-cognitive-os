# Agent Quality System

> Solving the biggest quality problem in agent-driven development: agents doing the MINIMUM instead of the MAXIMUM.

## The Problem

When agents receive vague or ambiguous prompts, they consistently deliver minimal results:

| Task Given | What Agent Does | What Was Expected |
|------------|----------------|-------------------|
| "Rebrand old-name to new-name" | Renames 3 obvious config files | Renames 203 occurrences across 37 files |
| "Migrate endpoints to Go" | Migrates 10 endpoints | Migrates all 317 endpoints |
| "Fix lint errors" | Fixes 5 easy ones | Fixes all 45 errors |
| "Follow existing patterns" | Uses some patterns | Uses the exact ginext/clean-arch patterns |

Root causes:
1. Ambiguous prompts are interpreted minimally
2. No measurable "done" means the agent decides when it's done
3. Agents optimize for speed, not completeness
4. No automated verification catches partial results

## The Solution: 4 Interlocking Fixes

### 1. Mandatory Acceptance Criteria

**File**: `rules/acceptance-criteria.md`

Every agent prompt MUST include measurable acceptance criteria with verification commands. The orchestrator defines "done" before the agent starts.

Format:
```
ACCEPTANCE CRITERIA:
1. [Check]: `command` = expected_value
2. [Check]: `command` exits 0
3. [Check]: `command` >= threshold
```

### 2. Auto-Verification Loop

**File**: `hooks/auto-verify.sh`
**Hook type**: PostToolUse on Agent (runs BEFORE dod-gate.sh)

When an agent reports completion:
1. Extracts acceptance criteria from the original prompt
2. Parses verification commands (backtick-wrapped with = or >= or exits N)
3. Runs each command with a timeout
4. Compares actual results to expected
5. Reports PASS or FAIL

On FAIL, the orchestrator should re-launch the agent with the failure context. Maximum 3 retries (configured in `cognitive-os.yaml` under `quality.verification_retries`).

### 3. Exhaustive Prompt Generator

**File**: `skills/exhaustive-prompt/SKILL.md`
**Invoke**: `/exhaustive-prompt`

Transforms high-level task descriptions into exhaustive, verifiable agent prompts:
1. Runs discovery commands to enumerate exact scope
2. Lists every file with line numbers and expected changes
3. Generates acceptance criteria with verification commands
4. Sets complexity-appropriate Definition of Done

Use BEFORE launching any agent for medium, large, or critical tasks.

### 4. Completeness Validator

**File**: `hooks/completeness-check.sh`
**Hook type**: PreToolUse on Agent

Advisory check that detects red flags in agent prompts before launch:
- "all files" without listing them
- Migration tasks without item counts
- "follow patterns" without specifying which
- Missing acceptance criteria section
- Large scope without explicit enumeration

Does NOT block the agent launch. Suggests running `/exhaustive-prompt` first.

## Hook Registration

In `.claude/settings.json`, the hooks should be registered in this order:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Agent", "hooks": ["completeness-check.sh", "agent-prelaunch.sh"] },
    ],
    "PostToolUse": [
      { "matcher": "Agent", "hooks": ["auto-verify.sh", "dod-gate.sh", "auto-refine.sh"] },
    ]
  }
}
```

Order matters: `auto-verify.sh` runs before `dod-gate.sh` so verification happens before Definition of Done checks.

## Configuration

In `cognitive-os.yaml`:

```yaml
quality:
  auto_verify: true           # Enable auto-verification hook
  exhaustive_prompts: true     # Enable completeness check hook
  completeness_check: true     # Enable pre-launch prompt validation
  verification_retries: 3      # Max retries on verification failure
```

## Metrics

### auto-verify.jsonl

Each entry logs a verification attempt:
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "status": "PASS|FAIL|NO_CRITERIA|NO_PARSEABLE_CRITERIA",
  "agent": "first 100 chars of prompt",
  "checks": 4,
  "passed": 4,
  "failed": 0
}
```

### completeness-check.jsonl

Each entry logs a completeness warning:
```json
{
  "timestamp": "2025-01-15T10:29:00Z",
  "warnings": 3,
  "agent": "first 100 chars of prompt"
}
```

### Key Metrics to Track

| Metric | Target | Description |
|--------|--------|-------------|
| Verification pass rate | > 80% | % of agent completions that pass auto-verify |
| Criteria coverage | > 90% | % of agent prompts that include acceptance criteria |
| Completeness warnings | Trending down | Number of red flags per session |
| Retry rate | < 20% | % of tasks requiring re-launch after verification failure |

## Workflow

```
1. User provides task → Orchestrator
2. Orchestrator runs /exhaustive-prompt → exhaustive prompt with criteria
3. Orchestrator launches agent → completeness-check.sh fires (advisory)
4. Agent works on task → reports completion
5. auto-verify.sh fires → extracts criteria, runs commands
6. If FAIL → orchestrator re-launches with failure context (up to 3x)
7. If PASS → dod-gate.sh fires → checks Definition of Done
8. Task confirmed complete
```

## Related Files

| File | Purpose |
|------|---------|
| `rules/acceptance-criteria.md` | Rule: every prompt needs acceptance criteria |
| `rules/agent-quality.md` | Meta-rule explaining the quality system |
| `hooks/auto-verify.sh` | PostToolUse hook: run verification commands |
| `hooks/completeness-check.sh` | PreToolUse hook: detect vague prompts |
| `skills/exhaustive-prompt/SKILL.md` | Skill: generate exhaustive prompts |
| `rules/definition-of-done.md` | Definition of Done by complexity level |
| `hooks/dod-gate.sh` | PostToolUse hook: check DoD criteria |
| `hooks/auto-refine.sh` | PostToolUse hook: retry on failure (PITER loop) |
