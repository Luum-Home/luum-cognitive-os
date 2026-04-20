<!-- SCOPE: both -->
# Prompt Quality Scoring

## Purpose

Scores agent prompts on 5 quality dimensions (specificity, actionability, context, measurability, scope clarity). Complementary to clarification-gate (which scores ambiguity). Quality is advisory -- it never blocks.

## Scoring (0-100)

| Dimension | Points | What it measures |
|---|---|---|
| Specificity | 0-20 | File paths, function names, concrete references |
| Actionability | 0-20 | Clear action verb + target |
| Context | 0-20 | Background, constraints, prior decisions |
| Measurability | 0-20 | Acceptance criteria, verification commands |
| Scope clarity | 0-20 | Bounded vs unbounded scope |

## Behavior

| Score | Level | Action |
|---|---|---|
| < 30 | WARNING | Output suggestions for improvement |
| 30-60 | INFO | Logged to metrics only |
| > 60 | Silent | Pass-through |

## Relationship to Clarification Gate

| Hook | What it scores | Behavior |
|---|---|---|
| `clarification-gate.sh` | Ambiguity (vague prompts) | Blocks on high ambiguity (exit 2) |
| `prompt-quality.sh` | Quality (weak prompts) | Advisory only (always exit 0) |

A prompt can be unambiguous but low-quality (clear what to do, but missing acceptance criteria and context). A prompt can be high-quality but ambiguous (detailed context but unclear scope). Both hooks complement each other.

## Hook Details

- **Hook**: `hooks/prompt-quality.sh`
- **Type**: PreToolUse
- **Matcher**: Agent
- **Exit code**: Always 0 (advisory only)
- **Auto-disabled**: Capability level 4+

## Metrics

Logged to `.cognitive-os/metrics/prompt-quality.jsonl`:

```json
{
  "timestamp": "ISO-8601",
  "score": 45,
  "specificity": 15,
  "actionability": 10,
  "context": 5,
  "measurability": 10,
  "scope_clarity": 5,
  "agent": "first 100 chars of prompt..."
}
```

## Contextual Trigger

This rule is loaded when: prompt quality, quality scoring, prompt improvement.
