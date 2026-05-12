# ADR Status Triage — Non-Standard "Other" Section

**Date**: 2026-05-12  
**Scope**: 38 ADRs from the "Other" group in `docs/adrs/INDEX.md`  
**Method**: Python script reads first ~45 lines of each ADR file, extracts status field,
applies deterministic classification rules, flags ambiguous cases.  
**Constraint**: Read-only — no ADR files were modified.

---

## Executive Summary

| Canonical Target | Count | Raw Status Values Mapped |
|-----------------|-------|--------------------------|
| **Active**      | 26    | Implemented (21), Addendum (3), Phase (1), empty/split (1) |
| **Deprecated**  | 11    | Tombstone (9), Resolved (1), Tombstone-via-consolidation (1) |
| **Proposed**    | 1     | Exploration (1) |
| **Superseded**  | 0     | — |
| **Total**       | 38    | |

No ADRs in the "Other" set warrant the `Superseded` canonical status — those are already
correctly categorized in the existing Superseded section.

---

## Classification by Canonical Target

### → Active (26 ADRs)

These ADRs represent living decisions. "Implemented" is a delivery sub-state, not a lifecycle
termination. "Addendum" patches a living parent ADR and is itself active. The single "Phase"
ADR has partially-resolved phases but remains the authoritative decision document.

| ADR-ID | Raw Status | File Status (extracted) | Justification |
|--------|-----------|------------------------|---------------|
| ADR-027a | Addendum | `Addendum to ADR-027` | Amendment to active ADR-027; itself an active patch document |
| ADR-028a | Addendum | `Addendum to ADR-028` | Amendment to active ADR-028; reconciliation document |
| ADR-028b | Addendum | `Addendum to ADR-028` | Amendment to active ADR-028; D1.C replanning |
| ADR-044  | Phase    | `Phase 2 RESOLVED …`  | Active decision with phased implementation; some phases blocked, not tombstoned |
| ADR-052  | Implemented | `implemented` | Provider Benchmark Harness — fully delivered, decision stands |
| ADR-053  | Implemented | `implemented` | Dispatch Auto-Optimizer — fully delivered, decision stands |
| ADR-105  | Implemented | `implemented` | Bilateral Claim Verification Contract — delivered |
| ADR-119  | Implemented | `implemented` | Session Filesystem Reaper — delivered |
| ADR-123  | Implemented | `implemented` | Operational Stability and Friction Reduction Program — delivered |
| ADR-139  | Implemented | `implemented` | Account-Agnostic Multi-Provider Runtime — delivered |
| ADR-141  | Implemented | `implemented` | Engram Cloud as Cross-Instance Replication Transport — delivered |
| ADR-142  | Implemented | `implemented` | Compliance, Audit, and Air-Gapped Surface — delivered |
| ADR-151  | Implemented | `implemented` | Consumer Availability Classification Manifest — delivered |
| ADR-152  | Implemented | `implemented` | Shell CI Projection and Local Surface Defaults — delivered |
| ADR-154  | Implemented | `implemented` | Multi-IDE Structural Harness Projection — delivered |
| ADR-156  | Implemented | `implemented` | Qwen Code Structural Harness Projection — delivered |
| ADR-157  | Implemented | `implemented` | Kimi Code CLI Structural Harness Projection — delivered |
| ADR-160  | Implemented | `implemented` | Rules/MCP Structural Harness Batch and Kiro Adapter Design — delivered |
| ADR-161  | Implemented | `implemented` | Remote Control Plane and Provider Adapter Boundary — delivered |
| ADR-162  | Implemented | `implemented` | Task Lifecycle, Interruption, Question, Worktree, PR Protocol — delivered |
| ADR-164  | Implemented | `implemented` | Host CLI Bridge Security Boundary — delivered |
| ADR-165  | Implemented | `implemented` | Proof Drill and Smoke Opt-In Primitives — delivered |
| ADR-166  | Implemented | `implemented` | Expected Skip Registry and Opt-In Test Lanes — delivered |
| ADR-167  | Implemented | `implemented` | Proof Drill Selector and ACC Evidence Adapter — delivered |
| ADR-168  | Implemented | `implemented` | Cross-Device Dependency Installation Contract — delivered |
| ADR-174b | *(empty / split)* | `part_a: accepted / part_b: proposed` | Active extension of ADR-174; YAML has composite status, not a lifecycle marker |

