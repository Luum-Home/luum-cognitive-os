---
adr: 283
title: Script Exposure Audit and Invocation Ratchet
status: accepted
implementation_status: implemented
classification_basis: 'implemented: ADR-283 ships a script exposure audit library, CLI, and unit/behavior tests that classify agentic primitives and maintainer tools without skill consumers or other invocation paths.'
date: 2026-05-12
supersedes: []
superseded_by: null
extends: [ADR-072, ADR-120, ADR-206, ADR-274, ADR-281]
implementation_files:
  - lib/script_exposure_audit.py
  - scripts/cos-script-exposure-audit
  - tests/unit/test_script_exposure_audit.py
  - tests/behavior/test_script_exposure_audit_cli.py
tier: maintainer
tags: [agentic-primitives, skills, exposure, maintainer-tools, audit, token-efficiency]
---
# ADR-283: Script Exposure Audit and Invocation Ratchet

## Status

Accepted and implemented — 2026-05-12.

<!-- SCOPE: OS -->

**Date**: 2026-05-12

## Context

Cognitive OS has grown enough that a script existing in `scripts/` no longer
means an agent will know when to call it. This creates the same scalability
problem that ADR-282 solved for product answers: agents repeatedly rediscover a
large surface, spend tokens inspecting docs and ledgers, and still may miss the
right operational primitive.

The specific smell is not “many scripts”. The smell is unowned invocation:

```text
script exists
→ no skill consumer
→ no hook consumer
→ no command/router path
→ no explicit demotion to lab/migration/driver-specific
→ nobody reliably calls it
```

The primitive readiness ledgers already contain most of the raw facts, but there
was no dedicated P0/P1/P2/P3 audit that turns those facts into an actionable
exposure backlog.

## Decision

Add an ADR-283 script exposure audit primitive:

```bash
scripts/cos-script-exposure-audit
scripts/cos-script-exposure-audit --json
scripts/cos-script-exposure-audit --fail-p0
```

The audit reads `docs/reports/primitive-readiness-ledger-scripts-latest.json` by
default and classifies scripts into these priorities:

| Priority | Meaning | Expected action |
|---|---|---|
| P0 | `agentic-primitive` with no skill consumer | Add a skill consumer, document an equivalent hook/router route, or explicitly demote. |
| P1 | `maintainer-tool` with `total_consumers=0` | Archive, register, or wire to a maintainer entrypoint. |
| P2 | `maintainer-tool` with no skill consumer but with docs/tests/scripts consumers | Classify as internal or promote to a skill when it is meant for agents. |
| P3 | `lab`, `migration-only`, or `driver-specific` without skill consumer | Allowed exception if the lifecycle role is correct. |

The output is intentionally small and machine-readable:

```json
{
  "schema_version": "script-exposure-audit/v1",
  "adr": "ADR-283",
  "status": "warn",
  "summary": {
    "by_priority": {"P0": 60, "P1": 12, "P2": 300, "P3": 40, "OK": 100}
  },
  "findings": []
}
```

The audit does not claim every script needs a skill. It claims every script with
an agentic or maintainer role needs an explicit invocation story: skill, hook,
router, documented internal ownership, or demotion.

## Consequences

### Positive

- Agents can ask one cheap audit instead of rereading the whole scripts surface.
- Agentic primitives that are not reachable through skills become visible as P0.
- Maintainer tools with no consumers become visible as P1 instead of silently
  accumulating.
- Lab, migration-only, and driver-specific scripts remain legitimate exceptions
  instead of creating noisy “everything must be a skill” pressure.
- `--fail-p0` gives future CI or release lanes a ratchet without blocking the
  first inventory pass.

### Negative / trade-offs

- The audit depends on the freshness and fidelity of the primitive readiness
  scripts ledger.
- Some P0 rows may already have hook/router exposure; they still need either a
  skill, documented equivalent route, or explicit demotion to avoid ambiguity.
- The first version classifies command-router exposure heuristically from ledger
  consumers; richer router manifests can replace that later.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Manually inspect `scripts/` when confused | Repeats the token-heavy discovery loop and produces inconsistent answers. |
| Require every script to have a skill | Too blunt; lab, migration-only, driver-specific, and private maintainer helpers can be valid without skills. |
| Only rely on primitive readiness ledgers | Ledgers contain facts but not the P0/P1/P2/P3 backlog semantics needed by agents and maintainers. |
| Immediately delete zero-consumer scripts | Unsafe during reconstruction; visibility and classification should precede deletion. |

## Verification

```bash
python3 -m py_compile lib/script_exposure_audit.py scripts/cos-script-exposure-audit
python3 -m pytest tests/unit/test_script_exposure_audit.py tests/behavior/test_script_exposure_audit_cli.py -q
scripts/cos-script-exposure-audit --json
```
