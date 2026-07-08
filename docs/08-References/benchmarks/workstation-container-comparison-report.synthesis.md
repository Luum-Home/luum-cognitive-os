---
type: reference-synthesis
source: docs/08-References/benchmarks/workstation-container-comparison-report.md
provenance: "Defines the fixture set, row schema, and comparison dimensions for measuring COS overhead and catch value between workstation and container execution environments, before any real worker runtime exists to run them against."
---

## What it is

A benchmark methodology document (not a results document) that specifies how to compare vanilla Claude/Codex against COS-enabled runs across workstation and container environments, using two deterministic, dependency-free Python fixtures.

## Key mechanics

- **Fixtures**: `bugfix-python-logic` and `refactor-python-multifile`, both repository-owned, MIT-compatible, and runnable with plain `pytest` success commands — no network or external services required.
- **Report generation**: operators record run rows as JSON (`fixture_id`, `environment`, `mode`, `success`, `elapsed_ms`, `cost_usd`, `catch_value`, `artifact_quality`, `notes`) and render them via `scripts/workstation_container_benchmark_report.py`.
- **Comparison dimensions**: vanilla vs. COS-enabled results on the same fixture; workstation vs. container elapsed time; latency/cost overhead; catch value (e.g., failing-test detection, governance refusal); artifact quality (tests passing, minimal diff quality).
- Scope is explicitly narrowed to workstation and container only — Kubernetes, local cluster, and fleet benchmarks are deferred pending a real worker runtime.

## Relations & where used

Feeds the broader "prove the outcomes, not just claim them" thread shared with `cognitive-os-efficiency-operating-model.md` (`cos-so-impact-eval`) and the A/B/C falsification protocol in `cos-vs-ai-slop-falsification.md`. Report output lands at `docs/08-References/benchmarks/workstation-container-results-YYYYMMDD.md`.

## Status / caveats

This is a methodology/tooling scaffold, not a results report: as of the document's own text, "No live agent/container benchmark run was executed in this slice." Treat any absence of a dated results file alongside it as expected — the fixture set and renderer are ready, but no comparative numbers exist yet. Point-in-time note: work ID `worker-g-p5-p6-20260520` ties this to a specific work slice; later slices may have since produced actual run data not reflected here.
