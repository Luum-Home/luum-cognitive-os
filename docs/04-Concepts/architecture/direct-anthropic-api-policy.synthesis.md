---
type: concept-synthesis
source: docs/04-Concepts/architecture/direct-anthropic-api-policy.md
status: "Accepted, reconstruction phase"
provenance: "Process-level environment inheritance made an ambient ANTHROPIC_API_KEY visible to Claude Code children, MCP servers, test processes, and workflow subprocesses even when those children were supposed to use the native logged-in Claude Code account instead of pay-per-token billing."
---

## What it is
Policy that gates all pay-per-token direct Anthropic API usage behind an explicit config flag, so a merely-present `ANTHROPIC_API_KEY` env var can never silently activate billed API calls.

## Key mechanics
- Single opt-in: `llm_providers.claude_sdk.enabled: true` in `cognitive-os.yaml`. No separate env-var gate is introduced.
- Two policy levels: "Direct API provider enabled" = `claude_sdk.enabled` true (allows explicit `claude_sdk` provider calls when key and SDK are present); "Advisor strategy enabled" = direct API enabled AND `ORCHESTRATOR_MODE=executor` (preserves the sonnet+advisor boundary as executor-mode-only, not normal local-account behavior).
- Flow classification: Claude Code local/operator sessions never require the key (native harness account); `claude_sdk` provider / sonnet+advisor executor path requires the enabled flag plus SDK plus key plus executor mode; `packages/advisor-mcp` defaults to `provider=auto` with Anthropic policy-gated last; `packages/cos-advisory-llm` prompt hooks need no direct key; Cognee Docker profile defaults to local Ollama+Fastembed (Anthropic only via explicit override); GitHub Claude workflows may use the repo secret (CI has no local logged-in account); Promptfoo/DeepEval examples should be provider-neutral or explicitly marked cost-bearing.
- 6 categories of allowed remaining references: (1) explicit direct API support files (`cognitive-os.yaml`, `lib/anthropic_direct_policy.py`, `lib/claude_executor.py`, `packages/llm-providers/lib/claude_sdk.py`, `rules/model-routing.md`, `pyproject.toml`); (2) explicit CI workflows (`claude-interactive.yml`, `claude-issue-triage.yml`, `claude-pr-review.yml`); (3) optional advisor-mcp transport files; (4) optional Cognee override docs (`infra/cognee/README.md`); (5) historical records (should avoid repeating the exact var name where not technically necessary); (6) tests/benchmarks/audits (`tests/audit/test_anthropic_api_key_references.py`, `tests/arena/arena-config.yaml`).
- Forbidden surfaces for new unclassified references: default Docker Compose services, bootstrap next-step output, default `.env` examples, `packages/cos-advisory-llm` native prompt-hook packages, Cognee default skill/package config, MCP registration examples that run by default.
- Consequences: ambient key not propagated to Claude CLI subprocess safe environments; `select_model(..., use_advisor=True)` only means "prefer advisor if available," never forces a disabled path; `ClaudeExecutor.run_with_advisor()` enforces the same router policy so direct callers can't bypass it; `claude_sdk.py` must check the same policy before reporting itself configured; GitHub Actions may still use repo secrets (separate from local defaults); Cognee/`cos-advisory-llm` service defaults must not select Anthropic direct API.
- Rejected alternatives: new env-var gate (redundant with cognitive-os.yaml), API-key-presence-as-activation (lets ambient inheritance change billing), disabling all Anthropic API code (CI/benchmarks/advisor experiments still need it).

## Relations & where used
`lib/anthropic_direct_policy.py`, `lib/claude_executor.py`, `packages/llm-providers/lib/claude_sdk.py`, `rules/model-routing.md`, `packages/advisor-mcp/`, `packages/cos-advisory-llm/`, `infra/cognee/`.

## Status / caveats
Enforced by `tests/unit/test_direct_anthropic_default_surfaces.py` (blocks default/local surfaces reintroducing active key requirements) and `tests/audit/test_anthropic_api_key_references.py` (classifies every reference, fails on unclassified new references and stale allowlist entries).
