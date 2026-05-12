---
adr: 259
title: 'holaOS Adoption Posture: Patterns-Only Library with Clean-Room Rewrite'
status: accepted
implementation_status: partial
date: '2026-05-11'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit partial/phase scope
partial_remaining: documentation text) is categorically blocked. A formal clean-room process
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-259 — holaOS Adoption Posture: Patterns-Only Library with Clean-Room Rewrite

## Status

Accepted

**Date:** 2026-05-11
**Owner:** platform-safety
**Tier:** core
**Authors:** orchestrator (Claude Opus 4.7)
**Supersedes:** none
**Related:** ADR-006 (AGPL License Compliance), ADR-007 (rebrand), ADR-255 (Feature to External Tool Due Diligence)

---

## Context

On 2026-05-10 a systematic external due-diligence sweep included a deep
comparison of luum-agent-os against holaOS (Holaboss AI, 2026), documented in
[private clean-room research dossier]. holaOS is an agent-computer
platform — an Electron + TypeScript runtime (Fastify, SQLite) in which humans
and agents share a persistent, inspectable workspace. It solves a number of
problems luum-agent-os has partially addressed: session-level memory governance,
tool-replay budgeting, skill auto-evolution, context-reserve compaction, HMAC
grants, and proactive context bootstrapping.

Annex E of that research ([private clean-room research dossier])
assessed holaOS as high-value for pattern adoption and simultaneously identified
a blocking license constraint. holaOS is published under Apache 2.0 **modified
with BSL-like clauses**: section 1.a prohibits using holaOS source code to
provide a hosted service to third parties or to embed it in a commercially
distributed product; section 2.a reserves to Holaboss the right to tighten
those terms unilaterally at any time. Under the project's `[license-policy]`
rule (§10, `rules/RULES-COMPACT.md`), BSL-like licenses are classified as
BLOCK for code adoption.

Annex F (private clean-room compliance dossier — internal records) established
the operational posture and the clean-room protocol. The conclusion: holaOS
ideas, algorithms, state machines, taxonomies, and policies are freely adoptable
under 17 USC §102(b) — copyright does not protect ideas, procedures, or
processes. The expression (source code, identifiers, comments, fixtures,
documentation text) is categorically blocked. A formal clean-room process
modelled on the Compaq/IBM BIOS precedent (*Phoenix Technologies v. NEC*, 1984)
makes re-implementation legally defensible.

Without a project-level ADR, individual adoption attempts risk inconsistent
process, gaps in audit trail, and exposure in future commercial or SaaS
scenarios. This ADR canonizes the posture established in Annex F as a binding
architectural decision.

---

## Decision

### 1. patterns-only library designation

luum-agent-os treats holaOS as a **patterns-only reference library**. Adoption
of ideas, algorithms, policies, state machines, taxonomies, and observable
behaviors is permitted without restriction. Direct or substantially similar
copying of holaOS source code, identifiers, comments, fixtures, documentation
text, or directory structure is **categorically blocked** under the Annex F §2
Level 3 table, regardless of distribution context. The operative legal basis is
17 USC §102(b): copyright protection does not extend to any idea, procedure,
process, system, method of operation, concept, principle, or discovery.

### 2. mandatory clean-room rewrite protocol

Every adoption of a holaOS pattern requires a clean-room rewrite following the
three-role separation defined in Annex F §4:

- **Research agent** (completed during the 2026-05-10 investigation): reads
  holaOS source and produces purely abstract specification documents (Annexes
  A–F). Outputs contain no identifiers, code fragments, or structural replicas
  from the original. May read `/tmp/holaOS*` paths.
- **Implementer agent**: receives only the abstract spec (one of Annexes A–F or
  a supplementary spec produced by a new research agent). Has a categorical
  prohibition against reading any path matching `/tmp/holaOS*` or any direct
  holaOS source mirror. Writes the implementation from scratch guided solely by
  the spec. If an implementer agent's prompt contains holaOS paths or literal
  source fragments, the agent MUST stop immediately and emit:
  `NEEDS_CLARIFICATION: prompt contains holaOS source references; resend with
  only the abstract spec (Annexes A–F).`
- **Reviewer agent or human**: may read both worlds (spec + implementation +
  original source) solely to verify the absence of literal transcription. The
  reviewer's only permitted output is a verification report, never code.

The orchestrator is responsible for enforcing prompt isolation: no implementer
prompt may carry content originating from holaOS source paths.

### 3. per-adoption ADR requirements

Each ADR that adopts a holaOS pattern (ADR-260, ADR-261, …) must:

(a) Reference this ADR-259 in its **Related** field.
(b) Cite the specific Annex and section that is the pattern source (e.g.,
    `AnnexB::§3.2`).
