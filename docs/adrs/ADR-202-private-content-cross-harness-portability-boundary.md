---
adr: 202
title: Private Content Cross-Harness Portability Boundary
status: accepted
implementation_status: implemented
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit accepted/implemented status
---

# ADR-202 — Private Content Cross-Harness Portability Boundary

<!-- SCOPE: OS -->

**Status**: Accepted — conservative manifest and audit substrate implemented  
**Date**: 2026-05-06  
**Related**: ADR-008, ADR-081, ADR-111, ADR-124, ADR-136, ADR-190, ADR-193, ADR-194, ADR-196, ADR-201  
**Report**: `docs/reports/private-content-portability-gap-2026-05-06.md`

---

## Context

ADR-008 established that Cognitive OS should not be Claude Code-only. It focused
on public multi-tool portability: hook adapters, MCP bridges, rules projection,
and tool support across Claude Code, Codex, Cursor, Aider, OpenCode, and similar
hosts.

That decision did not explicitly define the portability boundary for **private
content**. Cognitive OS now carries private or semi-private state across several
surfaces:

- `.cognitive-os/strategy/` and business strategy documents;
- private local plans under `.cognitive-os/plans/`;
- session handoffs and recovery artifacts;
- Engram observations and summaries;
- local metrics and action receipts;
- consumer-project evidence bundles;
- private repository context and non-public project facts;
- local harness state for Codex, Claude Code, and future service/cloud hosts.

Public multi-tool support answers how primitives can be projected into different
hosts. It does not answer which private content may cross harnesses, which must
stay local, what must be redacted, and what cloud/service runtimes may retain.

## Decision

Define a private-content portability boundary separate from public harness
portability.

Every private content surface must declare a portability class:

| Class | Meaning | Examples |
|---|---|---|
| `secret-never-touch` | Must not be read, copied, exported, summarized, or scanned except by an explicitly authorized secret-specific API. | `.env`, OAuth tokens, API keys, SSH keys, private certs |
| `local-only` | Must not leave the current project/workstation by automation. | raw private strategy, unredacted recovery artifacts, raw local transcripts |
| `same-user-harness` | May move between local harnesses for the same operator on the same trusted machine. | sanitized session summaries, local skill state, non-secret preferences |
| `project-private` | May be shared inside the same private repo/project boundary. | reviewed ADRs, private plans, bounded metrics summaries |
| `sanitized-export` | May leave the project only after redaction/provenance checks. | consumer evidence bundles, failure patterns, adoption reports |
| `public` | Safe for OSS docs/packages. | public ADRs, public skills, package metadata |

Adapters and service runtimes must not infer portability from file location
alone. They must read an explicit policy or conservative default.

This ADR intentionally does **not** rename or move private paths. For example,
`.cognitive-os/strategy/` remains where it is; the new behavior is that it is
classified by policy, initially as `local-only`. The boundary is classification,
not a new `.agents-private/` path convention.

Default policy:

```text
known secrets/credentials -> secret-never-touch
unknown private content -> local-only
unknown generated artifact -> local-only
unknown metrics payload -> project-private only after secret scan
unknown memory observation -> same-user-harness only after summary/redaction
```

## Secret-never-touch boundary

`secret-never-touch` is stricter than `local-only`. Local-only content can be
read by local audit code if policy allows it; secret-never-touch content cannot.
It is excluded from generic grep, summarization, memory capture, metrics export,
classification scans, and cloud/service ingestion by default. Any explicit access
must use a secret-specific authorized API and emit an immediate audit alert.

## Required metadata

Any new cross-harness private content surface must declare:

- content kind;
- portability class;
- allowed hosts;
- allowed destinations;
- retention policy;
- redaction rule;
- provenance requirement;
- operator approval requirement;
- audit metric emitted on export/projection.

## Class transition protocol

Class changes must be explicit events, not silent metadata edits.

| Transition | Required gate |
|---|---|
| `local-only` -> `same-user-harness` | operator approval and same-machine trust check |
| `local-only` -> `sanitized-export` | redaction proof, provenance record, export receipt |
| `project-private` -> `public` | human review, leakage check, and publication receipt |
| any class -> stricter class | audit event and sync/export revocation check where applicable |
| any class -> `secret-never-touch` | immediate stop of generic readers/exporters for that surface |

Already-exported content cannot be made private by metadata alone. Downgrades
must record whether prior sync/export artifacts exist and whether revocation or
remote deletion was requested.

## Audit log destination

Every projection/export/read of classified private content must write a dedicated
audit row to `.cognitive-os/metrics/private-content-access.jsonl` with content
class, source surface, destination host, action, approval/provenance ids, and
result. Run traces may reference these rows, but the audit log is the durable
source for private-content access events.

## Unknown surface detection

The defensive export checker blocks unknown surfaces at projection time. A
separate proactive audit must also enumerate unmanifested private roots by
comparing the manifest against disk and known memory/metric stores. The audit is
intended for scheduled/session-end use and should report new unclassified
surfaces before they reach an export path.

