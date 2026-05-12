---
adr: 126
title: Agentic Primitive Lifecycle Governor
status: proposed
implementation_status: planned
date: '2026-05-02'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit prose status migration for previously prose-only ADR
---

# ADR-126: Agentic Primitive Lifecycle Governor

## Status

Proposed — 2026-05-02

## Context

ADR-120 defines a conversation-to-primitive harvester that can identify repeated
operator/agent patterns and propose new agentic primitives. ADR-124 defines
distribution boundaries (`core`, `team`, `maintainer`, `lab`). ADR-125 defines a
governance value boundary (`runtime-safety`, `delivery-structure`,
`meta-governance`) and requires low-use or negative-ROI primitives to be
demoted, archived, or moved to lab.

Those ADRs are necessary but not sufficient for self-adjusting behavior. If the
OS can auto-create, auto-adjust, or auto-remove hooks, skills, rules, scripts,
or doctors, the lifecycle itself must be governed. Otherwise the SO will repeat
the historical failure mode from ADR-017: agents add primitives faster than they
can be wired, tested, understood, and retired.

The solo maintainer swarm persona makes this more important, not less. One
operator running Claude Code, Codex, multiple sessions, and multiple agents needs
agentic primitives that push the system toward determinism. Self-improvement must
therefore be treated as a controlled promotion pipeline, not as autonomous code
mutation.

## Decision

Introduce an agentic primitive lifecycle governor. Any primitive created,
modified, promoted, demoted, disabled, archived, or deleted by an agent or
self-improvement workflow must move through explicit lifecycle states and must
carry machine-checkable metadata.

### Lifecycle states

| State | Meaning | Runtime behavior |
|---|---|---|
| `candidate` | Proposed by harvester, user, or agent after a repeated pattern is found. | Not projected, not default-on. |
| `sandbox` | Implemented behind an isolated test/manual path. | May run only in explicit validation or lab profile. |
| `advisory` | Emits warnings/metrics but cannot block. | Allowed in maintainer/team profiles when latency budget is proven. |
| `blocking` | Can stop a tool/action. | Requires runtime-safety class, false-positive tests, repair message, and rollback path. |
| `default-on` | Projected by default for a distribution/profile. | Requires sustained positive ROI and low-noise evidence. |
| `demoted` | Still available but removed from default runtime. | May remain opt-in or move to lab. |
| `archived` | Removed from active projection and active docs indexes. | Restorable from git/archive path; no settings references. |
| `deleted` | Fully removed after archive/retention window. | Requires bilateral absence proof. |

### Required metadata

Each new or changed primitive must declare, eventually in a canonical manifest:

- `id`
- `kind`: `hook | skill | rule | script | doctor | test | template | manifest`
- `owner_adr`
- `lifecycle_state`
- `maturity`: `observe | advisory | blocking`
- `distribution`: `core | team | maintainer | lab`
- `governance_class`: `runtime-safety | delivery-structure | meta-governance`
- `risk_class`: `advisory | blocking | mutating | destructive`
- `supported_harnesses`
- `projection_targets`
- `runtime_projection` when present in generated harness settings
- `behavior_evidence` explaining whether the primitive observes, advises, or blocks
- `exit_behavior`: `exit_0 | exit_2 | mixed | manual`
- `metrics_file`: concrete JSONL path or `none` when the primitive does not emit metrics
- `docs_claim_level`: `observe | advisory | blocking`; product/docs claims cannot exceed maturity
- `latency_budget_ms` when runtime-facing and blocking
- `evidence_commands`
- `rollback_or_repair_command`
- `sunset_criteria`

Metadata may start in a transitional manifest, but runtime projection must not
infer these fields from prose forever.

### Promotion gates

A primitive may be promoted only when the next state has proof:

1. `candidate → sandbox`: ADR or plan exists, owner is declared, and no duplicate
   primitive already owns the same responsibility.
2. `sandbox → advisory`: targeted unit/behavior tests pass and docs explain what
   the primitive observes.
3. `advisory → blocking`: false-positive border tests pass, the block message is
   repair-first, bypass/repair path is documented, and latency budget is met.
4. `blocking → default-on`: ROI dashboard shows positive net value for the target
   distribution/profile, and chaos or multi-session tests cover realistic races.
5. Any promotion that changes projection must regenerate derived artifacts and
   pass projection parity checks.

### Demotion/removal gates

A primitive may be demoted, archived, or deleted when one of these is true:

- ROI is negative for the target tier over the configured window.
- It duplicates a canonical primitive or source of truth.
- It is noisy: repeated false positives or operator bypasses exceed the allowed
  threshold.
- It is stale: no execution, no references, and no maintainer use during the
  retention window.
- It is unsafe: it can mutate, stash, delete, or block without symmetric cleanup
  and tests.

Removal is archive-first unless the file is generated or explicitly disposable.
High-stakes verbs such as `archived`, `deleted`, `removed`, `wired`, and
`default-on` must satisfy ADR-105 claim verification.

### Self-adjustment constraints

Self-adjusting workflows may propose and patch primitives, but they must not
silently land new runtime behavior. They must:

1. classify the change by lifecycle, distribution, and governance class;
2. run the smallest evidence command set that proves the lifecycle transition;
3. publish a session/event-bus event for other sessions;
4. update derived artifacts or fail before commit;
5. avoid changing active projection when the working tree contains unrelated WIP;
6. require human approval or protected merge-queue landing before default-on or
   destructive behavior changes.

