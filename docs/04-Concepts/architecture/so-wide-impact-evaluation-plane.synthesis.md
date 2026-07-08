---
type: concept-synthesis
source: docs/04-Concepts/architecture/so-wide-impact-evaluation-plane.md
provenance: "Turns broad claims such as 'Cognitive OS reduces token use' or 'Cognitive OS improves agent delivery' into paired, replayable experiments with the same task, fixture project, model/harness, and verification commands, and isolated state per run."
---

## What it is
Design plus partially-implemented plan for an SO-wide (whole-operating-system) controlled evaluation plane that measures when Cognitive OS actually improves delivery vs. only adds ceremony, generalizing the narrower Graphify-trial evaluation approach to the full primitive set.

## Key mechanics
- Existing substrate reused: `scripts/so_vs_vanilla_benchmark.py` (vanilla vs. `so` dispatch-level runs), `docs/08-References/benchmarks/so-vs-vanilla-tasks.yaml`, `scripts/cos-token-savings-audit`, `scripts/cos-token-optimization-consumer-smoke`, `scripts/cos-portable-ai-real-consumer-smoke`, `scripts/agent-orchestration-benchmark.py`, `scripts/skill-router-benchmark.py`, `scripts/cos-loop-eval`/`cos-loop-report`/`cos-process-loop`.
- Gap in the current benchmark: dispatch-level only — lacks isolated capsules per mode, real file-changing tool traces, provider-normalized usage receipts, generated diffs/touched-file counts, verification receipts, process-loop state transitions, claim/false-completion events, and ablation isolation of which primitive family caused a delta.
- 9 evaluation modes: `vanilla`, `full-so`, `graphify-only`, `process-loop-only`, `skill-selection-only`, `token-optimization-only`, `governance-hooks-only`, `full-so-minus-graphify`, `full-so-minus-process-loop`. An unsupported mode must be recorded as `unsupported`, never silently approximated.
- Task contract schema `cos.so-impact-eval.v1`: `taskId`, `class`, `fixture` (repo/setupCommands/`resetPolicy: clean-worktree-per-mode`), `prompt` (objective/constraints), `controls` (harness/provider/model/maxDiscoveryToolCalls/maxTotalToolCalls/maxWallClockSeconds/allowedTools), `verification.commands`, `metrics` (requireUsageReceipt/requireDiffReceipt/requireVerificationReceipt), `modes`, `verdict` (correctness required, tokens compared after-correctness, latency advisory).
- Execution model: select task contract -> isolated capsule per mode -> run with fixed controls -> capture trace/usage/diff/verification receipts -> score correctness first -> compare efficiency -> emit report + claim tier. The runner must never reuse mutable state between modes unless the contract explicitly marks it shared and deterministic.
- Metrics table (mostly Required): verification status, total tokens, cost, wall-clock time, discovery context lines, discovery tool calls, total tool calls, relevant files found, diff size/files touched, retries/repeated tool patterns, false completion events, blocked unsafe actions, final diff quality (recommended).
- Artifact layout: `docs/09-Quality/evals/so-impact/{task-id}/{run-id}/` with `contract.yaml`, `report.md`, and per-mode/ablation subdirectories each containing `trace.jsonl`, `usage.json`, `diff.patch`, `verify.json`, `process.json`.
- Scoring order: correctness gate -> safety gate -> coverage gate -> efficiency comparison -> quality comparison. Verdicts: `win`/`neutral`/`loss`/`inconclusive`.
- Claim tiers (5, escalating evidence requirements): structural estimate, paired live run, replicated task class (≥3 tasks), cross-harness (≥2 harnesses), cross-provider. Broad claims require the matching tier — e.g. "Cognitive OS optimizes tokens portably" is blocked until replicated task-class evidence exists.
- Implemented primitive: `scripts/cos-so-impact-eval` (backed by `scripts/cos_so_impact_eval.py`, ADR-338) — `plan`/`run` subcommands; bundled smoke contract `docs/08-References/benchmarks/so-impact-money-format-refactor.yaml` against deterministic fixture `fixtures/so-impact/money-format-refactor`; conversational entry `/so-impact-smoke` or `make test-so-impact-smoke`; deterministic smoke verdict = "win - fewer false completion events; less discovery context."
- Lifecycle trigger: `hooks/so-impact-eval-trigger.sh` runs `vanilla` vs. `full-so` automatically on Stop/shutdown when dirty changes touch so-impact/Graphify/process-loop surfaces, writing to `.cognitive-os/reports/so-impact-auto/` and `.cognitive-os/metrics/so-impact-eval-trigger.jsonl`; advisory-only, dedupes, disable via `COS_SO_IMPACT_EVAL_TRIGGER_DISABLE=1`.
- Remaining slices: provider/harness usage normalization, connecting live CLI/IDE runners (currently deterministic-smoke only), richer quality oracles for real diffs, promoting replicated runs to CI/nightly.

## Relations & where used
ADR-338. Relationship to Graphify: Graphify is one ablation mode inside this plane, not proof of whole-SO savings — the doc gives explicit valid/invalid claim-shape examples.

## Status / caveats
First implementation slice is complete (contract-shaped receipts, isolated capsules, initial mode matrix, reports under `docs/09-Quality/evals/so-impact/`, unit/red-team receipt tests). Live-harness connection and CI/nightly promotion remain open. A 9-item validation checklist gates promoting any benchmark result publicly.
