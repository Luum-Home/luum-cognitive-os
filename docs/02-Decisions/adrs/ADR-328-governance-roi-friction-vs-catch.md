---
adr: 328
title: Governance ROI Friction-vs-Catch Ratios
status: accepted
implementation_status: partial
date: '2026-05-20'
supersedes: []
superseded_by: null
implementation_files:
- scripts/cos_governance_roi.py
- scripts/cos-status.sh
- scripts/cos
- scripts/hook-timing-wrapper.sh
- hooks/_lib/governance-policy.sh
- hooks/destructive-git-blocker.sh
- hooks/destructive-rm-blocker.sh
- hooks/direct-main-guard.sh
- hooks/protected-config-write-guard.sh
- hooks/network-egress-guard.sh
- hooks/release-guard.sh
- tests/unit/test_cos_governance_roi.py
- tests/behavior/test_cos_status.py
- tests/contracts/test_hook_timing_wrapper.py
tier: maintainer
classification_basis: Cognitive OS governance only pays when guard friction prevents real work loss, security risk, high-blast-radius mistakes, or multi-agent coordination failure; the system needs explicit reviewed catch evidence and phase-aware blocking thresholds.
tags:
- governance-roi
- friction
- phase-aware
- cos-status
- metrics
---

# ADR-328 — Governance ROI Friction-vs-Catch Ratios

## Status

Accepted. Read-side dashboard, write-side catch logging, optional blocked-hook prompts, weighted severity normalization, and the executable phase-policy adapter are implemented. Initial hard-blocking hooks (`destructive-git-blocker`, `destructive-rm-blocker`, `direct-main-guard`) and the next high-friction guard set (`protected-config-write-guard`, `network-egress-guard`, `release-guard`) call the adapter. Full per-guard phase-policy enforcement remains incremental: each additional hard-blocking hook must call the policy adapter before returning a block.

## Context

Cognitive OS governance is not a neutral benefit in every context. It pays for itself when the work has high blast radius, multiple agents, security sensitivity, release risk, destructive operations, or meaningful risk of silent work loss. For single-file, exploratory, or low-risk single-developer work, the same guards can create more friction than value.

Recent dogfooding exposed both sides:

- Correct governance prevented silent loss around stash safety, dispatch queue collapse, validation locks, and empty agent payloads.
- Governance itself also produced bugs and false friction: stale validation locks, queue stalls without an automatic tick, and shell/JSON corruption.

A raw count of guard blocks is therefore insufficient. The OS must distinguish **block frequency** from **confirmed useful catches** and tune blocking posture by project phase.

## Decision

Add a first-class **friction-vs-catch ratio** to the governance ROI dashboard and expose it in `cos status`. This ADR has three executable surfaces:

1. **Read-side** — `cos governance roi` and `cos status` expose ROI, ratio, catch ledger counts, and phase policy.
2. **Write-side** — blocked hooks emit optional catch-review prompts, and operators can record reviewed outcomes with `cos governance catch log`.
3. **Enforcement adapter** — hooks can ask `cos governance policy --category <category>` whether a category is allowed to hard-block in the current phase.

### Catch ledger

Reviewed guard outcomes are recorded in an append-only JSONL ledger:

```text
.cognitive-os/metrics/governance-catches.jsonl
```

Minimal row shape:

```json
{"ts":"2026-05-20T00:00:00Z","hook":"dispatch-gate","verdict":"confirmed_valid_block","reason":"blocked empty Agent prompt that would have lost operator intent"}
```

Supported verdict families:

- `confirmed_valid_block` — operator verified the block was correct.
- `false_positive_override` — operator verified the block was noisy or wrong.
- `silent_loss_prevented` — the guard prevented hidden loss of work, intent, or state.
- `high_blast_radius_catch` — the guard prevented a high-impact mistake.

`silent_loss_prevented` and `high_blast_radius_catch` count as confirmed useful catches.

### Catch logging write-side

The hook timing wrapper records an optional prompt whenever a wrapped hook exits with code `2`:

```text
.cognitive-os/metrics/governance-catch-prompts.jsonl
```

The prompt defaults to `skip`; it never blocks and never forces an operator answer. It only prints a short command suggestion:

