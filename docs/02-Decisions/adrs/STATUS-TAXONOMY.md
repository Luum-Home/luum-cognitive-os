# ADR Status Taxonomy

Status: Active
Date: 2026-05-12
Scope: OS documentation and tooling

## Purpose

ADR metadata must separate three concepts that were historically collapsed into
one `status` string:

1. **Decision status** — whether the architecture decision is proposed,
   accepted, exploratory, closed, replaced, deprecated, or a reserved tombstone.
2. **Implementation status** — whether the accepted work is implemented,
   partial, blocked, deferred, or not applicable.
3. **Index bucket** — where the ADR appears in `docs/02-Decisions/adrs/INDEX.md` for human
   and agent navigation.

When these concepts are mixed, ADRs acquire labels such as `Phase`, `Resolved`,
or nested `part_a/part_b` maps that are hard for tooling to interpret and easy
for agents to overclaim.

## Canonical Decision Status Values

Use lowercase values in frontmatter.

| status | Meaning | Index bucket | Notes |
|---|---|---|---|
| `proposed` | Actionable decision awaiting acceptance. | Proposed | Has enough shape to review or implement once accepted. |
| `exploration` | Non-binding research gate or pending fork decision. | Exploration | Does not authorize implementation; prevents premature commitment. |
| `accepted` | Decision is approved and still governs future work. | Active | Implementation may be complete, partial, blocked, or deferred. |
| `implemented` | Accepted decision with required implementation evidence present. | Active | Use only when implementation files/tests are declared and verified. |
| `resolved` | Tracking/follow-up ADR whose enumerated items are closed. | Resolved | Terminal but not deprecated; useful for bug registries and cleanup lanes. |
| `superseded` | Replaced by a newer ADR or authority. | Superseded | Must include `superseded_by` when a successor is known. |
| `deprecated` | No longer recommended, but without a single authoritative replacement. | Deprecated | Use for retired guidance or surfaces in staged removal. |
| `tombstone` | Reserved/retired ADR slot or retired component marker. | Tombstone | Do not reuse the ADR number; may include `superseded_by`. |

## Canonical Implementation Status Values

Every ADR that has YAML frontmatter must include `implementation_status`. Prose-only historical ADRs may remain unclassified until their gradual frontmatter migration batch.

| implementation_status | Meaning |
|---|---|
| `not-applicable` | Exploration/tombstone/status-only ADR has no implementation surface. |
| `planned` | Accepted or proposed work is not started. |
| `partial` | Some accepted slices are implemented; more remain. |
| `partial-blocked` | Some accepted slices are implemented and a named blocker remains. |
| `blocked` | Work cannot proceed until a named blocker clears. |
| `deferred` | Work is intentionally delayed by policy or sequencing. |
| `implemented` | Required implementation files/tests exist and all declared `implementation_files` resolve on disk. |
| `resolved` | Tracking items are closed. |

`implementation_status` must not replace decision status. For example, an ADR
can be `status: accepted` and `implementation_status: partial-blocked`.

## Mixed-State Rule

A single ADR file must not use a map or list as `status`. If a document contains
multiple independent lifecycle states, split the pending state into a follow-up
ADR or addendum. The original ADR may retain implemented/propose-only mechanism
scope, while the future operational promotion receives its own `proposed` ADR.

## Index Mapping

`docs/02-Decisions/adrs/INDEX.md` groups first by decision status. The Active bucket is subdivided by `implementation_status` so accepted decisions remain semantically active while navigation stays bounded.

| Decision status | Bucket |
|---|---|
| `accepted`, `implemented` | Active |
| `proposed` | Proposed |
| `exploration` | Exploration |
| `resolved` | Resolved |
| `superseded` | Superseded |
| `deprecated` | Deprecated |
| `tombstone` | Tombstone |

## Canonical Examples

| ADR | Decision status | Implementation status | Bucket | Rationale |
|---|---|---|---|---|
| ADR-044 | `accepted` | `partial-blocked` | Active | Lazy context loading still governs; slash-command slice is blocked. |
| ADR-132 | `exploration` | `not-applicable` | Exploration | Explicitly non-binding pending Shape A/B fork decision. |
| ADR-174b | `accepted` | `implemented` | Active | Auto-generation and propose-only soak evaluator are accepted. |
| ADR-174c | `proposed` | `deferred` | Proposed | Actual advisory-to-blocking promotion awaits soak data and operator approval. |
| ADR-238 | `resolved` | `resolved` | Resolved | All tracked Tier 1-4 bugs are fixed and verified. |
| ADR-253 | `tombstone` | `not-applicable` | Tombstone | Squads slot is retired; ADR-251 is canonical authority. |

## Tooling Contract

- Validators must reject nested/non-string `status` values for new or normalized
  ADRs.
- `exploration`, `resolved`, and `tombstone` are valid decision statuses.
- ADR routing and suggestion tools should skip `superseded`, `deprecated`, and
  `tombstone` records by default.
- Capability coverage may count `resolved` ADRs when the coverage contract asks
  for accepted-or-resolved ADRs.
- Generated indexes must display implementation status separately from decision
  status and subdivide the Active bucket by implementation status.
- ADRs with YAML frontmatter must include scalar `implementation_status`; prose-only
  ADRs remain `Active / Unclassified` until gradual frontmatter migration.
- Every declared `implementation_files` entry is a falsifiable disk claim and
  must resolve on disk regardless of decision `status` or `implementation_status`.
  Runtime/generated artifacts that are not committed must be documented outside
  `implementation_files` or covered by a specialized allowlist audit.
- `implementation_status: implemented` must fail audit if any declared
  `implementation_files` entry is missing. A §Operational Guide rendered from
  §Decision prose is operator documentation, not implementation evidence.

## Alternatives Rejected

- **Map every non-active value to `Deprecated`** — rejected because it destroys
  the difference between replaced, closed, exploratory, and reserved-slot ADRs.
- **Map `exploration` to `proposed`** — rejected because proposed decisions are
  actionable while exploration ADRs deliberately prevent premature execution.
- **Keep nested status maps** — rejected because tooling cannot infer a single
  lifecycle state and agents overclaim mixed records.
