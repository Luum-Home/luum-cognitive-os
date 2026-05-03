---
adr: 105
title: Bilateral Claim Verification Contract
status: implemented
date: 2026-05-02
supersedes: []
superseded_by: null
implementation_files:
  - hooks/claim-validator.sh
  - hooks/plan-claim-validator.sh
  - hooks/orchestrator-claim-gate.sh
  - scripts/verify_plan_claims.py
  - scripts/verify-archived.sh
  - scripts/orchestrator_claim_gate.py
  - lib/orchestrator_verify.py
tier: strict
tags: [verification, claims, orchestrator, bilateral]
---

# ADR-105 — Bilateral Claim Verification Contract

<!-- SCOPE: OS -->

**Status**: Accepted — Partially Implemented
**Date**: 2026-05-02
**Author**: Maintainer
**Related**: ADR-088 (provenance markers), ADR-098 (multi-agent file coordination), ADR-104 (startup circuit breaker), `docs/incidents/2026-05-02-false-done-compounding.md`

## Status

Accepted — Partially Implemented. The contract is now backed by `hooks/claim-validator.sh`, `hooks/plan-claim-validator.sh`, `hooks/orchestrator-claim-gate.sh`, `scripts/verify_plan_claims.py`, `scripts/verify-archived.sh`, `scripts/orchestrator_claim_gate.py`, and `lib/orchestrator_verify.py`. Remaining work is to add domain-specific verifiers when new claim verbs need richer predicates.

## Context

On 2026-05-02, a sub-agent committed a plan as "done" based on a partial verification: 3 files present in `docs/archive/hooks/` was treated as proof that "3 DELETE hooks already archived." The inverse check — that the originals were absent from `hooks/` and absent from `settings.json` — was never run. The files existed in both locations. One "archive" was a symlink.

This is a **bilateral claim failure**: the agent verified one half of a two-sided predicate and reported the whole predicate as true.

High-stakes claims appear throughout agent reports, commit messages, and plan files:

- "archived" (implies: archive present AND original absent AND no config refs)
- "wired" (implies: code references the wired target AND target exists)
- "integrated" (implies: integration code calls the target AND target is reachable)
- "registered" (implies: registration entry exists AND registered entity exists)
- "done" / `[x]` in a plan (implies: all sub-conditions verified, not just stated)

Every one of these has an optimistic partial form (the "present" half) and a necessary inverse (the "absent / referenced / reachable" half). Agents default to the optimistic partial.

## Decision

### 1. High-Stakes Claim Definition

A **high-stakes claim** is any assertion in a commit message, agent report, or plan file that uses one of these verbs with respect to a filesystem artifact or system configuration:

`archived`, `deleted`, `removed`, `wired`, `integrated`, `registered`, `done` (as plan closure), `closed`, `migrated`, `tested`, `verified`, `claimed`

High-stakes claims require bilateral verification before they are accepted as true.

### 2. Bilateral Verification Contract

A claim is verified when the agent (or orchestrator) can produce an executable command whose stdout proves the **complete predicate** — not the optimistic partial.

| Claim verb | Optimistic partial (insufficient) | Required bilateral proof |
|---|---|---|
| `archived` | archive path exists | archive present **AND** original absent **AND** grep config files returns nothing |
| `deleted` / `removed` | `rm` exit 0 | path does not exist in working tree **AND** not referenced in any config |
| `wired` | target file exists | caller code references target **AND** target resolves at call site |
| `registered` | registration block exists in config | registered entity exists at the path the config points to |
| `done` (plan checkbox) | sub-steps mentioned | each sub-step has an attached verification command with captured output |

Proof is a shell command or pipeline whose exit code 0 means "predicate is fully true." A directory listing is not proof of deletion. A file existence check is not proof of registration.

### 3. Plan Checkbox Extension

Plan files that use `[x]` to close items MUST attach an inline verification record:

```
[x] Archive completeness-check.sh (verified: ls hooks/completeness-check.sh 2>&1 → No such file; grep -r completeness-check .claude/settings.json cognitive-os.yaml → no match)
```

Bare `[x]` without `(verified: ...)` is treated as **unverified** by any downstream agent or orchestrator reading the plan. An orchestrator reading a bare `[x]` on a high-stakes claim MUST run its own bilateral check before trusting it.

### 4. Orchestrator Self-Check Protocol

When an orchestrator receives a sub-agent report containing a high-stakes claim:

