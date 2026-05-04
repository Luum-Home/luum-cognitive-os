---
adr: 155
title: Shell CI Formal Harness Projection
status: accepted
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos_init.py
  - scripts/project_shell_ci.py
  - manifests/harness-projection.yaml
  - manifests/harness-implementation-phases.yaml
  - tests/unit/test_project_shell_ci.py
  - tests/behavior/test_consumer_project_projection.py
  - tests/contracts/test_acc_pipeline_contract.py
  - docs/manual-tests/shell-ci-formal-harness.md
tier: maintainer
tags: [harness, shell-ci, projection, acc, ci]
---

# ADR-155: Shell CI Formal Harness Projection

## Status

**Accepted** — 2026-05-04

## Context

ADR-152 added `scripts/project_shell_ci.py` and `manifests/shell-ci-projection.yaml`, allowing ACC to prove shell/CI command projection inside consumer temp projects. The registry still marked `shell-ci` as `planned`, which made the implementation harder to reason about: shell/CI was proven as an adapter but not promoted as a harness surface.

The next slice is to make shell/CI a first-class harness while preserving the boundary that this is structural command/workflow projection, not a guarantee that every projected command succeeds in every consumer stack.

## Decision

Promote `shell-ci` to an implemented harness.

`cos_init.py --default|--full --harness shell-ci` now:

1. installs the normal `.cognitive-os/` rules, hooks, skills, templates, and metadata;
2. invokes `scripts/project_shell_ci.py` for the selected profile;
3. writes `.cognitive-os/shell-ci-projection.json`;
4. creates canonical command copies under `.cognitive-os/scripts/cos/`;
5. creates consumer-facing command symlinks under `scripts/`;
6. writes `.github/workflows/cognitive-os-shell-ci.yml`.

ACC now treats `shell-ci` like other implemented harnesses: it creates default/full temp projects and records projection counts under `shell-ci/default` and `shell-ci/full`.

## Consequences

### Positive

- Shell/CI no longer has split semantics: the registry, installer, ACC, and tests all agree it is implemented.
- Consumer projects can install a CLI/workflow surface without using an IDE account.
- The harness provides a bridge for CI-only adoption and headless validation.

### Negative

- The proof remains structural and syntax-oriented. Runtime command success still depends on the consumer project's stack and installed dependencies.
- The repository's disabled broad CI workflow is not automatically re-enabled by this harness promotion.
- `cos_init.py --harness shell-ci` invokes the shell/CI projector, so projector regressions now affect installer validation for that harness.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep shell/CI only as an ACC adapter | Preserves ambiguity: projected and scored, but still marked planned. |
| Reuse an IDE harness to imply shell/CI support | Overcouples CLI/workflow adoption to IDE settings. |
| Require all projected commands to execute fully in tests | Too stack-dependent for default CI; structural proof plus targeted syntax tests is the right baseline. |

## Verification

```bash
python3 -m pytest tests/unit/test_project_shell_ci.py tests/behavior/test_consumer_project_projection.py tests/contracts/test_acc_pipeline_contract.py tests/contracts/test_harness_implementation_phases.py -q
python3 -m py_compile scripts/cos_init.py scripts/project_shell_ci.py scripts/acc_pipeline.py
python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new
```

## Implementation Evidence

- `scripts/cos_init.py` accepts `--harness shell-ci` and delegates to `scripts/project_shell_ci.py`.
- `manifests/harness-projection.yaml` marks `shell-ci` as `implemented` with structural limitations.
- `manifests/harness-implementation-phases.yaml` marks `shell-ci-formal-harness` as `done`.
- Automated tests assert generated command drivers, workflow syntax commands, executable bits, and ACC projection counts.
