# ADR-087 — ADR Namespace Consolidation

<!-- SCOPE: OS -->

**Status**: Proposed
**Date**: 2026-04-30
**Author**: Matias Nahuel Améndola
**Related**: ADR-082 (sibling for plans), ADR-027, ADR-027a, ADR-084
**Sources**: `docs/measurements/cos-adr-namespace-audit-2026-04-30.md`,
`docs/measurements/cos-duplication-audit-2026-04-30.md`

---

## Status

Proposed.

---

## Context

### The problem: ADRs are invisible to each other and to tooling

As of 2026-04-30, 97 ADR files are spread across four directories with no
governing rule about where a new ADR must land:

| Directory | File count | Naming convention | Notes |
|---|---|---|---|
| `docs/adrs/` | 61 | `ADR-NNN[-slug].md` (uppercase prefix) | Canonical by convention only; startup hook indexes this exclusively |
| `docs/architecture/adrs/` | 26 | `NNN-slug.md` (lowercase, no prefix) | Legacy; predates `docs/adrs/`; ADR-006 through ADR-027 |
| `docs/architecture/cos-dispatch/adrs/` | 12 | `NNN-slug.md` (no prefix, local numbering) | Subsystem namespace for the cos-dispatch Go module |
| `docs/architecture/harness-adoption-gap/` | 3 | `ADR-NNN-slug.md` (uppercase, local numbering) | Orphaned work-stream files; no README |

**Grand total: 97 files. 36 are invisible to all tooling.**

The startup hook (`hooks/session-startup-protocol.sh`, line 88) hard-codes:

```sh
ADRS_DIR="$PROJECT_DIR/docs/adrs"
ADR_COUNT=$(_count_md "$ADRS_DIR")
```

Only `docs/adrs/` is counted and cross-referenced. The 26 files in
`docs/architecture/adrs/` — which contain core historical decisions from the
stabilization phase — are not indexed. This is what caused the "ghost ADR"
incident documented in the audit: the orchestrator saw no ADR-002 in
`docs/adrs/` and began drafting one, unaware that three different ADR-002
files already exist across three namespaces.

### This is the same failure mode as ADR-082 at higher severity

ADR-082 fixed plan fragmentation across seven directories. That problem was
diagnosed through two confirmed duplication incidents and resolved by choosing
a single canonical root. The ADR namespace has the same structural failure:
multiple directories, only one indexed, tooling produces false negatives for
everything outside it.

The severity is higher here for two reasons:

1. **Number collisions involve Accepted decisions.** Plans landing in the
   wrong directory create discoverability gaps. ADRs in the wrong directory
   create number collisions — two different Accepted decisions that both claim
   ADR-027. Any bare citation `ADR-027` in code or documentation is now
   ambiguous even between canonical directories, not just between canonical
   and subsystem namespaces.

2. **Bare-number citations are in production files.** The audit identified
   `ADR-002` cited eight times in `install.sh` (lines 4, 43, 106, 116, 117,
   122, 251, 428) and twice in `cognitive-os.yaml` (lines 538, 541). Three
   different ADR-002 files exist across three namespaces; the citation resolves
   only by reader inference. `docs/prompt-driven-governance.md` cites `ADR-012`
   bare; `docs/HOW-TO-USE-COS.md` cites `ADR-021` bare. All four ambiguous
   citations point to ADRs that live in `docs/architecture/adrs/` but are not
   visible to tooling.

### The legacy directory predates the canonical one

`docs/architecture/adrs/` was the original ADR location during the
stabilization phase (2026-03-23 to 2026-04-28). `docs/adrs/` was established
as the canonical location starting at ADR-027, but the existing files in
`docs/architecture/adrs/` were never migrated. The `docs/adrs/README.md` now
documents the split boundary ("ADR-001 through ADR-026 live in
`docs/architecture/adrs/`") but no tool enforces it and no ADR governs it.
The disambiguation note in the README was added today as a temporary measure;
this ADR is the governing decision.

### The ADR-027 collision

The most critical collision: ADR-027 exists as two different Accepted decisions
in two directories that both claim to be part of the project namespace.

- `docs/adrs/ADR-027.md` — "SO Slimming — Test Strategy, Context Overhead,
  Resource Consumption" (Accepted 2026-04-21; has addendum ADR-027a; cited by
  ADR-028 in the same directory)
