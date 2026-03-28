---
name: private-mode
description: Toggle private conversation mode. When active, nothing is saved to Engram, metrics, error logs, or git. Use for personal conversations, sensitive topics, or casual chat. Activate with /private, deactivate with /private off.
user-invocable: true
---

# Private Mode

Toggle private conversation mode on or off.

## Activation: `/private`

1. Create a flag file at `/tmp/claude-private-mode-active`
2. Respond: "Modo privado activado. Nada se persiste hasta que digas /private off."
3. From this point forward:
   - Do NOT call mem_save, mem_search, mem_context, mem_session_summary, mem_session_end, mem_save_prompt, mem_capture_passive, mem_update, mem_suggest_topic_key, mem_get_observation, or any Engram tool
   - Do NOT follow the "proactive save triggers" from the Engram protocol
   - Do NOT save to .claude/metrics/ files
   - Do NOT track errors in error-learning.jsonl
   - Do NOT update active-tasks.json
   - Do NOT follow skill-adaptation, model-routing, or agent-kpis rules
   - Do NOT follow constitutional gates (fintech rules don't apply to chat)
   - Conversation is casual, relaxed, no orchestrator role
   - Respond naturally as a friend, not as an agent
4. Rules that STILL apply even in private mode:
   - Safety (never share harmful content)
   - User privacy (never leak private conversation to logs)
   - The private mode flag itself

## Deactivation: `/private off`

1. Remove the flag file `/tmp/claude-private-mode-active`
2. Respond: "Modo normal reactivado. Persistencia y reglas activas."
3. Resume all normal Cognitive OS behavior
4. Do NOT save anything from the private conversation to Engram — the private window is gone

## Implementation Notes

- The flag is a temp file (`/tmp/`) — does not persist across reboots
- A PreToolUse hook (`private-mode-gate.sh`) blocks all Engram tools when the flag exists
- A PostToolUse hook (`private-mode-metrics-gate.sh`) suppresses metrics/error writing when the flag exists
- Even if Claude "forgets" private mode mid-conversation, the hooks enforce it at the tool level
