---

adr: 152
title: Shell CI Projection and Local Surface Defaults
status: implemented
implementation_status: implemented
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - manifests/shell-ci-projection.yaml
  - scripts/project_shell_ci.py
  - scripts/acc_pipeline.py
  - manifests/primitive-consumer-availability.yaml
  - hooks/_lib/artifact-status.sh
tier: maintainer
tags: [acc, shell-ci, projection, duplication, consumer-availability]
---

# ADR-152: Shell CI Projection and Local Surface Defaults

## Status

**Implemented for shell/CI projection and local-surface defaults** — 2026-05-04. The projection manifest, projector, ACC integration, and artifact-status extraction exist; runtime behavior remains structural projection proof, not universal shell runtime parity.

## Context

After ACC projection profiles and explicit candidate classification, remaining partial debt came from 15 shell/CI candidate scripts. Remaining unverified debt came from SO-local scripts/hooks, repo-only skills, and doctrinal/contextual rules. At the same time, the primitive duplication audit identified duplicated hook artifact-status loaders in `auto-verify.sh` and `dod-gate.sh`.

## Decision

Add a dedicated shell/CI projection path instead of overloading IDE harness initialization:

- `manifests/shell-ci-projection.yaml` declares the 15 projected shell/CI commands and generated workflow.
- `scripts/project_shell_ci.py` projects canonical command copies under `.cognitive-os/scripts/cos/`, creates consumer-facing driver symlinks under `scripts/`, and writes `.github/workflows/cognitive-os-shell-ci.yml`.
- ACC runs shell/CI projection after Claude/Codex default/full temp-project initialization and counts proven shell/CI command paths as projected consumer surfaces.

Also add pattern defaults in `manifests/primitive-consumer-availability.yaml` for local surfaces:

- unprojected `scripts/**` are SO-local by default;
- unprojected `hooks/_lib/**` are support files, not standalone consumer capabilities;
- unprojected `hooks/*.sh`, `rules/*.md`, `skills/**/SKILL.md`, and `.codex/skills/**/SKILL.md` are local/doctrinal/repo-only unless projection proof exists.

Finally, extract duplicated hook artifact-status loaders into `hooks/_lib/artifact-status.sh` and source them from `hooks/auto-verify.sh` and `hooks/dod-gate.sh`.

## Consequences

### Positive

- Shell/CI commands are now proven by temp-project projection instead of remaining partial candidates.
- ACC no longer penalizes explicitly local support/doctrine surfaces as missing consumer projection.
- Duplicate hook loader logic is centralized.

### Negative

- ACC can reach perfect coverage for the current declared scope; future work must avoid interpreting that as universal product completeness.
- Broad local-surface defaults must be reviewed if a future package wants to project more scripts/rules/skills by default.
- Shell/CI projection currently proves structural projection and syntax, not every runtime behavior.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Add `--harness shell-ci` to `cos_init.py` | Rejected because shell/CI is a command/workflow projection layer, not an IDE settings harness. |
| Keep shell/CI candidates partial | Rejected because they now have a manifest and projection proof path. |
| Leave hook artifact loaders duplicated | Rejected because the duplication audit identified a small safe extraction. |

## Verification

```bash
python3 scripts/acc_pipeline.py --project-dir . --refresh
python3 -m pytest tests/unit/test_project_shell_ci.py tests/unit/test_acc_pipeline.py tests/contracts/test_acc_pipeline_contract.py -q
bash -n hooks/_lib/artifact-status.sh hooks/auto-verify.sh hooks/dod-gate.sh
```

## Implementation Evidence

- `scripts/project_shell_ci.py` implements shell/CI projection.
- `scripts/acc_pipeline.py` merges shell/CI command proof into consumer projection.
- `hooks/_lib/artifact-status.sh` centralizes artifact status loading.
- `docs/acc/latest.json` reports `partial_weight=0`, `unverified_weight=0`, and `stale_weight=0` for declared ACC scope.
