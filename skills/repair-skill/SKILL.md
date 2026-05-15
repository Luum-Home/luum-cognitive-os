---
name: repair-skill
description: 'Use when you need this Cognitive OS skill: Drain the skill repair queue
  and propose regeneration or deprecation for degraded skills; do not use when a narrower
  skill directly matches the task.'
trigger: repair skill, repair-skill, drain repair queue, fix failing skill, skill
  repair
model: sonnet
effort: sonnet
audience: os
version: 1.0.0
platforms:
- claude-code
prerequisites:
  commands:
  - python3
  - jq
routing_patterns:
- pattern: \brepair[- ]?skill\b
  confidence: 0.95
- pattern: \bdrain\s+skill\s+repair\s+queue\b
  confidence: 0.85
- pattern: \bdegraded\s+skills?\s+(repair|fix)\b
  confidence: 0.75
summary_line: Drain the skill repair queue and propose regeneration or deprecation
  for degraded skills.
routing_intents:
- intent: repair_skill_request
  description: User asks to drain the skill repair queue and propose regeneration
    or deprecation for degraded skills.
  confidence: 0.85
triggers:
- repair-skill
- /repair-skill
- Repair Skill
- Drain the skill repair queue and propose regeneration or deprecation for degraded
  skills
---
<!-- SCOPE: os-only -->
# Repair Skill

Read the next pending entry from `skill-repair-queue.jsonl` and take the
appropriate gated action: propose regeneration (via `/add-skill` or
`/skill-creator`), flag for investigation, or recommend deprecation.

This is the **gated consumer** for signals emitted by `hooks/skill-failure-monitor.sh`.
Auto-regeneration is intentionally NOT automatic — see ADR-089 for rationale
(cost gate + runaway-loop prevention).

## Protocol

### Step 0 — Locate the repair queue

```bash
METRICS_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}/.cognitive-os/metrics"
QUEUE="$METRICS_DIR/skill-repair-queue.jsonl"
```

If the queue file does not exist or is empty, report "No pending skill repairs"
and stop.

### Step 1 — Read the oldest pending entry

```python
import json
from pathlib import Path

queue = Path("$QUEUE")
lines = [l for l in queue.read_text().splitlines() if l.strip()]
pending = [json.loads(l) for l in lines if json.loads(l).get("status") == "pending"]
if not pending:
    print("No pending entries.")
else:
    entry = pending[0]   # oldest first
    print(json.dumps(entry, indent=2))
```

### Step 2 — Act based on `suggested_action`

| `suggested_action` | Action |
|-|-|
| `regenerate` | Run `/add-skill {skill_name}` or `/skill-creator` to regenerate the skill. Pass the `sample_errors` as context so the creator knows what went wrong. |
| `investigate` | Open `skills/{skill_name}/SKILL.md` (if it exists) and the last 3 entries from `skill-feedback.jsonl` for `{skill_name}`. Report findings. Ask the user if they want to regenerate or deprecate. |
| `deprecate` | Confirm with the user. If confirmed, move `skills/{skill_name}/` to `skills/_archived/{skill_name}-deprecated-YYYY-MM-DD/`. |

### Step 2.5 — Regeneration classification gate

If the action regenerates or replaces a skill, the regenerated artifact must pass
`/primitive-authoring` and the exact-path classifier gate before the queue item is
marked done:

```bash
python3 scripts/primitive_scope_classifier.py \
  --project-dir . \
  --paths skills/{skill_name}/SKILL.md \
  --fail-contradictions \
  --fail-low-confidence
```

Update consumer availability, behavior evidence, and paired portability proof if
the repair changes runtime surface or `SCOPE: both` semantics.

### Step 3 — Mark the entry as processed

After taking action, update the queue entry's `status` from `"pending"` to
`"done"` (or `"skipped"` if the user declined):

```python
import json
from pathlib import Path
from datetime import datetime, timezone

queue = Path("$QUEUE")
lines = queue.read_text().splitlines()
updated = []
found = False
for line in lines:
    if not line.strip():
        continue
    rec = json.loads(line)
    if not found and rec.get("status") == "pending" and rec.get("skill") == "{skill_name}":
        rec["status"] = "done"
        rec["resolved_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        found = True
    updated.append(json.dumps(rec))
queue.write_text("\n".join(updated) + "\n")
```

### Step 4 — Report

Output a brief summary:
- Skill name
- Action taken
- Number of remaining pending entries in queue

## Relationship to other skills

- `/optimize-skill` — improves a skill's prompt quality; use when `suggested_action` is
  `investigate` and the skill is fundamentally sound but underperforming.
- `/skill-creator` — creates a new skill from scratch; use when `suggested_action` is
  `regenerate` and the existing skill file is corrupt or missing.
- `/add-skill` — adds a skill from a template; alternative to `/skill-creator` for
  simpler cases.
- `hooks/skill-failure-monitor.sh` — emits entries to this queue at session end.
- `ADR-089` — explains the two-step signal/action design and why direct auto-regen was
  rejected.

## ACCEPTANCE CRITERIA

- `skill-repair-queue.jsonl` has at least one `pending` entry before running.
- After running, that entry's status is `"done"` or `"skipped"`.
- The skill named in the entry has been regenerated, investigated, or deprecated
  per the `suggested_action`.
- A summary is printed showing skill name, action taken, remaining queue depth.
