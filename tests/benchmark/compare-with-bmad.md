# Cognitive OS vs BMAD METHOD v6 -- Comparison Guide

## Overview

This document guides manual comparison between Cognitive OS and BMAD METHOD v6
on the same 5 standardized benchmark tasks.

## Prerequisites

- Claude CLI installed (`claude` command available)
- BMAD v6 cloned at `bmad-method/` in project root
- `yq` and `jq` installed (`brew install yq jq`)

## Running Benchmarks

### Step 1: Run Cognitive OS benchmarks

```bash
bash .cognitive-os/tests/benchmark/run-benchmark.sh --system cognitive-os
```

### Step 2: Run BMAD benchmarks

```bash
bash .cognitive-os/tests/benchmark/run-benchmark.sh --system bmad
```

The BMAD run wraps each prompt with BMAD context instructions so Claude
operates under BMAD conventions instead of Cognitive OS rules.

### Step 3: Run a single task (optional)

```bash
# Cognitive OS - single task
bash .cognitive-os/tests/benchmark/run-benchmark.sh --system cognitive-os --task create-go-service

# BMAD - single task
bash .cognitive-os/tests/benchmark/run-benchmark.sh --system bmad --task create-go-service
```

## Side-by-Side Comparison Table

Fill in after running both systems:

| Metric | Cognitive OS | BMAD v6 | Winner |
|--------|----------|---------|--------|
| **Task 1: Create Go Service** | | | |
| Time (seconds) | | | |
| Tokens used | | | |
| Files created | | | |
| Tests created | | | |
| Compiles | | | |
| Architecture score (/10) | | | |
| **Task 2: Fix Bug** | | | |
| Time (seconds) | | | |
| Bug fixed | | | |
| Test added | | | |
| No regressions | | | |
| **Task 3: Add Endpoint** | | | |
| Time (seconds) | | | |
| Endpoint works | | | |
| Follows patterns (/10) | | | |
| Test added | | | |
| **Task 4: Refactor Code** | | | |
| Time (seconds) | | | |
| Logic moved | | | |
| Tests pass | | | |
| Architecture improved (/10) | | | |
| **Task 5: Cross-Service** | | | |
| Time (seconds) | | | |
| Services touched | | | |
| Kafka event added | | | |
| All compile | | | |
| Integration test | | | |
| **Totals** | | | |
| Total time | | | |
| Total tokens | | | |
| Overall score (/50) | | | |
| Estimated cost | | | |

## Evaluation Criteria

### Quantitative (automated)
- **Time**: Wall-clock seconds from start to finish
- **Tokens**: Total input + output tokens consumed
- **Files/Tests**: Count of created artifacts
- **Compilation**: Does the code build without errors

### Qualitative (LLM-evaluated, 0-10 scale)
- **Architecture score**: Clean architecture compliance
- **Follows patterns**: Consistency with existing codebase patterns
- **Architecture improved**: Quality of refactoring outcome

### Scoring Formula
Each boolean metric worth its configured weight (see benchmark-config.yaml).
LLM scores normalized to their weight range. Time and token penalties applied.

## Key Differences to Watch

| Dimension | Cognitive OS | BMAD v6 |
|-----------|----------|---------|
| Planning overhead | Rules + skills auto-loaded | Persona-driven planning phase |
| Code generation | Direct execution | Story-driven with acceptance criteria |
| Architecture guidance | Go-specific rules in .cognitive-os/rules/ | Generic clean architecture patterns |
| Context usage | Engram memory + skill registry | Document-based knowledge |
| Quality gates | Constitutional gates enforced | Checklist-based verification |

## Interpreting Results

- **Cognitive OS wins on time**: Rules reduce planning overhead
- **BMAD wins on time**: Structured planning prevents rework
- **Cognitive OS wins on architecture**: Domain-specific rules guide output
- **BMAD wins on architecture**: Explicit architecture phase catches issues early
- **Tie**: Both systems comparable -- focus on cost efficiency

## Notes

- Run benchmarks on the same machine, same model, same time of day for fairness
- Network latency to Claude API affects timing -- run multiple times and average
- LLM evaluation scores have variance -- run evaluations 3 times and average
- Record the exact model version used (it matters for reproducibility)