For the solo maintainer swarm, this is the safety valve: the SO can learn, but it
cannot silently rewrite its own operating envelope while multiple IDEs and agents
are live.


### 2026-05-03 Runtime hook inventory hardening

`manifests/primitive-lifecycle.yaml` now contains lifecycle metadata for every
hook projected by `.claude/settings.json` at the time of implementation. The
manifest records 116 runtime-projected hooks plus non-hook lifecycle primitives.

The hardening contract is intentionally anti-aspirational:

- every projected hook must have a manifest entry;
- every runtime-projected hook entry must point to an existing hook file;
- `maturity: blocking` must correspond to `exit_behavior: exit_2`, a hook with an
  observable `exit 2` path, and pytest evidence;
- evidence commands must be syntactically executable references, not prose-only
  placeholders;
- non-blocking maturity cannot claim a blocking/default-on lifecycle state;
- `docs_claim_level` cannot exceed runtime maturity, so docs cannot sell an
  observe/advisory hook as blocking;
- projected hooks cannot be marked archived, demoted, or deleted.

The runtime reality audit (`scripts/runtime_hook_reality.py`) classifies the
projected hook set into real blocking, real advisory, observe-only, dormant,
projected-but-undocumented, and documented-but-not-projected buckets. It is wired
into architecture readiness as `runtime-hook-reality`.

### 2026-05-03 First semantic demotion

`hooks/task-completed.sh` is the first lifecycle primitive moved to
`lifecycle_state: demoted`. The hook remains in the repository for opt-in task
systems, but it is no longer projected by default and no longer counts toward the
active/default-visible surface. Proof is documented in
`docs/06-Daily/reports/lifecycle-demotion-task-completed-2026-05-03.md`.

This does not mean every hook is product-core. Many projected hooks remain
`lab`/`sandbox` or advisory because this repository is the maintainer runtime,
not the minimal consumer distribution.

This first demotion is deliberately classified as **semantic-portability
signed**, not ROI-signed. The reason was stronger than the ROI heuristic:
`TaskCompleted` is a COS extension event and should not be default-projected as a
portable baseline. Therefore the governance ROI dashboard remains an instrument
after this demotion, not yet the decision knife.

The lifecycle governor is considered a repeated control loop only after a
second demotion lands, and at least one demotion records governance ROI as the
primary signing signal. Until then, ADR-126 has proven that demotion works
mechanically, but not that demotion happens reflexively under normal operation.

This is now visible through `scripts/cos-demotion-loop-audit` and the
`demotion-loop-maturity` architecture-readiness check. The check warns rather
than fails while there is only one semantic demotion; it becomes green when the
manifest contains at least two demotions and at least one is ROI-signed.

### 2026-05-03 Second semantic demotion

`hooks/context-watchdog.sh` is the second lifecycle primitive moved to
`lifecycle_state: demoted`. This demotion was signed by
`scripts/cos-manifest-tier-claim-audit`, not by the ROI dashboard: the hook is an
advisory-only `PostToolUse` wildcard that adds default runtime surface without
blocking unsafe state. The hard compaction path remains
`hooks/pre-compaction-flush.sh` plus the session-summary/memory protocol.

The hook remains available for opt-in maintainer sessions, but it is no longer
projected by default in `.claude/settings.json`. Candidate resolution is
documented in
`docs/06-Daily/reports/second-demotion-candidate-resolution-2026-05-03.md`.

After this transition, the lifecycle governor has repeated demotion behavior
(`demotion_count >= 2`), but the ROI dashboard still has not signed a demotion
decision (`roi_signed_demotion_count == 0`). That remaining warning is
intentional.

The warning is intentionally **bounded**. If the ROI-signed demotion gap remains
open for 30 days after the second demotion, `scripts/cos-demotion-loop-audit`
escalates `roi-signed-demotion-missing` from `warn` to `fail`, and architecture
readiness propagates that failure. A permanent warning is treated as governance
rot: either real-world ROI data signs a demotion, or the operator must revisit
the policy instead of normalizing the warning.

## Consequences

- Primitive creation becomes slower but safer.
- Auto-generated primitives stay in `candidate`/`sandbox` until evidence exists.
- Demotion and archival become normal hardening actions, not admissions of
  failure.
- Distribution/profile projection can become deterministic because every
  primitive carries explicit metadata.
- The primitive harvester remains useful without becoming an uncontrolled source
  of runtime drift.
- The repo needs a future manifest and tests that enforce metadata completeness,
  promotion gates, and bilateral archive/delete claims.

## Alternatives rejected

- **Let agents freely add/remove primitives**: rejected because it recreates
  primitive sprawl and silent runtime drift.
- **Require human approval for every generated candidate**: rejected because it
  prevents useful advisory/sandbox experimentation.
- **Use documentation only**: rejected because agents need machine-checkable
  lifecycle state and projection gates.
- **Ban self-improvement**: rejected because the SO's value includes learning
  from incidents and repeated workflows.

## Verification

Initial documentation-level proof:

```bash
python3 -m pytest tests/audit/test_adr_contracts.py tests/audit/test_adr_locations.py -q
```

Future enforceable proof:

```bash
python3 -m pytest tests/contracts/test_primitive_lifecycle_manifest.py -q
python3 -m pytest tests/behavior/test_primitive_lifecycle_promotion.py -q
python3 -m pytest tests/behavior/test_primitive_lifecycle_archive_claims.py -q
scripts/cos-demotion-loop-audit --json
```
