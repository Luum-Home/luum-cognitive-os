---
type: quality-synthesis
source: docs/09-Quality/legal/m3-adr-sweep-report.md
provenance: "M3 pre-public-readiness checklist item: a read-only manual sweep of the 21 ADRs (ADR-218 through ADR-238) landed in the AI-agent batch over 2026-05-06/07, surfacing inconsistencies before public launch without modifying any ADR."
---

## What it is
A read-only reviewer report (M3 manual-sweep agent, 2026-05-08) auditing 21 ADRs (218-238) for status-header contradictions, broken cross-references, prose drift, and AI-slop patterns ahead of public release. No ADR files were modified by the sweep itself.

## Key mechanics
- Methodology: extract front matter (Status/Date/Related) per ADR; verify every `ADR-NNN` cross-reference resolves (both slugged and bare filename styles); spot-check backticked path references for load-bearing files; scan Status/Decision prose for drift; cross-check date plausibility and bidirectional `Related:` pairing. Implementation/tests were not run — only the ADR documents were inspected.
- One CRITICAL finding (C1): ADR-228 has a self-contradicting status header — `## Status` block literally says `Tombstone` while the body's bolded `**Status**:` line says `Accepted`. ADR-229 (the real tombstone) explains 228 absorbed the cost-budget ADR, so 228 is the live document; the `Tombstone` line is a one-line bug that could mislead automated status scrapers. Remediation: change line 4 of ADR-228 to `Accepted`.
- 4 MEDIUM findings: ADR-220 references `manifests/worktree-audit.yaml` in its path table but the file doesn't exist on disk; ADR-224 (311 words) and ADR-234 (299 words) are the most templated/thin ADRs in the batch; ADR-232 names three sandbox tiers without committing to a default-on/off posture; plus a cross-cutting governance gap — `lib/dispatch.py` is modified by ADRs 226/228/232/236 with no single-owner sequencing contract documented.
- ~16 LOW findings: mostly bare-filename vs. path-prefixed references used interchangeably (stylistic drift, not broken links), missing "Source" footers, thin Consequences sections.
- Severity/cleanliness tally: 15 ADRs clean (only stylistic LOW notes), 4 with MEDIUM doc-only issues (220/224/232/234), 0 major, 1 blocker (228). Total reviewed: 21 (218-238 inclusive, incl. tombstone 229).
- AI-slop check: found templated boilerplate in 224/234, un-owned future-tense language absent elsewhere, ADR-232 as the closest thing to a "decision that doesn't decide," and confirmed ADR-228's dual-gap consolidation is a documented merge, not scope creep.
- Recommendations: MUST-FIX = one-line ADR-228 status correction (blocks public release); SHOULD-FIX = ship or delete the ADR-220 manifest reference, expand/merge ADR-224, commit ADR-232/234 to concrete defaults; NICE-TO-HAVE = a sequencing note for `lib/dispatch.py` ownership across the four touching ADRs.

## Relations & where used
Directly consumed by `docs/09-Quality/legal/pre-public-readiness-checklist.md` §M3 ("ADR sweep — 14 recent ADRs"), which cites this report as evidence that the ADR-228 fix and the 4 MEDIUM follow-ups were closed, and cross-references `docs/09-Quality/legal/h3-unknown-license-resolution.md`, ADR-067 (template policy), and the ADR pairs discussed (226↔227/228/230/233, 223↔224/227).

## Status / caveats
Dated, point-in-time audit (2026-05-08) tied to one specific ADR batch snapshot — the checklist that consumes it reports all findings as since resolved, but this source document itself is frozen as an "as-observed" report and was not updated. Note the report's own cleanliness-summary table contains a visible self-correcting arithmetic aside ("that's 15... Recounting... = 15") — flagged here as a minor internal inconsistency in the source rather than fixed.
