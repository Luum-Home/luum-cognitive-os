# Advisor MCP Architecture Review

> Status: current investigation and decision frame.
> Scope: `packages/advisor-mcp`, `sonnet+advisor`, and direct-provider advisor calls.

## Executive Summary

`packages/advisor-mcp` was introduced as a model-agnostic way for any MCP-capable
coding agent to ask a stronger external model for short strategic advice. That
is useful as an optional extension, but it is not the optimal core mechanism for
Claude Code-native advising.

For the core product path, the advisor should be a harness-native agentic
primitive: a subagent, task delegation surface, or harness adapter that uses the
host's own account/session and permission model. MCP should remain the boundary
for external systems, tools, data, workflows, and optional third-party model
gateways.

## Why This Exists

Commit `47d81773` added two advisor paths at the same time:

1. **Native Anthropic Advisor Strategy**
   - `lib/claude_executor.py` added `run_with_advisor()`.
   - `lib/model_router.py` added the virtual tier `sonnet+advisor`.
   - The intended execution pattern was: Sonnet executes, Opus gives bounded
     strategic advice.
   - This path uses direct Anthropic API calls and therefore must be explicitly
     gated.

2. **Model-agnostic Advisor MCP server**
   - `packages/advisor-mcp/advisor_server.py` exposes `consult_advisor`.
   - Providers include `anthropic`, `openai`, `google`, `litellm`, and `local`
     Ollama.
   - The server logs cost estimates to
     `.cognitive-os/metrics/advisor-consultations.jsonl`.
   - It was positioned as portable across Claude Code, Cursor, Windsurf, and
     other MCP clients.

The conflation is the root problem: "advisor" is an execution strategy, while
MCP is an integration protocol. An MCP server can implement an advisor tool, but
it should not become the default way for a Claude Code session to consult Claude.

## MCP Boundary

The official MCP framing is that MCP connects AI applications to external
systems: tools, data sources, APIs, and workflows. Claude Code's MCP
documentation describes MCP servers as giving Claude Code access to external
tools, databases, and APIs, and the MCP overview describes the protocol as a
standard connection between AI applications and external systems.

Sources:

- [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp)
- [Model Context Protocol overview](https://modelcontextprotocol.io/docs/getting-started/intro)
- [MCP tools specification](https://modelcontextprotocol.io/specification/draft/server/tools)

Implication for this repo:

- An MCP server does not automatically inherit Claude Code's model session as a
  callable "advisor model".
- If the MCP server calls Anthropic's SDK, that is a separate direct API call
  and needs explicit provider configuration, auth, cost tracking, and tests.
- If the goal is "use the Claude Code account I am already logged into", the
  solution should be harness-native delegation, not a local MCP server that
  shells out to a pay-per-token provider SDK.

## Current Risk Assessment

| Risk | Current state | Target state |
|---|---|---|
| Ambient `ANTHROPIC_API_KEY` usage | Anthropic provider is now config-gated, but the provider still exists. | Keep only as explicit external-provider option. |
| Default behavior | `consult_advisor` defaults to `auto` with safe provider resolution. | Keep `auto` contract-tested so Anthropic is never selected from ambient credentials alone. |
| Product boundary | README still frames Advisor MCP as a broad strategic advisor. | Classify it as optional `external-advisor` extension. |
| Claude Code native account | MCP cannot be assumed to reuse it. | Core advisor path should use harness-native subagent/delegation. |
| Cost model | MCP logs estimates for successful calls. | Keep logs, but make cost-bearing providers opt-in and policy-gated. |
| Test coverage | Unit tests cover routing, errors, logging, and Anthropic policy gate. | Add contract tests for safe auto resolution and no Anthropic selection when disabled. |

## Decision

Advisor should be split into three explicit layers:

1. **Native advisor primitive**
   - Core path.
   - Uses the active harness' native delegation mechanism.
   - Examples: Claude Code subagent, Codex worker, bare CLI fallback.
   - Does not require `ANTHROPIC_API_KEY`.

2. **External advisor provider**
   - Optional extension path.
   - Uses OpenAI, Google, LiteLLM, Anthropic API, or local Ollama.
   - Must be explicit and cost/policy-gated.

3. **Advisor MCP transport**
   - Compatibility surface for MCP clients.
   - Exposes external advisor provider calls as a tool.
   - Should not be registered by default for every project.

## Recommended Implementation Plan

### Phase 1 — Rename the contract, not necessarily the package

- Keep the package path for compatibility: `packages/advisor-mcp`.
- Update docs and metadata to call it an "External Advisor MCP".
- Make clear that it is optional and not the canonical Claude Code-native
  advisor.

### Phase 2 — Add safe provider resolution

Implemented resolver contract:

```text
provider=auto
  1. local, if Ollama is reachable and the requested/default model exists
  2. litellm, if LiteLLM is installed/configured
  3. openai, if OPENAI_API_KEY is present and SDK is installed
  4. google, if GOOGLE_API_KEY or GEMINI_API_KEY is present and SDK is installed
  5. anthropic, only if direct_anthropic_api_enabled() and ANTHROPIC_API_KEY exists
  6. otherwise return an actionable ERROR without making a paid provider API call
```

The important invariant is that Anthropic direct API is never selected because
an ambient key happens to exist.

### Phase 3 — Add contract tests

Required tests:

1. `provider=auto` never chooses `anthropic` when
   `llm_providers.claude_sdk.enabled` is false.
2. `provider=auto` returns actionable error when no provider is available.
3. `provider=anthropic` remains explicitly callable only when direct API policy
   and credentials are present.
4. Docs/examples do not include `ANTHROPIC_API_KEY` in default MCP registration.
5. Cost-bearing providers are absent from first-run/default project setup.

### Phase 4 — Native advisor follow-up

Define a harness-neutral advisor primitive contract:

```text
consult_native_advisor(context, question, max_turns=1)
```

The implementation should live behind harness adapters:

- Claude Code: subagent/delegation path.
- Codex: worker/sub-agent path when available.
- Bare CLI/CI: no-op or local model fallback, depending on config.

This keeps the advisor concept portable without pretending MCP can reuse a host
model session.

## Acceptance Criteria

1. `packages/advisor-mcp` is documented as optional external-advisor transport.
2. Default MCP registration examples do not pass `ANTHROPIC_API_KEY`.
3. Anthropic direct API remains controlled by `llm_providers.claude_sdk.enabled`.
4. Tests prove router, executor, provider, and MCP server agree on the policy.
5. Native advisor work is tracked separately from MCP provider work.

