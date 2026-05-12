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

## Operational Guide

### What changes for the operator

Before this ADR: 15 shell/CI candidate scripts stayed partial in ACC because shell/CI had no projection path separate from the IDE harness initializer. Hook artifact-status loaders were duplicated across `auto-verify.sh` and `dod-gate.sh`.

After this ADR:

| Surface | Before | After |
|---|---|---|
| Shell/CI candidate scripts | Partial (no projection path) | Projected via `manifests/shell-ci-projection.yaml` and `scripts/project_shell_ci.py` |
| Hook artifact loaders | Duplicated in 2 hooks | Centralized in `hooks/_lib/artifact-status.sh` |
| Unprojected `scripts/**` | Unclassified | SO-local by pattern default |
| Unprojected `hooks/_lib/**` | Unclassified | Support files (not standalone consumer capabilities) |

To run shell/CI projection standalone:
```bash
python3 scripts/project_shell_ci.py --project-root . --profile default
```

To verify the hook extraction:
```bash
bash -n hooks/_lib/artifact-status.sh hooks/auto-verify.sh hooks/dod-gate.sh
```

### What this answers (and what it doesn't)

**Answers:**
- "Which shell/CI commands are projected and available in consumer projects?" — See `manifests/shell-ci-projection.yaml` for the declared 15 commands and generated workflow.
- "Why does ACC show zero partial weight for scripts I didn't explicitly classify?" — Pattern defaults in `manifests/primitive-consumer-availability.yaml` classify unprojected `scripts/**` as SO-local.
- "Is the hook artifact loader shared or copied?" — `hooks/_lib/artifact-status.sh` is now the single source; `auto-verify.sh` and `dod-gate.sh` source it.

**Does not answer:**
- "Will every projected shell/CI command succeed in the consumer's stack?" — Projection proves structural syntax and command paths. Runtime success depends on the consumer's installed dependencies.
- "Is ACC reporting perfect coverage?" — Perfect coverage for the declared scope only. Future new scripts/rules/skills require explicit classification or they trigger the `--fail-new` gate (see ADR-153).

### Reading guide for cold readers

1. Read `manifests/shell-ci-projection.yaml` to see which commands are declared for shell/CI projection.
2. Run `python3 scripts/project_shell_ci.py --project-root . --profile default` to see what gets generated in a temp consumer project.
3. Read `hooks/_lib/artifact-status.sh` to understand the centralized artifact-status loading contract.
4. Check `docs/acc/latest.json` for current `partial_weight`, `unverified_weight`, and `stale_weight` — all should be 0 for the declared scope after a successful ACC refresh.

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
