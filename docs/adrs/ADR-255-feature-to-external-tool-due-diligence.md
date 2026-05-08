# ADR-255 — Feature-to-External-Tool Due Diligence

## Status
Accepted — Slice A implemented

**Date**: 2026-05-08  
**Owner**: platform-safety  
**Related**: ADR-252, ADR-254, ADR-250, ADR-251, `docs/architecture/external-tool-adoption-doctrine.md`

## Context

The external-tools radar and ADR-254 established a central adoption manifest,
project overlays, and research-check packets. That is necessary but not enough.
COS can still build a custom feature and only later discover that a mature
third-party tool already solved the mechanism better.

The risk is not only dependency sprawl. The opposite risk is worse for product
focus: COS quietly becomes a maintenance-heavy clone of many tools instead of a
control plane that composes mature tools behind governance boundaries.

## Decision

Every custom COS feature that claims `BUILD` or equivalent first-party ownership
must have a machine-readable due-diligence record before it is promoted to REAL
or public-facing status.

The record must link:

```text
COS capability / feature
  -> external candidates
  -> GitHub/package/paper/source links
  -> DeepWiki URL when the source is GitHub-backed
  -> optional off-repo source snapshot
  -> benchmark or falsification fixture
  -> decision: ADOPT / INTEGRATE / BUILD / DEFER / REMOVE
```

This does not require cloning every repository. It requires an auditable reason
when COS keeps building the feature itself.

## New primitives

- `manifests/feature-tool-due-diligence.yaml`
- `scripts/cos-feature-tool-scan`
- `scripts/cos-external-source-fetch`
- `scripts/cos-feature-vs-tool-benchmark`
- `docs/reports/external-tools-deep-dive/{tool-id}.md`
- `.cognitive-os/external-source-cache/` as a gitignored scratch cache

## Policy

A custom feature may remain BUILD only when its record includes:

1. at least one external candidate, or a documented no-candidate search query;
2. source links;
3. license and footprint posture;
4. source/deepwiki/deps.dev/scorecard receipts where available;
5. benchmark, falsification fixture, or explicit non-benchmarkable rationale;
6. maintenance-cost estimate;
7. rollback/deprecation path if a better external tool appears.

## Non-goals

- Do not vendor code by default.
- Do not make internet access mandatory for normal test lanes.
- Do not clone third-party repos into git-tracked paths.
- Do not block emergency security fixes on fresh market research.

## Implementation status

Slice A implements the local control plane:

- manifest schema and seed records;
- scan CLI that detects BUILD-like capabilities missing due diligence;
- source-fetch CLI that clones GitHub repos only into the gitignored scratch cache;
- benchmark CLI that checks due-diligence records for benchmark/source evidence;
- tests for missing scans, deepwiki URL derivation, and scratch-cache behavior.

Future slices can enrich records from deps.dev and OpenSSF Scorecard APIs.
