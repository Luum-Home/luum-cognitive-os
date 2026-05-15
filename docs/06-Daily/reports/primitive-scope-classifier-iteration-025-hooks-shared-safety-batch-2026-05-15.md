# Primitive SCOPE classifier — Iteration 025 hook shared-safety batch

Date: 2026-05-15

## Goal

Start reviewing the 117 remaining hook unknowns that were all declared `SCOPE: both`.

This batch intentionally keeps a narrow criterion: only hooks whose behavior is generic repository/agent-session safety or quality governance were treated as true shared surfaces.

## Manual classification decision

Keep these 25 hooks as `both` and add `shared-surface` consumer proof:

- `hooks/adaptive-bypass.sh`
- `hooks/assumption-tracker.sh`
- `hooks/auto-verify.sh`
- `hooks/blast-radius.sh`
- `hooks/claim-validator.sh`
- `hooks/clarification-gate.sh`
- `hooks/completeness-check-llm.sh`
- `hooks/concurrent-write-guard.sh`
- `hooks/confidence-gate-llm.sh`
- `hooks/confidence-gate.sh`
- `hooks/context-budget-meter.sh`
- `hooks/context-diet.sh`
- `hooks/context-watchdog.sh`
- `hooks/destructive-git-blocker.sh`
- `hooks/direct-main-guard.sh`
- `hooks/dod-gate.sh`
- `hooks/large-file-advisor.sh`
- `hooks/prompt-quality-llm.sh`
- `hooks/resource-check.sh`
- `hooks/scope-creep-detector.sh`
- `hooks/scope-proportionality.sh`
- `hooks/secret-detector.sh`
- `hooks/token-budget-monitor.sh`
- `hooks/tool-loop-detector.sh`
- `hooks/trust-score-validator.sh`

## Evidence rule used

A hook is `both` in this batch only if its body/header implements behavior that is useful while maintaining COS and while operating an adopter project:

- repository safety: destructive git blocker, branch isolation, secret detection, concurrent write guard;
- agent quality gates: prompt quality, clarification, completeness, DoD, trust/confidence validation;
- session/resource hygiene: token/context/resource budgets, tool-loop detection, large-file advice;
- scope/claim governance: blast radius, scope creep, proportionality, file-claim verification.

These do not require COS source paths such as `docs/02-Decisions/adrs/`, primitive manifests, package parity, self-install, or COS-only daemons to make sense.

## Metadata added

For each hook, added a `primitive-consumer-availability.yaml` row:

```yaml
status: shared-surface
```

with concrete rationale. Existing lifecycle rows already describe runtime projection; the missing proof for classifier purposes was consumer availability.

## Before / after

Before this batch:

```json
{
  "total_unknown": 358,
  "by_prefix": {"hooks": 117, "rules": 83, "scripts": 158}
}
```

After this batch:

```json
{
  "total_unknown": 333,
  "by_prefix": {"hooks": 92, "rules": 83, "scripts": 158},
  "by_suggested_scope": {"both": 188, "os-only": 555, "project": 112, "unknown": 333}
}
```

## Next review target

The remaining 92 hooks should be reviewed in smaller semantic groups. Likely risky groups:

- agent/orchestrator/message bus hooks;
- Engram/session lifecycle hooks;
- ADR/rule/skill router hooks;
- project-docs/pending-truth/control-plane hooks.

Those should not be kept `both` just because they run inside adopter projects; they need repo-agnostic behavior, not COS-maintenance-only semantics.
