# Primitive SCOPE classifier — Iteration 026 semantic-pattern feedback

Date: 2026-05-15

## Goal

Convert repeated manual review findings into classifier logic so future primitive batches do not require rediscovering the same hook families by hand.

## Change

Added `semantic-pattern` evidence to `scripts/primitive_scope_classifier.py`.

This evidence is deliberately lower-priority than durable manifests and remains orthogonal to `distribution` tier. It does not replace paired portability proof for `both` claims.

## Learned shared-surface hook patterns

The classifier now recognizes declared-`both` hook families as shared when their names match generic repository/agent-session concerns:

- repo/git/security safety: destructive git, direct main, secret detection, concurrent writes;
- agent quality: clarification, completeness, prompt quality, confidence, Trust Report validation;
- verification/delivery: DoD, auto-verify, claim validation;
- context/resource hygiene: token/context/resource budgets, context diet/watchdog, large-file advice;
- scope/session safety: blast radius, scope creep, proportionality, tool-loop detection.

## Learned maintainer-only hook patterns

The classifier now flags COS maintainer hook families as `os-only` when the hook name and body are bound to COS internals such as `.cognitive-os/`, `docs/02-Decisions/`, `manifests/`, or Cognitive OS wording:

- ADR governance;
- rule/skill primitive governance;
- control-plane/profile governance;
- Engram lifecycle hooks;
- pending-truth ledger hooks;
- self-install/self-knowledge hooks.

## Guardrails

- Semantic patterns do not inspect or infer from `distribution: core|team|lab|maintainer`.
- Shared patterns require the primitive to be explicitly declared `SCOPE: both`; they do not promote explicit `os-only` hooks by name alone.
- COS maintainer patterns require internal COS tokens in the hook body before suggesting `os-only`.
- Exact/stem-prefix matching avoids accidental substring matches such as treating `plan-claim-validator` as `claim-validator`.

## Before / after

Before this classifier feedback:

```json
{
  "total_unknown": 333,
  "hooks_unknown": 92
}
```

After this classifier feedback:

```json
{
  "total_unknown": 320,
  "hooks_unknown": 79,
  "semantic_pattern_rows": 50,
  "semantic_pattern_scopes": {"both": 25, "os-only": 25}
}
```

The unknown reduction comes from common hook families now producing explicit evidence. The increased contradiction count is expected: several remaining declared-`both` COS governance hooks now have evidence-derived `os-only` suggestions and should be reviewed next.

## Validation

- `tests/unit/test_primitive_scope_classifier.py` covers shared safety hooks, COS governance hooks, and distribution orthogonality.
- Full targeted validation should run before commit.
