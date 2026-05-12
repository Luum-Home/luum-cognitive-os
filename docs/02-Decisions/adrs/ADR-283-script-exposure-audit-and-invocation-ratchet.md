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

The audit reads `docs/06-Daily/reports/primitive-readiness-ledger-scripts-latest.json` by
default and classifies scripts into these priorities:

| Priority | Meaning | Expected action |
|---|---|---|
| P0 | `agentic-primitive` with no skill consumer | Add a skill consumer, document an equivalent hook/router route, or explicitly demote. |
| P1 | `maintainer-tool` with `total_consumers=0` | Archive, register, or wire to a maintainer entrypoint. |
| P2 | `maintainer-tool` with no skill consumer but with docs/tests/scripts consumers | Classify as internal or promote to a skill when it is meant for agents. |
| P3 | `lab`, `migration-only`, or `driver-specific` without skill consumer | Allowed exception if the lifecycle role is correct. |

P0 is further refined into exposure classes so manual triage does not confuse
“missing skill” with “unreachable”:

| Exposure class | Meaning | Expected action |
|---|---|---|
| `P0-unrouted` | No skill consumer and no observed hook/router/script/doc/test/config consumers. | Wire skill/hook/router or demote/archive. |
| `P0-route-undocumented` | No skill consumer, but a hook or command-router path is visible. | Document the equivalent route or add a skill. |
| `P0-promotion-candidate` | Docs/tests/config/scripts mention it, but no direct agent-facing route is visible. | Promote through skill/router or demote out of `agentic-primitive`. |

Command-router exposure is deliberately conservative: only central dispatcher
paths such as `scripts/cos` and future `cmd/*` entries count as router
consumers. A sibling `scripts/cos-*` consumer is just a script consumer unless it
is the dispatcher itself.

Manual route and backend dispositions live in
`manifests/script-exposure-dispositions.yaml`. A row with
`resolution: documented_route` records the equivalent hook/router/operator path
and resolves the audit finding as `OK-documented-route` without pretending that
the script has a skill consumer. A row with `resolution: internal_backend`
records that a maintainer tool is an implementation backend owned by a wrapper
or orchestration workflow, resolving it as `OK-internal-backend` instead of
creating a low-value skill for an implementation detail. A row with
`resolution: operator_workflow` accounts for top-level maintainer/operator
workflows that should remain explicit workflows rather than narrow skills. Rows
with `resolution: documented_maintainer_tool` or `resolution: test_fixture`
account for active doc/test-backed tools without archiving references blindly.

P2 is also refined so the audit does not force every maintainer helper into a
new skill:

| Exposure class | Meaning | Expected action |
|---|---|---|
| `OK-classified-maintainer` | Maintainer tool has lifecycle metadata or an override rationale. | No skill required by default. |
| `P2-runtime-route-undocumented` | Hook/router exposure but no explicit internal classification. | Document route, add lifecycle/override, or promote to a skill. |
| `OK-internal-backend` | Maintainer tool has a manual `internal_backend` disposition. | No skill required; keep the wrapper/workflow as the invocation surface. |
| `OK-operator-workflow` | Maintainer tool has a manual `operator_workflow` disposition. | No skill required by default; keep it as an explicit operator workflow. |
| `OK-documented-maintainer` | Maintainer tool has active docs/manifests/tests evidence but no direct skill route. | No skill required until product value justifies promotion. |
| `OK-test-fixture` | Maintainer tool is a test fixture or smoke target. | No skill required by default. |
| `P2-script-orchestrated` | Script consumers but no hook/router/skill and no explicit classification. | Classify as internal backend/operator workflow or promote a grouped skill. |
| `P2-evidence-only` | Docs/tests evidence but no runtime route or explicit classification. | Classify internal, archive stale docs, or promote. |
| `P2-doc-only` / `P2-test-only` / `P2-config-only` | Single-family evidence only. | Treat as likely internal/test/stale unless product value justifies promotion. |

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
