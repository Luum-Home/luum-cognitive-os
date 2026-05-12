---

adr: 167
title: Proof Drill Selector and ACC Evidence Adapter
status: implemented
implementation_status: implemented
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - scripts/proof-drill-select
  - scripts/proof_drill_select.py
  - scripts/proof-drill-evidence-record
  - scripts/proof_drill_evidence_record.py
  - manifests/proof-drill-registry.yaml
  - docs/06-Daily/reports/proof-drill-evidence-latest.json
  - scripts/cos_instance_init.py
  - manifests/cos-instance-profiles.yaml
  - scripts/acc_pipeline.py
  - manifests/runtime-env-flags.yaml
  - tests/contracts/test_proof_drill_select.py
  - tests/unit/test_acc_proof_drill_evidence.py
  - tests/contracts/test_runtime_env_flags.py
tier: maintainer
tags: [proof-drills, acc, instance-installer, runtime-flags, consumer-projection]
---

# ADR-167: Proof Drill Selector and ACC Evidence Adapter

## Status

**Implemented for the proof-drill selector, evidence recorder, ACC adapter, instance-profile projection, and runtime-flag registry scope** — 2026-05-05. Live proof execution remains opt-in according to the proof-drill registry; this ADR closes the selector/evidence/control-plane integration boundary.

## Context

ADR-165 created a proof-drill registry and a `proof-drill` skill, but agents
still needed a machine-readable selector, COS instance profiles still listed
smoke commands by prose, and ACC could not consume proof-drill evidence as
coverage input.

The first provider proof also introduced a real runtime flag:
`COS_CODEX_EXEC_MODEL`. Without registering it, future agents could rediscover
or misuse the flag outside the normal runtime flag contract.

## Decision

1. Add `scripts/proof-drill-select` as the selector/doctor primitive for the
   proof-drill registry. It selects by id, scope, class, projection profile, and
   text tokens such as `provider`, `docker`, `headless`, and `codex`.
2. Add `scripts/proof-drill-evidence-record` so proof runs can update the
   machine-readable evidence report consumed by ACC.
3. Extend `manifests/proof-drill-registry.yaml` with explicit
   `consumer_projection` classification and projection profiles:
   `consumer-default`, `consumer-opt-in`, and `maintainer-only`.
4. Extend `cos-instance-init` so instance plans expose registered proof drills
   and default-safe doctor commands without executing opt-in drills.
5. Add `docs/06-Daily/reports/proof-drill-evidence-latest.json` and teach
   `scripts/acc_pipeline.py` to load proof-drill evidence as aligned/stale/
   unverified ACC capabilities.
6. Register `COS_CODEX_EXEC_MODEL` in `manifests/runtime-env-flags.yaml` and
   document it as a test opt-in/provider-smoke model pin.

## Consumer projection rule

Consumer projects get `/run-tests` by default. Proof drills travel only through
an explicit projection profile. Provider and Docker proof drills are
`maintainer-only` unless a later ADR proves a safe project-local adapter.

## Consequences

- Agents can ask the registry for the correct command instead of reading long
  reports.
- COS instance plans now know which proof drills are available for their profile.
- ACC can show proof-drill evidence without manual classification.
- Provider model pins are governed as runtime flags rather than ad hoc shell
  environment.

## Operational Guide

### What changes for the operator

Before this ADR, selecting the right proof drill required reading long report documents and manually inferring which command was appropriate for the current instance profile. ACC had no way to consume proof-drill evidence programmatically, and the `COS_CODEX_EXEC_MODEL` flag was undocumented outside ad hoc shell invocations.

After this ADR:

