---
name: arena
description: Run competitive benchmarks comparing Cognitive OS against other AI coding
  tools
invoke: /arena
version: '1.0'
routing_intents:
- "run competitive coding agent benchmarks against external tools"
- "compare Cognitive OS against other agent tools"
- "benchmark an external AI coding competitor"
- "generate arena benchmark results with reproducible comparison data"
- "evaluate benchmark runs against competitor agent systems"

triggers:
- manual
args:
- name: competitor
  description: Filter to a specific competitor ID
  required: false
- name: task
  description: Filter to a specific task ID
  required: false
- name: list
  description: List all competitors and tasks
  flag: true
- name: dry-run
  description: Show what would run without executing
  flag: true
- name: evaluate
  description: LLM-evaluate quality of existing results
  flag: true
- name: report
  description: Generate report from latest results
  flag: true
audience: os-dev
summary_line: '"Run competitive benchmarks comparing Cognitive OS against other AI
  coding…'
platforms:
- claude-code
prerequisites: []
---
<!-- SCOPE: both -->
# Arena — Competitive Benchmark Skill

## Purpose

Run standardized benchmarks comparing Cognitive OS against 10+ AI coding competitors.
Measures quality, speed, cost, and completeness across 10 task categories.

## Usage

```
/arena                                    # Run full benchmark (all competitors, all tasks)
/arena --competitor cognitive-os              # Run only Cognitive OS
/arena --task create-go-service           # Run only one task
/arena --competitor bmad --task fix-bug   # Specific competitor + task
/arena --list                            # List all competitors and tasks
/arena --dry-run                         # Preview without executing
/arena --evaluate                        # LLM-evaluate existing results
/arena --report                          # Generate report from latest results
```

## Execution Protocol

### Step 1: Parse Arguments

Extract `--competitor`, `--task`, `--list`, `--dry-run`, `--evaluate`, `--report` from args.

### Step 2: Route Action

**If `--list`:**
1. Read `.cognitive-os/tests/arena/arena-config.yaml`
2. Display competitors table: ID, Name, Type, Installed, Requires
3. Display tasks table: ID, Name, Category, Difficulty, Timeout
4. STOP

**If `--dry-run`:**
1. Show which competitor/task combinations would run
2. Show estimated total time
3. STOP

**If `--evaluate`:**
1. Find latest results in `.cognitive-os/metrics/arena/`
2. For each completed run, read the output log
3. Score quality (0-10) and completeness (0-10) using rubrics from config
4. Update the results JSONL with scores
5. STOP

**If `--report`:**
1. Find latest results in `.cognitive-os/metrics/arena/`
2. Generate markdown report using template
3. STOP

**Otherwise (run benchmark):**
1. Execute `tests/arena/run-arena.sh` with appropriate flags
2. Collect results
3. Report summary inline

### Step 3: Run Benchmark

For the shell-based runner:

```bash
tests/arena/run-arena.sh \
  ${COMPETITOR:+--competitor $COMPETITOR} \
  ${TASK:+--task $TASK}
```

For competitors not automatable via shell (IDE-based tools, manual runners):

1. Inform the user which competitors require manual benchmarking
2. Provide the exact prompt to use
3. Ask user to report time and results
4. Record manually-reported data

### Step 4: Report Results

Display inline summary:

```
=== Arena Results ===

Task: Create Go Microservice
┌─────────────┬────────┬───────┬───────┬──────────┐
│ Competitor   │ Status │ Time  │ Files │ Quality  │
├─────────────┼────────┼───────┼───────┼──────────┤
│ Cognitive OS     │ done   │  45s  │  12   │ 9/10     │
│ Aider        │ done   │  62s  │   8   │ 7/10     │
│ Codex CLI    │ done   │  38s  │  10   │ 6/10     │
│ Cursor       │ skip   │   —   │   —   │  —       │
└─────────────┴────────┴───────┴───────┴──────────┘
```

### Step 5: Save Metrics

Results saved to `.cognitive-os/metrics/arena/arena-results-{date}.jsonl`
Report saved to `.cognitive-os/metrics/arena/arena-report-{date}.md`

## Configuration

All competitors, tasks, and scoring defined in:
`.cognitive-os/tests/arena/arena-config.yaml`

## Adding New Competitors

1. Add entry to `arena.competitors[]` in config
2. If CLI-based, add runner case in `tests/arena/run-arena.sh`
3. If IDE-based, mark as `type: ide` (manual benchmark only)

## Adding New Tasks

1. Add entry to `arena.tasks[]` in config
2. Define prompt, timeout, metrics, and evaluation criteria
3. Tasks apply to ALL competitors

## Scoring

| Weight | Metric |
|--------|--------|
| 35% | Quality — architecture patterns, code correctness, error handling |
| 25% | Completeness — all requirements met, tests included |
| 20% | Speed — time to complete |
| 20% | Cost — tokens/output size as proxy |

Quality and completeness scored 0-10 via LLM evaluation.
Speed and cost scored relative to the fastest/cheapest competitor.

## Dependencies

- `yq` — YAML parser (for shell runner)
- `jq` — JSON processor
- `git` — for worktree isolation
- Competitor CLIs must be installed and configured