- `docs/architecture/adrs/027-headless-clustered-runtime-direction.md` —
  "Headless and Clustered Runtime Direction" (Accepted as direction 2026-04-28;
  thematically overlaps with ADR-084)

This is not a subsystem collision — both files purport to be project-level ADRs.
Any tool that resolves `ADR-027` to a file will either silently pick one or
report an error. Neither outcome is acceptable in a governance system where ADRs
are the authoritative record.

### The cos-dispatch local namespace

`docs/architecture/cos-dispatch/adrs/` was created as an isolated decision log
for the cos-dispatch Go subsystem. Its local numbering (001–011, no `ADR-`
prefix) is intentional per its README: "Records are immutable once accepted;
supersession is recorded via a new ADR that references the old one." There is
no cross-reference with project ADR numbers. This is appropriate for a
subsystem with its own release lifecycle. The audit confirms it is a deliberate
scoping choice, not accidental drift.

The question is whether this namespace should remain as-is, adopt a
disambiguating prefix, or be promoted to the root namespace. The answer affects
whether a future project-level ADR-001 through ADR-011 would collide with it.

### The harness-adoption-gap orphan

`docs/architecture/harness-adoption-gap/` holds three ADR files (ADR-001
through ADR-003, uppercase format matching the main namespace) from a focused
investigation in 2026-04-16. No README exists. These files were never
registered in any index. They are de facto orphans with local sequential
numbers that collide with the cos-dispatch namespace and, if project-level ADR
slots 001–003 are ever filled, with the main namespace too.

---

## Decision

### Option A — Consolidate everything to `docs/adrs/`

Migrate all `docs/architecture/adrs/` files to `docs/adrs/` with renaming to
`ADR-NNN-kebab-slug.md`. Leave one-line redirect stubs at all old paths for
one release cycle. Update startup hook to scan only `docs/adrs/`. Promote or
archive the three harness-adoption-gap orphans. Decide definitively on the
cos-dispatch namespace.

### Option B — Keep the split, expand tooling

Add `docs/architecture/adrs/` to the startup hook scan. Generate a unified
`docs/adrs/INDEX.md` that merges both directories. Resolve number collisions
by renaming within their current directories. Leave cos-dispatch and
harness-gap as isolated local namespaces.

**Recommendation: Option A.**

Justification by trade-off:

| Concern | Option A | Option B |
|---|---|---|
| Discoverability | Single root; one glob pattern indexes everything | Two roots; two patterns; sync risk persists |
| Collision prevention | Single namespace; linting is unambiguous | Two directories sharing the same number sequence; collision detection requires cross-directory comparison |
| Agent compliance | Agents that do not read this ADR land in `docs/adrs/` by default — the convention formalizes existing gravity | Agents must know which of two canonical directories to use; without a rule they pick wrong |
| Migration cost | 26 files renamed and moved; scriptable per ADR-082 precedent | No file moves; but tooling changes required and collision invariants cannot be enforced per-directory |
| Citation rewrite | All bare citations updated once; permanent | Bare citations remain ambiguous; tooling disambiguation adds complexity proportional to the collision count |
| Precedent | Mirrors ADR-082 exactly; reuses the same migration pattern | Diverges from the approach already proven to work for plans |

Option B's main argument — avoiding migration cost — does not hold. ADR-082
proved that 26-file migrations are scriptable and low-risk when executed as a
single changeset. The discoverability and collision invariants cannot be
enforced without a single root.

### Canonical structure (adopted)

```
docs/adrs/
  ADR-NNN-kebab-slug.md     — project-level ADRs, all of them
  ADR-NNN.md                — project-level ADRs without a slug (legacy form, permitted)
  ADR-NNNa-slug.md          — addenda (letter suffix after the number)
  README.md                 — index and convention reference (this file updates to reflect migration)
```

Any ADR appearing outside `docs/adrs/` after this ADR is accepted is a
violation, with the following two explicit exemptions:

- **`docs/architecture/cos-dispatch/adrs/`** — retained as a local subsystem
  namespace (see cos-dispatch decision below).
- **Redirect stubs** — one-line stubs left at old paths for one release cycle
  are not violations; they are migration artifacts governed by this ADR.

---

## Naming convention

- **File names**: `ADR-NNN-kebab-slug.md`. The `ADR-` prefix is uppercase,
  the number is zero-padded to three digits, the slug is lowercase kebab-case.
