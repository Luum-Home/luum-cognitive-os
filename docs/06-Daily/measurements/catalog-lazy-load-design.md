# Catalog Lazy-Load Design

**Status**: Live (default ON as of 2026-04-30)
**Token savings**: ~3.5K tokens per session (15,097 bytes / ~4 chars-per-token)
**Weekly savings**: ~875K tokens at 250 sessions/week

## Behavior Change

CATALOG-COMPACT.md (~3.5K tokens, 193 lines) was previously injected into
every SessionStart context unconditionally. It is now loaded **on-demand**
(lazy) when the first skill-related user prompt arrives.

Sessions that never reference skills save the full ~3.5K tokens. Sessions
that do reference skills pay the cost at the first matching prompt turn
instead of at session start.

## Mechanism

### SessionStart (hooks/session-init.sh)

When `COS_LAZY_CATALOG=1` (default), the hook emits a single-line pointer:

```
Skills catalog available (lazy): catalog injected on first skill-related prompt.
```

When `COS_LAZY_CATALOG=0` (opt-out), the full catalog content is injected
eagerly (original behavior).

### UserPromptSubmit (hooks/lazy-catalog-injector.sh)

Fires on every user prompt. Extracts the prompt text from `CLAUDE_TOOL_INPUT`
JSON, checks it against the keyword list, and if matched, outputs the full
`skills/CATALOG-COMPACT.md` content as additional context for the current turn.

Must complete in ≤50ms. Exits 0 silently on any error.

### Trigger Keywords

Configured in `cognitive-os.yaml > skills.catalog.lazy_triggers`. Defaults:

```
/skill, what skills, available skills, skill that, list skills,
show skills, which skill, skill for, skills for, skill router,
skill search, invoke skill, run skill, use skill, skill help,
help with skill, what can you, what commands, /catalog
```

Any prompt matching one of these terms (case-insensitive, partial match)
triggers catalog injection for that turn.

## Telemetry

### Event log

`.cognitive-os/runtime/skill-discovery.jsonl` — append-only JSONL.

Two event types:

**catalog_injected** — emitted by `lazy-catalog-injector.sh` when keywords match:
```json
{"ts": 1234, "event": "catalog_injected", "session_id": "...", "lazy_catalog_active": true, "trigger_match": true}
```

**agent_telemetry** — emitted by `skill-discovery-telemetry.sh` after Agent tool completes:
```json
{
  "ts": 1234, "event": "agent_telemetry",
  "session_id": "...", "agent_id": "...",
  "lazy_catalog_active": true,
  "prompt_keywords": ["..."],
  "skills_invoked": ["..."],
  "reimpl_detected": false,
  "suspected_missed_skills": []
}
```

### Aggregator

```bash
python3 scripts/check_lazy_catalog_health.py          # human summary
python3 scripts/check_lazy_catalog_health.py --json   # machine-readable
python3 scripts/check_lazy_catalog_health.py --window-hours 48
```

Exit codes: 0=healthy, 1=degraded (recommend revert), 2=insufficient data.

## Auto-Revert

`hooks/lazy-catalog-auto-revert.sh` runs at SessionStart (low priority).

It reads the 24h aggregator output and compares the `suspected_missed_skills`
per-session rate against the baseline in
`docs/06-Daily/measurements/lazy-catalog-baseline.json`.

**Revert condition**: `current_rate > 2× baseline_rate AND current_rate > 5%`

When triggered:
- Exports `COS_LAZY_CATALOG=0` for the current session
- Writes warning to stderr
- Does NOT permanently change the setting

To permanently disable lazy-loading:
```bash
export COS_LAZY_CATALOG=0  # in ~/.zshrc or ~/.bashrc
```

## Baseline

`docs/06-Daily/measurements/lazy-catalog-baseline.json` — initial synthetic baseline
of 5% miss rate (estimated pre-implementation). Update after 72h of real data:

```bash
python3 scripts/check_lazy_catalog_health.py --json > docs/06-Daily/measurements/lazy-catalog-baseline.json
```

## Opt-Out

```bash
export COS_LAZY_CATALOG=0   # session-level: eager injection at SessionStart
```

Or set in project `.env` / shell profile for persistent opt-out.

## Token Accounting

| Item                   | Value         |
|------------------------|---------------|
| CATALOG-COMPACT size   | 15,097 bytes  |
| Estimated tokens       | ~3,500        |
| Sessions saved (lazy)  | all sessions  |
| Cost per session saved | ~3,500 tokens |
| At 250 sessions/week   | ~875K tokens/week |
| At $0.04/10K (Sonnet)  | ~$3.50/week   |

## Hook Registration

New hooks registered in `.claude/settings.json`:

- `hooks/lazy-catalog-injector.sh` — UserPromptSubmit
- `hooks/skill-discovery-telemetry.sh` — PostToolUse (Agent tool)
- `hooks/lazy-catalog-auto-revert.sh` — SessionStart (runs after session-init.sh)

All three hooks are in the `default` and `full` efficiency profiles.
