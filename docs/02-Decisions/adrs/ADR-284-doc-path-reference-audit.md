---
adr: 284
title: Documentation Path Reference Audit
status: accepted
implementation_status: implemented
classification_basis: 'implemented: ADR-284 ships a tracked docs path scanner, CLI report writer, and audit tests that fail missing exact references and runtime legacy references after bridge removal.'
date: 2026-05-12
supersedes: []
superseded_by: null
extends: [ADR-277, ADR-281, ADR-283]
implementation_files:
  - scripts/cos-doc-path-audit
  - scripts/cos_doc_path_audit.py
  - tests/audit/test_doc_path_references.py
  - docs/06-Daily/reports/doc-path-audit-latest.md
tier: maintainer
tags: [documentation, docs-vault, audit, path-integrity, agentic-primitives]
---
# ADR-284: Documentation Path Reference Audit

## Status

Accepted and implemented — 2026-05-12.

<!-- SCOPE: OS -->

**Date**: 2026-05-12

## Context

The numbered documentation vault migration intentionally removed legacy bridge
paths instead of preserving compatibility forever. That is the right final state,
but it creates a new operational requirement: every remaining tracked reference
to repository documentation must be auditable after the bridges are gone.

A plain grep is not enough. A documentation path inside a hook or primitive is a
runtime breakage risk; the same string inside an archived handoff can be valid
historical context. The OS needs a dedicated path-reference audit that sees both
the filesystem target and the surface where the reference appears.

## Decision

Add a documentation path reference audit primitive:

```bash
scripts/cos-doc-path-audit --json
scripts/cos-doc-path-audit --fail-on missing,legacy-runtime
scripts/cos-doc-path-audit --write-report docs/06-Daily/reports/doc-path-audit-latest.md
```

The audit scans tracked text files for documentation path references such as
Markdown links, quoted paths, CLI arguments, and `Path(...)` literals. Each
reference is normalized to a repository-relative target when possible and then
validated as an exact path or glob.

Findings use these categories:

| Category | Meaning |
|---|---|
| `missing-exact` | A concrete documentation path no longer exists. |
| `missing-glob` | A documentation glob no longer matches any path. |
| `legacy-reference` | A path still targets a non-numbered legacy docs bucket. |
| `legacy-runtime` | A legacy reference appears in runtime or primitive metadata surfaces. |
| `historical-allowed` | A synthetic fixture or historical reference is explicitly allowlisted. |
| `ambiguous` | The scanner found a docs reference that cannot be safely normalized. |

References are classified by semantic surface:

| Surface | Scope | Priority |
|---|---|---|
| P0 | `hooks/`, `scripts/`, `lib/`, `cmd/`, `crates/`, `bin/`, `.githooks/` | Runtime scripts, hooks, and primitives must not drift. |
| P1 | `tests/` | Tests should fail when fixtures or expectations preserve stale paths accidentally. |
| P2 | `.ai/primitives/`, `manifests/`, `.github/workflows/`, `.cognitive-os/` | Metadata and automation manifests must be explicit. |
| P3 | `docs/`, `templates/`, `rules/`, `skills/` | Documentation references are audited but can include historical narrative. |
| P4 | `docs/99-Archive/`, `archive/` | Archived references may remain when explicitly historical. |

## Consequences

- The final bridge-removal phase has a repeatable detector rather than relying
  on ad hoc grep commands.
- Runtime surfaces can be gated with `--fail-on missing,legacy-runtime` while
  documentation surfaces can continue to report ambiguous or historical cases.
- Allowlisted historical references are counted, not hidden, so the report still
  exposes long-tail cleanup work.
- The latest audit report is written under the numbered daily reports bucket and
  can be used by future agents as a migration ledger.

## Alternatives rejected

1. **Keep legacy symlink bridges indefinitely.** Rejected because the final vault
   state requires canonical numbered paths, and compatibility bridges hide broken
   runtime/doc references instead of forcing repair.
2. **Use ad hoc grep-only audits.** Rejected because grep cannot distinguish a
   P0 runtime path from P4 archived history, cannot validate exact/glob targets,
   and cannot produce a machine-readable migration ledger.
3. **Fail every historical docs string immediately.** Rejected because migration
   reports, archived handoffs, and synthetic tests need explicit historical
   allowances while still remaining visible in counts and reports.

## Verification

The implementation is verified with targeted scanner tests, existing ADR path
contracts, syntax checks, and runtime smoke commands:

```bash
scripts/cos-doc-path-audit --json --fail-on legacy-runtime --write-report docs/06-Daily/reports/doc-path-audit-latest.md
python3 -m pytest tests/audit/test_doc_path_references.py tests/audit/test_doc_paths_tracked.py tests/unit/test_adr_detector.py -q
python3 -m py_compile scripts/cos_doc_path_audit.py scripts/generate_adr_index.py
bash -n hooks/*.sh
cargo test -q
```

A stricter migration-burn-down gate is intentionally available but not yet green
until the generated report backlog is repaired:

```bash
scripts/cos-doc-path-audit --json --fail-on missing,legacy-runtime
```

## Acceptance Criteria

1. No exact documentation path references point to missing files under the strict
   `missing` gate.
2. No runtime or primitive metadata surface references legacy documentation paths
   under the `legacy-runtime` gate.
3. Historical references only pass through an explicit allowlist or inline audit
   annotation.
4. The generated report lists every remaining ambiguous or allowed reference.