- **Addenda**: `ADR-NNNa-slug.md` (letter suffix directly after the number,
  before the hyphen-slug). Example: `ADR-027a-session-state-addendum.md`.
- **No slug files**: `ADR-NNN.md` is tolerated for files already in
  `docs/adrs/` that predate this convention. New files must include a slug.
- **Forbidden**: lowercase prefix (`027-topic.md`), no prefix (`027-topic.md`),
  mixed case, spaces.

---

## Renumbering policy for collisions

When migrating a file from `docs/architecture/adrs/` to `docs/adrs/`, and a
file with the same number already exists in `docs/adrs/`, one of the two ADRs
must be renumbered. The policy:

1. **The file already in `docs/adrs/` keeps its number.** It was written after
   `docs/adrs/` was established as canonical; it is already indexed by tooling;
   its addenda and cross-references use that number. Renumbering the canonical
   copy would break more references than renumbering the migrating copy.
2. **The migrating file gets the next available slot** at or above 085 (since
   084 is the highest project-level number used today).
3. **Both files get cross-reference fields** in their front matter:
   - Renumbered file: `Renumbered-from: ADR-NNN` (original number in source directory)
   - Original file that kept its number: no field required, but a note in its
     `Context` or `Status` section that a legacy ADR with the same number
     existed under a different path may be added for clarity.
4. **Any ADR linter must handle these fields**: when renaming collision-affected
   files, the linter must not flag the `Renumbered-from` field as invalid and
   must not treat the old number as a live pointer.

### ADR-027 collision resolution

`docs/adrs/ADR-027.md` (SO Slimming) keeps number 027. Rationale:

- It was written on 2026-04-17, before
  `docs/architecture/adrs/027-headless-clustered-runtime-direction.md`
  (2026-04-28). It has chronological priority.
- ADR-027a already exists in `docs/adrs/` and references ADR-027 by number.
  Renumbering the SO Slimming ADR would require renumbering ADR-027a and
  updating every citation in ADR-028 and other files in the same directory.
- The headless clustered runtime direction overlaps thematically with ADR-084
  ("Headless and Clustered Runtime Shape", Proposed retroactive). ADR-084 is
  the more recent and more complete treatment of that topic.

`docs/architecture/adrs/027-headless-clustered-runtime-direction.md` gets
renumbered to **ADR-088** (next free slot after ADR-087, this ADR). Its
migrated filename becomes `ADR-088-headless-clustered-runtime-direction.md`.
The file receives `Renumbered-from: ADR-027 (docs/architecture/adrs/)` in its
front matter. A note is added to ADR-084 cross-referencing ADR-088 as the
earlier direction document.

---

## cos-dispatch namespace decision

**Recommendation: keep as a local subsystem namespace, add a file prefix to
prevent root collisions.**

Rationale:

- The cos-dispatch decision log is a closed, immutable-once-accepted record for
  a Go subsystem with its own release lifecycle. It is not a project-level
  governance record. Promoting its 11 ADRs to the root namespace would assign
  project-level slots (001–011) to subsystem-internal decisions that have no
  meaning to the rest of the project.
- However, the current naming (`001-reuse-klaudiush-predicates.md`) has no
  prefix, creating ambiguity if a tool ever performs a recursive ADR search
  across `docs/architecture/`. A file prefix makes the isolation explicit and
  machine-readable.

**Required change**: rename all files in `docs/architecture/cos-dispatch/adrs/`
from `NNN-slug.md` to `CD-NNN-slug.md`. The `CD-` prefix identifies the
cos-dispatch namespace. The README in that directory must document: "These ADRs
use a local `CD-NNN` numbering sequence. They are not project-level ADRs and
must not be cited by bare `ADR-NNN` references."

No file moves. No number changes. No index update to `docs/adrs/`.

---

## harness-adoption-gap decision

**Decision: promote the three files to `docs/adrs/` at the next available
slots after 086.**

Rationale:

- These files use the `ADR-NNN-slug.md` format identical to the main
  namespace. They were authored as project-level decisions (git safety,
  profile simplification, harness sync path), not subsystem-internal decisions.
  The directory name reflects the work stream that produced them, not a
  subsystem boundary.
- There is no README, no declared local namespace, and no isolation policy.
  Leaving them in place would require documenting an exception with no
  principled basis.
