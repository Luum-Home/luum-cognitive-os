<!-- SCOPE: os-only -->
---
name: cognitive-os-benchmark
description: Run benchmark comparisons between Cognitive OS and BMAD METHOD v6
triggers:
  - /benchmark
  - /run-benchmark
  - /compare-bmad
tags: [testing, benchmark, comparison, quality]
audience: os-dev
version: "1.0.0"
platforms: ["claude-code"]
prerequisites: []
routing_patterns:
  - pattern: '\bcognitive[- ]?os[- ]?benchmark\b'
    confidence: 0.95
  - pattern: '\bbenchmark\s+(cognitive[- ]?os|cos)\b'
    confidence: 0.85
  - pattern: '\bcos\s+vs\s+(bmad|baseline)\b'
    confidence: 0.75
---

# Cognitive OS Benchmark Skill

Run standardized benchmarks to compare Cognitive OS vs BMAD METHOD v6 on 5 coding tasks.

## Usage

```
/benchmark                    # Run all benchmarks with Cognitive OS
/benchmark --system bmad      # Run all benchmarks with BMAD v6
/benchmark --task fix-bug     # Run a single benchmark task
/benchmark --dry-run          # Preview what would run
```

## What It Does

1. Reads task definitions from `.cognitive-os/tests/benchmark/benchmark-config.yaml`
2. For each task, creates an isolated git worktree
3. Runs Claude Code headless with the task prompt
4. Measures: time, tokens, files created, tests created, compilation success
5. Runs LLM evaluation for architecture/pattern compliance scores
6. Saves results to `.cognitive-os/metrics/benchmark-results.jsonl`
7. Generates a markdown report

## Benchmark Tasks

| ID | Description |
|----|-------------|
| `create-go-service` | Create a new Go microservice with clean architecture |
| `fix-bug` | Fix a validation bug and add regression tests |
| `add-endpoint` | Add an endpoint following existing patterns |
| `refactor-code` | Refactor controllers to use cases |
| `cross-service-feature` | Implement a feature spanning multiple services |

## Commands

### Run All Benchmarks

```bash
bash .cognitive-os/tests/benchmark/run-benchmark.sh
```

### Run Cognitive OS Only

```bash
bash .cognitive-os/tests/benchmark/run-benchmark.sh --system cognitive-os
```

### Run BMAD Only

```bash
bash .cognitive-os/tests/benchmark/run-benchmark.sh --system bmad
```

### Run Single Task

```bash
bash .cognitive-os/tests/benchmark/run-benchmark.sh --task create-go-service
```

### Dry Run (preview)

```bash
bash .cognitive-os/tests/benchmark/run-benchmark.sh --dry-run
```

### Keep Worktrees After Run

```bash
bash .cognitive-os/tests/benchmark/run-benchmark.sh --no-cleanup
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--system` | `cognitive-os` or `bmad` | `cognitive-os` |
| `--task` | Run single task by ID | all tasks |
| `--model` | Override Claude model | from config |
| `--max-turns` | Override max turns | from config |
| `--dry-run` | Show tasks without executing | false |
| `--no-cleanup` | Keep worktrees after run | false |

## Output

- **JSONL results**: `.cognitive-os/metrics/benchmark-results.jsonl`
- **Markdown report**: `.cognitive-os/metrics/benchmark-report-{run-id}.md`
- **Comparison guide**: `.cognitive-os/tests/benchmark/compare-with-bmad.md`

## Dependencies

- `claude` CLI
- `yq` (YAML parser)
- `jq` (JSON processor)
- `git` (for worktree isolation)

Install missing deps: `brew install yq jq`

## Metrics Collected

| Metric | Type | Description |
|--------|------|-------------|
| `time_seconds` | duration | Wall-clock execution time |
| `tokens_used` | count | Total input + output tokens |
| `files_created` | count | New/modified files |
| `tests_created` | count | Test files created |
| `compilation_success` | boolean | Code builds without errors |
| `architecture_score` | llm_eval | Clean architecture compliance (0-10) |
| `follows_patterns` | llm_eval | Codebase pattern consistency (0-10) |
| `architecture_improved` | llm_eval | Refactoring quality (0-10) |

## Scoring

Maximum score: 50 points across all 5 tasks. Weights defined in
`benchmark-config.yaml` under `scoring.weights`. Time and token usage
apply small negative penalties to reward efficiency.
