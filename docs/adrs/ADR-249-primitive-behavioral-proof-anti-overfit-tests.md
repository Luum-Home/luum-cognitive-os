---
adr: 249
title: Primitive Behavioral Proof and Anti-Overfit Testing
status: accepted
relationship_chain_exempt: true
date: 2026-05-08
supersedes: []
superseded_by: null
extends: [ADR-240, ADR-247, ADR-248]
implementation_files:
  - manifests/primitive-behavior-contracts.yaml
  - scripts/primitive-behavior-audit.py
  - tests/unit/test_primitive_behavior_audit.py
tier: maintainer
tags: [testing, primitive-coherence, behavioral-proof, anti-overfit, control-plane]
---

<!-- ADR_RELATION_CHAIN_EXEMPT: part of the 2026-05-08 implementation-ledger ADR burst; relationship depth is tracked by control-plane audits rather than new transitive ADR scope. -->

# ADR-249: Primitive Behavioral Proof and Anti-Overfit Testing

## Status

Accepted — Slice A implemented.

## Context

ADR-240 through ADR-248 moved Cognitive OS from ad-hoc primitive fixes toward a
manifest-driven control plane: primitive coherence, postmortem regression audits,
release freeze transactions, and a recurring control-plane audit loop.

That still leaves a deeper failure mode: **tests can overfit to the existence or
shape of a primitive instead of proving the behavior that protects the
operator**.

Examples of insufficient proof:

| Weak test | Why it overfits |
|---|---|
| `hooks/foo.sh` exists | Does not prove it is wired or blocks the unsafe action |
| `.claude/settings.json` contains `foo.sh` | Does not prove the hook fails closed on the real payload |
| ADR says `Implemented` | Does not prove runtime behavior follows the ADR |
| A test greps for a string | Does not prove the primitive executes in the real path |
| A manifest validates | Does not prove the consumer honors the manifest |
| A happy-path fixture passes | Does not prove false negatives, bypasses, races, or failure modes are covered |

The operator summarized the concern as test overfitting: tests may be tied to a
prompt, file, hook, skill, or rule instead of testing how the SO behaves under
pressure.

## Decision

A critical governance primitive is not considered behaviorally proven until it
has a declared **behavioral proof contract** with at least one falsification
probe.

Introduce:

```text
manifests/primitive-behavior-contracts.yaml
scripts/primitive-behavior-audit.py
```

The manifest declares, per critical primitive:

- the primitive or surface under test;
- the ADR that owns the behavior;
- the proof test files expected to exist;
- the minimum behavioral evidence required in those tests;
- overfit smells that are allowed to warn but not substitute for proof.

The audit script is read-only. It does not run the heavy suite. It checks that
the declared proof files contain evidence of:

1. **negative/falsification probes** — input that should fail closed;
2. **runtime execution** — the primitive or public API is actually invoked;
3. **fail-closed assertion** — exit code, exception, or `status: block` is asserted;
4. **boundary evidence** — bypasses, positive controls, or preservation cases are
   tested where relevant.

## Proof levels

| Level | Question | Sufficient for critical primitive? |
|---|---|---|
| Existence | Does the file/config exist? | No |
| Wiring | Is it registered in the intended path? | No, but required |
| Contract | Does a direct API call return expected output? | Partial |
| Behavioral proof | Does a realistic falsification attempt fail closed? | Yes |
| Chaos / race proof | Does it survive kill/race/concurrency? | Required for high-risk primitives |

## Slice A critical contracts

Slice A starts with the incident classes that caused the ADR-239+ postmortems:

| Primitive | Required behavioral proof |
|---|---|
| Branch switch blocker | `git switch` / `git checkout <branch>` fails closed, and explicit bypass is tested |
| Pre-public sensitive data gate | configured sensitive token, X-COS trailers, fake provider authors block; human author email is preserved |
| History sanitization | blob content rewrites; author metadata and commit messages remain preserved unless explicitly enabled |
| Release freeze | dirty tree, active claims, and transaction mismatch block destructive/public operations |
| Hook registration/classification projection | active hooks missing registration block; manual/future hooks registered automatically block |

## Relationship to existing audits

This ADR complements, but does not replace, existing detectors:

| Audit | Scope |
|---|---|
| `primitive-coherence-audit` | topology, surfaces, ownership, registration, ordering |
| `cos-postmortem-regression-audit` | ADR-specific regression artifacts and forbidden patterns |
| `cos-control-plane-audit` | lane aggregator, metrics, remediation queue |
| `primitive-behavior-audit` | proof quality: does the test suite contain falsification evidence? |

## Consequences

Positive:

- Prevents false confidence from tests that only assert a hook/script exists.
- Makes “implemented” claims depend on behavioral proof, not prose or wiring.
- Gives future primitives a repeatable proof contract before they become part of
  release readiness.

Negative:

- Static proof audit cannot guarantee full semantic coverage. It is a guardrail,
  not a replacement for manual adversarial review or chaos tests.
- Manifest patterns must be maintained when tests are refactored.

## Acceptance criteria

```bash
python3 scripts/primitive-behavior-audit.py --json
python3 -m pytest tests/unit/test_primitive_behavior_audit.py -q
scripts/cos-control-plane-audit --lane hook-fast --json
```

Expected: all pass with zero block findings on the current repo.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Trust existing unit/behavior tests | Existing tests can overfit to files, manifests, or happy paths. The failure class is proof quality, not raw test count. |
| Manually review every critical test during release | Manual review remains useful, but it is not repeatable and does not create stable findings, metrics, or remediation queue entries. |
| Run the full test suite from every hook | Too expensive for hot paths. ADR-249 is a static proof-quality audit that points to missing behavioral evidence; heavy suites remain targeted/release lanes. |
| Require chaos tests for every primitive immediately | Correct long-term direction for high-risk primitives, but too broad for Slice A. Slice A requires falsification evidence first and leaves chaos/race hardening as an escalation tier. |

## Verification

Slice A verification:

```bash
python3 scripts/primitive-behavior-audit.py --json
scripts/cos-control-plane-audit --lane hook-fast --json
python3 -m pytest tests/unit/test_primitive_behavior_audit.py -q
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

Expected current result: `primitive-behavior-audit` passes with zero findings,
`hook-fast` includes the ADR-249 audit and passes, and ADR contract tests accept
this ADR's required sections.