- They do not have a subsystem lifecycle justification comparable to
  cos-dispatch. They belong in the project namespace.

Assigned slots: **ADR-089**, **ADR-090**, **ADR-091** (see migration table).

---

## Migration plan

The following table covers every file outside `docs/adrs/` that must move.
The audit (`docs/measurements/cos-adr-namespace-audit-2026-04-30.md`) is the
inventory source. No file moves in this ADR — this is design only. Migration
is a follow-up task to be executed as a single changeset immediately after
this ADR is accepted.

### Files from `docs/architecture/adrs/` — migrate to `docs/adrs/`

Files whose number has no collision in `docs/adrs/` keep their number and
receive only a rename to uppercase-prefix format.

| Current path | Target path | Number change | Rationale |
|---|---|---|---|
| `docs/architecture/adrs/ADR-001-abc-parallel-dedup-fix-broken-infra-add-global-verify.md` | `docs/adrs/ADR-001-abc-parallel-dedup-fix-broken-infra-add-global-verify.md` | None (001 not in `docs/adrs/`) | Rename to canonical format; Draft status |
| `docs/architecture/adrs/ADR-002-docker-pip-localhost-envs-targetedtestresolver-redis-dep.md` | `docs/adrs/ADR-002-docker-pip-localhost-envs-targetedtestresolver-redis-dep.md` | None (002 not in `docs/adrs/`) | Rename to canonical format; Draft status; bare citations in install.sh and cognitive-os.yaml updated as part of citation rewrite |
| `docs/architecture/adrs/006-agpl-license-compliance.md` | `docs/adrs/ADR-006-agpl-license-compliance.md` | None (006 not in `docs/adrs/`) | Rename prefix to uppercase |
| `docs/architecture/adrs/007-cognitive-os-rebrand.md` | `docs/adrs/ADR-007-cognitive-os-rebrand.md` | None | Rename prefix |
| `docs/architecture/adrs/008-multi-tool-support.md` | `docs/adrs/ADR-008-multi-tool-support.md` | None | Rename prefix |
| `docs/architecture/adrs/009-package-architecture.md` | `docs/adrs/ADR-009-package-architecture.md` | None | Rename prefix |
| `docs/architecture/adrs/010-hook-architecture-v2.md` | `docs/adrs/ADR-010-hook-architecture-v2.md` | None | Rename prefix |
| `docs/architecture/adrs/011-dual-gateway.md` | `docs/adrs/ADR-011-dual-gateway.md` | None | Rename prefix |
| `docs/architecture/adrs/012-prompt-driven-governance.md` | `docs/adrs/ADR-012-prompt-driven-governance.md` | None (012 not in `docs/adrs/`) | Rename prefix; resolves bare citation in prompt-driven-governance.md |
| `docs/architecture/adrs/013-*.md` | `docs/adrs/ADR-013-*.md` | None | Rename prefix |
| `docs/architecture/adrs/014-*.md` | `docs/adrs/ADR-014-*.md` | None | Rename prefix |
| `docs/architecture/adrs/015-*.md` | `docs/adrs/ADR-015-*.md` | None | Rename prefix |
| `docs/architecture/adrs/016-*.md` | `docs/adrs/ADR-016-*.md` | None | Rename prefix |
| `docs/architecture/adrs/017-*.md` | `docs/adrs/ADR-017-*.md` | None | Rename prefix |
| `docs/architecture/adrs/018-*.md` | `docs/adrs/ADR-018-*.md` | None | Rename prefix |
| `docs/architecture/adrs/019-*.md` | `docs/adrs/ADR-019-*.md` | None | Rename prefix |
| `docs/architecture/adrs/020-*.md` | `docs/adrs/ADR-020-*.md` | None | Rename prefix |
| `docs/architecture/adrs/021-vendor-agnostic-with-adapters.md` | `docs/adrs/ADR-021-vendor-agnostic-with-adapters.md` | None (021 not in `docs/adrs/`) | Rename prefix; resolves bare citation in HOW-TO-USE-COS.md |
| `docs/architecture/adrs/022-*.md` | `docs/adrs/ADR-022-*.md` | None | Rename prefix |
| `docs/architecture/adrs/023-*.md` | `docs/adrs/ADR-023-*.md` | None | Rename prefix |
| `docs/architecture/adrs/024-*.md` | `docs/adrs/ADR-024-*.md` | None | Rename prefix |
| `docs/architecture/adrs/025-*.md` | `docs/adrs/ADR-025-*.md` | None | Rename prefix |
| `docs/architecture/adrs/026-*.md` | `docs/adrs/ADR-026-*.md` | None | Rename prefix |
| `docs/architecture/adrs/026a-decisions.md` | `docs/adrs/ADR-026a-decisions.md` | None | Addendum, rename prefix |
| `docs/architecture/adrs/027-headless-clustered-runtime-direction.md` | `docs/adrs/ADR-088-headless-clustered-runtime-direction.md` | **027 → 088** | Collision with `docs/adrs/ADR-027.md` (SO Slimming, keeps 027); add `Renumbered-from: ADR-027 (docs/architecture/adrs/)` to front matter |