(c) Include a `pattern_source` frontmatter field using the schema from
    Annex F §4.2:
    ```yaml
    pattern_source: "holaos-comparison-2026-05-10::Annex<X>::<section>"
    holaos_files_read_by_research: []
    holaos_files_blocked_for_impl: ["ALL"]
    ```
(d) Certify clean-room compliance using the checklist in Annex F §5 — all
    twelve items must be marked and results recorded.
(e) Use the commit message template from Annex F §6 for every commit that lands
    adoption code:
    ```
    <scope>: <change>

    Pattern adopted from holaOS (clean-room rewrite).
    Refs: [private clean-room research dossier]
    Source-pattern: <annex>::<section>
    License: Apache-2.0 modified (BSL-like). No source code copied.
    ```

### 4. implementer agent categorical prohibition

Implementer agents operating under any adoption ADR derived from this one have
a standing prohibition on reading any file path that matches `/tmp/holaOS*`,
`/tmp/hola*`, or any directory identified as a mirror of holaOS source. This
prohibition is not waivable by the orchestrator, the user, or any other agent.
The prohibition extends to receiving holaOS code fragments embedded in prompts,
tool outputs, or context injections. Detection of any such fragment requires
immediate execution halt and `NEEDS_CLARIFICATION:` emission before any other
action.

### 5. mandatory audit trail per adoption

Every verified adoption must produce three artifacts:

(i) **Engram observation** with `topic_key: compliance/holaos-adoption/<feature>`,
    `type: policy`, `scope: project`, and the fields specified in Annex F §7.1
    (What, Why, Where, Annex reference, Grep result, Date, Implementer agent ID,
    Reviewer ID). Created via `mem_save` immediately after a verified commit,
    before session close.

(ii) **Append-only registry entry** in the private holaOS adoptions registry
    (to be created before the first adoption commit — see internal records). The file is evidence of
    due diligence and must never have rows edited or deleted.

(iii) **Pre-commit gate execution** via `hooks/external-pattern-cleanroom-gate.sh` (to be
    implemented per §8 of the Implementation Plan in this ADR). The hook scans
    staged diffs for literal tokens matching holaOS source and blocks commits on
    any match. Executions are logged to `.cognitive-os/audit/external-pattern-cleanroom-gate.jsonl`.

---

## Consequences

### Positive

- **Roadmap acceleration**: the holaOS research surface (Annexes A–E) represents
  pre-digested, abstractly specified patterns for problems — memory governance,
  cost budgeting, skill evolution, security hardening — that luum-agent-os is
  actively solving. Clean-room adoption makes that acceleration available without
  license exposure.
- **Legal defensibility**: the three-role separation, append-only registry,
  Engram audit trail, and per-commit checklist create a documented chain of
  evidence that clean-room process was followed — replicating the legal posture
  that prevailed in *Phoenix Technologies v. NEC*.
- **Traceability**: each adoption ADR is self-contained and cites its annex
  source, making future audits or re-evaluations straightforward.
- **Scope boundary**: the patterns-only designation creates a clear, enforceable
  bright line that prevents scope creep toward code copying over time.

### Negative

- **Governance overhead**: every adoption requires a research spec, an implementer
  pass, a reviewer verification, an Engram observation, a registry entry, and a
  gate-passing commit. This is materially slower than copy-paste.
- **No rapid hotfixes from holaOS**: if holaOS fixes a bug in a pattern luum has
  adopted, luum cannot cherry-pick the fix; it must derive a new spec and
  re-implement.
- **Naming and structure re-derivation**: identifiers, module names, and directory
  structure must be independently chosen. This imposes cognitive overhead on
  contributors who have read holaOS source.
- **Dependency on research annexes**: if a new adoption target has no annex, a
  new research-agent pass is required before implementation can begin.

### Mitigations

- The per-adoption ADR template (`docs/adrs/templates/adoption-from-holaos.template.md`,
  to be created) pre-populates checklist, frontmatter schema, and commit message
  template, reducing the governance friction to filling in blanks.
- `hooks/external-pattern-cleanroom-gate.sh` automates the most error-prone checklist item
  (grep verification), making compliance low-effort once the hook is installed.
- This ADR-259 is cited by reference in all derived ADRs; the rationale does not
  need to be re-litigated in each one.

---

## Implementation Plan

The following artifacts are required before the first adoption ADR (ADR-260+)
can be filed. They are design-level work items; no implementation is performed
in this ADR.

1. **Create the private holaOS adoptions registry** (internal records): append-only registry with
   the table schema from Annex F §7.2. Schema columns: Feature, Fecha, ADR ref,
   Implementer agent ID, Grep verify, Status. The file must exist and carry the
   table header before any adoption commit lands.