**Bulk `sed` command (Active group)**:
```bash
# Files with "Implemented" → "Active"
for f in ADR-052 ADR-053 ADR-105 ADR-119 ADR-123 ADR-139 ADR-141 ADR-142 \
          ADR-151 ADR-152 ADR-154 ADR-156 ADR-157 ADR-160 ADR-161 ADR-162 \
          ADR-164 ADR-165 ADR-166 ADR-167 ADR-168; do
  # find the actual filename (prefix match), then sed
  find docs/adrs -name "ADR-${f#ADR-}*.md" | xargs -I{} sed -i '' 's/^status: implemented/status: Active/' {}
done

# Files with "Addendum" → "Active"
for f in ADR-027a ADR-028a ADR-028b; do
  find docs/adrs -name "ADR-${f#ADR-}*.md" | xargs -I{} sed -i '' 's/^status: Addendum.*/status: Active/' {}
done

# ADR-044: Phase → Active
sed -i '' 's/\*\*Status\*\*: Phase .*/\*\*Status\*\*: Active/' docs/adrs/ADR-044-context-payload-slimming.md

# ADR-174b: composite YAML → normalize
# See "Ambiguous" section — operator judgment needed before touching
```

---

### → Deprecated (11 ADRs)

"Tombstone" files represent slots that were vacated, never filled, or explicitly consolidated
into another ADR. They have no living decision content. "Resolved" (ADR-238) was a temporary
bug-tracking record — all bugs fixed, record closed.

| ADR-ID | Raw Status | File Status (extracted) | Justification |
|--------|-----------|------------------------|---------------|
| ADR-003 | Tombstone | `tombstone` | Reserved slot — never filled |
| ADR-004 | Tombstone | `tombstone` | Reserved slot — never filled |
| ADR-005 | Tombstone | `tombstone` | Reserved slot — never filled |
| ADR-043 | Tombstone | `tombstone` | Local-daemon integration decision removed |
| ADR-046 | Tombstone | `tombstone` | Reserved slot — never filled |
| ADR-085 | Tombstone | `tombstone` | Reserved slot — never filled (numbering race) |
| ADR-214 | Tombstone | `tombstone` | Vacated by parallel-session number collision |
| ADR-224 | Tombstone | `tombstone` | Consolidated into ADR-227 |
| ADR-229 | Tombstone | `tombstone` | Consolidated into ADR-228 |
| ADR-253 | Tombstone | `tombstone` | Squads orchestration superseded by ADR-251 |
| ADR-238 | Resolved  | `Resolved`  | Bug-tracking addendum — all 5 bugs fixed 2026-05-08; no further action |

> **Note on "Tombstone" → "Deprecated" mapping**: The canonical set has no "Tombstone" value.
> These slots carry no architectural decision — they are decommissioned records.
> "Deprecated" is the closest standard value. Alternatively, see §Extended Canonical Set below.

**Bulk `sed` command (Deprecated group)**:
```bash
for num in 003 004 005 043 046 085 214 229 253; do
  find docs/adrs -name "ADR-${num}*.md" | xargs -I{} sed -i '' 's/^status: tombstone/status: Deprecated/' {}
done
# ADR-224
sed -i '' 's/status: tombstone/status: Deprecated/' docs/adrs/ADR-224-shadow-state-snapshots-off-repo.md
# ADR-238
sed -i '' 's/^## Status/## Status (normalized)/' docs/adrs/ADR-238-tier-1-4-followup-bug-tracking.md
# then manually set status: Deprecated in frontmatter or heading
```

---

### → Proposed (1 ADR)

| ADR-ID | Raw Status | File Status (extracted) | Justification |
|--------|-----------|------------------------|---------------|
| ADR-132 | Exploration | `exploration` | Open investigation — no decision committed; file explicitly says "does not commit to an architectural change" |

**Edit**:
```bash
sed -i '' 's/^status: exploration/status: Proposed/' \
  docs/adrs/ADR-132-solo-swarm-vs-multi-maintainer-fork.md
```

---

### → Superseded (0 ADRs)

None of the 38 "Other" ADRs warrant "Superseded". Tombstoned-by-consolidation entries
(ADR-224, ADR-229, ADR-253) could be argued as "superseded" by their target ADRs, but
"Deprecated" is the convention used throughout — they have no living decision body to carry
forward in superseded form.

---

## Ambiguous Cases Requiring Operator Judgment

These 5 entries need a human call before bulk editing.

### 1. ADR-044 — Context Payload Slimming (raw: `Phase`)
**Ambiguity**: The status string "Phase 2 RESOLVED … Phase 2 slash commands BLOCKED" is
actually an implementation progress note, not a lifecycle status. Phase 1 completed, Phase 2
blocked indefinitely.  
**Recommended**: `Active` (the decision is still the authoritative policy; blocked phase ≠ deprecated decision).  
**Alternative**: If Phase 2 is never going to ship, the operator may want `Deprecated`.  
**Action needed**: Confirm whether the blocked Phase 2 is permanently abandoned.

