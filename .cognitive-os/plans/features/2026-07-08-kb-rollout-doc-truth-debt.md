---
title: KB Synthesis Rollout — Documentation-Truth Debt
type: chore
status: draft
created: 2026-07-08
author: agent
service: documentation-truth
audience: os
---

<!--
RECONCILIATION STATUS: LIVE
Related ADRs: ADR-277 (documentation-truth-control), ADR-273 (pending-truth-ledger-and-bilateral-verification), ADR-275 (closure-and-projection-primitives)
Reconciled: 2026-07-08
Origin: RULES-COMPACT #16 (session-close-doc-truth discipline). The OKF
knowledge-base synthesis rollout (419 pages, faithful-to-source extraction)
surfaced genuine internal inconsistencies in SOURCE docs while writing
synthesis pages. Per rules/session-close-doc-truth.md, every documentation
contradiction discovered during a session must terminate in a pointwise
fix + documentation-truth claim, OR an explicit debt entry here. This pass
recorded debt only — no source docs were fixed (out of scope for the
synthesis session that found them).
-->

# Plan: KB Synthesis Rollout — Documentation-Truth Debt

> **Date discovered**: 2026-07-08
> **Discovery method**: KB synthesis rollout (419-page OKF concept-synthesis
> wave 1, `docs/04-Concepts/`). Faithful-to-source synthesis requires reading
> the full source doc; contradictions inside a single doc, or between two
> related docs, surfaced naturally during that read.
> **Disposition**: DEBT (option b of `rules/session-close-doc-truth.md`).
> None of these are fixed in this pass — none are `documentation-truth-claims.yaml`
> candidates because we cannot assert a corrected fact without doing the fix
> first (that manifest is for post-verification TRUE claims, not open debt).

## How to close an item here

1. Fix the source doc(s) named in the checkbox.
2. If the fixed fact is a volatile claim (coverage/counts/status per
   `rules/session-close-doc-truth.md` §"What gets added to documentation-truth"),
   add/extend a claim in `manifests/documentation-truth-claims.yaml` in the
   same commit.
3. Check the box `[x]` and append `(verified: path:line)` or run:
   `python3 scripts/cos-pending-truth-close --id <ledger-id> --proof <path:line|commit-sha>`
4. Re-run `python3 scripts/cos-pending-truth-aggregator --write && python3 scripts/cos-pending-truth-verify` to refresh the ledger.

## Debt items

> Note on path formatting: paths below are deliberately written as
> "directory `x/y/` (file `name.md`)" rather than one contiguous
> `x/y/name.md` token. `scripts/cos-pending-truth-verify`'s plan-checkbox
> evidence check treats any contiguous path-with-extension found in the
> checkbox text as an existence claim to verify, and — since these are
> *content* contradictions in files that genuinely exist, not missing
> files — a contiguous path would make the verifier wrongly report
> `verified-done`. Splitting the token keeps the item honestly
> `verified-pending` while still uniquely identifying the file. See
> §Notes below for the full explanation.

- [ ] [DOC-TRUTH-DEBT][high][governance] directory `docs/09-Quality/legal/` (file `pre-public-readiness-checklist.md`): sections C4 and C5 are marked `done` while their own sub-checkboxes remain `[ ]` and the reviewer sign-off table (operator/legal/security/comms) is entirely blank. Found via KB synthesis rollout (2026-07-08); resolution deferred.

- [ ] [DOC-TRUTH-DEBT][high][security-counts] directory `docs/09-Quality/security/` (file `supply-chain.md`): §3.2 summary says REVIEW=15 but §3.4 heading "REVIEW — 14 entries" lists 14 rows; §3.6 "OK — 91 entries" per-license counts sum to 93; two syft vintages (205 vs 186 UNKNOWN components) are cited unreconciled. Found via KB synthesis rollout (2026-07-08); resolution deferred.

- [ ] [DOC-TRUTH-DEBT][high][license-counts] directory `docs/08-References/root/` (file `competitive-analysis.md`): lists license as "Proprietary", contradicting the repo's actual FSL-1.1-MIT posture; also cites 3 different rule counts (92/55/14) across sections, unreconciled. Found via KB synthesis rollout (2026-07-08); resolution deferred.

- [ ] [DOC-TRUTH-DEBT][high][counts] directory `docs/05-Methodology/root/` (files `rules.md` and `rules-consolidation-plan.md`): conflicting current always-loaded rule state (16 core / 150+ total vs 14 core / 73 total) between the two docs. Found via KB synthesis rollout (2026-07-08); resolution deferred.

- [ ] [DOC-TRUTH-DEBT][high][counts] directory `docs/09-Quality/root/` (file `hook-security-profiles.md`): paranoid profile header says "Active hooks: 61" vs comparison matrix total of 62; safety-mesh layer-numbering has a gap (layer 12 missing). Found via KB synthesis rollout (2026-07-08); resolution deferred.

- [ ] [DOC-TRUTH-DEBT][medium][adr-numbering] directory `docs/05-Methodology/root/` (file `executable-acceptance-specification.md`): labels its own ADR as "ADR-317" but cites the filename `ADR-324-executable-acceptance-specification-eas.md` (mismatched ADR number vs cited filename). Found via KB synthesis rollout (2026-07-08); resolution deferred.

- [ ] [DOC-TRUTH-DEBT][high][counts] directory `docs/08-References/business/` (file `case-study.md`): claims "170+ endpoints" with "79+ migrated (31%)" — 79/170 is approximately 46%, not 31%; also claims "47 use-case domains" vs "8+ of 46" elsewhere in the same doc (46 vs 47 mismatch). Found via KB synthesis rollout (2026-07-08); resolution deferred.

- [ ] [DOC-TRUTH-DEBT][medium][stale-duplicate] directory `docs/05-Methodology/runbooks/` (files `history-sanitization.md` and `cos-history-sanitization.md`): same ADR-218 workflow documented with divergent command sets across the two docs; the shorter doc is likely the stale duplicate and should be reconciled or archived. Found via KB synthesis rollout (2026-07-08); resolution deferred.

## Notes

- All 8 items were vetted against source text before being recorded here
  (not auto-flagged); severity and category tags are inline in each
  checkbox for triage.
- None of these block the KB synthesis rollout itself — the synthesis
  pages describe the concepts faithfully and separately note the source
  ambiguity where relevant; this ledger entry is the durable tracking
  artifact per ADR-277.
- Known limitation: `scripts/cos-pending-truth-verify`'s plan-checkbox
  evidence heuristic treats "path mentioned in next_action exists" as
  `verified-done` evidence. Since every item above legitimately names a
  real, existing doc path (that's the whole point — the doc exists and
  is wrong), the bilateral verifier may mis-classify these as
  `verified-done` on a re-run, even though the underlying contradiction
  is unresolved. This is a heuristic mismatch (built for
  code/feature-existence checks, not doc-content contradiction checks),
  not a resolution. Treat `verified-done` status on any `DOC-TRUTH-DEBT`
  item as suspect until a human confirms the source doc was actually
  fixed.
