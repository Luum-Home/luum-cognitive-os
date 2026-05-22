# Graphify Run Telemetry Report

This report joins Graphify preload selection with real session telemetry. Preload token counts are deterministic local estimates; session token counts come from Claude Code JSONL usage parsed by `lib.session_parser.py`.

## Summary

Metric label: `mixed`
Session: `1dd08301-7acd-4ba6-8792-17ebbbb5c966`
Bundles: harness-events
Preload estimated tokens: 21111
Actual input tokens: 2244
Actual output tokens: 1204183
Actual total input+output tokens: 1206427
Cache creation tokens: 15634699
Cache read tokens: 386979758
Duration minutes: 2712.7
Tool uses: 589
Subagents: 48
Models: <synthetic>, claude-opus-4-7

## Graphify Preload Bundles

### Harness event contract

Key: `harness-events`

Graphify Phase C.1 identified CanonicalEvent as the strongest cross-adapter hotspot.

## Preload Files

- `lib/sprint_orchestrator.py` — 4890 estimated tokens
- `lib/harness_adapter/base.py` — 4408 estimated tokens
- `lib/harness_adapter/codex.py` — 3544 estimated tokens
- `lib/harness_adapter/aider.py` — 2627 estimated tokens
- `lib/harness_adapter/bare_cli.py` — 2391 estimated tokens
- `lib/harness_adapter/dispatch.py` — 1666 estimated tokens
- `lib/harness_adapter/aider_streaming.py` — 1585 estimated tokens

## Relevant Dependencies and Inspection Paths

- `lib/harness_adapter/base.py`
- `lib/harness_adapter/`
- `lib/sprint_orchestrator.py`

## Recommended Confirmation Tests

```bash
.venv/bin/python -m pytest tests/unit/test_harness_adapter_base.py tests/unit/test_sprint_orchestrator.py tests/integration/test_preamble_v2_wave1.py -q
```

## Session Tools

- `Bash` — 392
- `Agent` — 61
- `Edit` — 57
- `Read` — 51
- `AskUserQuestion` — 12
- `Write` — 9
- `Skill` — 3
- `mcp__plugin_engram_engram__mem_save` — 2
- `ToolSearch` — 1
- `mcp__plugin_engram_engram__mem_session_summary` — 1

## Before/After Comparison

Mode: `paired-run`
Baseline session: `b145f66c-3990-45eb-8e0d-33e1671c08a0`
Baseline total tokens: 59614
Current total tokens: 1206427
Delta tokens: 1146813
Baseline/current ratio: 0.0494

Paired comparison only. Treat this as directional evidence unless task, model, prompt, tool policy, and cache state were controlled.

## Evidence vs Inference

Evidence:

- Graphify selected preload bundles and session_parser extracted real token usage from the provided session JSONL.

Inference boundary:

- Any token-reduction claim requires comparable before/after runs; one run only shows observed usage plus estimated preload context size.
