---
adr: 312
title: Harness-Normalized Primitive Closure
status: accepted
implementation_status: implemented
date: 2026-05-14
implementation_files:
- manifests/harness-projection.yaml
- manifests/harness-driver-capabilities.yaml
- manifests/primitive-contracts.yaml
- manifests/primitive-closure-ratchet.yaml
- scripts/primitive_closure_ratchet.py
- tests/contracts/test_primitive_closure_ratchet.py
tier: maintainer
tags:
- primitive-closure
- harnesses
- projection
- governance
classification_basis: harness-normalized primitive closure manifest, ratchet implementation,
  and contract tests are implemented; no remaining in-scope work for this ADR
---
# ADR-312: Harness-Normalized Primitive Closure

## Status

Accepted

- **Status**: Accepted
- **Date**: 2026-05-14
- **Owner**: Cognitive OS maintainers
- **Scope**: governance, harness projection, primitive closure, runtime parity

## Context

ADR-311 introduced a primitive closure ratchet for high-risk governance hooks, but
its first manifest shape used `claude_required` and `codex_required` booleans.
That closed the immediate Claude/Codex contradiction while leaving a deeper
contradiction surface:

1. `manifests/harness-projection.yaml` already models many implemented harnesses,
   including structural instruction harnesses and Shell/CI.
2. `manifests/harness-driver-capabilities.yaml` already records that runtime hook
   semantics vary by harness.
3. `manifests/primitive-contracts.yaml` already records runtime support beyond
   Claude and Codex.
4. `manifests/primitive-closure-ratchet.yaml` only asked whether Claude and Codex
   projected a critical hook.

That split allowed agents to repair one driver pair and still claim primitive
closure while leaving Cursor, VS Code Copilot, AGENTS.md, OpenCode, Shell/CI, and
other implemented harness classes unclassified. The bug was not that every
harness must enforce every hook; many harnesses are intentionally structural or
command-surface only. The bug was that the closure primitive did not require an
explicit per-harness classification before claiming closure.

## Decision

Replace Claude/Codex-only closure booleans in the primitive closure ratchet with
`harness_requirements`.

Each critical primitive must now classify every implemented harness from
`manifests/harness-projection.yaml`, either directly or through an explicit group
with `applies_to`.

Supported statuses are:

- `required`: the harness must have a runtime projection checked by the ratchet.
- `capability_gap`: the harness is in scope but lacks the lifecycle capability
  needed for this primitive.
- `adapter_gap`: the host has a plausible runtime surface, but COS has not signed
  an adapter/runtime smoke for this primitive.
- `structural_advisory`: the harness projects instructions/rules/skills but does
  not claim native runtime hook enforcement.
- `command_surface`: the harness can run command-level audits or workflows but
  cannot intercept every interactive tool/skill event.
- `roadmap`: the harness is tracked but not implemented enough for this primitive.

Non-`required` statuses must include a reason. This keeps gaps explicit and
prevents future agents from silently treating structural projection as runtime
enforcement.

The ratchet still checks actual runtime projection for `required` Claude and
Codex requirements, including dispatcher-mediated Codex routes. It also blocks if
a future manifest marks another harness `required` before the ratchet knows how
to verify that harness's runtime projection.

## Consequences

### Positive

- Primitive closure becomes harness-normalized instead of driver-pair-specific.
- Agents can no longer claim closure by checking only Claude and Codex when the
  OS has more implemented projection surfaces.
- Structural/advisory harnesses remain honest: they are covered by the contract
  without overclaiming runtime enforcement.
- Future runtime-capable harnesses, such as an OpenCode plugin adapter, must add
  a checker before being marked `required`.

### Negative / Tradeoffs

- The closure manifest is more verbose because it must classify all implemented
  harness classes.
- Adding a new implemented harness now requires updating critical primitive
  closure classifications or the ratchet blocks.
- Structural harnesses are still not runtime-enforcing; this ADR prevents
  contradiction, not the runtime gap itself.

## Alternatives rejected

- **Keep Claude/Codex booleans and rely on other manifests.** Rejected because multiple manifests already had broader harness context, but the ratchet was the primitive that agents used to claim closure. The closure primitive itself must encode the broader harness contract.
- **Require every implemented harness to enforce every critical hook.** Rejected because Cursor, AGENTS.md, Shell/CI, and similar surfaces do not currently have native interactive lifecycle interception. Forcing them to appear runtime-equal would create a false claim.
- **Treat non-Claude/Codex harnesses as out of scope.** Rejected because they are already implemented projection targets in the SO. The contract must classify them even when the classification is structural or a capability gap.

## Implementation

- `manifests/primitive-closure-ratchet.yaml` now uses `harness_requirements` for
  critical hook projections.
- `scripts/primitive_closure_ratchet.py` expands grouped harness requirements,
  validates supported statuses, requires reasons for non-runtime statuses, and
  blocks missing implemented harness classifications.
- `tests/contracts/test_primitive_closure_ratchet.py` proves that legacy
  Claude/Codex-only booleans are rejected, implemented harnesses must be
  classified, and non-required statuses need reasons.

## Acceptance Criteria

1. `scripts/primitive_closure_ratchet.py --json` exits `0` on the current repo.
2. A critical primitive manifest using only `claude_required`/`codex_required`
   fails the contract.
3. A critical primitive manifest that omits an implemented harness fails the
   contract.
4. A non-`required` harness status without a reason fails the contract.
5. Dispatcher-mediated Codex runtime closure still passes only when the dispatcher
   source routes the required hook.

## Verification

```bash
.venv/bin/python -m pytest tests/contracts/test_primitive_closure_ratchet.py -q
.venv/bin/python scripts/primitive_closure_ratchet.py --json
```