### Files from `docs/architecture/harness-adoption-gap/` — migrate to `docs/adrs/`

| Current path | Target path | Number change | Rationale |
|---|---|---|---|
| `docs/architecture/harness-adoption-gap/ADR-001-harness-skills-sync-path.md` | `docs/adrs/ADR-089-harness-skills-sync-path.md` | **001 → 089** | Local number 001 collides with architecture/adrs ADR-001 and cos-dispatch CD-001; add `Renumbered-from: ADR-001 (harness-adoption-gap)` |
| `docs/architecture/harness-adoption-gap/ADR-002-simplify-profiles.md` | `docs/adrs/ADR-090-simplify-profiles.md` | **002 → 090** | Collision with architecture/adrs ADR-002 and cos-dispatch CD-002; add `Renumbered-from: ADR-002 (harness-adoption-gap)` |
| `docs/architecture/harness-adoption-gap/ADR-003-agent-git-safety.md` | `docs/adrs/ADR-091-agent-git-safety.md` | **003 → 091** | Collision with cos-dispatch CD-003; add `Renumbered-from: ADR-003 (harness-adoption-gap)` |

### Files in `docs/architecture/cos-dispatch/adrs/` — rename in place

No directory change. Only file prefix added.

| Current filename | Target filename | Notes |
|---|---|---|
| `001-reuse-klaudiush-predicates.md` | `CD-001-reuse-klaudiush-predicates.md` | Add `CD-` prefix |
| `002-transformer-separate-interface.md` | `CD-002-transformer-separate-interface.md` | Add `CD-` prefix |
| `003-*.md` through `011-*.md` | `CD-003-*.md` through `CD-011-*.md` | Add `CD-` prefix to all |
| `README.md` | `README.md` | Update to document `CD-NNN` convention; no move |

### Redirect stubs

After each `git mv`, a one-line stub is created at the old path:

```markdown
# Moved

This ADR has moved to `docs/adrs/ADR-NNN-slug.md` (ADR-087 migration, 2026-04-30).
```

Stubs are removed after one release cycle (v0.13.0 or equivalent).

### Timing

Migration is a single follow-up task. It must not be split across multiple
changesets because partial migration leaves the namespace in a worse state
than either the pre- or post-migration state: tooling may index migrated files
while legacy paths still exist, producing duplicates in any ADR count.

---

## Citation rewrite plan

The following citation sites must be updated as part of the migration changeset.
After migration, every citation must be either a full path or a bare number
that resolves unambiguously within `docs/adrs/` (i.e., no two files in
`docs/adrs/` share that number).

| File | Current citation | Required change |
|---|---|---|
| `install.sh` (lines 4, 43, 106, 116, 117, 122, 251, 428) | `ADR-002` (bare) | Update to full path `docs/adrs/ADR-002-docker-pip-...md` or `docs/adrs/ADR-090-simplify-profiles.md` depending on which decision each line actually invokes — verify per-line during migration |
| `cognitive-os.yaml` (lines 538, 541) | `ADR-002` (bare) | Same per-line verification and full-path update |
| `tests/unit/test_efficiency_optimization.py` (line 88) | `ADR-002` (bare) | Same per-line verification |
| `docs/prompt-driven-governance.md` | `ADR-012` (bare) | Update to `docs/adrs/ADR-012-prompt-driven-governance.md` after migration |
| `docs/HOW-TO-USE-COS.md` (line 170) | `ADR-021` (bare) | Update to `docs/adrs/ADR-021-vendor-agnostic-with-adapters.md` after migration |
| `docs/architecture/stabilization-roadmap.md` | References `docs/architecture/adrs/` by full path | Update all full-path references to `docs/adrs/` after migration |
| `docs/architecture/why-skills-and-rules-became-claude-centered.md` | `docs/architecture/adrs/` by full path | Update all full-path references |
| `docs/architecture/adrs/026a-decisions.md` | Relative path to parent ADR | Update after rename |

