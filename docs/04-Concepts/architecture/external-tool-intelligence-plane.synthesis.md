---
type: concept-synthesis
source: docs/04-Concepts/architecture/external-tool-intelligence-plane.md
status: proposed
provenance: "Consumer projects should not each replicate a full deep-research structure for external tools — that creates noise, duplicated analysis, and drift between projects."
---

## What it is

Proposal splitting external-tool intelligence into three layers so consumer projects never recreate deep research: `COS repo = central intelligence/deep radar/doctrine/benchmarks`, `Consumer project = lightweight overlay/local evidence/local constraints`, `Final view = COS radar + project overlay + real receipts`.

## Key mechanics

- External models referenced: Thoughtworks/Zalando ring-based tech radar (Hold/Assess/Trial/Adopt — Trial requires real project use, Adopt requires confidence at scale), Backstage Tech Radar (centralizes standards, doesn't ask every repo to recreate research), CycloneDX/SPDX/SBOM (verifiable inventory, doesn't decide adoption), OpenSSF Scorecard/deps.dev/OSV/SLSA (health/security signals that enrich but don't replace architectural judgment).
- COS repo owns: `docs/06-Daily/reports/external-tools-radar-INDEX.md`, dated radar reports, master-inventory, reassessment-scope, per-tool deep-dives, `external-tool-adoption-doctrine.md`, `external-tool-adapter-taxonomy.md`, and the not-yet-built `manifests/external-tools-adoption.yaml` (machine-readable adoption ledger — example schema includes `id`, `verdict`, `adoption_kind`, `license`, `source_of_truth`, `allowed_surfaces`, `consumer_contract`, `evidence`, `status`).
- Consumer project owns `.cognitive-os/external-tools-overlay.yaml` (`inherits.from_os_radar`, `project_constraints` like `no_daemons`/`allowed_licenses`, `local_tools` list with `local_status: enabled|assess` and evidence pointers).
- Rules: if the tool is already in the COS radar, the project only references it plus local evidence; if project-only, keep it local or propose promotion; if the project contradicts the COS verdict, it must declare an override with reason/owner/expiry/evidence.
- Recommended flow: repo scan/SBOM/docs scan -> master inventory -> dedup + domain grouping -> external metadata enrichment -> deep-dive for candidates -> verdict (ADOPT/INTEGRATE/BUILD/DEFER/REMOVE) -> `manifests/external-tools-adoption.yaml` -> project overlays -> effective radar view -> adoption truth/capability coverage/public claims.
- Three-layer rule avoids two failure modes: every consumer project drifting by recreating deep research, and the OS pretending to know local project context only the consumer project can prove.

## Relations & where used

`docs/04-Concepts/architecture/external-tool-adoption-doctrine.md`, `docs/04-Concepts/architecture/external-tool-adapter-taxonomy.md`, `manifests/cross-stack-adoption-truth.yaml`, `manifests/capability-coverage.yaml`, ADR-217 (adoption truth), ADR-252 (capability coverage).

## Status / caveats

Status: proposed. The design-implications list (`manifests/external-tools-adoption.yaml`, `.cognitive-os/external-tools-overlay.yaml` template, `scripts/cos-tool-adoption-audit`, `scripts/cos-tool-radar-render`, `scripts/cos-tool-research-check`) is future work, not yet built as of this doc.
