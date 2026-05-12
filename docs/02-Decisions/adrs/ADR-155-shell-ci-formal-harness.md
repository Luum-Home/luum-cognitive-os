---

adr: 155
title: Shell CI Formal Harness Projection
status: accepted
implementation_status: implemented
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
  - docs/09-Quality/manual-tests/shell-ci-formal-harness.md
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

## Operational Guide

### What changes for the operator

Before this ADR: `shell-ci` was an ACC adapter (it could score shell/CI commands) but was still listed as `planned` in `manifests/harness-projection.yaml`. This created a confusing split: the adapter ran, but the harness was not promoted, so consumers could not use `cos_init.py --harness shell-ci`.

After this ADR:

- `cos_init.py --harness shell-ci` is a first-class installation path:
  ```bash
  python3 scripts/cos_init.py --default --harness shell-ci --project-dir /path/to/consumer
  ```
  This installs `.cognitive-os/` content, runs the shell/CI projector, writes `.cognitive-os/shell-ci-projection.json`, creates command copies under `.cognitive-os/scripts/cos/`, driver symlinks under `scripts/`, and generates `.github/workflows/cognitive-os-shell-ci.yml`.
- ACC records `shell-ci/default` and `shell-ci/full` projection counts alongside IDE harnesses.
- `manifests/harness-implementation-phases.yaml` marks `shell-ci-formal-harness` as `done`.

### What this answers (and what it doesn't)

**Answers:**
- "Can I adopt COS in a CI-only project without an IDE account?" — Yes. `--harness shell-ci` installs a fully functional CLI/workflow projection.
- "Is the generated GitHub Actions workflow correct?" — The syntax is validated by tests; see `tests/unit/test_project_shell_ci.py`. Runtime job success still depends on the consumer's stack.
- "Does the shell/CI harness get the same rules/skills as Claude/Codex?" — Yes. The normal `.cognitive-os/` content (rules, hooks, skills, templates) is installed for all harnesses.

**Does not answer:**
- "Will projected commands run without errors in any consumer stack?" — Proof is structural (command paths, workflow syntax). Runtime behavior depends on installed dependencies.
- "Does the shell/CI harness re-enable the SO's disabled broad CI workflow?" — No. The SO's own `.github/workflows/` state is not changed by this ADR.

### Daily operational pattern

For a CI-first consumer project adoption:
1. Run `python3 scripts/cos_init.py --default --harness shell-ci --project-dir .`
2. Inspect `.github/workflows/cognitive-os-shell-ci.yml` and adjust trigger conditions to match the consumer's CI setup.
3. Review the command symlinks under `scripts/` — each maps to a canonical COS command under `.cognitive-os/scripts/cos/`.
4. Run `python3 scripts/acc_pipeline.py --project-dir . --refresh` in the consumer project to confirm `shell-ci/default` appears in the projection counts.

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
