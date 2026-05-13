---
adr: 289
title: 'Three-Layer Knowledge Architecture: Raw Sources, Compiled Vault, Operational Engram'
status: accepted
implementation_status: partial
classification_basis: 'Layer 2 (vault) and Layer 3 (engram) are implemented; Layer 1 (raw sources) canonical location and ingest pipeline are not yet formalized.'
date: '2026-05-13'
supersedes: []
superseded_by: null
extends: [ADR-284, ADR-287, ADR-285, ADR-286, ADR-256]
implementation_files:
  - docs/
  - lib/engram_wave3_schema.py
  - lib/engram_obsidian_exporter.py
  - lib/engram_crystallizer.py
  - lib/engram_bundle_exporter.py
  - manifests/capability-coverage.yaml
tier: maintainer
tags:
  - knowledge-architecture
  - documentation
  - engram
  - vault
  - raw-sources
  - traceability
partial_remaining: |
  Layer 1 (raw sources) has no canonical on-disk location and no ingest
  pipeline from raw to vault; vault->engram retrieve pipeline is also not
  implemented. Both are tracked as known gaps.
partial_remaining_basis: specific classification_basis
---

# ADR-289 — Three-Layer Knowledge Architecture: Raw Sources, Compiled Vault, Operational Engram

## Status

Accepted — 2026-05-13.

<!-- SCOPE: OS -->

**Date:** 2026-05-13
**Owner:** orchestrator
**Tier:** core
**Authors:** orchestrator
**Related:** ADR-284 (doc path audit), ADR-287 (engram v3), ADR-285 (skill registry runtime drift), ADR-286 (stack-aware skill recommendation), ADR-256 (primitive contract registry)

---

## Context

Between 2026-05-11 and 2026-05-12 the project completed two large knowledge-side
migrations in rapid succession:

1. **Compiled documentation vault.** Twenty-plus commits under
   `feat(docs): bridge … vault` consolidated dispersed documentation into a
   numbered PARA + Johnny.Decimal vault at `docs/`
   (`00-MOCs`, `01-Build-Log`, `02-Decisions`, `03-PoCs`, `04-Concepts`,
   `05-Methodology`, `06-Daily`, `07-Capabilities`, `08-References`,
   `09-Quality`, `99-Archive`). ADR-284 added the path-reference audit that
   guarantees there are no dangling references after the legacy bridges were
   removed.
2. **Operational memory layer (engram v3).** ADR-287 shipped evidence-grounded
   claims, a dry-run write gate, BM25 retrieval, and portable bundles on top of
   the existing Wave-2 engram schema. Crystallization
   (`lib/engram_crystallizer.py`), Obsidian export
   (`lib/engram_obsidian_exporter.py`), graph traversal
   (`lib/engram_graph_walker.py`), and lifecycle management
   (`lib/engram_lifecycle.py`) were already in place.

Each layer is solid on its own. The fragmentation risk is **conceptual**: the
project does not yet have a single document that names how these surfaces fit
together. As a result:

- New contributors (human and agent) cannot tell whether a given fact belongs
  in `docs/`, in engram, or only in a transcript.
- Raw inputs (URLs cited in commits, PDFs dropped into the working tree,
  upstream transcripts, third-party code being reverse-engineered) live in
  scattered places. They are referenced by claims (engram `evidence_sources`,
  vault footnotes) but have no canonical home and no integrity guarantees.
- The pipelines that already move information between layers
  (`engram_crystallizer`, `engram_obsidian_exporter`) work, but their roles are
  not described as a system.
- Future automation — for example a `/wiki-ingest` skill that converts a raw
  URL or PDF into a vault page — has no architectural slot to plug into.

This ADR names the architecture so that future surface decisions (raw-sources
location, ingest skill, retrieve pipeline, schema invariants) reference one
shared model rather than re-deriving it.

---

## Decision

Adopt a **three-layer knowledge architecture** as the canonical model for how
durable information lives in this repository. Every knowledge artifact belongs
to exactly one layer.

### Layer 1 — Raw sources (immutable)

Original, unmodified inputs. Treated as ground truth that other layers cite but
never paraphrase.

| Property | Value |
| --- | --- |
| Purpose | Capture inputs verbatim so claims can be re-verified against them. |
| Mutability | Immutable. New revisions are new files with new hashes. |
| Format | Whatever the source is — PDF, HTML snapshot, transcript, image, source-code snapshot. |
| Canonical location | `docs/08-References/raw/<type>/<source-id>.<ext>` (proposed; see "Known gaps"). |
| Integrity | SHA-256 of file bytes. Hash is the source's stable identity. |
| Discovery | Indexed by an `evidence_sources` row (engram) and/or a vault footnote. |
| Owner | The contributor who introduced the source. |

