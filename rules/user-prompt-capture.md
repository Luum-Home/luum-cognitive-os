# User Prompt Capture Protocol

## Purpose

Engram captures what agents DO (decisions, bugs, discoveries) but NOT what the user ASKED. Between sessions, user intent is lost. Future sessions know what was built but not WHY the user requested it. This rule closes that gap.

## Rule (Always Active)

The orchestrator MUST call `mem_save_prompt` for every user message that contains actionable intent. Use `lib/prompt_classifier.py` to classify prompts before deciding.

### Capture These Categories

| Category | Signal | Examples |
|----------|--------|----------|
| `task_request` | Action verbs + targets | "build the auth module", "fix the broken test", "add JWT support" |
| `decision` | Decision language | "use PostgreSQL", "go with approach A", "let's do REST not GraphQL" |
| `feedback` | Correction or praise | "don't use sed for docs", "that's wrong, revert it", "keep doing that" |
| `context` | Project information | "we're working on payments", "the deadline is Friday", "the stack is Go + React" |

### Skip These Categories

| Category | Signal | Examples |
|----------|--------|----------|
| `acknowledgment` | Short affirmations | "ok", "yes", "dale", "sure", "go ahead" |
| `status_query` | Questions about state | "what's left?", "how's it going?", "progress?" |
| `navigation` | File/tool references | "show me the file", "read handler.go", "check the logs" |

### Spanish Support

The classifier handles Spanish prompts natively:

| Category | Spanish Examples |
|----------|-----------------|
| `task_request` | "construyamos el modulo", "arreglemos el test", "agregale soporte JWT" |
| `decision` | "usemos PostgreSQL", "vamos con el enfoque A" |
| `feedback` | "no hagas eso", "perfecto, segui asi" |
| `acknowledgment` | "dale", "si", "bueno", "listo" |

## Format

```python
from lib.prompt_classifier import classify_prompt

result = classify_prompt(user_message)
if result.should_capture:
    mem_save_prompt(
        content=user_message,
        project="{project name}",
        session_id="{current session ID}"
    )
```

## Why This Matters

Future sessions can search user prompts to understand:

1. **What was requested vs what was delivered** -- compare mem_save_prompt entries with mem_save entries to find gaps
2. **User preferences and patterns** -- repeated decisions ("always use approach X") surface naturally
3. **Decision history in the user's own words** -- not the agent's interpretation, but the original request
4. **Task evolution across sessions** -- how requirements changed over time

## Classifier Library

`lib/prompt_classifier.py` provides:

| Function | Returns | Purpose |
|----------|---------|---------|
| `classify_prompt(text)` | `ClassificationResult(category, should_capture, confidence)` | Full classification with confidence score |
| `should_capture_prompt(text)` | `bool` | Quick yes/no for capture decisions |

The classifier uses regex pattern matching with weighted scoring. Each category has English and Spanish patterns. The highest-scoring category wins. Confidence ranges from 0.0 to 1.0.

## Integration with Engram

Captured prompts are stored via `mem_save_prompt` which uses engram's built-in prompt storage. They are searchable alongside regular observations but tagged as user prompts.

### Searching Past Prompts

```python
# Find what the user asked about auth
mem_search(query="auth authentication JWT", type="prompt")

# Find recent user decisions
mem_search(query="use choose prefer decide", type="prompt")
```

## No Hook Available

Claude Code does not expose a `UserPromptSubmit` hook event. The available hook events are: `SessionStart`, `PreToolUse`, `PostToolUse`, and `Stop`. None fire on user message submission. Therefore, prompt capture MUST be handled by the orchestrator as a behavioral rule, not an automated hook.

## Orchestrator Protocol

On every user message:

1. Run `classify_prompt(message)` from `lib/prompt_classifier.py`
2. If `result.should_capture` is True, call `mem_save_prompt(content=message, project=project)`
3. If `result.should_capture` is False, skip silently
4. Proceed with normal task processing

This adds negligible overhead (regex matching only, no LLM calls) and preserves the full intent record.

## Contextual Trigger

This rule is always active. It applies to every user message received by the orchestrator.