## Service/cloud boundary

A standalone or cloud Cognitive OS service may consume private content only when
all are true:

1. the content has a portability class that allows the target host;
2. secrets and credentials are excluded by policy, not best effort;
3. `.cognitive-os/metrics/private-content-access.jsonl` records the content class,
   source surface, destination, action, and approval/provenance ids;
4. exported evidence carries provenance and redaction status;
5. the operator can inspect and revoke persisted private state.

## Safety boundaries

The system must not:

- read or scan `secret-never-touch` content through generic audit/export paths;
- upload raw `.cognitive-os/strategy/` or `.cognitive-os/recovery/` content to a
  cloud host by default;
- treat Engram memory as automatically shareable across all hosts;
- project private plans into public package artifacts;
- use private consumer evidence to sign public adoption claims without explicit
  sanitized-export provenance;
- allow a router hint to invoke destructive or recovery primitives solely because
  a user mentioned them while discussing architecture or risk.

## Consequences

### Positive

- Multi-tool support becomes safe for private strategy and service runtimes.
- Harness adapters gain a clear rule for what may be projected or retained.
- Cloud/headless operation can be audited without leaking local operator state.
- Router and maintainer-agent proposals can reason about content class before
  suggesting actions.

### Negative / trade-offs

- More metadata is required for new private content surfaces.
- Some convenient cross-harness sync behavior will be blocked until classified.
- Existing docs and metrics surfaces need a classification audit.

## Alternatives rejected

- **Assume private repo means all content is portable**: rejected because local
  recovery artifacts, memory, and strategy can exceed the intended host boundary.
- **Block all private portability**: rejected because same-user local harness
  continuity is a core usability requirement.
- **Rely only on secret scanning**: rejected because non-secret strategy and
  memory can still be private.
- **Let each harness decide**: rejected because portability must be an OS-level
  contract, not a driver-specific accident.

## Implementation slices

1. Add a private-content surface manifest.
2. **Slice 2a — skeleton manifest with conservative defaults**: classify the
   known private-content roots as `local-only` first, classify credential/secret
   patterns as `secret-never-touch`, including strategy, local plans, recovery
   artifacts, raw metrics, Engram summaries, and consumer evidence bundles. This
   slice is intentionally quick and conservative.
3. **Slice 2b — justified elevations**: elevate specific items from `local-only`
   to `same-user-harness`, `project-private`, or `sanitized-export` only with
   explicit redaction, provenance, retention, and host-allowance justification.
4. Add a projection/export checker that blocks unknown private surfaces by
   default and a scheduled audit that reports unmanifested private surfaces.
5. Add router context guards so recovery/destructive skills are not suggested
   when mentioned as risk analysis rather than operator intent. The first
   `/auto-rollback` negative-context guard is implemented as a narrow bug fix;
   the broader policy remains part of this ADR.
6. Add service/headless smoke tests proving private content does not leave the
   local boundary without policy.

## Open questions / future work

- **Engram integration**: decide whether classification is per observation,
  topic key, namespace, or export bundle; preserve backward compatibility for
  existing `mem_save` calls while preventing unclassified cloud sync.
- **GDPR / data deletion**: define deletion/export-revocation workflows for
  hosted `cosd` and Engram Cloud. This must integrate with ADR-199 retention so
  archive-first safety does not conflict with deletion rights.
- **Cross-machine same-user**: same-user-harness currently means same trusted
  machine. Laptop-to-desktop sync for the same operator needs a separate trust
  and revocation model before elevation.
- **Router intent classifier**: distinguishing execution intent from discussion
  or risk analysis is not a regex-only problem. Slice 4 needs a fixture dataset
  and likely a small intent classifier contract before generalizing beyond the
  narrow `/auto-rollback` guard.
- **Transition receipts**: class upgrades/downgrades need durable receipts and
  possibly a separate ADR if the transition workflow grows beyond manifest/audit
  scope.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_private_content_portability.py -q
python3 -m pytest tests/behavior/test_private_content_projection_guard.py -q
python3 -m pytest tests/unit/test_skill_router.py -q
scripts/cos-private-content-audit --json
scripts/cos-private-content-audit --strict --json
scripts/cos-private-content-audit --unknown-surfaces --json
```

The audit must pass first with a skeleton conservative manifest where known
private roots default to `local-only` and secret/credential paths are
`secret-never-touch`. The behavior test must prove that private strategy content
remains in place but is classified as `local-only`, generic audit/export paths do
not read secrets, sanitized evidence can be exported only with provenance, and
router mentions of recovery primitives in risk-analysis context do not produce
action suggestions.

## Status

Accepted — conservative manifest and audit substrate implemented. This ADR fills the private-content gap left implicit by ADR-008 and
must be reconciled before treating cloud/headless service portability as safe by
default.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