Raw sources are addressed by the same `source_id` schema introduced by ADR-287
(`sha256(type ':' locator)[:16]`). For local files the locator is the
repository-relative path; for URLs it is the canonical URL.

### Layer 2 — Compiled vault (curated markdown)

Human- and agent-readable synthesis of what the project has learned. The
vault is the layer designed for browsing.

| Property | Value |
| --- | --- |
| Purpose | Make knowledge legible: MOCs, concepts, methodology, daily logs, capabilities, decisions. |
| Mutability | Mutable. Pages evolve with the project. |
| Format | Markdown with YAML frontmatter. |
| Canonical location | `docs/{00-MOCs … 99-Archive}` following PARA + Johnny.Decimal. |
| Integrity | Path-reference audit (`scripts/cos-doc-path-audit`, ADR-284). Page-level hashes are optional. |
| Discovery | Vault navigation (MOCs, daily indexes), grep, future retrieval pipeline. |
| Owner | Whoever curates the relevant section. |

Vault pages may cite Layer 1 sources by `source_id` and Layer 3 claims by
observation id. They should not duplicate raw content; they should link.

### Layer 3 — Operational engram (lifecycle-aware claims)

Structured, machine-queried memory. The layer agents use during a task.

| Property | Value |
| --- | --- |
| Purpose | Provide low-latency, evidence-grounded retrieval of claims, decisions, bug fixes, conventions, session summaries. |
| Mutability | Append-mostly. Updates via `mem_update`; supersedes/conflicts via judgment edges. Lifecycle (`engram_lifecycle.py`) handles archival. |
| Format | SQLite-backed observations (Wave-2 + Wave-3 schema). |
| Canonical location | `~/.engram/engram.db` (workstation-local) plus portable bundles (ADR-287). |
| Integrity | Per-claim `evidence_hashes` (ADR-287); per-bundle SHA-256 (ADR-287). |
| Discovery | `mem_search`, BM25 (`engram_fts5_search`), graph walk (`engram_graph_walker`). |
| Owner | The agent or operator who saved the claim. |

Engram is intentionally not the place to store narrative or extended prose —
that belongs in Layer 2. Engram is the place to store *what we decided*, *what
we discovered*, and *what evidence backs it*.

---

## Pipelines

Movement of information between layers is performed by named modules. Pipelines
are unidirectional; each has a single direction of truth.

| Pipeline | Direction | Module / Surface | Status |
| --- | --- | --- | --- |
| `ingest` | Raw (L1) → Vault (L2) | `/wiki-ingest` skill (planned) | planned |
| `crystallize` | Raw / conversations (L1) → Engram (L3) | `lib/engram_crystallizer.py` | active |
| `export` | Engram (L3) → Vault (L2) | `lib/engram_obsidian_exporter.py` | active |
| `reinforce` | Engram (L3) → Engram (L3) | `lib/engram_lifecycle.py` (decay, supersede, archive) | active |
| `bundle` | Engram (L3) → Engram (L3, remote) | `lib/engram_bundle_exporter.py` / `_importer.py` | active |
| `retrieve` | Vault (L2) → Engram (L3) | (planned) vault-to-engram indexer | future |

`ad-hoc save` via `mem_save` is not a pipeline — it is the primary write path
into Layer 3 and is governed by the engram write gate (ADR-287).

---

## Schema invariants (traceability)

Two invariants make the layers mechanically interoperable:

1. **Vault → Engram and Vault → Raw.** A vault page's YAML frontmatter MAY
   carry:

   ```yaml
   sources: [<source_id>, …]        # Layer 1 sources cited by this page
   engram_refs: [<observation_id>, …]   # Layer 3 claims this page summarizes
   ```

   When present, `cos-doc-path-audit` (ADR-284) and a future vault audit verify
   that referenced source IDs and observation IDs resolve.

2. **Engram → Raw and Engram → Vault.** An engram observation's
   `evidence_sources` (ADR-287) MUST resolve to either a Layer 1 source row
   (`evidence_sources` table) or a Layer 2 vault page (locator path under
   `docs/`). Engram-side validators reject claim-bearing types
   (`fact | decision | workflow`) without evidence in strict mode.

The result is bidirectional traceability: starting from a claim an agent can
walk to the page that contextualizes it and to the raw source that justifies
it; starting from a raw source an operator can find every claim and every page
that depends on it.

---

## Why three layers (not two, not four)

| Alternative | Reason rejected |
| --- | --- |
| **Two layers: vault + engram.** | Without a named raw layer there is no canonical home for inputs; evidence hashes silently degrade as files move. |
| **Two layers: raw + engram (no vault).** | Loses the human-browsing surface. Daily logs, MOCs, methodology, and ADRs need long-form prose engram is not designed for. |
| **Four+ layers (e.g. split engram into "working" and "archive").** | Engram already has a lifecycle phase (`engram_lifecycle.py`) that handles archival inside the same store. A separate archive layer adds operational cost without changing semantics. |

