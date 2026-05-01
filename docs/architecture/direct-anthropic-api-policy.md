# Direct Anthropic API Policy

## Status

Accepted — reconstruction phase.

## Problem

Cognitive OS has two distinct ways to reach Claude-family models:

1. **Claude Code native execution** — local/operator sessions use the logged-in
   Claude Code account through the CLI or harness-native flow.
2. **Direct Anthropic API execution** — SDK/provider flows use
   `ANTHROPIC_API_KEY` and are billed per token.

These paths must not be activated by the mere presence of an ambient
`ANTHROPIC_API_KEY`. Process-level inheritance made the key visible to Claude
Code children, MCP servers, test processes, and workflow subprocesses even when
those children were supposed to use the native Claude Code account.

## Decision

Direct Anthropic API use is governed by the existing provider configuration:

```yaml
llm_providers:
  claude_sdk:
    enabled: false
```

`llm_providers.claude_sdk.enabled: true` is the single repo-level opt-in for
pay-per-token Anthropic SDK/provider usage. No additional ad-hoc environment
variable is introduced.

The policy has two levels:

- **Direct API provider enabled**: `llm_providers.claude_sdk.enabled is true`.
  This allows explicit provider calls such as `claude_sdk` when the API key and
  SDK are also present.
- **Advisor strategy enabled**: direct API provider is enabled **and**
  `ORCHESTRATOR_MODE=executor`. This preserves the original Advisor Strategy
  boundary: `sonnet+advisor` is executor-mode functionality, not normal local
  Claude Code account usage.


## Flow Classification

| Flow | Classification | Policy |
|---|---|---|
| Claude Code local/operator sessions | Native harness account | Never require `ANTHROPIC_API_KEY`. |
| `claude_sdk` provider and `sonnet+advisor` executor path | Direct Anthropic API | Requires `llm_providers.claude_sdk.enabled: true`, SDK, key, and executor-mode when advisor is used. |
| `packages/advisor-mcp` | Optional external-advisor MCP transport | Defaults to safe `provider=auto`; Anthropic is last and policy-gated. |
| `packages/cos-advisory-llm` prompt hooks | Harness-native prompt hook extension | Uses prompt-type hook output; no direct provider API key required. |
| Cognee reference Docker profile | Optional memory service | Defaults to local Ollama + Fastembed; Anthropic only via explicit Cognee override. |
| GitHub Claude workflows | Explicit CI direct API | May use repository secret because CI has no local logged-in Claude Code account. |
| Promptfoo/DeepEval examples | Optional eval tooling | Examples should be provider-neutral or explicitly marked cost-bearing. |

## Consequences

- Ambient `ANTHROPIC_API_KEY` is not propagated to Claude CLI subprocess safe
  environments.
- `select_model(..., use_advisor=True)` means "prefer advisor if available";
  it does not force a disabled direct-API path.
- `ClaudeExecutor.run_with_advisor()` enforces the same policy as the router,
  so direct callers cannot bypass the router and spend API tokens outside the
  configured executor-mode path.
- `packages/llm-providers/lib/claude_sdk.py` must check the same direct API
  provider policy before reporting itself configured.
- GitHub Actions may still use repository secrets explicitly because CI cannot
  rely on a local logged-in Claude Code account. Those workflows are separate
  from local/operator defaults.
- Optional service defaults must not select Anthropic direct API. Cognee defaults
  to local Ollama/Fastembed, and `cos-advisory-llm` uses harness-native prompt
  hooks rather than SDK calls.

## Rejected alternatives

- **New env var gate**: rejected
  because it adds another policy surface when `cognitive-os.yaml` already owns
  provider enablement.
- **API key presence as activation**: rejected because it makes ambient process
  inheritance change billing behavior.
- **Disabling all Anthropic API code**: rejected for now because CI, benchmarks,
  and model-agnostic advisor experiments may still need explicit direct API
  paths.

## Verification

- Unit tests cover enabled/disabled provider config using real temporary
  `cognitive-os.yaml` files.
- Router and executor tests cover fallback when advisor is disabled.
- Grep must show no references to ad-hoc direct-Anthropic env gates.