The ADR-002 citations in `install.sh` and `cognitive-os.yaml` are the
highest-risk rewrite. Each occurrence must be verified against context (profile
collapse logic vs. docker/pip logic) before assigning a target path. This
per-line verification is mandatory; a bulk substitution is not acceptable.

---

## Enforcement

### Audit test

A new test `tests/audit/test_adr_locations.py` must be created, parallel to
`tests/audit/test_plan_locations.py` established by ADR-082. It fails if any
`.md` file matching `ADR-[0-9]*.md` (case insensitive) is found outside
`docs/adrs/` except for:

- Files matching `docs/architecture/cos-dispatch/adrs/CD-*.md` (exempted
  subsystem namespace)
- Files matching `docs/adrs/` (the canonical location itself)
- One-line redirect stubs identified by the string `# Moved` as the first line

The allowlist of exemptions is maintained in the test itself with a documented
rationale for each exemption.

### Startup hook update

`hooks/session-startup-protocol.sh` must be updated to replace the current
single-directory scan with a scan of `docs/adrs/` exclusively (after
migration, that directory contains everything). The line:

```sh
ADRS_DIR="$PROJECT_DIR/docs/adrs"
```

is already correct for the post-migration state and requires no change to the
variable itself. However, the hook must be verified to not also scan
`docs/architecture/adrs/` after migration (it currently does not, but the
absence of a scan line should be confirmed, not assumed).

### ADR linter field handling

Any ADR linter introduced in the future must:

1. Recognize `Renumbered-from: ADR-NNN (source-directory)` as a valid
   front-matter field and not flag it as unknown.
2. Not treat the value of `Renumbered-from` as a live pointer (it references
   a path that may no longer exist after stub removal).
3. Recognize `Renumbered-to: ADR-NNN` as the reciprocal field on a source
   stub and not report the stub as a malformed ADR.

### Pre-commit gate

Not mandated by this ADR. The audit test runs in the `broad` test lane and is
sufficient as a CI gate. Whether to add a pre-commit hook that rejects ADR
files written outside `docs/adrs/` is left as an open question (see below).

---

## Consequences

### Positive

- **Single root, one glob** — startup indexing requires one path pattern. After
  migration, `docs/adrs/` contains all 88+ project-level ADRs and the startup
  hook requires no logic changes to achieve full coverage.
- **Number collision eliminated** — the ADR-027 ambiguity and all other
  numeric collisions between `docs/adrs/` and `docs/architecture/adrs/` are
  resolved permanently. Any future collision is detected immediately by the
  audit test.
- **Bare-number citations become safe** — after the citation rewrite, bare
  `ADR-NNN` references in production files resolve unambiguously to
  `docs/adrs/ADR-NNN-*.md`. No per-reader inference required.
- **cos-dispatch isolation is explicit** — the `CD-` prefix makes the subsystem
  namespace machine-readable. A recursive ADR search that finds `CD-001` cannot
  confuse it with a project-level ADR-001.
- **harness-adoption-gap decisions are recoverable** — three accepted decisions
  (git safety, profile simplification, harness sync path) that were invisible
  to tooling are promoted to the main index at slots 087–089.

### Negative / Trade-offs

- **One-time migration cost** — 29 files must move or rename (26 from
  `docs/architecture/adrs/`, 3 from `docs/architecture/harness-adoption-gap/`,
  11 cos-dispatch renames in place). Each move requires updating cross-references.
  Per ADR-082's precedent this is scriptable and low-risk when executed as a
  single changeset.
- **Redirect stubs at old paths** — stubs are required to avoid breaking any
  external links (e.g., GitHub blame links, external references to legacy paths).
  They must be tracked and removed after one release cycle; if not removed they
  become their own form of fragmentation.
- **`docs/architecture/adrs/` becomes an empty deprecated directory** — after
  migration it should be removed. A directory that still exists but is no longer
  used creates confusion for agents that enumerate `docs/architecture/` and
  find an empty `adrs/` subdir. Removal should be part of the migration
  changeset.
