# Competitive Arena — Documentation

## Overview

The Cognitive OS Competitive Arena is a benchmark suite that compares our Cognitive OS against 10+ AI coding tools across standardized tasks. It measures quality, speed, cost, and completeness to identify strengths, weaknesses, and improvement opportunities.

## Architecture

```
.cognitive-os/tests/arena/
  arena-config.yaml          # All competitors, tasks, scoring config
  run-arena.sh               # Shell runner (worktree isolation, metrics)
  arena-report-template.md   # Report template with placeholders

.cognitive-os/skills/arena/
  SKILL.md                   # /arena skill definition

.cognitive-os/metrics/arena/
  arena-results-{date}.jsonl # Raw results (one JSON per line)
  arena-report-{date}.md     # Generated markdown report
  output-{comp}-{task}-{date}.log # Raw output from each run
```

## Quick Start

```bash
# List all competitors and tasks
/arena --list

# Run full benchmark
/arena

# Run single competitor on single task
/arena --competitor cognitive-os --task create-go-service

# Dry run (no execution)
/arena --dry-run

# Generate report from existing results
/arena --report
```

## Competitors

### Currently Configured (13 total)

| ID | Name | Type | Automatable |
|----|------|------|-------------|
| cognitive-os | Cognitive OS | native | Yes |
| bmad | BMAD METHOD v6 | clone | Partial |
| aider | Aider | cli | Yes |
| codex | Codex CLI (OpenAI) | cli | Yes |
| goose | Goose (Block) | cli | Yes |
| opencode | OpenCode (Anthropic) | cli | Yes |
| openhands | OpenHands | docker | Yes (Docker) |
| metagpt | MetaGPT | python | Yes |
| kiro | Kiro (AWS) | ide | No (manual) |
| cursor | Cursor | ide | No (manual) |
| windsurf | Windsurf | ide | No (manual) |
| spec-kit | Spec Kit | cli | Yes |
| claude-code | Claude Code (vanilla) | cli | Yes |

### How to Add a New Competitor

1. Edit `.cognitive-os/tests/arena/arena-config.yaml`
2. Add an entry under `arena.competitors`:

```yaml
- id: new-tool
  name: "New Tool Name"
  type: cli          # cli | docker | ide | clone | python | native
  command: "newtool"  # CLI command name
  install: "npm i -g newtool"
  requires: ["API_KEY_NAME"]
  installed: false
  notes: "Brief description"
```

3. If CLI-based, add a runner case in `run-arena.sh` under the `cli)` section:

```bash
new-tool)
    timeout "${task_timeout}s" newtool run "$task_prompt" \
        > "$output_file" 2>&1 || exit_code=$?
    ;;
```

4. If IDE-based, mark as `type: ide` — it will be flagged for manual benchmarking.

## Tasks

### Currently Configured (10 tasks)

| ID | Category | Difficulty | What it Tests |
|----|----------|------------|---------------|
| create-go-service | greenfield | hard | Full service creation from scratch |
| fix-known-bug | bugfix | easy | Bug diagnosis and fix with tests |
| add-endpoint | feature | medium | Adding to existing service |
| refactor | refactor | hard | Architecture improvement |
| cross-service | integration | hard | Multi-service feature |
| debug-issue | debugging | medium | Production issue diagnosis |
| write-tests | testing | medium | Comprehensive test writing |
| spec-planning | planning | medium | Technical planning (no code) |
| codebase-qa | analysis | easy | Codebase understanding |
| documentation | docs | easy | API documentation generation |

### How to Add a New Task

1. Edit `.cognitive-os/tests/arena/arena-config.yaml`
2. Add an entry under `arena.tasks`:

```yaml
- id: my-new-task
  name: "Human-Readable Task Name"
  category: feature    # greenfield|bugfix|feature|refactor|integration|debugging|testing|planning|analysis|docs
  difficulty: medium   # easy|medium|hard
  prompt: |
    Detailed instructions for the AI agent.
    Be specific about requirements.
    Include expected outputs.
  timeout: 180         # seconds
  metrics: [files_created, tests_created, compiles, time_seconds, tokens_used]
  evaluation:
    key_check: "How to verify this metric"
```

3. The task will automatically be included for all competitors.

## Scoring Methodology

### Weights

| Dimension | Weight | How Measured |
|-----------|--------|-------------|
| Quality | 35% | LLM evaluation against architecture patterns and rubric |
| Completeness | 25% | Requirements checklist: all deliverables present |
| Speed | 20% | Wall-clock time, normalized against fastest |
| Cost | 20% | Output size as proxy for token usage |

### Quality Rubric (0-10)

| Score | Meaning |
|-------|---------|
| 10 | Perfect: follows all patterns, clean code, proper error handling |
| 8 | Good: minor deviations, works correctly |
| 6 | Acceptable: works but some pattern violations |
| 4 | Poor: works but significant issues |
| 2 | Broken: does not compile or has major bugs |
| 0 | Failed: no meaningful output |

### Speed Scoring

Normalized to the fastest competitor per task:

```
speed_score = (fastest_time / competitor_time) * 10
```

### Cost Scoring

Normalized to the smallest output per task (output bytes as proxy for tokens):

```
cost_score = (smallest_output / competitor_output) * 10
```

### Final Score

```
total = (quality * 0.35) + (completeness * 0.25) + (speed * 0.20) + (cost * 0.20)
```

## Interpreting Results

### JSONL Format

Each line in the results file is a JSON object:

```json
{
  "competitor": "cognitive-os",
  "task": "create-go-service",
  "status": "completed",
  "timestamp": "20260322-143000",
  "metrics": {
    "time_seconds": 45,
    "exit_code": 0,
    "files_changed": 12,
    "files_created": 8,
    "tests_created": 3,
    "compiles": "true",
    "output_bytes": 15234
  }
}
```

### Status Values

| Status | Meaning |
|--------|---------|
| completed | Ran to completion |
| timeout | Exceeded timeout |
| error | Non-zero exit code |
| skipped | Not installed or not automatable |

### Report Sections

The generated report includes:
- Per-task comparison table (all competitors side by side)
- Overall scores with weighted totals
- Radar chart data for visualization
- Category breakdown (which tools excel at what)
- Strengths/weaknesses analysis
- Improvement recommendations

## Isolation

Each benchmark run uses a **git worktree** to ensure competitors work on isolated copies of the codebase. This prevents one competitor's changes from affecting another's results.

Worktrees are created in `.arena-worktrees/` and cleaned up after each run.

## Limitations

1. **IDE tools** (Cursor, Windsurf, Kiro) cannot be automated — require manual benchmarking
2. **Token counting** is approximate (output size proxy) since most tools do not report tokens
3. **Quality scoring** requires LLM evaluation (`/arena --evaluate`) which costs tokens
4. **Docker competitors** require Docker to be running
5. **API keys** must be configured for each competitor's provider

## Tips

- Start with `--dry-run` to verify your setup
- Use `--competitor cognitive-os --task create-go-service` for quick single comparisons
- Run `/arena --evaluate` after benchmark to get quality scores
- Compare reports over time to track Cognitive OS improvements
- Add custom tasks relevant to your specific codebase patterns
