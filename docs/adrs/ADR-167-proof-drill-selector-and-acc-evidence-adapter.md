---
adr: 167
title: Proof Drill Selector and ACC Evidence Adapter
status: implemented
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - scripts/proof-drill-select
  - scripts/proof_drill_select.py
  - scripts/proof-drill-evidence-record
  - scripts/proof_drill_evidence_record.py
  - manifests/proof-drill-registry.yaml
  - docs/reports/proof-drill-evidence-latest.json
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
5. Add `docs/reports/proof-drill-evidence-latest.json` and teach
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
- `docs/reports/proof-drill-evidence-latest.json` is consumed by `scripts/acc_pipeline.py`.
- Runtime flag and instance-profile contracts are covered by `manifests/runtime-env-flags.yaml` and `manifests/cos-instance-profiles.yaml`.
