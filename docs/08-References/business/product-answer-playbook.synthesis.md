---
type: reference-synthesis
source: docs/08-References/business/product-answer-playbook.md
provenance: "Defines the operational discipline for answering product/commercial questions about Cognitive OS with the same evidence-and-maturity standard applied to runtime agent work, via the ADR-280 product-answer primitive."
---

## What it is

An operational playbook for generating and publishing product/commercial
answers (positioning, ICP, pitch, wedge, claims) through a scripted,
evidence-linked pipeline rather than ad hoc copywriting, anchored on
`scripts/cos-product-answer` and two governing manifests.

## Key mechanics

- **North star statement**: "Cognitive OS is the behavioral governance and
  evidence layer for agentic development. It makes fast but opaque coding
  agents prove work, coordinate safely, expose cost/risk, and leave
  replayable receipts across supported tools." Short pitch: "AI agents ship
  faster. Cognitive OS makes them prove it." (Spanish variant included.)
- **Canonical command**: `scripts/cos-product-answer "<question>" --json` or
  `--question-id <id> --format markdown`, driven by
  `manifests/product-question-bank.yaml`.
- **Answer discipline** (6 rules): start from the question bank; join every
  answer to `manifests/product-claim-evidence.yaml`; treat `blocked` claims
  as non-publishable; treat `aspirational` claims as roadmap/gaps, never
  shipped behavior; flag uncertainty on competitive/market claims that may
  have gone stale; treat private strategy docs as evidence context only,
  never public copy verbatim.
- **Manual pre-publish check**: run `scripts/cos-product-answer
  --question-id differentiator --json` and
  `scripts/cos-public-claim-gate --json` before using an answer externally;
  refresh external research before any named-competitor comparison.
- **Maintainer update flow**: when evidence changes — update claim rows in
  `product-claim-evidence.yaml`, update question rows in
  `product-question-bank.yaml`, add/update tests in
  `tests/unit/test_product_answer.py` and
  `tests/behavior/test_product_answer_cli.py`, rerun ADR-280 verification,
  only then update public docs.
- **Token-efficient answer cards (ADR-282)**: `scripts/cos-product-answer-
  refresh --all` (or `--question-id`) writes gitignored local artifacts under
  `.cognitive-os/product-answers/`: per-question `.md` (compact, source-
  hashed) and `.json` (full report), an `index.yaml` routing index, and an
  append-only `freshness-ledger.jsonl`. After cards exist, the canonical
  command defaults to reading a fresh card and only falls back to live
  ADR-280 generation when the card is missing or stale (`--no-cache` forces
  live generation).

## Relations & where used

- Implements ADR-280 (product-question-to-evidence primitive) and ADR-282
  (product-answer card cache and freshness ledger), both referenced by
  `master-plan-checklist.md` under "Product Promise."
- Shares its north-star wording and short pitch almost verbatim with the
  primary product message in `product-messaging.md`.
- Its evidence-gating discipline (`blocked` / `aspirational` claim states) is
  the same discipline applied by `install-scope-anti-slop-audit-2026-05-15.md`
  when it recommends specific "allowed vs. avoid" product wording.

## Status / caveats

- Operational/process document, not a status report — it describes how
  answers should be produced, not the current content of any particular
  answer. No claims within this document itself require evidence-gate
  verification.
- No internal inconsistency found.
