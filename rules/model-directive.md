<!-- SCOPE: both -->
# Model Directive Protocol

## Rule: Orchestrator MUST Follow MODEL_DIRECTIVE

When `dispatch-gate.sh` outputs `MODEL_DIRECTIVE: {model}` to stderr, the orchestrator
MUST use that model for the agent launch. This is not advisory — it is a binding routing
decision made by the dispatch system based on:

1. **Task type** — matched against the routing table in `rules/model-routing.md`
2. **Budget remaining** — monthly and hourly spend from `cost-events.jsonl`
3. **Consequence history** — DEGRADE/PROMOTE records from `consequence-history.jsonl`

## Output Markers

The dispatch gate emits one of three markers:

| Marker | Meaning | Required Action |
|--------|---------|-----------------|
| `MODEL_DIRECTIVE: sonnet` | Use this model — directive (confidence >= 0.7) | MUST use the specified model |
| `MODEL_ADVICE: sonnet` | Suggested model — advisory (confidence < 0.7) | SHOULD use; can override with justification |
| `MODEL_DISABLED: reason` | Skill is DISABLED | MUST NOT launch; see reason for remediation |

## Override Rules

The orchestrator MAY override a `MODEL_DIRECTIVE` only when:
1. The user **explicitly** specifies a different model in their request
2. The task requires a capability the directive model cannot handle (e.g., 1M context window)

In all other cases, the directive is binding.

## MODEL_DISABLED Behavior

When `MODEL_DISABLED` is emitted, the dispatch gate exits with code 2 (BLOCK). The
agent launch is prevented. The orchestrator MUST:

1. Report the disabled skill to the user
2. Suggest running `/optimize-skill {skill-name}` to rewrite and re-enable it
3. NOT attempt to re-launch with a different model (the skill itself is blocked, not the model)

## Budget Downgrade Chain

The dispatch system applies the resource-governance downgrade chain automatically:

| Condition | Action |
|-----------|--------|
| Monthly spend > 95% | Force `haiku` for all tasks |
| Monthly spend > 80% | Downgrade `opus` → `sonnet` |
| Hourly remaining < 5% | Force `haiku` + warn |
| Hourly remaining < 20% | Force `haiku` |

## Consequence Feedback Loop

The dispatch system reads `consequence-history.jsonl` before every launch:
- **DEGRADED** skill → model is downgraded one tier (opus→sonnet, sonnet→haiku)
- **DISABLED** skill → launch is blocked entirely
- **PROMOTED** skill → model is set to `opus` (highest quality)

This creates a closed feedback loop: poor performance → automatic model downgrade →
lower cost + lower expectations → either recovers or gets disabled for rewrite.

## Integration

| Primitive | Role |
|-----------|------|
| `hooks/dispatch-gate.sh` | Emits MODEL_DIRECTIVE on every allowed agent launch |
| `lib/dispatch_model_advisor.py` | `format_model_directive()` formats the marker |
| `lib/model_router.py` | `get_consequence_override()` reads consequence history |
| `lib/consequence_engine.py` | Records DEGRADE/PROMOTE/DISABLE actions |
| `rules/resource-governance.md` | Defines budget thresholds used here |
| `rules/model-routing.md` | Defines task-type → model routing table |
| `rules/consequence-system.md` | Defines the OKR-driven feedback loop |

## Contextual Trigger

This rule is loaded when: model directive, MODEL_DIRECTIVE, model routing, dispatch gate model,
budget downgrade, consequence override.
