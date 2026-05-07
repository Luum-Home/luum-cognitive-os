# ADR-234 — Approval Policies as Code

<!-- SCOPE: OS -->

**Status**: Accepted — Slices A–C implemented (2026-05-07)  
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

Implemented Slices B–C:

- `hooks/destructive-rm-blocker.sh` evaluates `policies/destructive-bash.yaml` before its legacy parser.
- `hooks/protected-config-write-guard.sh` evaluates `policies/protected-config-write.yaml` before falling back to the legacy manifest parser.
- `scripts/cos-policy-eval` accepts `--file-path` as well as `--command`.
- `scripts/cos-policy-settings-projection` emits Claude Code/Codex PreToolUse hook plans from policy manifests without mutating settings.

Not implemented yet:

- External policy engines; OPA/Cedar/Casbin remain deferred until multi-tenant/cloud policy inheritance needs them.

## Hard rules

- No OPA/Cedar/Casbin dependency in default local mode.
- Block/deny wins over ask/warn/allow.
- Migrated hooks must keep legacy fallback until policy parity is covered by per-hook tests.
- Settings projection is plan-only; user-global settings mutation remains out of scope.
