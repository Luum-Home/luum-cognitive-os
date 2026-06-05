---
adr: 334
title: Portable Duplicate-Code Quality Primitive
status: accepted
implementation_status: implemented
date: '2026-06-05'
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos-quality-duplicates
  - scripts/cos_quality_duplicates.py
  - scripts/cos_init.py
  - manifests/dependencies.yaml
  - docs/04-Concepts/architecture/language-agnostic-duplication-tooling-audit-2026-06-05.md
tier: consumer
tags: [quality, duplication, jscpd, semgrep, cpd, install, consumer-projects]
classification_basis: portable CLI, consumer install projection, dependency manifest coverage, baseline ratchet, and tests
---

# ADR-334: Portable Duplicate-Code Quality Primitive

## Status

Accepted — implemented on 2026-06-05.

## Context

Multiple local consumer projects using Cognitive OS had independently built duplicate-code gates. The repeated pattern was not a single scanner; it was a stack:

- `jscpd` for broad lexical copy/paste detection across many languages and document formats.
- Function/body normalization for repeated logic that lexical clone scans miss.
- Go-specific lanes such as `dupl` and `golangci-lint` where Go is present.
- Policy-pattern lanes such as Semgrep and ast-grep for repeated business-rule or architecture smells.
- Baseline/ratchet behavior so existing debt is visible but only new duplicate findings block.

If each consumer repository keeps writing its own scripts, the OS violates its product promise: projects should consume portable agentic primitives instead of rebuilding governance glue.

External tool research on 2026-06-05 confirmed:

- `jscpd` is the best primary external clone detector for language breadth.
- PMD CPD is useful but narrower and should be optional.
- Semgrep generic mode is useful for policy/common-logic pattern matching, but generic mode is not syntax-aware clone proof.

## Decision

Add a portable duplicate-code primitive:

1. `scripts/cos-quality-duplicates` runs a project-local duplicate scan.
2. `scripts/cos_quality_duplicates.py` is the implementation and is dependency-free by default.
3. Consumer installs copy both files into `.cognitive-os/bin/` so downstream projects do not need local custom scripts.
4. The scanner always runs fallback COS-owned lanes:
   - lexical normalized token similarity;
   - normalized function-body repeats for Python, shell, and JS/TS-like syntax.
5. External scanners are discovered and reported as adapters:
   - `jscpd`: primary lexical clone detector;
   - `pmd`: optional CPD adapter;
   - `semgrep`: policy/common-logic adapter, not clone proof;
   - `dupl` and `golangci-lint`: optional Go lanes;
   - `ast-grep`: optional AST policy lane.
6. The dependency manifest installs/plans these tools in dev, CI, full, and headless profiles. The default/core profile stays lightweight.
7. The CLI supports `--write-baseline`, `--fail-on-new`, `--fail-on-findings`, and `--fleet`.
8. Fleet discovery uses the existing COS installations registry first and marker scan second.

## Alternatives rejected

- **Only use `jscpd`**: rejected because it leaves projects without a scanner when Node/npm is absent and misses normalized business-logic repeats.
- **Make Semgrep the clone detector**: rejected because Semgrep generic mode is not syntax-aware and is better as a policy-pattern lane.
- **Require every consumer repo to keep its own duplicate-quality scripts**: rejected because this duplicates governance code across the fleet.
- **Install all tools in the default/core profile**: rejected because default install must stay lightweight and portable. Quality tools belong in dev/CI/full/headless profiles and remain discoverable in reports when absent.

## Consequences

- Consumer projects get a no-dependency duplicate-code report immediately after SO install/update.
- Mature projects can opt into external scanners without rewriting wrapper logic.
- CI can use fail-new ratchets instead of strict all-debt blocking on first adoption.
- COS maintainers can run fleet discovery to find projects using the SO and coordinate quality tooling adoption.
- External tool absence degrades to fallback lanes rather than blocking basic quality visibility.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. `scripts/cos-quality-duplicates --project-root <tmp> --json` works without Node, Go, PMD, Semgrep, dupl, golangci-lint, or ast-grep.
2. `--write-baseline` writes a stable baseline and `--fail-on-new` fails only after a new duplicate identity appears.
3. `--fleet --json` discovers registry projects and marker-scan projects with paths redacted by default.
4. `cos_init.py` installs `.cognitive-os/bin/cos-quality-duplicates` and `.cognitive-os/bin/cos_quality_duplicates.py` into consumer projects.
5. `manifests/dependencies.yaml` includes `jscpd`, `pmd`, `dupl`, `ast-grep`, and `semgrep` in dev/CI/full/headless install profiles.
6. The dependency manifest validates.
```

## Verification

```bash
python3 -m pytest tests/unit/test_cos_quality_duplicates.py tests/behavior/test_cos_quality_duplicates_cli.py tests/integration/test_install_quality_duplicates_primitive.py -q
bash scripts/manifest-check.sh --json
python3 -m py_compile scripts/cos_quality_duplicates.py scripts/cos_init.py
```