1. Extract all high-stakes claim verbs from the report.
2. For each claim, run the bilateral proof command independently (not sourced from the agent's report).
3. If any proof fails, do NOT commit. Surface the discrepancy to the operator.
4. Only after independent proof succeeds: commit, mark plan checkbox `[x]`, and attach the verification command.

This is the orchestrator's responsibility, not the sub-agent's. Sub-agents can lie (by omission or by optimistic inference). The orchestrator is the final gate.

### 5. Verification Helper Strategy

A domain-specific helper `scripts/verify-archived.sh <file>` SHALL be implemented to encapsulate the bilateral archive check:

```bash
# Exit 0 only when ALL three hold:
# 1. docs/archive/hooks/<file> exists AND is a regular file (not symlink)
# 2. hooks/<file> does not exist
# 3. grep -r <file> .claude/settings.json cognitive-os.yaml → empty
```

Similar helpers for other claim types (verify-wired, verify-registered) SHOULD be created when patterns recur. The shared orchestrator surface is `scripts/orchestrator_claim_gate.py`, which composes `lib/orchestrator_verify.py` and plan verifiers without trusting sub-agent supplied commands. The existence of these helpers makes bilateral verification a one-liner, removing the incentive to skip it.

### 6. Commit Message Policy

Commit messages containing high-stakes claim verbs MUST reference the proof command or its output in the message body or in a linked PR/issue. A bare verb ("archived X", "wired Y") in a commit message with no proof reference is a policy violation and SHOULD be flagged by `adr-detector.sh`.

### 7. Applicability

This contract applies to:

- All sub-agent reports delivered to an orchestrator
- All plan file checkbox transitions from `[ ]` to `[x]`
- All commit messages on the `main` branch touching plan files, hooks, or configuration
- All `git commit` / `git push` attempts observed through portable Bash hook surfaces

It does NOT apply to:

- Work-in-progress branches before commit
- Documentation-only commits with no filesystem claims
- Commits that introduce new artifacts (creation, not closure)

## Consequences

### Positive

- False-done claims are structurally harder: bilateral proof is required, not optional.
- Plan files carry their own verification audit trail (`verified:` inline).
- Orchestrators have a defined self-check protocol rather than trusting TRUST_REPORT scores.
- Domain-specific helpers standardize what bilateral means per claim type.

### Negative

- Plan file format changes: existing `[x]` entries without `(verified:)` annotations are technically non-conformant. Backfill is impractical; apply forward only.
- Orchestrator self-check adds latency per committed wave (~2-5 commands per high-stakes claim). Cost is bounded and dominated by the N-session recovery cost of a missed false-done.
- Helpers must be maintained as paths and config file names evolve.

### Neutral

- TRUST_REPORT scores are unaffected. This ADR adds an orthogonal check; it does not replace trust scoring.

## Alternatives rejected

| Alternative | Rejection reason |
|---|---|
| Require sub-agents to self-verify | Sub-agents already do this and it fails. The optimistic partial is what they naturally produce. The orchestrator is the correct gate. |
| Enforce via CI on plan files | Plan files change in every session; CI latency is too slow for real-time commit gating. Pre-commit is the right layer. |
| Trust TRUST_REPORT 90+ as sufficient | The incident showed 90+ TRUST_REPORT is compatible with false factual claims when the verification is adjacent (not inverse) to the claim. |

## Verification

Policy is verified by:

1. `scripts/verify-archived.sh` exits 0 only when all three bilateral conditions hold.
2. `hooks/plan-claim-validator.sh` detects bare `[x]` transitions without `(verified:)` in plan files.
3. `hooks/orchestrator-claim-gate.sh` blocks portable Bash `git commit` / `git push` attempts when high-stakes claims lack independent evidence.
4. `lib/orchestrator_verify.py` and `scripts/orchestrator_claim_gate.py` map claim verbs to deterministic repo verifiers.

```bash
# ADR contract smoke check: the ADR must keep the required sections and at
# least one executable verification block.
python3 -m pytest tests/audit/test_adr_contracts.py tests/contracts/test_orchestrator_verify.py tests/contracts/test_orchestrator_claim_gate.py -q
```

## References

- Matrix: `docs/architecture/claim-verification-matrix.md`

- Incident: `docs/incidents/2026-05-02-false-done-compounding.md`
- ADR-106: multi-session safety primitives (companion ADR)
- ADR-088: provenance markers (commit-level evidence chain)
- `rules/adversarial-review.md`: forced-findings review policy
- `rules/trust-score.md`: trust scoring (orthogonal, not superseded)
