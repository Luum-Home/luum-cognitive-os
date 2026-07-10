---
type: reference-synthesis
source: docs/08-References/root/adw-patterns.md
provenance: "Explains AI Developer Workflows (ADW), the deterministic-pipeline-plus-agent pattern that Cognitive OS's workflow YAMLs implement, sourced from IndyDevDan's 'Tactical Agentic Coding' concept."
---

## What it is

A reference explaining the ADW (AI Developer Workflow) pattern — combining deterministic pipeline code with non-deterministic LLM agent steps — and how Cognitive OS's `.cognitive-os/workflows/` directory is a concrete ADW implementation, including the pipeline authoring format, lifecycle, and relationship to other COS concepts (PITER, SDD, ZTE).

## Key mechanics

- **Core formula**: `ADW = Deterministic Pipeline + Non-Deterministic Agents`. Properties: repeatable (same trigger → consistent structure), measurable (per-step metrics), optimizable (metrics drive tuning), composable (ADWs can embed other ADWs).
- **Named COS pipelines**: Feature (`feature-pipeline.yaml`: propose→spec→design→tasks→apply→verify→archive), Bug Fix (`bugfix-pipeline.yaml`: reproduce→diagnose→fix→test→verify), Refactor (`refactor-pipeline.yaml`: analyze→plan→apply→verify), SRE (`sre-pipeline.yaml`: detect→classify→repair→verify→document), Review (`review-pipeline.yaml`: analyze→check-gates→report).
- **Step anatomy** (YAML): `type` (`agent`|`script`|`gate`), `skill`, `model` (sonnet|opus|haiku), `inputs`/`outputs`, `success_criteria`, `on_failure` (retry|skip|abort|escalate), `max_retries`.
- **Step types**: `agent` (sub-agent executes with a named skill loaded, e.g. `sdd-apply`), `script` (deterministic command, e.g. `yarn test`), `gate` (boolean check that blocks the pipeline, e.g. coverage threshold).
- **5-stage ADW lifecycle**: Design (define steps/dependencies/gates/budget) → Test (validate with known-good inputs, verify artifacts and gate behavior, measure baseline metrics) → Deploy (add to `.cognitive-os/workflows/`, register in `cognitive-os.yaml`, document trigger) → Monitor (`skill-metrics.jsonl`, agent KPIs, error learning) → Optimize (model-routing downgrades, step consolidation, gate-threshold tuning, budget adjustment).
- **Authoring a new ADW**: define the workflow YAML with `budget` (max_cost, max_duration) and `steps`; optionally add a `piter-loop` step type for self-correcting implement/test/refine cycles (`max_iterations`, `plan`, `implement_skill`, `test_command`, `evaluate_skill`); register the workflow under `workflows:` in `cognitive-os.yaml` with a trigger command.
- **6 named anti-patterns** with fixes: all-agent pipeline (no checkpoints) → add gates; no budget limits (cost spiral) → set max_cost/max_duration; missing success criteria → every agent step needs verification; monolithic steps → break into smaller focused steps; no failure handling → define `on_failure` per step; hardcoded models → use the model-routing table.
- **Runtime**: `lib/pipeline_executor.py` executes workflow YAMLs, invocable via a skill (`/run-pipeline feature my-feature`) or direct CLI (`python3 -m cos_lib.pipeline_executor --workflow ... --change ...`). State persists to `.cognitive-os/pipeline-state/{change}.json` after every phase, resumable with `--resume`.

## Relations & where used

Explicit relationship table: PITER is an inner loop nested inside ADW agent steps (implement/test/refine); SDD is named the most mature ADW in COS (8 phases with defined artifacts); Closed-loop prompts let agent steps self-correct within a step; ADWs are called out as the execution mechanism for ZTE (event-triggered ADWs are labeled Phase 2, i.e., not yet built); ADWs are equated directly with "Leverage Point 10" (workflow automation) in COS's broader leverage-point framework.

## Status / caveats

The document states SDD as "8 phases" here, consistent with the "8 core phases plus optional init/bootstrap" language standardized in the 2026-05-15 promise-compliance remediation pass — no phase-count inconsistency found relative to that source. One forward-looking note is preserved as-is: "event-triggered ADWs are Phase 2" under the ZTE relationship, meaning that specific integration is described as not yet implemented at time of writing; this is a design/roadmap note within an otherwise reference-style document, not a dated audit.