| Surface | Before | After |
|---|---|---|
| Proof drill selection | Read prose, guess command | `scripts/proof-drill-select --scope <scope> --class <class>` returns the right command |
| ACC coverage | No proof-drill evidence rows | `scripts/acc_pipeline.py` loads `docs/06-Daily/reports/proof-drill-evidence-latest.json` as aligned/stale/unverified rows |
| Instance plans | Listed smoke commands by prose | `cos-instance-init` exposes registered proof drills and default-safe doctor commands per projection profile |
| Runtime flag `COS_CODEX_EXEC_MODEL` | Undocumented, ad hoc | Registered in `manifests/runtime-env-flags.yaml`; governed as a test opt-in model pin |

### What this answers (and what it doesn't)

**Answers:**
- "Which proof drill should I run for this instance profile?" — `scripts/proof-drill-select --profile consumer-default` returns only safe drills for that context.
- "Does ACC have coverage evidence for this capability?" — Check `docs/06-Daily/reports/proof-drill-evidence-latest.json`; `acc_pipeline.py` loads it automatically.
- "Is `COS_CODEX_EXEC_MODEL` a known flag?" — Yes; see `manifests/runtime-env-flags.yaml` for purpose and opt-in semantics.

**Does not answer:**
- Whether a proof drill passed — only `scripts/proof-drill-evidence-record` updates pass/fail status after a live execution.
- Whether provider or Docker drills are safe for a consumer project — by design those are `maintainer-only` unless a later ADR promotes them.

### Daily operational pattern

1. When adding a new proof drill: declare it in `manifests/proof-drill-registry.yaml` with `consumer_projection` classification.
2. To find the right drill for the current context: `scripts/proof-drill-select --scope local --class smoke`.
3. After a proof run: `scripts/proof-drill-evidence-record --id <drill-id> --status pass` to update `docs/06-Daily/reports/proof-drill-evidence-latest.json`.
4. ACC picks up evidence on next pipeline run — no manual classification needed.

### Reading guide for cold readers

1. Read `manifests/proof-drill-registry.yaml` to understand which drills exist and their projection profiles (`consumer-default`, `consumer-opt-in`, `maintainer-only`).
2. Run `scripts/proof-drill-select --list` to see the current selectable drill set.
3. Read `docs/06-Daily/reports/proof-drill-evidence-latest.json` for the latest pass/fail evidence rows.
4. The consumer projection rule is the critical constraint: provider and Docker drills are `maintainer-only` — do not surface them to consumer project operators unless a future ADR creates a safe adapter.
5. The test suite at `tests/contracts/test_proof_drill_select.py` is the authoritative contract for the selector interface.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep proof selection in prose only | Agents must load long docs and can choose provider/Docker drills by mistake. |
| Execute all profile smokes from `cos-instance-init` | Would turn opt-in provider/Docker proof into default installer side effects. |
| Let ACC infer proof from Markdown only | Markdown is useful evidence, but ACC needs stable machine-readable rows. |
| Project all proof drills to consumer projects | Provider and Docker drills are SO-maintainer surfaces unless explicitly packaged and proven safe. |

## Verification

```bash
python3 -m pytest \
  tests/contracts/test_proof_drill_registry.py \
  tests/contracts/test_proof_drill_select.py \
  tests/contracts/test_cos_instance_profiles.py \
  tests/unit/test_acc_proof_drill_evidence.py \
  tests/contracts/test_runtime_env_flags.py \
  -q
```

## Implementation Evidence

- `scripts/proof-drill-select` and `scripts/proof_drill_select.py` provide registry selection.
- `scripts/proof-drill-evidence-record` and `scripts/proof_drill_evidence_record.py` update machine-readable proof evidence.
- `docs/06-Daily/reports/proof-drill-evidence-latest.json` is consumed by `scripts/acc_pipeline.py`.
- `manifests/proof-drill-claim-map.yaml` lets ACC emit `proof_claim:*` capabilities for claims backed by concrete proof drills.
- `scripts/cos-headless-service-drill` auto-records evidence for the local Docker/headless proof and for the explicit Codex provider proof.
- Runtime flag and instance-profile contracts are covered by `manifests/runtime-env-flags.yaml` and `manifests/cos-instance-profiles.yaml`.
