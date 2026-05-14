<!-- SCOPE: os-only -->
---
name: simulation-arena
description: Run scripted end-to-end agent workflow simulations to validate safety mesh, measure OS evolution (cost/speed/quality), and regression-test after hook/rule/skill changes.
summary_line: End-to-end agent workflow simulation for safety-mesh regression.
version: 1.0.0
last-updated: 2026-03-27
auto-generated: false
tech: python
triggers:
  - simulation
  - arena
  - simulate scenario
  - agent simulation
  - evolution test
audience: os-dev
platforms: ["claude-code"]
prerequisites: []
---

# Simulation Arena — End-to-End Agent Workflow Simulation

## Purpose

Runs scripted scenarios that simulate real developer workflows end-to-end. Each scenario is a sequence of "turns" (user messages + expected OS behaviors). The arena measures which safety layers activated, total cost, time taken, quality of output, and whether the OS "learned" (memory, calibration, archive).

Running the SAME scenario twice should show improvement (cheaper, faster, fewer retries).

## Invoke

```
/simulate <scenario-name> [--dry-run]
```

## When to Use

- To validate that the safety mesh responds correctly to different prompt types
- To measure OS evolution: does the system get cheaper and faster over time?
- To regression-test after changes to hooks, rules, or skills
- To preview what the OS would do for a scenario without executing (--dry-run)

## Steps

1. **Load scenario** from `tests/arena/scenarios/<name>.yaml`
2. **Validate** scenario structure (required fields, valid turn types)
3. **Run each turn**, measuring OS response:
   - USER_MESSAGE: score clarification gate, blast radius, SDD suggestion, planning poker, cost
   - EXPECTED_BEHAVIOR: verify expectations against simulated OS state
   - CHECKPOINT: measure cumulative metrics
   - DELAY: simulate time passing (for memory/learning tests)
4. **Compare with previous runs** of the same scenario
5. **Generate evolution report** with improvement metrics
6. **Save results** to `.cognitive-os/metrics/arena-results/arena-results.jsonl`

## Scenario Format

Scenarios are YAML files in `tests/arena/scenarios/`:

```yaml
name: "Scenario Name"
description: "What this tests"
category: feature|bugfix|research|refactor
expected_total_cost: 3.00
expected_duration_minutes: 30
tags: [sdd, safety-mesh, memory]

turns:
  - type: user|expect|checkpoint|delay
    content: "Message or description"
    expectations:
      clarification_gate_activates: true
      blast_radius: "LOW"
      cost_under: 0.50
```

## Available Expectations

### For USER_MESSAGE turns:
- `clarification_gate_activates`: true/false
- `clarification_gate_passes`: true/false
- `blast_radius`: LOW/MEDIUM/HIGH/CRITICAL
- `sdd_pipeline_suggested`: true/false
- `planning_poker_runs`: true/false
- `cost_prediction_shown`: true/false
- `memory_search_first`: true/false
- `memory_hit`: true/false
- `cost_lower_than_first`: true/false
- `deep_research_skill`: true/false

### For EXPECTED_BEHAVIOR turns:
- `phase`: explore/propose/spec/design/tasks/apply/verify
- `files_analyzed`: true/false
- `proposal_created`: true/false
- `files_modified_max`: int
- `files_deleted`: int

### For CHECKPOINT turns:
- `cost_under`: float (USD threshold)
- `memory_saved`: true/false
- `trust_score_above`: float (0.0-1.0)

## Output

The arena produces:
1. **Turn-by-turn report** showing which expectations passed/failed
2. **Metrics summary** (cost, duration, pass rate, safety activations)
3. **Evolution comparison** with previous runs (cost/speed/quality deltas)
4. **ASCII evolution chart** showing improvement trends over multiple runs

## Library

`lib/simulation_arena.py` — all logic. Key classes:
- `SimulationArena`: main runner
- `Scenario` / `Turn`: scenario data model
- `ScenarioResult` / `TurnResult`: results data model

## Typical Cost

$0.00 — simulation runs locally without LLM calls.
