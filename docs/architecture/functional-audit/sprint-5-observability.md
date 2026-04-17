# Sprint 5 — Capa-4 Observability

> **Capa-3** answers “what EXISTS and is FUNCTIONAL” (static scorecards).
> **Capa-4** answers “what is actually USED” (runtime telemetry).

This sprint adds a minimal, file-based runtime telemetry layer so that after
some real usage we can answer questions like:

- Of the ~120 skills exposed under `.claude/skills/`, which are actually
  invoked?
- Which hooks fire most often? Which never fire at all?
- What is the token-efficiency gain from skills versus the token cost of hook
  infrastructure?
- How are agent launches distributed across models (opus / sonnet / haiku /
  local / free)?
- How often do we hit rate-limit events and what queue depth do we observe?

All data is stored under `.cognitive-os/metrics/` as append-only JSONL. No
external database, no daemon, no network. Telemetry is best-effort — failures
are swallowed, never propagated to the caller.

## Architecture

```
 ┌─────────────────────────────────────────────────────────────┐
 │ Recorders (fire-and-forget writers)                         │
 │                                                             │
 │  lib/telemetry.py                                           │
 │   ├─ record_skill_invocation   → skill-usage.jsonl          │
 │   ├─ record_hook_fired         → hook-usage.jsonl           │
 │   ├─ record_agent_launch       → agent-launches.jsonl       │
 │   └─ record_rate_limit_event   → rate-limit-events.jsonl    │
 │                                                             │
 │  hooks/skill-usage-tracker.sh (PostToolUse Skill)           │
 │   └─ calls record_skill_invocation()                        │
 └─────────────────────────────────────────────────────────────┘
                │ (append-only JSONL, auto-rotated at 10 MB)
                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ Aggregators (read-only scanners)                            │
 │                                                             │
 │  scripts/cos-usage-report.sh   (heatmap + efficiency)       │
 │  scripts/cos-ghost-skills.sh   (zero-invocation skills)     │
 └─────────────────────────────────────────────────────────────┘
```

### Files on disk

| File | Producer | Consumer |
|------|----------|----------|
| `.cognitive-os/metrics/skill-usage.jsonl`    | `record_skill_invocation`, `hooks/skill-usage-tracker.sh` | `cos-usage-report`, `cos-ghost-skills` |
| `.cognitive-os/metrics/hook-usage.jsonl`     | `record_hook_fired` (future hook integration)             | `cos-usage-report` |
| `.cognitive-os/metrics/agent-launches.jsonl` | `record_agent_launch` (orchestrator / cost-tracker hook)  | `cos-usage-report` |
| `.cognitive-os/metrics/rate-limit-events.jsonl` | `record_rate_limit_event` (rate-limiting layer)        | `cos-usage-report` |

All files use the same envelope: one JSON object per line, with at minimum an
`event` tag, a `timestamp` (UTC, ISO-8601, trailing `Z`), and an identifying
`name` / `type`. Additional fields depend on the event.

### Rotation

The recorder checks file size before each append. When the current file
exceeds `COS_TELEMETRY_MAX_BYTES` (10 MB default), it is renamed to
`<stem>.<UTC-timestamp>.jsonl` and a fresh file is started. Rotated siblings
are scanned transparently by `iter_records()`, so aggregators do not need to
know about rotation at all.

## Usage

### Record events from Python

```python
from lib.telemetry import (
    record_skill_invocation,
    record_hook_fired,
    record_agent_launch,
    record_rate_limit_event,
)

record_skill_invocation("compose-prompt", duration_ms=42, tokens_estimated=1200)
record_hook_fired("adaptive-bypass", event_type="PreToolUse",
                  duration_ms=15, decision="warn")
record_agent_launch("Refactor handler", model="sonnet",
                    tokens_in=1200, tokens_out=3400, cost_estimated=0.07)
record_rate_limit_event("throttled", queue_depth=5, delay_s=1.5)
```

All arguments beyond the first are optional. An `extra` dict is accepted to
carry context (session id, sprint id, etc.).

### Read the heatmap

```bash
# Pretty text, last 7 days.
bash scripts/cos-usage-report.sh

# JSON, last 14 days, with efficiency section.
bash scripts/cos-usage-report.sh --days 14 --efficiency --json
```

Output sections:

- **Top 10 skills** — `skill_counter.most_common(10)` over the window
- **Top 10 hooks** — same, over hook firings
- **Ghost skills** — exposed under `.claude/skills/` but never invoked in the
  window (candidates for archive)
