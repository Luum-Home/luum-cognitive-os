---
adr: 55
title: Docs Convention Enforcement + Skill Writers
status: accepted
implementation_status: partial
date: '2026-04-21'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: '`sdd-design` extension deferred.'
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-055 — Docs Convention Enforcement + Skill Writers

## Status

**Accepted** — 2026-04-21. Addendum to ADR-054. Implementation lives in
`lib/docs_writer.py`, `scripts/security_audit_writer.py`,
`scripts/rules_export.py`, `skills/rules-export/`,
`hooks/project-docs-convention.sh`, and a new validator contract in
`scripts/cos-config-audit.sh`.

## Context

ADR-054 formalized the 10-category `docs/` convention and shipped the
scaffolder. That ADR left two open questions explicitly deferred:

1. Which SO skills should actually WRITE into the convention (as
   opposed to merely being cross-referenced in category READMEs)?
2. Should adoption be enforced (fail CI if dirs are missing)?

This ADR closes both.

## Decision

### 1. Skill writers — 2 of 3 in-repo

Two SO skills gain `--project-dir` support and persist their output
into the correct category:

| Skill | Category | Writer |
|---|---|---|
| `security-audit` | `04-seguridad` | `scripts/security_audit_writer.py` |
| `rules-export` (NEW) | `08-estandares` | `scripts/rules_export.py` |

The third target (`sdd-design` → `02-arquitectura`) lives OUTSIDE this
repo (`~/.claude/skills/sdd-design` and `~/Tools/agent-teams-lite/`).
Editing third-party/user-level skills is out of scope for this change;
the convention is documented authoritatively here so any future
sdd-design implementation can honor it without additional coordination.

### 2. Shared writer library

`lib/docs_writer.py` centralizes the category→path mapping and the
timestamped-filename convention. Every writer that emits into the
10-category tree goes through it. This keeps the contract in ONE
place: changing ADR-054's category names requires edits to exactly
two files (`project_scaffolder.py` + `docs_writer.py`), and a unit
test asserts the two lists stay in sync.

Filename convention: `<slug>-<YYYY-MM-DD>-<HHMMSS>.md`. Timestamped so
re-runs don't clobber; projects can prune by date later.

### 3. Backward compatibility

When `--project-dir` is NOT set, skills behave exactly as before
(inline report, no file writes). This means existing invocations
continue to work; the feature is opt-in per call.

### 4. Enforcement — soft by default

`hooks/project-docs-convention.sh` checks that an adopting project has
all 10 canonical dirs. Behavior:

- Default: WARNING to stderr, exit 0 (non-blocking).
- `--strict` or `COS_STRICT_DOCS_CONVENTION=1`: exit 2.

The hook is **dual-mode**:
- CLI: `bash hooks/project-docs-convention.sh --project-dir <path>`
- PreToolUse hook: reads JSON payload from stdin; only warns when the
  triggering tool writes to a `docs/` path.

Not auto-registered in any profile — registration is an opt-in
decision by the adopting project, consistent with ADR-054's "convention
over enforcement" stance.

### 5. CI integration

`make check-docs-convention` — defaults to the SO repo, overridable:

```bash
PROJECT_DIR=/path/to/adopter make check-docs-convention            # soft-warn
STRICT=1 PROJECT_DIR=/path/to/adopter make check-docs-convention   # exit 2 on miss
```

### 6. Validator contract

New contract in `scripts/cos-config-audit.sh`:
`meta.docs_convention_enforcement`. It verifies the 7 SO-side artefacts
that enable the convention (writer lib, scaffolder lib, scaffolder CLI,
security-audit-writer CLI, rules-export CLI, enforcement hook, rules-export
skill). IMPL/PARTIAL/ASPIR per the usual tri-state, advisory-only.

## Consequences

### Positive

- Adopting projects get PREDICTABLE output locations from SO skills —
  no more ad-hoc "where did that report go".
- The writer library is the choke point — future skills (sdd-design,
  document-feature, deep-research) plug in with ~10 lines each.
- Soft-warn enforcement gives adopters time to migrate without breaking
  their build; STRICT mode is there when they're ready.
- Tests (20+ new, real-filesystem, zero mocks) prevent regression.

### Negative

- Two code paths in each writer skill (with/without `--project-dir`).
  Mitigated: the branch is a 3-line early-exit pattern; writers don't
  carry state across the two modes.
- The 10-category contract now has THREE places where the list
  appears (project_scaffolder, docs_writer, hook). A sync test asserts
  two of the three; the third (the bash hook) is visually inspected.

### Neutral

- `sdd-design` extension deferred. Documented as a follow-up: any
  implementation (in or out of this repo) that writes to
  `<project>/docs/02-arquitectura/` via `lib/docs_writer.write_doc()`
  satisfies ADR-054/055 by construction.

## Verification

- `uv run pytest tests/unit/test_project_docs_writers.py -v` — 20+ tests.
- `uv run pytest tests/unit/test_project_scaffolder.py -v` — 19/19 still pass.
- `bash scripts/cos-config-audit.sh | grep docs_convention` — shows IMPL once
  all artefacts are in place.
- `make check-docs-convention` — runs cleanly against the SO repo (warns,
  since SO itself doesn't adopt the convention — it SHIPS it).

## Related

- ADR-054 — parent convention.
- `lib/docs_writer.py` — single source of truth for category→path resolution.
- `lib/project_scaffolder.py` — category names + starter content.
- `skills/security-audit/SKILL.md` — now documents `--project-dir`.
- `skills/rules-export/SKILL.md` — new skill.
- `hooks/project-docs-convention.sh` — soft-warn enforcement.
- `scripts/cos-config-audit.sh` — validator contract.
- Engram: `adr-054/skill-extension-enforcement` — design notes.

## Open questions

1. Register `project-docs-convention.sh` in the `standard` efficiency
   profile when the first Luum adopter migrates? — Deferred until a
   real adopter is onboarded, to avoid hook noise.
2. Extend sdd-design (external) with a matching `--project-dir` arg?
   — Tracked as follow-up task; blocked on access to the external
   skill's repo.
3. Should `rules-export` also mirror `docs/02-Decisions/adrs/` as a snapshot? —
   Deferred; ADRs already have stable URLs, a snapshot may stale fast.
