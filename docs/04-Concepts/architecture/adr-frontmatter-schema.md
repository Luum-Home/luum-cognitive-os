# ADR Frontmatter Schema

Machine-parseable YAML frontmatter for Architecture Decision Records.

## Purpose

ADRs have historically used free-form prose for status and metadata. This schema
adds a structured YAML block at the top of each ADR so that tooling can:

- Report overall ADR health without parsing prose
- Verify that `status: implemented` ADRs have their claimed files on disk
- Detect superseded/deprecated records automatically
- Drive CI gates and dashboards from a single source of truth

The schema is **additive**: existing prose (`**Status**: ...`, `## Status`, etc.)
is preserved for human readability. The frontmatter block lives at the top and
is the authoritative machine-readable source.

## Full Schema

```yaml
---
adr: 116
title: Multi-Session Coordination Primitives
status: implemented   # see Status Values below
date: 2026-05-02
supersedes: []         # optional list of ADR numbers this ADR supersedes
superseded_by: null    # optional single ADR number that supersedes this one
implementation_files:  # files whose existence on disk is required for status: implemented
  - lib/task_claim_ledger.py
  - hooks/agent-prelaunch.sh
tier: standard         # see Tier Values below
tags: [coordination, multi-session]
---
```

## Field Reference

### `adr` (integer, required)
The canonical ADR number. Must match the number in the filename
(`ADR-{adr}-*.md`).

### `title` (string, required)
Human-readable title. Should match the first `#` heading in the document.

### `status` (string, required)
See Status Values below.

### `date` (string, required)
ISO-8601 date (`YYYY-MM-DD`). Date the ADR was accepted or last materially
revised.

### `supersedes` (list of integers, optional)
ADR numbers that this ADR supersedes. The referenced ADRs should carry
`superseded_by` pointing back to this number.

Default: `[]`

### `superseded_by` (integer or null, optional)
ADR number that supersedes this record. Mutually exclusive with
`status: implemented`.

Default: `null`

### `implementation_files` (list of strings, optional)
Paths relative to the repository root. The audit script resolves each path
via `Path.resolve()` (symlink-aware) and verifies existence when
`status: implemented`.

An ADR with `status: implemented` and an empty or absent `implementation_files`
list is treated as **self-certifying** — the audit reports it as `OK` but
notes that no files were verified.

Default: `[]`

### `tier` (string, optional)
Integration tier from the adoption-tiers system.

Default: `standard`

### `tags` (list of strings, optional)
Free-form tags for grouping and search.

Default: `[]`

## Status Values

| Value | Meaning |
|---|---|
| `proposed` | Draft, not yet accepted. |
| `accepted` | Accepted by the operator; may or may not be fully implemented. |
| `implemented` | All `implementation_files` exist and the design is live. |
| `superseded` | Replaced by another ADR (`superseded_by` must be set). |
| `deprecated` | Retired without a direct replacement. |

The audit script treats `proposed` and `accepted` as informational. It only
validates `implementation_files` presence for `status: implemented`. A
`STATUS_REALITY_MISMATCH` finding is raised when an `implemented` ADR has
one or more missing `implementation_files`.

## Tier Values

| Value | Meaning |
|---|---|
| `lean` | Minimal safety layer — small projects. |
| `standard` | Default for most ADRs. |
| `strict` | Full governance, audit trails, chaos tests required. |
| `meta` | ADR about the ADR system itself. |

## Placement Rules

1. The `---` delimiters must appear at the **very top** of the file (line 1 and
   the closing `---` before the first blank line or heading).
2. Do not modify existing prose content below the frontmatter block.
3. If the ADR already has a `**Status**: ...` line, leave it in place —
   frontmatter is the machine source, prose is the human source.

## Examples

### Minimal (proposed)

```yaml
---
adr: 130
title: New Routing Strategy
status: proposed
date: 2026-05-15
tier: standard
tags: [routing]
---
```

### Fully implemented with files

```yaml
---
adr: 105
title: Bilateral Claim Verification Contract
status: implemented
date: 2026-05-02
supersedes: []
superseded_by: null
implementation_files:
  - hooks/claim-validator.sh
  - hooks/plan-claim-validator.sh
  - hooks/orchestrator-claim-gate.sh
  - scripts/verify_plan_claims.py
  - scripts/verify-archived.sh
  - scripts/orchestrator_claim_gate.py
  - lib/orchestrator_verify.py
tier: strict
tags: [verification, claims, orchestrator]
---
```

### Superseded

```yaml
---
adr: 88
title: Provenance Markers (legacy)
status: superseded
date: 2025-11-10
superseded_by: 105
tier: standard
tags: [provenance]
---
```

## Audit Tool

`scripts/audit_adrs.py` validates frontmatter across all ADRs.

```
python3 scripts/audit_adrs.py --strict
python3 scripts/audit_adrs.py --json
python3 scripts/audit_adrs.py --migrate-from-prose  # dry-run suggestion mode
```

See `scripts/audit_adrs.py --help` for full CLI reference.

## Migration Approach

Frontmatter is being added incrementally. The five highest-citation ADRs
(105, 116, 119, 121, 123) serve as the proof-of-concept. A bulk sweep of all
remaining ADRs is tracked separately and is out of scope for this initial
implementation.

ADRs without frontmatter produce `MISSING_FRONTMATTER` warnings (not failures)
in the audit output. Only `MALFORMED_YAML` and `STATUS_REALITY_MISMATCH` are
hard failures in `--strict` mode.