- **Citation rewrite is non-trivial for ADR-002** — the eight `install.sh`
  references must be verified per-line. An incorrect rewrite (pointing to the
  wrong ADR-002 file) would silently alter the documented rationale for
  installation decisions. This is the highest-risk step in the migration.

---

## Open questions

**1. Should a pre-commit hook reject new ADRs created outside `docs/adrs/`?**

The audit test catches violations at CI time. A pre-commit hook would catch
them earlier, before the file is committed. The risk of false positives
(rejecting a file that happens to match `ADR-*.md` but is not actually an ADR)
must be evaluated. Recommendation: add the hook in a follow-up once the
migration is complete and the exemption list is stable.

**2. Should `docs/architecture/cos-dispatch/adrs/` ever be absorbed?**

If the cos-dispatch subsystem is ever dissolved or fully absorbed into the
project core, its local ADR log would need a decision: promote to root
namespace at the next free slots, or archive in place. This ADR exempts the
subsystem but does not preclude a future ADR from absorbing it. The `CD-NNN`
prefix makes that future migration straightforward.

**3. What is the correct ADR-002 interpretation in `install.sh`?**

The audit identified three candidate files. The per-line verification during
migration will produce a definitive answer. If the install.sh citations actually
refer to `docs/architecture/harness-adoption-gap/ADR-002-simplify-profiles.md`
(now ADR-090), the migration team should also update the comment text in
`install.sh` to reference the migrated path explicitly so future readers do not
face the same ambiguity.

---

## Alternatives rejected

- **Option B (keep split, expand tooling)**: Rejected because expanding the
  startup hook to scan two directories does not resolve the ADR-027 collision
  — it makes the collision visible but requires a second rule to say which
  file wins. Option A eliminates the collision by placing both files in a
  namespace where the number must be unique.
- **Promote cos-dispatch ADRs to root namespace**: Rejected because it assigns
  project-level numbers (001–011) to subsystem-internal decisions. The
  cos-dispatch ADRs were written to govern the internal design of a Go module;
  promoting them to the project namespace would inflate the project ADR count
  and create misleading precedents (e.g., a project-level "ADR-001" that is
  actually about a predicate-matching library in a dispatcher subsystem).
- **Leave harness-adoption-gap as an exempted local namespace**: Rejected
  because the files use project-namespace format (`ADR-NNN-slug.md`) with no
  local isolation marker. Exempting them would require documenting an exception
  with no principled basis, unlike the cos-dispatch exemption which is backed
  by a README and an isolated naming convention.

---

## Verification

```bash
# After migration is complete
python3 -m pytest tests/audit/test_adr_locations.py -q --tb=short

# Confirm startup hook scans only docs/adrs/ and not the legacy directory
grep -n "architecture/adrs" hooks/session-startup-protocol.sh
# Expected: no output (legacy directory no longer in scope)

# Confirm no bare ADR-002 citations remain in production files
grep -rn "ADR-002[^-]" install.sh cognitive-os.yaml tests/
# Expected: no output

# Confirm redirect stubs exist for every moved file
find docs/architecture/adrs docs/architecture/harness-adoption-gap -name "*.md" | xargs grep -l "# Moved"
# Expected: one stub per moved file
```

---

## Cross-references

- ADR-082: Plan Location Convention (sibling decision; migration pattern reused here)
- ADR-027: SO Slimming — Test Strategy, Context Overhead (keeps number 027)
- ADR-027a: SO Slimming addendum (unaffected; in canonical directory)
- ADR-084: Headless and Clustered Runtime Shape (thematic successor to ADR-088)
- ADR-088: Headless and Clustered Runtime Direction (renumbered from `docs/architecture/adrs/027`)
- ADR-089: Harness Skills Sync Path (renumbered from `harness-adoption-gap/ADR-001`)
- ADR-090: Simplify Install Profiles (renumbered from `harness-adoption-gap/ADR-002`)
- ADR-091: Agent Git Operations Safety (renumbered from `harness-adoption-gap/ADR-003`)
- Namespace audit: `docs/measurements/cos-adr-namespace-audit-2026-04-30.md`
- Duplication audit: `docs/measurements/cos-duplication-audit-2026-04-30.md`
- `hooks/session-startup-protocol.sh` (verification target post-migration)
- `tests/audit/test_adr_locations.py` (to be created)
