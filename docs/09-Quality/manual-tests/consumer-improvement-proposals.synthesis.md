---
type: quality-synthesis
source: docs/09-Quality/manual-tests/consumer-improvement-proposals.md
provenance: "Manual test proving that consumer-project primitive-improvement signals can be exported and imported as review-only proposals without mutating SO runtime state."
---

## What it is
A manual test procedure for the consumer-improvement-proposals pipeline: a consumer project (running Cognitive OS) exports sanitized primitive-improvement signals from its local `.cognitive-os/metrics/`, and the SO repository imports them as review-only proposals. The goal is to prove the path never auto-merges, auto-promotes, or leaks secrets/vault content upstream.

## Key mechanics
- **Export**: `scripts/cos-export-consumer-improvement-proposals --project <name> --profile core --since 30d --threshold 3 --output <file>` produces JSON with `schema_version: cos-consumer-improvement-proposals.v1`, `mode: propose_only`, `runtime_effect: none`, and a policy block asserting `auto_merge: false`, `auto_promote_core_or_team: false`, `credential_copy: false`, `raw_vault_export: false`. Proposal entries are typed as one of `project-local`, `upstream-candidate`, `harness-gap`, `docs-only`, `reject`.
- **Sanitization**: excerpts must exclude `.env` content, tokens, provider keys, home paths, and full Obsidian vault content.
- **Import**: `scripts/cos-import-consumer-improvement-proposals <bundle.json>` (run from the SO repo) exits 0 for valid bundles, reports `status: proposed` / `runtime_effect: none`, and writes a review artifact under `.cognitive-os/improvements/proposals/` — no hook, rule, skill, manifest, Engram DB, or Obsidian vault is mutated.

## Relations & where used
Part of the consumer-project feedback loop that lets downstream adopters propose primitive improvements back to the SO without granting them write authority over core/team primitives. Complements other consumer-accessibility proofs (e.g. `consumer-project-primitive-accessibility.md`, `consumer-sdd-lane.md`) that validate the SO's promises actually project correctly to consumer projects.

## Status / caveats
Point-in-time manual test spec, not a dated run log — no evidence of an actual executed run is embedded in the source (no observed output shown). Treat as a documented procedure with expected results rather than a proof of a specific historical execution.
