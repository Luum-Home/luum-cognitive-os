---
adr: 217
title: Cross-Stack Adoption Truth Audit Toolchain
status: accepted
implementation_status: partial
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: 162 pending /repo-scout).
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-217 — Cross-Stack Adoption Truth Audit Toolchain

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted — slice 1 audit substrate active
**Date**: 2026-05-06
**Related**: ADR-212, ADR-215, ADR-208, ADR-211, ADR-031, ADR-206
**Source**: Operator question — *"analysis is missing on whether it is already adopted and how (this should also be in the primitives)"*

---

## Context

ADR-212 closed the cross-stack license-audit gap. ADR-215 proposes the
symmetric cross-stack secret-audit toolchain. **Both audit what is in the
codebase**, not whether it is adopted as documented.

The 2026-05-06 dependency-audit pass surfaced the structural gap that motivates
this ADR: dependency state is split across four sources of truth, none of
which fully agrees with the others, and no canonical primitive enforces
agreement:

1. **Lockfiles** (`pyproject.toml` + `uv.lock`, `go.mod` + `go.sum`,
   `dashboard/package-lock.json`, `.gitmodules`) — what is actually integrated.
2. **`NOTICE`** at the repo root — what we publicly accredit.
3. **`docs/04-Concepts/root/component-sources.md`** — manual status declarations
   (OPTIONAL/EVALUATED/WATCH/PLANNED/Listed in NOTICE).
4. **`docs/06-Daily/reports/external-tools-inventory-*.md`** — research buckets
   (3 deep-audited / 17 upstream-or-own / 76 surface-investigated /
   162 pending /repo-scout).

When these sources disagree, four dangerous combinations emerge:

| Combination | Risk |
|---|---|
| Listed in `NOTICE` AND not in any lockfile / submodule | "Dead dep in NOTICE" — accrediting fictitious deps |
| `Status=PLANNED` in `component-sources.md` AND appears in marketing/business docs as feature | Aspirational claim leakage (ADR-206 territory) |
| In lockfile/code AND not declared in `component-sources.md` | Untracked adoption (drift from declared inventory) |
| `Status=WATCH/EVALUATED` AND docs say "we use X" | Overclaim of integration |

ADR-031 (Continuous Aspirational/Dormant/Real Audit) classifies internal
primitives. ADR-208 (Imported Pattern Closure Contract) gates dependency
adoption at commit time. **Neither closes the loop on the four dangerous
combinations above**, because they operate at a different layer.

## Decision

Adopt a manifest-backed cross-stack adoption-truth audit, mirroring ADR-212's
shape:

1. **Single canonical CLI**: `cos adoption audit [--json] [--strict]`.
2. **Manifest declaration**: `manifests/cross-stack-adoption-truth.yaml`
   (path globs for lockfiles, NOTICE schema, component-sources schema,
   inventory paths).
3. **Schema-versioned report**: `cross-stack-adoption-truth-report/v1`.
4. **Implementation**: `lib/cross_stack_adoption_truth.py`
   + `scripts/cos-cross-stack-adoption-truth` Python entrypoint.
5. **Wrapper**: `cos adoption` shell dispatch in `scripts/cos`.

The audit MUST:

- Inventory all top-level dependencies across stacks (Python top-level via
  `pyproject.toml [project] dependencies`, Go direct via `go.mod` `require`
  blocks, Node via `dashboard/package.json`, submodules via `.gitmodules`).
- Parse `NOTICE` into structured entries (name, URL, declared license).
- Parse `docs/04-Concepts/root/component-sources.md` into structured rows
  (name, URL, license, status).
- Parse `docs/06-Daily/reports/external-tools-inventory-*.md` into bucketed URL sets.
- Emit unified matrix with one row per dep:
  ```
  name | url | in_lockfile | in_notice | component_sources_status |
  inventory_bucket | adoption_verdict
  ```
- Classify each row's `adoption_verdict`:
  ```
  INTEGRATED            in lockfile + declared
  INTEGRATED_UNTRACKED  in lockfile + NOT in component-sources
  DEAD_IN_NOTICE        in NOTICE + NOT in lockfile/submodule
  ASPIRATIONAL_PLANNED  Status=PLANNED + appears as feature in marketing docs
  OVERCLAIMED           Status=WATCH/EVALUATED + docs say "we use X"
  ACTIVELY_TRACKED      In tracked-but-not-yet-integrated bucket
  NOT_APPLICABLE        Excluded by manifest (transitive-only, etc.)
  ```
- `--strict` exits non-zero on any DEAD_IN_NOTICE, ASPIRATIONAL_PLANNED, or
  OVERCLAIMED finding.

The manifest MUST declare:

- Top-level dep paths (lockfiles, NOTICE, component-sources, inventory globs).
- Allowlist for transitive deps (NOT required to appear in component-sources).
- Allowlist for submodules used as code-reading references (e.g., hermes-agent
  per ADR-080, caveman per ADR-067) where lockfile mismatch is expected.
