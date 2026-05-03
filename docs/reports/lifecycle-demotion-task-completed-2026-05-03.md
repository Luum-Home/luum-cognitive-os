# Lifecycle Demotion Proof — task-completed hook

Date: 2026-05-03

## Why this exists

ADR-126 defines `demoted` as a semantic lifecycle state: the primitive remains in
the repository and can be opted into, but it stops contributing to the default
active/default-visible surface.

Until this proof, demotion was only described as doctrine. The lifecycle manifest
had no `lifecycle_state: demoted` entry, so the governor had not signed a real
retirement decision.

## Decision

Demote `hooks/task-completed.sh` from the default team/runtime projection.

This hook is still available for explicit task-system integrations, but it no
longer belongs in the default projected surface because `TaskCompleted` is a COS
extension event and not a portable/native baseline across harnesses.

## Semantic effect

- `hooks/task-completed.sh` remains on disk.
- `manifests/primitive-lifecycle.yaml` keeps the primitive entry.
- `lifecycle_state: demoted` removes it from active/default-visible counts.
- `runtime_projection: false` prevents the manifest from claiming default runtime
  projection.
- `.claude/settings.json` keeps an empty `TaskCompleted` event bucket, but no
  default hook command.

## Why this is demotion, not archive

Archive would remove the primitive from active consideration. Demotion preserves
it for opt-in/manual task systems while making the default profile smaller.

## Required proof

```bash
scripts/cos-active-primitive-index --json
scripts/cos-adoption-profile --profile team
python3 -m pytest tests/unit/test_active_primitive_index.py tests/contracts/test_primitive_lifecycle_manifest.py tests/contracts/test_lab_first_promotion_gate.py -q
python3 scripts/cos_architecture_readiness.py --json
bash scripts/cos-ci-local.sh quick
```

Expected outcome: active/default-visible counts drop by one compared with the
previous team surface, while `hooks/task-completed.sh` remains available.
