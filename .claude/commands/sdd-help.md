---
description: Load full Spec-Driven Development pipeline spec (phases, DAG, fast-path, topic keys)
---

# SDD — Spec-Driven Development Pipeline

## Artifact Store
- `engram`: default, persistent across sessions
- `openspec`: file-based, only when user requests
- `hybrid`: both backends
- `none`: inline only

## Commands
- `/sdd-init` → `sdd-init`
- `/sdd-explore <topic>` → `sdd-explore`
- `/sdd-new <change>` → `sdd-explore` then `sdd-propose`
- `/sdd-continue [change]` → next missing artifact
- `/sdd-ff [change]` → fast path (Opus) or full path
- `/sdd-apply [change]` → `sdd-apply` in batches
- `/sdd-verify [change]` → `sdd-verify`
- `/sdd-improve [change]` → `sdd-improve`
- `/sdd-archive [change]` → `sdd-archive`

Meta-commands (`/sdd-new`, `/sdd-continue`, `/sdd-ff`) are orchestrator-handled. Do NOT invoke as skills.

## Dependency Graph
```
proposal → specs ──→ tasks → apply ↔ verify → archive
             ↑         │    │       │       │
             │         │    │       └───────┘ (retry, max 3)
           design      │    └── improve (spec-driven refinement)
                       └── verify(spec) → improve → tasks
```

## Fast Path (Opus only — per `cognitive-os.yaml sdd.fast_path.model_threshold`)
- **Fast**: explore → propose → apply → verify → archive (skip spec/design/tasks)
- **Full**: explore → propose → spec → design → tasks → apply → verify → archive

Use `SDDPipeline.get_phases(model, config)` from `lib/sdd_pipeline.py` to resolve.

## Apply-Verify Cycle
1. **PASS** / **PASS WITH WARNINGS** → `sdd-archive`. Warnings noted, no retries.
2. **FAIL with CRITICALs** → retry loop: load DAG state (`sdd/{change}/state`), increment retry_count. If ≥3 → STOP, report. If <3 → re-launch `sdd-apply` with CRITICALs + failing scenarios, then re-launch `sdd-verify`. Update DAG state after EVERY phase transition.
3. **FAIL without CRITICALs** → archive with warnings noted.

## Loop Rules
- NEVER retry without FAIL+CRITICALs
- NEVER exceed 3 retries
- Save DAG state after EVERY transition
- Pass only CRITICALs as retry context
- Each retry = fresh sub-agent

## Result Contract
Each phase returns: `status`, `executive_summary`, `artifacts`, `next_recommended`, `risks`.

## Sub-Agent Context (SDD phases)

Each phase reads required deps from backend (orchestrator passes topic keys, NOT content):

| Phase | Reads | Writes |
|---|---|---|
| explore | nothing | explore |
| propose | exploration? | proposal |
| spec | proposal | spec |
| design | proposal | design |
| tasks | spec + design | tasks |
| apply | tasks + spec + design | apply-progress |
| verify | spec + tasks | verify-report |
| improve | verify + spec + design | updated artifacts |
| archive | all | archive-report |

## Topic Keys
- `sdd-init/{project}`
- `sdd/{change}/explore`
- `sdd/{change}/proposal`
- `sdd/{change}/spec`
- `sdd/{change}/design`
- `sdd/{change}/tasks`
- `sdd/{change}/apply-progress`
- `sdd/{change}/verify-report`
- `sdd/{change}/improve`
- `sdd/{change}/archive-report`
- `sdd/{change}/state`

Sub-agents retrieve: `mem_search(query: "{topic_key}")` → get ID → `mem_get_observation(id)` (REQUIRED — search truncates).

## Recovery
- engram: `mem_search` → `mem_get_observation`
- openspec: read `openspec/changes/*/state.yaml`
- none: state not persisted — explain to user
