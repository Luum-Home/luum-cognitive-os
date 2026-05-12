# Benchmarking Cognitive OS

## Purpose

The benchmark system provides a repeatable way to measure Cognitive OS performance
against alternative agent frameworks -- specifically BMAD METHOD v6. It runs
5 standardized coding tasks, collects quantitative metrics, and uses LLM
evaluation for qualitative scoring.

## Architecture

```
benchmark-config.yaml     Task definitions + metric specs
        |
run-benchmark.sh          Orchestrator script
        |
   +---------+--------+
   |         |        |
worktree   claude    metrics
isolation  headless  collection
   |         |        |
   +----+----+--------+
        |
benchmark-results.jsonl   Raw results (append-only)
benchmark-report-*.md     Human-readable reports
```

## File Locations

| File | Purpose |
|------|---------|
| `.cognitive-os/tests/benchmark/benchmark-config.yaml` | Task definitions and metric specs |
| `.cognitive-os/tests/benchmark/run-benchmark.sh` | Main benchmark runner script |
| `.cognitive-os/tests/benchmark/compare-with-bmad.md` | Manual comparison guide and template |
| `.cognitive-os/tests/benchmark/benchmark-report-template.md` | Report template |
| `.cognitive-os/skills/cognitive-os-benchmark/SKILL.md` | Skill definition for `/benchmark` command |
| `.cognitive-os/metrics/benchmark-results.jsonl` | Accumulated results (append-only) |
| `.cognitive-os/metrics/benchmark-report-*.md` | Generated reports per run |

## The 5 Benchmark Tasks

### 1. Create Go Service (`create-go-service`)
Tests the system's ability to scaffold a complete microservice following
clean architecture patterns. Measures structural compliance, test generation,
and compilation success.

### 2. Fix Bug (`fix-bug`)
Tests debugging capability. A validation gap is introduced via setup, then
the agent must find and fix it, add a regression test, and avoid breaking
existing functionality.

### 3. Add Endpoint (`add-endpoint`)
Tests pattern recognition. The agent must add a new endpoint that matches
the existing codebase's conventions for naming, error handling, DTOs, and
test structure.

### 4. Refactor Code (`refactor-code`)
Tests architectural understanding. Business logic must be extracted from
controllers into use cases without breaking existing tests.

### 5. Cross-Service Feature (`cross-service-feature`)
Tests system-level thinking. A feature spanning multiple services requires
event-driven communication (Kafka), proper service boundaries, and
integration testing.

## Metric Types

| Type | How Measured | Example |
|------|-------------|---------|
| `count` | Automated file counting | files_created, tests_created |
| `boolean` | Shell command exit code or file inspection | compilation_success |
| `duration` | Wall-clock time (seconds) | time_seconds |
| `llm_eval` | Second Claude call rates output 0-10 | architecture_score |

## Running Benchmarks

### Quick Start

```bash
# Run all tasks with Cognitive OS
bash .cognitive-os/tests/benchmark/run-benchmark.sh

# Run all tasks with BMAD v6
bash .cognitive-os/tests/benchmark/run-benchmark.sh --system bmad

# Compare results
# See .cognitive-os/metrics/benchmark-report-*.md
```

### Single Task

```bash
bash .cognitive-os/tests/benchmark/run-benchmark.sh --task create-go-service
```

### Dry Run

```bash
bash .cognitive-os/tests/benchmark/run-benchmark.sh --dry-run
```

## Isolation

Each benchmark task runs in its own git worktree (or rsync copy if not in a
git repo). This prevents tasks from interfering with each other or with the
main working tree. Worktrees are cleaned up after each task unless
`--no-cleanup` is passed.

## Scoring System

Maximum score: 50 points. Weights are defined in `benchmark-config.yaml`
under `scoring.weights`. Boolean metrics score their full weight when true.
LLM eval scores are normalized. Time and token counts apply small negative
penalties to reward efficiency.

## Adding New Benchmark Tasks

1. Add a new entry to `benchmarks` in `benchmark-config.yaml`
2. Define `id`, `name`, `prompt`, and `metrics`
3. Optionally add a `setup` command for pre-task environment changes
4. Update scoring weights if needed
5. Run with `--task <new-id>` to test

## Comparing Systems

The benchmark runner supports two systems:

- **cognitive-os**: Uses the project's `.cognitive-os/` rules, skills, and conventions
- **bmad**: Wraps prompts with BMAD METHOD v6 context instructions

Run both and compare the generated reports. See `compare-with-bmad.md` for
a structured side-by-side comparison template.

## Limitations

- LLM evaluation scores have inherent variance (run 3 times and average)
- Compilation checks require the relevant build tools installed locally
- Token counting depends on Claude CLI JSON output format
- Network latency affects timing (run on same machine, similar conditions)
- BMAD comparison is approximate since it uses prompt wrapping rather than
  full BMAD toolchain integration
