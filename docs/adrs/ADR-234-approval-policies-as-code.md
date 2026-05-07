# ADR-234 — Approval Policies as Code

<!-- SCOPE: OS -->

**Status**: Accepted — Slice A implemented (2026-05-07)  
**Date**: 2026-05-07  
**Related**: ADR-216 (tool discovery gate), ADR-232 (sandbox tiers), ADR-235 (detached daemon)

---

## Context

COS has many shell hooks with embedded allow/deny logic. Research recommended a COS-native YAML policy evaluator before adopting heavy engines such as OPA, Cedar, or Casbin.

## Decision

Introduce `policies/*.yaml` with a small local evaluator. Slice A is intentionally simple: glob-style matching over action fields, deny/block precedence, and default-allow to avoid breaking existing hooks during migration.

## Implementation status (2026-05-07)

Implemented Slice A:

- `packages/agent-lifecycle/lib/policy_eval.py` loads/evaluates policies.
- `lib/policy_eval.py` package symlink.
- `policies/destructive-bash.yaml` sample policy.
- `manifests/policy-as-code.yaml` declares mode and invariants.
- `scripts/cos-policy-eval` exposes JSON/strict CLI.
- Unit/audit/behavior tests cover block/ask/default allow, manifest, and CLI strict exit code.

Not implemented yet:

- Migration of existing hooks to `policy_eval`.
- Claude/Codex settings projection from policies.
- External policy engines.

## Hard rules

- No OPA/Cedar/Casbin dependency in default local mode.
- Block/deny wins over ask/warn/allow.
- Slice A is observe/migration substrate; hook replacement requires per-hook tests.
