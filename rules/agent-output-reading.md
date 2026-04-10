# Agent Output Reading Protocol

## Purpose

Prevent token waste when reading sub-agent completion results. Agent output files are JSONL containing the full conversation transcript (prompts, tool calls, tool results, system messages). The useful text is ~5% of the file. Reading the raw file wastes 95% of tokens on noise.

## Rule (Always Active)

When a sub-agent completes (task-notification arrives), the orchestrator MUST follow this priority order:

### Priority 1: `<task-notification>` result field
The notification includes a `<result>` field with the agent's final output, already parsed and clean. Use this DIRECTLY. Cost: 0 extra tokens.

### Priority 2: Engram search
Agents are instructed (via agent-preamble.md) to ALWAYS save findings to Engram before finishing. Search by keywords from the task description, not by exact topic_key. Cost: ~100 tokens.

### Priority 3: `lib/agent_output_extractor.py`
Python module that extracts assistant text from JSONL. Functions: `extract_assistant_text()`, `extract_last_response()`, `summarize_agent_output()`. Cost: ~500 tokens for the bash call.

### Priority 4: `jq` one-liner
```bash
jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="text") | .text' output.jsonl | tail -5000
```

## Prohibited

- **NEVER** use the Read tool on agent JSONL output files
- **NEVER** use multiple Read calls with offset/limit to find content in JSONL
- **NEVER** skip the `<result>` field and go directly to the file

## Why This Matters

A single Read attempt on a JSONL file wastes 10K+ tokens. Multiple attempts (offset/limit) waste 20-30K tokens. The `<result>` field costs 0 extra tokens. Over a session with 10 agent completions, following this protocol saves 100-300K tokens.

## Integration

- **agent-preamble.md**: Instructs all sub-agents to save findings to Engram (ensures Priority 2 works)
- **CLAUDE.md**: Orchestrator rule to use `<result>` first (ensures Priority 1 is followed)
- **lib/agent_output_extractor.py**: Programmatic extraction (Priority 3)
- **scripts/extract-agent-output.sh**: CLI wrapper for manual use

## Contextual Trigger

This rule is always active. It applies every time an agent completes.