- Marketing-doc paths to scan for aspirational-claim leak detection
  (`docs/08-References/business/*.md`, `README.md`, future `docs/landing-*.md`).

## Enforcement and integration

- ADR-211 (Service-Mode Readiness Gate) nivel 9 ("Public claim gate passes")
  consumes `cos adoption audit --strict` exit code.
- ADR-206 (Aspirational Claim Decommission Gate) consumes
  ASPIRATIONAL_PLANNED + OVERCLAIMED findings.
- ADR-208 (Imported Pattern Closure Contract) consumes
  INTEGRATED_UNTRACKED findings as gate inputs at commit time.

## Implementation status — 2026-05-06

Active first slice:

- `manifests/cross-stack-adoption-truth.yaml` declares lockfile, NOTICE, component-sources, inventory, marketing-doc, allowlist, and strict-verdict sources.
- `lib/cross_stack_adoption_truth.py` parses Python, Go, Node, submodules, NOTICE, component-sources, and external inventory references into `cross-stack-adoption-truth-report/v1`.
- `scripts/cos-cross-stack-adoption-truth` plus `scripts/cos adoption audit` expose the CLI.
- `tests/unit/test_cross_stack_adoption_truth.py` and `tests/behavior/test_cross_stack_adoption_truth_cli.py` cover core classifications and live route smoke.

Not yet active: ADR-211 readiness consumption, ADR-206/208 downstream consumption, curated baseline remediation, and `--suggest` snippets for missing component-source entries.

## Consequences

### Positive

- One audit replaces four manual cross-references that today nobody runs.
- Marketing copy cannot ship with WATCH/PLANNED features represented as
  shipped (ADR-206 enforces; ADR-217 detects).
- NOTICE never accredits a dep that does not exist (avoids the "Dead in
  NOTICE" embarrassment we found in `secrets-and-leaks-2026-05-06.md`'s
  follow-up scan).
- Schema-versioned output enables Maintainer agent (ADR-201) to consume
  verdicts deterministically.
- Closes the dogfood-evidence pattern of "research docs exist but are not
  cross-referenced against lockfile" recorded across this 2026-05-06 session.

### Negative / trade-offs

- Requires curation of `manifests/cross-stack-adoption-truth.yaml` whenever
  a new dep type or research-doc shape is introduced.
- May produce false-positive INTEGRATED_UNTRACKED for transitive deps if the
  allowlist is incomplete; mitigation is the `transitive-allowlist` block.
- Initial baseline run will surface a backlog of OVERCLAIMED entries from
  legacy marketing copy — this is expected and is the gate's value.

## Alternatives rejected

- **Treat adoption as `docs/04-Concepts/root/component-sources.md` is enough**: rejected. The
  manual table drifts; nobody reconciles it weekly.
- **Per-stack tools** (e.g., `pip-licenses` adoption matrix, `go list -m`
  inventory): rejected. Different output formats, no cross-stack truth.
- **Bake adoption into ADR-208 commit gate only**: rejected. ADR-208 protects
  forward; this ADR audits backward (existing state). Both are needed.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_cross_stack_adoption_truth.py tests/behavior/test_cross_stack_adoption_truth_cli.py -q
scripts/cos adoption audit --json
scripts/cos adoption audit --strict
```

The behavior tests must prove:

- A dep present in `uv.lock` and absent from `component-sources.md` is
  classified `INTEGRATED_UNTRACKED`.
- A `NOTICE` entry whose name does not appear in any lockfile/submodule is
  classified `DEAD_IN_NOTICE`.
- A `component-sources.md` entry with `Status=PLANNED` whose name appears in
  `docs/08-References/business/*.md` as a feature is classified `ASPIRATIONAL_PLANNED`.
- Transitive-only deps in the manifest allowlist are NOT flagged as
  `INTEGRATED_UNTRACKED`.
- `--strict` exits 1 on any DEAD/ASPIRATIONAL/OVERCLAIMED finding.

## Implementation slices

1. `manifests/cross-stack-adoption-truth.yaml` skeleton (lockfile globs,
   transitive allowlist, submodule allowlist, marketing-doc globs).
2. `lib/cross_stack_adoption_truth.py` — parsers per source + classifier.
3. `scripts/cos-cross-stack-adoption-truth` + `cos adoption` shell dispatch.
4. Unit tests (parser correctness, classification matrix, allowlist
   round-trip).
5. Behavior tests (CLI smoke, strict-mode exit codes, baseline run on the
   live repo with documented expected backlog).
6. ADR-211 nivel 9 integration.
7. ADR-206 + ADR-208 cross-link consumption hooks.

## Open questions

- Should the audit attempt to auto-suggest the missing
  `component-sources.md` entry for INTEGRATED_UNTRACKED deps? Recommendation:
  yes, with `--suggest` flag emitting a YAML snippet operator can paste.
- Should baseline-run findings be archived in
  `.cognitive-os/reports/adoption-truth/` like the license/secret audits?
  Recommendation: yes — same convention.
- Cadence: runs as part of `cos pre-launch verify` and on a weekly cron in
  service mode (ADR-031 sibling cadence)?

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