- **Agent cost per model** — grouped by `model`, sums `cost_estimated` and
  raw token counts
- **Rate-limit histogram** — counts by `type`
- **Efficiency (optional)** — net tokens saved vs spent (see below)

### Efficiency metric

Skills save tokens (they replace inline canon). Hooks cost tokens (they inject
context). The net is a first-order approximation:

```
tokens_saved = Σ per_skill_saving(name) × invocation_count(name)
tokens_spent = Σ PER_HOOK_COST × hook_firing_count(name)
net_tokens   = tokens_saved − tokens_spent
```

Default heuristics (tunable — see `scripts/cos-usage-report.sh`):

- `compose-prompt`: ~1150 tokens saved per invocation (inline canon ~1200
  versus template reference ~50)
- Every other skill: ~200 tokens saved per invocation (generic bound)
- Every hook firing: ~50 tokens cost (generic measured-duration × token-rate)

These are approximations. They become more accurate as we collect real
observations and can be refined per-skill and per-hook.

### Detect ghost skills

```bash
bash scripts/cos-ghost-skills.sh             # 30-day window, pretty text
bash scripts/cos-ghost-skills.sh --days 14   # shorter window
bash scripts/cos-ghost-skills.sh --json      # JSON for scripting
```

Ghosts are the set `exposed(skills) − invoked(skills, window)`. Feed the list
into the next cleanup sprint to archive or de-expose unused skills.

## Hook integration

`hooks/skill-usage-tracker.sh` is written but **not registered** in
`.claude/settings.json` yet. Registration is UX8’s responsibility — this
sprint only creates the artifact.

Registration target (to be added by `apply-efficiency-profile.sh` default
tier):

```json
{
  "event":   "PostToolUse",
  "matcher": "Skill",
  "hooks": [
    { "type":    "command",
      "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/skill-usage-tracker.sh\"" }
  ]
}
```

The tracker is designed to be **fire-and-forget**: it spawns a background
subshell and exits immediately, so it can never delay a tool call or inject
content into the model’s context. All work (stdin parse, Python handoff) runs
asynchronously in the backgrounded subshell.

## Testing

Unit / behavior tests live in `tests/behavior/test_telemetry.py`:

- `record_*` smoke tests (one per public function)
- Extra-field propagation
- Rotation threshold (`COS_TELEMETRY_MAX_BYTES=512`, write many records,
  assert rename happened)
- `iter_records` merges rotated siblings
- Corrupt-line tolerance
- Read-only metrics dir does not raise
- Aggregation grouping by `model`

Run them with:

```bash
python3 -m pytest tests/behavior/test_telemetry.py -v
```

## Acceptance criteria (sprint brief)

```bash
# 1. Telemetry module importable
python3 -c "from lib.telemetry import record_skill_invocation, record_hook_fired; print('OK')"

# 2. Hook tracker is valid bash
bash -n hooks/skill-usage-tracker.sh

# 3. Usage report runs
bash scripts/cos-usage-report.sh --help 2>&1 | grep -iE "usage|report"

# 4. Ghost detection script
bash scripts/cos-ghost-skills.sh 2>&1 | tail -5

# 5. Tests pass
python3 -m pytest tests/behavior/test_telemetry.py -v

# 6. Metrics file created on first invocation
python3 -c "from lib.telemetry import record_skill_invocation; record_skill_invocation('test', 100, 50)"
test -f .cognitive-os/metrics/skill-usage.jsonl
```

## Follow-ups / known gaps

- **Hook registration**: UX8 must add `skill-usage-tracker.sh` to the default
  profile in `apply-efficiency-profile.sh`. Until then, no skill invocations
  will be captured live — manual `record_skill_invocation()` calls are the
  only source.
- **Agent launches / rate-limit events**: the recorders exist, but no
  producer currently calls them automatically. The orchestrator (or a future
  `agent-launch-tracker.sh` hook) should wire these in.
- **Efficiency heuristics**: the per-skill token-saving map is currently
  coarse. Once we have real telemetry, we can measure per-skill overhead
  directly and replace the constants.
- **Retention**: rotation keeps all historic data. A future sweeper can
  compress or prune files older than N days.

## Related documents

- [scorecard-skills.md](scorecard-skills.md) — static catalog of skills
- [scorecard-hooks.md](scorecard-hooks.md) — static catalog of hooks
- [ux6-idempotent-update.md](ux6-idempotent-update.md) — update pipeline
- `rules/token-economy.md` — cost-awareness rules that motivate this sprint
