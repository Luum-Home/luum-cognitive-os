---
type: capability-synthesis
source: docs/07-Capabilities/acc/latest.md
provenance: "Generated report snapshot from the ACC (Agent Capability Coverage) pipeline, published to give reviewers a diffable, git-tracked view of the latest coverage run."
---

## What it is
The latest generated Agent Capability Coverage (ACC) report: a snapshot of how completely Cognitive OS's real capabilities are represented to agentic primitives, produced by `scripts/acc_pipeline.py` (ADR-147).

## Key mechanics
- Headline metrics at generation time (2026-06-17T23:58:22Z, phase `reconstruction`, gate `pass`): ACC 0.9186, ACC effective 0.9190, total weight 8002, 3683 capabilities, 288 findings.
- Mapping-status weight breakdown: aligned 7351, partial 434, stale 214, unverified 3, missing 0, overexposed 0.
- Adapter Status table lists ~20 adapters (authority_write_effects, codebase_itinerary, consumer_availability, consumer_projection, docs_execution_report, documentation_truth, harness_coverage, harness_projection, primitive_fitness_ledger, primitive_interventions, projection_fidelity, projection_profiles, proof_drill_evidence, readiness:hooks/rules/scripts/skills/templates, shell_ci_projection) — all reporting `ok` with their source path and a summary payload.
- Findings table lists ~80+ `medium`/`partial` capability rows, almost all `script:scripts/*` entries flagged "Candidate/projectable surface needs consumer projection proof", with next action "add harness projection proof before promotion".
- New Debt section: none (pass).
- Consumer Accessibility Counts: breakdown across install-profile-managed, lifecycle-declared-consumer-candidate, lifecycle-declared-maintainer, maintainer-only, profile-driver, projected-consumer-surface (1945, the largest bucket), runtime-evidence, shell-ci-candidate, skill-referenced-not-projectable, so-local-only.
- Persistence: local history at `.cognitive-os/metrics/acc-pipeline-history.jsonl`; Engram noted as unavailable at generation time.

## Relations & where used
Companion artifact to `docs/07-Capabilities/root/agent-capability-coverage.md` (the ACC spec), which defines this report's four-layer persistence model (Engram canonical manifest, this file as the reviewable snapshot, `latest.json` as the drift baseline, per-capability evidence in Engram). Surfaced via `cos-coverage` CLI and the `statusline-coverage.sh` segment.

## Status / caveats
This is a dated, point-in-time generated snapshot (2026-06-17), not a stable narrative document — later pipeline runs will overwrite `latest.md`/`latest.json` with different numbers. The large "Findings" table is mechanically produced and dominated by one recurring finding type (missing consumer projection proof for scripts); no other finding categories appear in this run.