### 2. ADR-132 — Solo-Swarm vs Multi-Maintainer Fork (raw: `Exploration`)
**Ambiguity**: File says "exploration — does not commit to an architectural change." This is
essentially a Proposed investigation that has no decision yet.  
**Recommended**: `Proposed` (closest standard; it's an open question, not an accepted decision).  
**Alternative**: Keep as custom "Exploration" if the team wants to distinguish "exploring
a question" from "proposed a solution" — see §Extended Canonical Set.  
**Action needed**: Decide if `Proposed` vs a custom `Exploration` status is preferred.

### 3. ADR-174b — Routing-Pattern Prevention Followup (raw: empty / composite YAML)
**Ambiguity**: YAML `status` is a sub-object with `part_a: accepted` and `part_b: proposed`.
This is a composite status not representable as a single canonical value.  
**Recommended**: `Active` (Part A accepted and implemented; Part B in-flight under the same ADR).  
**Alternative**: Split into two separate ADRs if Part A/B have divergent lifecycles.  
**Action needed**: Decide whether to merge to `Active` or split.

### 4. ADR-238 — Tier 1-4 Follow-Up Bug Tracking (raw: `Resolved`)
**Ambiguity**: "Resolved" is not in the canonical set, but it clearly means the record is
closed — all 5 bugs fixed. Could map to `Active` (it's a record of work done) or `Deprecated`
(it's a closed tracking ticket with no ongoing relevance).  
**Recommended**: `Deprecated` (no actionable content remains; it is a closed postmortem artifact).  
**Alternative**: `Active` if the team wants all "decision records" to stay Active regardless
of completion.  
**Action needed**: Policy call — do closed tracking ADRs become Deprecated or stay Active?

### 5. ADR-253 — Tombstone (consolidated into ADR-251)
**Ambiguity**: The consolidation target ADR-251 is Active. Technically this is "superseded
by" ADR-251, not deprecated.  
**Recommended**: `Deprecated` (current project convention for consolidated tombstones is Deprecated).  
**Alternative**: `Superseded` with a `superseded_by: 251` annotation — more precise but breaks
uniformity with the other tombstone entries.  
**Action needed**: Decide whether consolidated tombstones are `Deprecated` or `Superseded`.

---

## Non-Standard Status String Inventory

The 6 distinct raw status values found in the "Other" section and their proposed fate:

| Raw Status | Count | Recommended Canonical | Disposition |
|-----------|-------|----------------------|-------------|
| `Tombstone` | 9 | `Deprecated` | Map to Deprecated (unanimous) |
| `Implemented` | 21 | `Active` | Map to Active (Implemented = Active+delivered) |
| `Addendum` | 3 | `Active` | Map to Active (amendment document, not a lifecycle state) |
| `Phase` | 1 | `Active` | Map to Active (implementation progress note, not lifecycle) |
| `Exploration` | 1 | `Proposed` | Map to Proposed (open investigation) |
| `Resolved` | 1 | `Deprecated` | Map to Deprecated (closed tracking record) |
| *(empty/composite)* | 1 | `Active` | Normalize to Active after operator review |
| **Total** | **37** | | (38th entry has empty status) |

---

## Option: Extend the Canonical Set

If the team wants finer granularity, two extensions are defensible:

| Proposed Extension | Maps From | Rationale | Verdict |
|-------------------|-----------|-----------|---------|
| **Implemented** | `Implemented` | Distinguishes "accepted+built" from merely "accepted+documented". Useful for dashboard filtering. | **Optional** — only adds value if tooling consumes it. Without tooling, adds noise. |
| **Exploration** | `Exploration` | Distinguishes "we're investigating a question" (ADR-132) from "we've proposed an answer" (Proposed). Hermes-style ADR workflows use this distinction. | **Optional** — useful if research-gate ADRs become a regular pattern (see ADR-069). |

**Recommendation**: Do NOT extend the canonical set in this pass. The overhead of maintaining
5+ status values outweighs the benefit. `Implemented → Active` and `Exploration → Proposed`
are clean mappings. If the team later wants the distinction, revisit via a dedicated ADR
(extend ADR-148 or create ADR-27x).

---

## Normalization Execution Plan

**Order of operations** (safest path):

1. **Non-ambiguous Tombstones → Deprecated** (9 files): pure `sed` on `status: tombstone`
2. **Non-ambiguous Implemented → Active** (21 files): pure `sed` on `status: implemented`
3. **Addenda → Active** (3 files): `sed` on `status: Addendum.*`
4. **ADR-132 Exploration → Proposed**: 1 file, 1 line
5. **ADR-238 Resolved → Deprecated**: 1 file, operator confirms first
6. **ADR-044 Phase → Active**: 1 file, operator confirms Phase 2 fate
7. **ADR-174b composite → Active**: 1 file, flatten composite YAML, operator confirms
8. **ADR-253 Tombstone (ambiguous consolidated)**: already covered in step 1, but operator
   may want `Superseded` instead

After edits: re-run `docs/adrs/INDEX.md` generator (if one exists) to refresh the index.
If no generator, manually move rows from "Other" to appropriate sections.

---

## Files Referenced

- Source index: `docs/adrs/INDEX.md`
- ADR files: `docs/adrs/ADR-{NNN}*.md`
- This report: `docs/reports/adr-status-triage-2026-05-12.md`
- Triage script (temp): `/tmp/adr_triage.py`
