# @luum/quality-gates

Pre- and post-tool quality gates — clarification, confidence, completion, and claim validation

## Install

```bash
cos install @luum/quality-gates
```

## Components

- `hooks/clarification-interceptor.sh` (hook) -- Intercept NEEDS_CLARIFICATION markers from sub-agents
- `hooks/clarification-gate.sh` (hook) -- Block agent launch on vague/ambiguous prompts
- `hooks/confidence-gate.sh` (hook) -- Enforce minimum trust score thresholds
- `hooks/completion-gate.sh` (hook) -- Verify acceptance criteria on agent completion
- `hooks/claim-validator.sh` (hook) -- Validate file creation/modification claims against filesystem

## License

Apache-2.0
