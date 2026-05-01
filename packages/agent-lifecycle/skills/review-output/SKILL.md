<!-- SCOPE: os-only -->
---
name: review-output
description: "Manually trigger review of a specific past sub-agent output or the most recent N outputs. Bypasses sample-rate gate but respects the daily budget cap. Produces review findings in Engram and .cognitive-os/metrics/review-findings.jsonl."
version: 0.1.0
user-invocable: true
auto-generated: false
last-updated: 2026-05-01
audience: both
effort: sonnet
model: sonnet
tags: [review, audit, learning-loop, adr-096]
trigger: "review-output, review output, audit output, /review-output"

platforms: ["claude-code"]
prerequisites: []
---

# Review Output Skill

Manually trigger the ADR-096 review-agent audit on a specific past sub-agent
output or on the last N outputs. Useful for spot-checking high-stakes tasks,
debugging review quality, or draining a backlog of unreviewed outputs.

**This skill bypasses the stochastic sample-rate gate** but still respects the
daily budget cap (`review.max_per_day` in `cognitive-os.yaml`). When the daily
budget is exhausted the skill emits an operator notification and exits without
dispatching.

## Usage

```
/review-output --task-id <id>
/review-output --recent 5
/review-output --recent 1 --force    # bypasses budget check (operator override)
```

## Arguments

| Flag | Description |
|------|-------------|
| `--task-id <id>` | Review a specific task by its producer_id (from agent-heartbeat.jsonl or trust-scores.jsonl) |
| `--recent <n>` | Review the last N sub-agent completions in order (oldest first) |
| `--force` | Bypass the daily budget cap (operator use only; logged to audit trail) |

## Instructions

When invoked, do the following:

### Step 1 — Load target outputs

If `--task-id` was given:
```python
import json
from pathlib import Path

project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
findings_path = project_dir / ".cognitive-os/metrics/review-findings.jsonl"
trust_path    = project_dir / ".cognitive-os/metrics/trust-scores.jsonl"
heartbeat_path = project_dir / ".cognitive-os/metrics/agent-heartbeat.jsonl"

# Read the heartbeat log to find the target agent's output
records = [json.loads(l) for l in heartbeat_path.read_text().splitlines() if l.strip()]
target = [r for r in records if r.get("producer_id") == task_id or r.get("task_id") == task_id]
```

If `--recent N` was given, read the last N completed-agent records from
`.cognitive-os/metrics/agent-heartbeat.jsonl` (sorted by timestamp, most
recent last; process oldest-first).

### Step 2 — Check daily budget (unless --force)

```python
from lib.review_agent import daily_budget_state, DEFAULT_MAX_PER_DAY
from lib.config_loader import load_structured

cfg = load_structured()
max_per_day = cfg.get("review", {}).get("max_per_day", DEFAULT_MAX_PER_DAY)
budget = daily_budget_state()
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
remaining = max_per_day - budget.get(today, 0)

if remaining <= 0 and not force_flag:
    print(f"Daily review budget exhausted ({max_per_day}/day). Use --force to override.")
    exit 0
```

### Step 3 — For each target output, dispatch review

```python
from lib.review_agent import (
    select_reviewer_model, build_review_prompt,
    parse_review_response, persist_finding,
)
from lib.dispatch import dispatch

for output_record in target_outputs:
    reviewer_model = select_reviewer_model(output_record.get("model", "sonnet"))
    # Allow COS_REVIEW_MODEL env override
    reviewer_model = os.environ.get("COS_REVIEW_MODEL", reviewer_model)

    prompt = build_review_prompt(output_record, criteria=[])
    result = dispatch(
        prompt=prompt,
        providers=["qwen", "claude"],
        claude_model=reviewer_model,
        task_type="review",
        skill_name="review-output",
    )

    if result.success:
        parsed = parse_review_response(result.text)
        finding = {
            **parsed,
            "producer_id": output_record.get("producer_id", "unknown"),
            "producer_model": output_record.get("model", "unknown"),
            "reviewer_id": f"manual-review-{int(time.time())}",
            "reviewer_model": reviewer_model,
            "task_description": output_record.get("task_description", ""),
            "triggered_by": "manual /review-output",
        }
        persist_finding(finding)
        print(f"  score={parsed['score']} gaps={len(parsed['gaps'])} reviewer={reviewer_model}")
    else:
        print(f"  Review dispatch failed for {output_record.get('producer_id')}: {result.error}")
```

### Step 4 — Summary

After all reviews complete, output:

```
Review complete: N output(s) reviewed.
  Average score: <avg>/100
  Total gaps found: <count>
  Findings saved to: .cognitive-os/metrics/review-findings.jsonl
  Engram topic: review-finding/<producer_id>-<hash>

Run /analyze-improvements to act on findings.
```

## ACCEPTANCE CRITERIA

- `--task-id` reviews exactly that one output and persists a finding.
- `--recent N` reviews the last N outputs in chronological order.
- Daily budget is respected unless `--force` is provided.
- Each finding is appended to `review-findings.jsonl` AND saved to Engram.
- Output includes score, gap count, and reviewer model for each reviewed output.
- Skill exits cleanly (no Python tracebacks visible to user) on dispatch failure.
