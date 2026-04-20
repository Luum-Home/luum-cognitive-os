<!-- SCOPE: both -->
# Cognitive Load Monitoring

## Purpose

Detect and respond to agent cognitive degradation caused by context overload. Based on the WISC framework (arxiv 2507.11538) finding that >150 instructions degrade LLM performance.

Cognitive OS loads ~88 rules (~73K tokens). As context fills during a session, agent quality degrades: instructions are forgotten, hallucinations increase, and output quality drops. This rule defines monitoring behavior and response thresholds.

## Degradation Types

| Type | Signal | What It Means |
|------|--------|---------------|
| `context_saturation` | Output length drops >30% vs baseline | Agent is losing capacity to generate thorough responses |
| `instruction_drift` | Preamble compliance <70% | Agent forgets PROGRESS markers, structured output, communication standards |
| `hallucination_spike` | Unverified claims increase 3x+ vs baseline | Agent starts fabricating files, inventing results |
| `tool_confusion` | Tool success rate <80% | Agent uses wrong tools, malformed arguments |
| `compound_degradation` | 3+ of the above simultaneously | Agent is overwhelmed -- session split required |

## Context-Triggered Behavior

### At 50% Context Usage

- Start tracking quality metrics via `CognitiveLoadMonitor` (if not already)
- Be concise in responses (per `context-management.md`)
- Record a snapshot after each significant tool call

### At 70% Context Usage

- If quality dropped >15% from baseline:
  - Output: `COGNITIVE LOAD WARNING: Quality at X/100 (baseline was Y/100)`
  - Save all important state to Engram immediately
  - Recommend session split to the user
- If quality is stable: continue with normal 70% context-management behavior

### At 85% Context Usage

- Mandatory: stop new work, save state, inform user
- If quality dropped >25% from baseline:
  - Output: `COGNITIVE LOAD ALERT: Severe degradation detected. Splitting recommended.`
  - Call `monitor.save_metrics()` to persist the degradation data
  - Include degradation data in `mem_session_summary`

## Integration with Existing Rules

| Rule | Integration |
|------|-------------|
| `context-management` | Cognitive load monitoring adds quality-based triggers ON TOP of the fixed context thresholds |
| `trust-score` | Trust score per-task; cognitive load tracks trust degradation TREND over time |
| `agent-kpis` | Cognitive health score feeds into Agent Quality OKR |
| `responsiveness` | Quality degradation is a reason to proactively inform the user |
| `self-improvement-protocol` | Persistent degradation patterns feed into self-improvement recommendations |

## Library

`lib/cognitive_load_monitor.py` provides:

| Function | Description |
|----------|-------------|
| `CognitiveLoadMonitor()` | Session-scoped monitor instance |
| `record_snapshot(**kwargs)` | Record a quality measurement |
| `detect_degradation()` | Analyze for degradation signals |
| `cognitive_health_score()` | Current health 0-100 |
| `format_health_report()` | Human-readable report with trend |
| `should_save_and_split()` | True when health <60 |
| `save_metrics(path)` | Persist to JSONL |

## Metrics

Snapshots saved to `.cognitive-os/metrics/cognitive-load.jsonl`:

```json
{
  "timestamp": 1711612800.0,
  "tool_call_number": 42,
  "context_usage_pct": 55.3,
  "output_length": 1200,
  "task_complexity": "medium",
  "preamble_compliance": 0.85,
  "hallucination_count": 1,
  "instruction_following": 0.9,
  "tool_call_success": 1.0,
  "response_quality_score": 82.5,
  "degradation_detected": false,
  "degradation_type": null
}
```

## Diagnostic Skill

Run `/agent-stress-test` to empirically measure the degradation point for the current model and configuration. The skill runs 13 tasks across 4 phases (baseline, load, saturation, recovery) and reports where quality starts dropping.

## Contextual Trigger

This rule is loaded when: context usage >50%, cognitive load, degradation, quality drop, burnout, stress test.
