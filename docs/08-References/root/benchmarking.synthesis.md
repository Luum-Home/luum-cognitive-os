---
type: reference-synthesis
source: docs/08-References/root/benchmarking.md
provenance: "Documents the repeatable benchmark harness used to measure Cognitive OS performance against BMAD METHOD v6 on 5 standardized coding tasks."
---

## What it is

Reference documentation for the Cognitive OS benchmark system: a harness that runs 5 standardized coding tasks against either "cognitive-os" (project rules/skills/conventions) or "bmad" (BMAD METHOD v6 prompt-wrapped context), collects quantitative and LLM-judged qualitative metrics, and produces comparison reports.

## Key mechanics

- **Pipeline**: `benchmark-config.yaml` (task + metric definitions) -> `run-benchmark.sh` (orchestrator) -> worktree isolation + headless Claude execution + metrics collection -> `benchmark-results.jsonl` (append-only) + `benchmark-report-*.md`.
- **5 tasks**: `create-go-service` (scaffolding/clean architecture), `fix-bug` (debugging + regression test), `add-endpoint` (pattern matching to existing conventions), `refactor-code` (extract business logic without breaking tests), `cross-service-feature` (event-driven, multi-service, Kafka).
- **Metric types**: `count` (automated file counting), `boolean` (exit code/file inspection), `duration` (wall-clock seconds), `llm_eval` (second Claude call scores 0-10).
- **Isolation**: each task runs in its own git worktree (or rsync copy outside a git repo); cleaned up after unless `--no-cleanup`.
- **Scoring**: max 50 points; weights defined in `benchmark-config.yaml` under `scoring.weights`; boolean metrics score full weight when true; LLM-eval scores normalized; time/token counts apply small negative efficiency penalties.
- **Usage**: `bash .cognitive-os/tests/benchmark/run-benchmark.sh` (all tasks, default system), `--system bmad` to switch systems, `--task <id>` for a single task, `--dry-run` for a no-op pass.
- **Extending**: add a new entry under `benchmarks` in `benchmark-config.yaml` with `id`, `name`, `prompt`, `metrics`, optional `setup` command, then run with `--task <new-id>`.

## Relations & where used

- Invoked via the `/benchmark` skill (`.cognitive-os/skills/cognitive-os-benchmark/SKILL.md`).
- Results accumulate in `.cognitive-os/metrics/benchmark-results.jsonl`; reports land in `.cognitive-os/metrics/benchmark-report-*.md`.
- `compare-with-bmad.md` provides a manual side-by-side comparison template for cross-system analysis.
- Complements `docs/08-References/root/competitive-analysis.md` and `competitive-landscape.md`, which reference test-count/quality claims that this harness is meant to substantiate empirically.

## Status / caveats

- Source explicitly documents its own limitations: LLM-eval variance (recommends averaging 3 runs), compilation checks require local build tooling, token counting depends on the Claude CLI JSON output format, timing is sensitive to network/machine conditions, and the BMAD comparison is "approximate" since it uses prompt wrapping rather than full BMAD toolchain integration — not a fully controlled head-to-head.
- No internal inconsistencies found in the source; this is a stable reference document, not a dated snapshot.
