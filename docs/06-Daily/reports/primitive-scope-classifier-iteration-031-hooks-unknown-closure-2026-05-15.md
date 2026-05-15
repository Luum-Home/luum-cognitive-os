# Primitive SCOPE classifier — Iteration 031 hook unknown closure

Date: 2026-05-15

## Goal

Close the remaining 43 hook unknowns before moving to skill contradictions.

## Manual classification decision

Kept 42 hooks as `SCOPE: both` and added shared-surface evidence. They cover reusable runtime behavior:

- audit/observability: audit-id enrichment, git-context capture, task recorder;
- quality/recovery: auto-refine, auto-repair, error learning/pattern/pipeline, completion/consequence, clarification interception;
- cross-session/session lifecycle: session init/cleanup/heartbeat/learning/sanity/startup/wrapup and cross-session coordination/event/peer context;
- memory/context hygiene: memory prefetch, pre-compaction flush, query-tailored context, result truncation, user-prompt capture;
- planning/docs/research governance: pending-truth checks, plan claim validator, project docs convention, research quality validator;
- runtime security/health: cosd auth guard, host tool doctor, rate-limit shim, state retention audit.

Reclassified 1 hook to `SCOPE: os-only`:

- `hooks/scope-marker-portability-gate.sh` — gates COS primitive SCOPE marker changes and KD6 portability proof, so it is taxonomy governance for COS maintainers.

## Classifier robustness update

Added exact semantic patterns for these reviewed hook names. This closes hook unknowns without adding broad wildcard promotions.

## Before / after

Before:

```json
{"total_unknown": 284, "hooks_unknown": 43}
```

After:

```json
{"total_unknown": 241, "hooks_unknown": 0, "rules_unknown": 83, "scripts_unknown": 158}
```

Hook contradictions remain 0. The remaining taxonomy debt is now rules + scripts, plus non-hook contradictions already identified.
