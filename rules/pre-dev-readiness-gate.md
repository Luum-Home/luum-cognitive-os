<!-- SCOPE: os-only -->
<!-- TIER: 2 -->
# Pre-Development Readiness Gate

## Purpose

Ensure minimum pre-development artifacts exist before transitioning from planning to implementation. Prevents "code first, plan later" anti-patterns by verifying that required documentation is in place before any implementation agent is launched.

## Required Artifacts

| Artifact | Expected Path | Recommended Skill |
|---|---|---|
| Project Context | `docs/01-context/` | `/context-analysis` |
| Threat Model | `docs/04-security/` | `/threat-model` |
| Execution Plan | `docs/09-execution-plan/` | `/execution-plan` |

## Optional Artifacts

| Artifact | Expected Path | Recommended Skill |
|---|---|---|
| Architecture | `docs/02-architecture/` | `/sdd-explore` |
| Features | `docs/05-features/` | — |
| Research | `docs/07-research/` | `/competitive-research` |
| Standards | `docs/08-standards/` | — |
| Summaries | `docs/10-summaries/` | `/audience-summaries` |

## Verdicts

| Verdict | Condition | Meaning |
|---|---|---|
| READY | All 3 required directories present with at least one `.md` file each | Safe to start implementation |
| PARTIAL | 1-2 of 3 required directories present | Some planning done, gaps remain |
| NOT_READY | 0 of 3 required directories present | No planning artifacts found |

## Phase-Aware Enforcement

| Phase | NOT_READY / PARTIAL | Action |
|---|---|---|
| `reconstruction` | WARNING only | Proceed with caution |
| `stabilization` | WARNING only | Proceed with caution |
| `production` | BLOCK (exit 2) | Must complete planning first |
| `maintenance` | BLOCK (exit 2) | Must complete planning first |

## Trigger Detection

The hook fires only on implementation-related agent prompts. Detection uses keyword matching:

| Trigger Keywords | Examples |
|---|---|
| Implementation verbs | "implement", "write code", "build", "create the service", "develop" |
| SDD apply | "sdd-apply", "apply the tasks", "start coding" |
| Does NOT trigger on | "research", "explore", "plan", "spec", "design", "document" |

## Hook

- **Hook**: `hooks/predev-completeness-check.sh` (PreToolUse on Agent)
- **Triggers on**: Implementation-related agent prompts
- **Does NOT trigger on**: Research, exploration, planning prompts
- **Exit codes**: 0 (READY or advisory), 2 (BLOCK in production/maintenance when NOT_READY/PARTIAL)

## Lib

`lib/completeness_checker.py` provides:

| Function | Description |
|---|---|
| `check_predev_artifacts(project_root)` | Checks required and optional artifact directories |
| `format_report(result)` | Human-readable readiness report with recommended next skills |
| `get_verdict(result)` | Returns `READY`, `PARTIAL`, or `NOT_READY` |

## Output Format

```
PRE-DEV READINESS: PARTIAL (2/3 required artifacts present)

Required:
  [x] Project Context (docs/01-context/)
  [x] Execution Plan (docs/09-execution-plan/)
  [ ] Threat Model (docs/04-security/) — run /threat-model to generate

Optional (present):
  [x] Architecture (docs/02-architecture/)

Recommendation: Complete the Threat Model before starting implementation.
```

## Metrics

Checks logged to `.cognitive-os/metrics/predev-completeness.jsonl`:

```json
{
  "timestamp": "ISO-8601",
  "verdict": "PARTIAL",
  "required_present": 2,
  "required_total": 3,
  "phase": "production",
  "action": "block"
}
```

## Integration

| Rule | Relationship |
|---|---|
| Readiness Check (`phase-aware-agents`) | Complements the SDD readiness gate — this gate checks docs, SDD gate checks specs |
| Plan-First (`plan-first`) | Pre-dev gate enforces plan-first at the doc-artifact level |
| Blast Radius (`blast-radius`) | High blast radius tasks especially benefit from completed threat models |
| Definition of Done (`definition-of-done`) | Large/critical tasks require this gate to be READY before DoD can be achieved |

## Contextual Trigger

This rule is loaded when: pre-development, readiness gate, implementation start, planning completeness.
