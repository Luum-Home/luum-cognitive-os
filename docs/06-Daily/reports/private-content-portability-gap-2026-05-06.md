# Private Content Cross-Harness Portability Gap — 2026-05-06

**Scope**: gap between public multi-tool support and private content portability
for strategy, memory, plans, metrics, recovery artifacts, and cloud/headless
service operation.

## Short answer

ADR-008 made Cognitive OS multi-tool in public architecture terms. It did not
fully specify what happens to private content when the same SO runs across Codex,
Claude Code, local CLI, containers, and future cloud service instances.

That matters because private content is not just secrets. It includes strategy,
local memory, recovery artifacts, metrics, action receipts, and consumer-project
facts that may be safe for one host but not another.

## Evidence

- ADR-008 focuses on adapter layers, MCP, and rules portability.
- Current work increasingly spans Codex, Claude Code, headless service drills,
  `cosd`, Engram, local metrics, and private `.cognitive-os/` artifacts.
- The user observed an agent correctly identifying that this is larger than one
  strategy folder: it is a cross-harness private-content portability gap.
- The same exchange produced bad router dogfood evidence: `/auto-rollback` was
  suggested while the user was discussing architecture/risk, not asking to roll
  back a failed change.

## The missing distinction

| Portability type | Existing coverage | Missing piece |
|---|---|---|
| Public primitive portability | ADR-008 and later harness ADRs. | Mostly covered by adapters/projection. |
| Private content portability | Implicit and fragmented. | Explicit content classes, allowed hosts, redaction, retention, and export gates. |
| Service/cloud portability | Partially covered by `cosd` ADRs. | Private content ingestion/retention policy per host. |

## Content classes needed

| Class | Default behavior |
|---|---|
| `secret-never-touch` | Never read through generic audit/export paths; only explicit secret-specific APIs. |
| `local-only` | Never auto-export or upload. |
| `same-user-harness` | Can move between local harnesses for the same operator on the same trusted machine. |
| `project-private` | Can stay within private repo/project boundary. |
| `sanitized-export` | Can leave after redaction and provenance checks. |
| `public` | Safe for public package/docs surfaces. |

Unknown content must default to `local-only`. Known secret/credential paths must
be stricter: `secret-never-touch`.

The first implementation should not try to classify every item deeply. It should
ship a skeleton manifest that marks known private roots as `local-only`, then add
specific elevations only when a destination and redaction/provenance rule are
justified. The goal is to close the unsafe default quickly, not create an endless
classification exercise.

This also means no path move is required. `.cognitive-os/strategy/` does not need
to become `.agents-private/`; it needs a portability policy.

## Why this connects to the router incident

The `/auto-rollback` suggestion is not primarily dangerous because the current
rollback hook executes destructive git. It does not: ADR-107 and the package
contract require human approval and the hook logs `destructive_commands_executed=false`.

The real issue is semantic routing. A user can mention a dangerous or recovery
primitive while discussing risk, architecture, or bad suggestions. The router
currently treats some mentions as intent. That is wrong for private/strategy
contexts and should be treated as negative evidence for ADR-201.

## Additional design gaps captured

- Class transitions need gates and audit receipts; metadata edits alone are not
  enough to move content from private to exportable or public.
- Private-content access events need a durable destination:
  `.cognitive-os/metrics/private-content-access.jsonl`.
- Engram classification needs a separate integration decision: per observation,
  topic key, namespace, or export bundle.
- Hosted service mode needs GDPR/data-deletion and export-revocation workflows.
- Cross-machine same-user sync is not covered by same-user-harness yet.
- Router risk-vs-intent classification needs fixtures/classifier work before the
  narrow `/auto-rollback` regex guard is generalized.

## Required follow-up

1. Adopt ADR-202.
2. Add a skeleton private-content surface manifest with conservative `local-only` defaults and `secret-never-touch` for credential patterns.
3. Add justified elevations only for specific surfaces that need cross-harness or export behavior.
4. Add projection/export guards plus a scheduled unknown-surface audit.
5. Add router negative-context guards for recovery/destructive primitives. The first narrow guard for `/auto-rollback` meta-discussions was added in `lib/skill_router.py`.
6. Feed wrong router suggestions into the ADR-201 `PromoteFromTelemetry` loop.

## Safe current reading of `/auto-rollback`

The current auto-rollback hook is a plan request, not an automatic destructive
rollback. It fires only after Agent/task/delegate output contains verify-apply
retry-exhaustion signals. The scary part in this incident was the router hint,
not destructive execution.
