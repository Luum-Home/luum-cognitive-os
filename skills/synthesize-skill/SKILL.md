<!-- SCOPE: os-only -->
---
name: synthesize-skill
description: Review the skill synthesis queue, list proposed drafts, and accept/reject/defer promotion candidates
trigger: synthesize skill, synthesize-skill, skill synthesis, review synthesis queue, skill proposals, experimental skills
model: sonnet
effort: sonnet
audience: project
version: "1.0.0"
platforms: ["claude-code"]
prerequisites:
  commands: [python3, jq]
routing_patterns:
  - pattern: '\bsynthesize[- ]?skill\b'
    confidence: 0.95
  - pattern: '\bskill\s+synthesis\s+queue\b'
    confidence: 0.85
  - pattern: '\bpromote\s+skill\s+candidate\b'
    confidence: 0.75
---

# Synthesize Skill

Drain and review the skill synthesis queue produced by `hooks/skill-synthesis-scanner.sh`.
For each proposed experimental skill, offer accept / reject / defer. For auto-promotion
candidates, confirm or skip promotion.

This is the **gated consumer** for signals emitted by the skill synthesizer. Skill movement
from `skills/experimental/` to `skills/` is NEVER automatic — it requires operator confirmation
here. See ADR-095 for rationale.

## Protocol

### Step 0 — Check the synthesis queue

```bash
METRICS_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}/.cognitive-os/metrics"
QUEUE="$METRICS_DIR/skill-synthesis-queue.jsonl"
EXPERIMENTAL="$CLAUDE_PROJECT_DIR/skills/experimental"
```

If the queue file does not exist or has no `"status": "proposed"` entries, report
"No pending skill synthesis proposals" and stop.

### Step 1 — List proposed skills

```python
import json
from pathlib import Path

queue = Path("$QUEUE")
if not queue.exists():
    print("Queue empty — run /skill-synthesis-scanner or wait for Stop hook.")
    exit()

lines = [l for l in queue.read_text().splitlines() if l.strip()]
records = [json.loads(l) for l in lines]
proposed = [r for r in records if r.get("status") == "proposed"]
candidates = [r for r in records if r.get("status") == "promotion-eligible"]

print(f"Proposed drafts: {len(proposed)}")
for r in proposed:
    print(f"  - {r['signature']}  (occurrences: {r['occurrences']}, sessions: {r['session_count']})")
    print(f"    Draft: {r['draft_path']}")

print(f"\nPromotion-eligible: {len(candidates)}")
for r in candidates:
    print(f"  - {r['draft_path']}")
```

### Step 2 — Review each proposed draft

For each proposed entry:
1. Show the user the draft SKILL.md content: `cat <draft_path>`
2. Ask: **Accept** (promote now), **Reject** (delete draft), or **Defer** (leave for later).

### Step 3 — Act on operator decision

| Decision | Action |
|----------|--------|
| **Accept** | `mv skills/experimental/<name>/ skills/<name>/` then `git add skills/<name>/` |
| **Reject** | `rm -rf skills/experimental/<name>/` |
| **Defer** | No action. Leave draft in `skills/experimental/`. |

Update the queue record status accordingly:

```python
# Mark entry as acted-on (append new status record)
import json, datetime
new_record = {
    "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "signature": entry["signature"],
    "draft_path": entry["draft_path"],
    "status": "accepted",   # or "rejected" / "deferred"
}
with open("$QUEUE", "a") as fh:
    fh.write(json.dumps(new_record) + "\n")
```

### Step 4 — Promotion-eligible candidates

For each `"status": "promotion-eligible"` entry, ask the operator if they want to
promote. Eligible means the experimental skill received ≥ 5 successful invocations
from `skill-feedback.jsonl`.

If operator confirms:
```bash
mv skills/experimental/<name>/ skills/<name>/
git add skills/<name>/
git commit -m "feat(skills): promote experimental skill <name> (ADR-095)"
```

### Step 5 — On-demand synthesis trigger

If the operator wants to force a scan without waiting for the Stop event:

```bash
python3 - <<'EOF'
import sys, json
from pathlib import Path
sys.path.insert(0, "${CLAUDE_PROJECT_DIR}")
from lib.skill_synthesizer import find_recurring_sequences, propose_skill_draft

seq = find_recurring_sequences(
    Path(".cognitive-os/metrics/tool-sequences.jsonl"),
    min_length=3, min_occurrences=3, window_days=7,
)
print(f"Found {len(seq)} recurring sequences")
for s in seq:
    draft = propose_skill_draft(s, Path("skills/experimental"))
    print(f"  Draft: {draft}")
EOF
```

## Notes

- `skills/experimental/` is git-tracked. Commit drafts after accepting to avoid
  them being swept by session-cleanup.
- Auto-promotion NEVER happens without this operator skill confirming it.
- Maximum recommended experimental catalog size: 30 skills. Prune zero-usage
  drafts older than 30 days periodically.