---

## Consequences

### Positive

- One named model anchors future surface decisions. New tools (skills,
  pipelines, audits) declare which layer they read and which they write.
- Operators can answer "where does this fact live?" with a one-word answer
  (`raw`, `vault`, `engram`) and follow the pipeline names from there.
- Evidence-grounded claims (ADR-287) gain a documented end-to-end story: the
  evidence in Layer 3 always points at something concrete in Layer 1 or Layer 2.
- Future automation has a slot: the `ingest` pipeline becomes the obvious place
  to wire `/wiki-ingest`; the `retrieve` pipeline becomes the obvious place to
  index vault pages back into engram.

### Negative / accepted

- Adds a vocabulary contributors must learn (`L1/L2/L3`, the six pipeline
  names). Mitigation: this ADR is the single reference and is linked from
  capability coverage.
- The model formalizes a gap: there is no canonical raw-sources directory
  today. Naming the layer makes the gap visible (which is the point) but the
  gap remains until follow-up work lands.

### Risks

- **Drift between layers.** If pipelines run out of band the layers can diverge
  (e.g. engram has a claim citing a vault page that was renamed). Mitigation:
  ADR-284 path audit covers vault references; engram evidence hashes detect
  source drift.
- **Layer confusion.** Contributors might save long prose to engram or
  ephemeral notes to the vault. Mitigation: format constraints in this ADR plus
  validator hints in `engram_write_gate`.
- **Raw-source sprawl before formalization.** Until the canonical raw location
  is established, contributors may continue dropping files ad-hoc. Mitigation:
  capability entry is `PARTIAL` with `known_gaps` so the deficit stays visible
  in the matrix.

---

## Known gaps (tracked, not resolved here)

1. **Layer 1 canonical location not yet on disk.** `docs/08-References/raw/`
   is proposed but not created in this ADR. A follow-up change creates the
   directory, adds a README defining the naming convention
   (`<type>/<source-id>.<ext>`), and migrates any in-tree raw artifacts that
   already exist.
2. **`ingest` pipeline (Raw → Vault) absent.** The `/wiki-ingest` skill that
   converts a raw URL or PDF into a curated vault page is planned in a parallel
   task. Until it lands, raw → vault remains a manual step.
3. **`retrieve` pipeline (Vault → Engram) absent.** Today vault pages are not
   automatically indexed back into engram. A future ADR will decide whether
   this is a periodic indexer or an on-demand resolver.

These gaps are recorded against capability
`knowledge-architecture-3-layer` in `manifests/capability-coverage.yaml`.

---

## Implementation files

- `docs/` — Layer 2 vault (existing).
- `lib/engram_wave3_schema.py` — evidence model used by Layer 3 to cite Layers
  1 and 2.
- `lib/engram_obsidian_exporter.py` — `export` pipeline (L3 → L2).
- `lib/engram_crystallizer.py` — `crystallize` pipeline (L1 → L3).
- `lib/engram_bundle_exporter.py` / `lib/engram_bundle_importer.py` — `bundle`
  pipeline (L3 ↔ L3 across machines).
- `lib/engram_lifecycle.py` — `reinforce` pipeline (L3 → L3 self-update).
- `manifests/capability-coverage.yaml` — capability
  `knowledge-architecture-3-layer` registered against this ADR.

## Verification

This ADR is a model-naming decision; verification is structural rather than
behavioral.

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
python3 -m pytest tests/unit/test_capability_matrix.py -q
scripts/cos-doc-path-audit --json
```

- `python3 -m pytest tests/audit/test_adr_contracts.py -q` — confirms the ADR
  satisfies the post-ADR-067 documentation contract (frontmatter, sections,
  classification basis).
- `python3 -m pytest tests/unit/test_capability_matrix.py -q` — confirms the
  new capability entry is well-formed and resolvable to this ADR.
- `scripts/cos-doc-path-audit --json` — confirms paths referenced from this ADR
  (`docs/08-References/raw/`, the named library modules, the manifest)
  resolve or are explicitly recorded as planned.

## Alternatives rejected

1. **Leave the architecture implicit and rely on contributors to infer it from
   ADR-284 + ADR-287.** Rejected: the inference is non-obvious and each
   contributor has been re-deriving it. Naming the model is the cheap fix.
2. **Treat raw sources as engram-only (no Layer 1 on disk).** Rejected:
   engram is workstation-local; raw inputs that justify cross-machine claims
   need a portable, git-tracked home.
3. **Treat the vault as a projection of engram.** Rejected: most vault pages
   (MOCs, methodology, ADRs themselves) are authored long-form, not
   crystallized from claims. The export pipeline is one-directional and
   partial.
