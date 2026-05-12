# Consumer Improvement Proposals Manual Test

**Purpose**: prove that a project implementing Cognitive OS can export sanitized
primitive-improvement signals and that the SO can import them as review-only
proposals without mutating runtime state.

## Export proof

From a consumer project or temp fixture with `.cognitive-os/metrics/` populated:

```bash
scripts/cos-export-consumer-improvement-proposals \
  --project my-service \
  --profile core \
  --since 30d \
  --threshold 3 \
  --output /tmp/my-service-cos-improvement-proposals.json
```

Expected:

- command exits 0;
- JSON contains `schema_version: cos-consumer-improvement-proposals.v1`;
- JSON contains `mode: propose_only` and `runtime_effect: none`;
- policy contains `auto_merge: false`, `auto_promote_core_or_team: false`,
  `credential_copy: false`, and `raw_vault_export: false`;
- proposals, when present, use one of `project-local`, `upstream-candidate`,
  `harness-gap`, `docs-only`, or `reject`;
- excerpts are sanitized: no `.env`, tokens, provider keys, home paths, or full
  Obsidian vault content.

## Import proof

From the SO repository:

```bash
scripts/cos-import-consumer-improvement-proposals \
  /tmp/my-service-cos-improvement-proposals.json
```

Expected:

- command exits 0 for a valid bundle;
- JSON reports `status: proposed` and `runtime_effect: none`;
- a review artifact is written under `.cognitive-os/improvements/proposals/`;
- no live hook, rule, skill, manifest, Engram DB, or Obsidian vault is mutated.

## Safety invariants

- Consumer projects keep local authority over project-local primitives.
- Upstream receives only sanitized proposals with provenance and counts.
- Imported proposals never auto-merge, auto-promote, or rewrite core/team
  primitives.
- Raw Engram stores and Obsidian vaults do not travel through this path.