2. **Design and implement `hooks/external-pattern-cleanroom-gate.sh`**: behavior as
   specified in Annex F §7.3 — staged diff scanning, generic-token exclusion
   list, JSONL audit log, graceful pass when `/tmp/holaOS-investigation` is
   absent (CI-clean environment). Register in `scripts/apply-efficiency-profile.sh`
   under profiles `standard` and `paranoid`; omit from `minimal`. Add to
   `.claude/settings.json` under `hooks.PreToolUse`.

3. **Create `docs/adrs/templates/adoption-from-holaos.template.md`**: a
   pre-filled ADR template that includes the required frontmatter fields, the
   Annex F §5 checklist in copy-ready form, the §6 commit message template, and
   the three mandatory audit-trail items listed in Decision §5.

4. **File ADR-260, ADR-261, … as needed**: each adoption ADR references this
   ADR-259 and targets one or more Annexes. Assignments are tracked in
   the private holaOS adoptions registry (internal records).

---

## Alternatives Considered

| Alternative | Rationale for rejection |
|---|---|
| **Alt 1 — Unconstrained adoption without compliance process** | High legal exposure if luum-agent-os is ever distributed as SaaS or embedded in a commercial product. Section 1.a of the holaOS LICENSE would be triggered if any copied source code were discovered. Rejected unconditionally. |
| **Alt 2 — Zero adoption (ignore holaOS entirely)** | Discards documented, concrete value: the research identified at least ten patterns (Annex F §2 table) that are directly applicable to luum roadmap items. Rejecting all of them to avoid governance overhead is disproportionate. Rejected. |
| **Alt 3 — Negotiate a commercial license with Holaboss** | Potentially viable if luum moves toward SaaS distribution. Does not address the current need and introduces a third-party dependency on negotiation timeline. Deferred to parking lot; does not block this ADR. |
| **Alt 4 — Re-license luum-agent-os toward a commercial model** | Separate concern that does not resolve the holaOS constraint: luum holding a commercial license does not grant rights to copy holaOS source. Rejected as outside scope. |

---

## Open Questions

1. **Jurisdictional applicability of section 1.a**: The clean-room analysis
   (Annex F §10, item 2) notes that section 1.a conditions the SaaS restriction
   on "use the holaOS source code," which grammatically limits it to actual source
   copying rather than functional equivalence. However, this reading has not been
   tested in any published case involving this specific Holaboss license text.
   European jurisdictions (EU Directive 2009/24/EC) and the UK (CDPA 1988) have
   interoperability provisions that may interact differently with BSL-like clauses
   than 17 USC §102(b). The governing jurisdiction for any future commercial
   dispute is not specified in the LICENSE. **Requires legal review before any
   SaaS or commercial-embed distribution decision.**

2. **Retroactive exposure under section 2.a**: Holaboss reserves the right to
   tighten license terms unilaterally (section 2.a). General contract doctrine
   suggests the terms at the moment of action govern, which would mean clean-room
   adoptions documented under the current (2026-05-11) LICENSE are not
   retroactively affected by future tightening. However, this position is not
   validated by case law for this specific license construct, and the boundary
   between "original clean-room work" and "work substantially derived from a
   holaOS pattern" could be contested if Holaboss argues functional similarity.
   **The risk surface grows if the functional overlap between luum-agent-os and
   holaOS increases over time. Monitor for LICENSE updates from Holaboss.**

---

## References

- [private clean-room research dossier] — master research document;
  primary source for the architectural comparison and license classification
- [private compliance dossier — see internal records] — operational clean-room
  protocol; primary source for the decision constraints codified here
- `rules/RULES-COMPACT.md` §10 `[license-policy]` — project rule that classifies
  BSL-like licenses as BLOCK for code adoption
- ADR-006 — AGPL License Compliance (established the project's general
  compliance stance)
- ADR-007 — Rebrand (license identity precedent)
- ADR-255 — Feature to External Tool Due Diligence (the due-diligence sweep that
  surfaced holaOS)
- 17 USC §102(b) — statutory basis for the idea/expression dichotomy underlying
  the patterns-only posture
- *Phoenix Technologies v. NEC* (1984) — clean-room precedent for BIOS
  re-implementation; establishes that two-actor role separation produces
  non-infringing original work
- EU Directive 2009/24/EC — software protection regime relevant for European
  distribution scenarios

---
*This ADR references a private clean-room research dossier whose specific
file paths and section headings are intentionally redacted from this public
record per ADR-267 §Layer 4 and the privatize-research migration (commit e961fd3b).*