```bash
scripts/cos governance catch log \
  --hook dispatch-gate \
  --event PreToolUse \
  --verdict confirmed-valid-block \
  --reason "blocked empty Agent prompt"
```

Operators can also classify false friction:

```bash
scripts/cos governance catch log \
  --hook edit-lock \
  --verdict false-positive-override \
  --reason "blocked a safe unrelated edit"
```

### Ratio

The ratio is:

```text
weighted blocking guard events / weighted confirmed useful catches
```

If no reviewed catches exist, status is `unknown`; the dashboard must ask for ledger entries instead of pretending that all blocks were correct.

Severity weights normalize block value:

| Severity | Weight |
|---|---:|
| `low` | `0.5` |
| `medium` | `1.0` |
| `high` | `2.0` |
| `critical` | `3.0` |

Hooks can provide explicit severity in catch rows. Otherwise the dashboard infers severity from hook names: destructive/secret/credential/protected-config/lethal are critical, dispatch/validation/stash/private/clean-room are high, edit-lock/budget are medium, and clarification/router/suggest are low.

Bands:

| Ratio | Status | Meaning |
|---:|---|---|
| `<= 2x` | `paying` | Guard friction is justified by confirmed catches. |
| `> 2x` and `<= 5x` | `watch` | Keep the guard, but review/tune top blockers. |
| `> 5x` | `cut` | Demote, relax, or make high-friction guards advisory outside high-risk phases. |

### Phase-aware policy

Blocking posture is shaped by `cognitive-os.yaml → project.phase`:

| Phase | Policy |
|---|---|
| `reconstruction` | Minimal blocking: destructive git, destructive file erasure, protected-branch writes, secrets, credential leaks, security, and work-loss risks block; style/process/config/release friction should be advisory. |
| `stabilization` | Contract-focused blocking: tests, primitive drift, runtime-state loss, destructive operations, security, protected-branch writes, and contract failures can block; config/release friction remains advisory until production. |
| `production` | Strict release blocking: release, security, migration, public claims, protected config changes, destructive operations, and protected-branch writes block. |
| `maintenance` | Regression-focused blocking: regressions, security issues, unsafe changes, destructive operations, protected-branch writes, and data loss block. |

Hooks must not treat this table as decorative config. The canonical executable adapter is:

```bash
scripts/cos governance policy --category destructive-git --json
```

Unknown phases or unknown categories default to advisory, not blocking. This prevents new low-signal guards from becoming always-on friction accidentally.

### Status surface

`cos status` now includes a `governance_roi` object in JSON output and a compact pretty line:

```text
Governance ROI: net=-10.27m ratio=unknown unknown catches=0 false+=0 phase=reconstruction/minimal-blocking
```

## Consequences

### Positive

- The OS can measure whether governance is paying for real catches instead of assuming more blocking is safer.
- False positives become visible and reviewable.
- Phase-specific policy prevents always-on friction from dominating exploratory work.
- The dashboard gives the operator a concrete recut signal: `>5x` means cut or demote guards.

### Negative / trade-offs

- The ratio depends on operator-reviewed ledger rows; without review, the status is intentionally `unknown`.
- The initial benefit model remains heuristic and should not be treated as financial accounting.
- Phase policy is coarse; individual guards still need local judgment and tests.
- Full per-guard adoption requires touching each hard-blocking hook. Until then, `cos governance policy` is the contract new/changed blocking hooks must use.

## Alternatives rejected

- **Always-on strict governance for every phase** — rejected because dogfooding showed that low-risk exploratory work can pay more friction than safety value. Phase-aware policy keeps high-blast-radius blocks while demoting low-signal friction.
- **Dashboard-only ROI with no write-side ledger** — rejected because block counts alone cannot distinguish real catches from false positives. Reviewed catch rows are required before ratios can justify keeping or cutting guards.
- **Operator-forced catch review after every block** — rejected because mandatory feedback would add more friction than it measures. The prompt is non-blocking and defaults to skip.

## Verification

```bash
python3 -m py_compile scripts/cos_governance_roi.py
python3 -m pytest tests/unit/test_cos_governance_roi.py tests/behavior/test_cos_status.py tests/contracts/test_hook_timing_wrapper.py -q
scripts/cos governance roi --json
scripts/cos governance catch pending --json
scripts/cos governance policy --category destructive-git --json
scripts/cos status --json
```
