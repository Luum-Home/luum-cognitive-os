# ADR-234 — Approval Policies as Code

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted — Slices A–C implemented (2026-05-07)  
**Date**: 2026-05-07  
**Related**: ADR-216 (tool discovery gate), ADR-232 (sandbox tiers), ADR-235 (detached daemon)

---

## Context

COS has many shell hooks with embedded allow/deny logic. Research recommended a COS-native YAML policy evaluator before adopting heavy engines such as OPA, Cedar, or Casbin.

## Decision

Introduce `policies/*.yaml` with a small local evaluator. Slice A is intentionally simple: glob-style matching over action fields, deny/block precedence, and default-allow to avoid breaking existing hooks during migration.

### Default tier (enforceable)

The default policy tier is **MIGRATION-COMPATIBLE LOCAL EVALUATOR, DEFAULT-ALLOW, BLOCK-WINS**. This is the contract `lib/policy_eval.py` enforces today:

| Dimension | Default behaviour | Enforcement point |
|---|---|---|
| **Engine** | COS-native YAML evaluator. OPA/Cedar/Casbin are NOT loaded at the default tier; activation requires a separate ADR. | `lib/policy_eval.py` |
| **Default verdict** | `allow` when no rule matches. This is intentional — it preserves migration compatibility while hooks land per-policy fallbacks. | `lib/policy_eval.py::evaluate()` |
| **Precedence** | `block`/`deny` > `ask`/`warn` > `allow`. Multiple matching rules: most-restrictive verdict wins. | `lib/policy_eval.py::evaluate()` |
| **When activated** | Per-hook opt-in. Each migrated hook (`hooks/destructive-rm-blocker.sh`, `hooks/protected-config-write-guard.sh`) calls `cos-policy-eval` *before* its legacy parser. Legacy parser remains as fallback until per-hook parity tests cover the policy. | `hooks/*.sh` migration sites |
| **Settings projection** | PLAN-ONLY. `cos-policy-settings-projection` emits PreToolUse hook plans for Claude Code / Codex consumers but never mutates user-global `settings.json`. Operator copies the plan manually. | `scripts/cos-policy-settings-projection` |
| **Owner** | platform-safety. New policy bundles require a new YAML under `policies/` plus an entry in `manifests/policy-as-code.yaml`. | This ADR + manifest |

**Bundles shipped by default** (Slice A–C):

- `policies/destructive-bash.yaml` — wired into `hooks/destructive-rm-blocker.sh`.
- `policies/protected-config-write.yaml` — wired into `hooks/protected-config-write-guard.sh`.

No other policy bundle is loaded by default. Adding a third bundle requires
both a YAML file under `policies/` and a hook (or other consumer) that calls
the evaluator — per the project rule "no metadata without consuming code".

**Enforceability**: `tests/audit/test_adr_contracts.py` plus the per-hook
unit/behavior suites cover each row. The default-tier contract is therefore
testable, not descriptive.

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

## Consequences
- The ADR can be checked by the common ADR contract audit.
- Future amendments must preserve this decision record instead of relying on conversation history.

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
