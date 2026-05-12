# Documentation Truth Control

> Canonical control for preventing stale or contradictory documentation claims when generated reports, manifests, or implementation status change.

## Why this exists

Cognitive OS has many generated truth surfaces: readiness ledgers, projection fidelity reports, authority/write-effects reports, ACC output, ADR indexes, and security reports. Human-authored Markdown can drift after those reports change. The recurring failure mode is not a missing test for code; it is a stale claim in docs that still says an implemented control is pending, or that a proof covers only an older harness set.

The documentation truth control makes volatile claims explicit and machine-checkable.

## Contract

The canonical manifest is `manifests/documentation-truth-claims.yaml`.

Each claim declares:

- source reports or manifests that provide the current facts;
- required documentation surfaces that must carry the claim;
- required phrases that anchor the current contract;
- forbidden stale phrases that must not reappear;
- optional generated blocks that must match current generated facts exactly.

The auditor is `scripts/documentation_truth_audit.py`, with CLI wrapper `scripts/cos-documentation-truth-audit`. It emits:

- `docs/reports/documentation-truth-latest.json`
- `docs/reports/documentation-truth-latest.md`

ACC consumes the report through the `documentation_truth` adapter.

## Implemented claim families

| Claim | Purpose | Primary source |
|---|---|---|
| `consumer_projection_harnesses` | Prevents projection docs from reverting to stale Claude/Codex-only claims. | `docs/reports/primitive-projection-fidelity-latest.json` |
| `primitive_authority_write_effects` | Prevents authority docs from describing ADR-276 as a pending gap after implementation. | `docs/reports/primitive-authority-latest.json` |
| `documentation_truth_control` | Keeps this control discoverable in docs and ACC. | `docs/reports/documentation-truth-latest.json` |

## Generated truth block

<!-- GENERATED:documentation-truth:documentation_truth_control:start -->
Generated documentation truth: documentation truth control.
Declared truth claims (4): consumer_projection_harnesses, documentation_truth_control, primitive_authority_write_effects, session_pending_protocol.
Contract surfaces: manifests/documentation-truth-claims.yaml; scripts/documentation_truth_audit.py; ACC adapter documentation_truth.
Report surfaces: docs/reports/documentation-truth-latest.json; docs/reports/documentation-truth-latest.md.
<!-- GENERATED:documentation-truth:documentation_truth_control:end -->

## Operating model

1. Update source report or manifest.
2. Run `python3 scripts/documentation_truth_audit.py --project-dir . --update-generated`.
3. Commit changed docs/reports together with source changes.
4. Contract tests fail if a required phrase, source report, or generated block drifts.

## Boundary

This is exhaustive for declared volatile claims. It is intentionally not a general natural-language theorem prover. New contradiction classes must be added to `manifests/documentation-truth-claims.yaml` as claim rules, stale phrases, required phrases, or generated blocks.
