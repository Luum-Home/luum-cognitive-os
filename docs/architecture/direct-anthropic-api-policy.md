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

## Why References Still Exist

The policy is **not** a total ban on the string `ANTHROPIC_API_KEY`. It is a
ban on accidental activation and default/local propagation. Remaining
references are allowed only when they fall into one of the categories below.

### 1. Explicit direct Anthropic API support

These files keep the opt-in `claude_sdk` / `sonnet+advisor` direct API path:

- `cognitive-os.yaml`
- `lib/anthropic_direct_policy.py`
- `lib/claude_executor.py`
- `packages/llm-providers/lib/claude_sdk.py`
- `packages/llm-providers/lib/__init__.py`
- `rules/model-routing.md`
- `pyproject.toml`

Reason: Cognitive OS still supports explicit pay-per-token Anthropic SDK usage
for executor-mode/advisor and direct-provider experiments. A key alone is not
enough; runtime code must also pass the `llm_providers.claude_sdk.enabled: true`
policy gate.

### 2. Explicit CI workflows

These files use the GitHub secret for Claude Code actions:

- `.github/workflows/claude-interactive.yml`
- `.github/workflows/claude-issue-triage.yml`
- `.github/workflows/claude-pr-review.yml`
- `docs/automation.md`
- `workflows/README.md`

Reason: GitHub Actions cannot rely on a developer's local logged-in Claude Code
account. These are CI-only direct API flows, not local/operator defaults.

### 3. Optional external advisor transport

These files document or implement the `advisor-mcp` Anthropic provider:

- `packages/advisor-mcp/advisor_server.py`
- `packages/advisor-mcp/README.md`
- `packages/advisor-mcp/cos-package.yaml`
- `docs/architecture/advisor-mcp-architecture-review.md`

Reason: `advisor-mcp` is an optional external-advisor MCP transport. It defaults
to safe `provider=auto`, does not pass `ANTHROPIC_API_KEY` in the default MCP
registration example, and selects Anthropic only when the shared direct API
policy and credentials are present.

### 4. Optional Cognee override documentation

Remaining Cognee docs may show how to opt into Anthropic manually:

- `infra/cognee/README.md`

Reason: the reference Docker profile defaults to local Ollama + Fastembed and
does not propagate `ANTHROPIC_API_KEY`. The Anthropic mention is an explicit
override example for users who choose direct API extraction.

### 5. Historical records

Historical decision and handoff documents preserve prior rationale:

- `CHANGELOG.md`
- `docs/SESSION-HANDOFF-*.md`
- `docs/adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md`
- `docs/adrs/ADR-063-agent-tool-replication-strategy.md`

Reason: these are not runtime surfaces. They explain why the direct-provider
path existed and how it was gated.

### 6. Tests, benchmarks, and audits

Tests and benchmark configs use the variable as a fixture or explicit
cost-bearing provider requirement:

- `tests/unit/test_*`
- `tests/audit/test_anthropic_api_key_references.py`
- `tests/arena/arena-config.yaml`
- `docs/benchmarks/so-vs-vanilla-tasks.yaml`

Reason: tests must be able to prove that the key does **not** activate direct
API flows by itself. Arena/benchmark configs are explicitly cost-bearing and
not part of local defaults.

## Forbidden References

New references are forbidden unless they are classified in
`tests/audit/test_anthropic_api_key_references.py`. In particular, the following
surfaces must not introduce unclassified `ANTHROPIC_API_KEY` usage:

- default Docker Compose services;
- bootstrap next-step output;
- default `.env` examples;
- native prompt-hook packages such as `packages/cos-advisory-llm`;
- Cognee default skill/package configuration;
- MCP registration examples that run by default.

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
- `tests/unit/test_direct_anthropic_default_surfaces.py` blocks default/local
  surfaces from reintroducing active Anthropic key requirements.
- `tests/audit/test_anthropic_api_key_references.py` classifies every remaining
  `ANTHROPIC_API_KEY` reference and fails on both unclassified new references
  and stale allowlist entries.
