---
adr: 63
title: Agent() Tool Replication Strategy
status: accepted
implementation_status: partial
date: '2026-04-24'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: Research report lands within 1 week (blocked on research agent output).
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-063 — Agent() Tool Replication Strategy

## Status

**Accepted** — 2026-04-24. Clarifies the scope of ADR-051 / ADR-062 and
rejects a full Claude Code Agent() clone.

## Context

Operator asked (2026-04-24): "¿podemos replicar completamente Agent()? ¿es
posible analizar sus entrañas?"

"Agent()" here means the native Claude Code tool that spawns isolated
sub-agent sessions. Its internals combine several pieces:
- Subprocess lifecycle + context isolation
- Tool registration (Bash, Read, Edit, Grep, Glob, WebFetch, Skill, TodoWrite, MCP…)
- Session transcript persistence compatible with `~/.claude/projects/`
- Integration with Claude Code's hooks, skills auto-discovery, slash commands
- Native MCP server protocol

Analyzing the internals is partially possible:
- `@anthropic-ai/claude-agent-sdk` (Anthropic's public SDK) exposes most
  of the primitives publicly — the canonical way to replicate Agent().
- `@anthropic-ai/sdk` is the underlying API client.
- Claude Code binary is minified Node.js, inspectable but ToS-sensitive.
- Via hooks we can observe the input/output JSON shape and infer the
  lifecycle.

Replicating Agent() fully would cost ~6 sessions:
- Full MCP protocol client
- Skill discovery engine at runtime
- Session transcript format compatibility
- Parity testing against Claude Code

ADR-051 already ships a partial replica for Qwen (tool loop + governance
injection + parity harness). ADR-062 generalizes it to any
OpenAI-compatible provider.

## Decision

**Do NOT replicate Agent() fully.** Instead:

1. **Adopt the official `@anthropic-ai/claude-agent-sdk`** as the backend
   option when we need Claude-semantics (tool calling, session transcripts)
   on non-Claude-Code harnesses. This avoids reverse-engineering work
   and tracks Anthropic's evolution.

2. **Extend `lib/qwen_agent_loop.py` (→ `openai_compatible_agent_loop.py`
   per ADR-062)** to cover the 20% of Agent() semantics we actually use.
   Stop short of full MCP / skill auto-discovery inside the loop — those
   stay in the Claude Code runtime layer.

3. **Accept feature-loss opt-in via ADR-056 L3** for skills that don't
   need the full Claude Code ecosystem. Skills that DO need it (MCP
   tool calls, native Skill tool, TodoWrite) keep running on Claude
   Code natively.

### What we replicate (via ADR-062 multi-provider loop)

- Tool calling (Bash / Read / Edit / Grep / Glob / WebFetch)
- Context injection (ADR-051 Phase 3: hooks/rules/skills governance)
- Trust report emission
- Escalation signals
- Multi-turn with timeout + iteration cap
- OTel span emission (Phoenix, per ADR-058)

### What we do NOT replicate

- Full MCP protocol client (skills that need MCP must run on Claude Code)
- Skill auto-discovery at runtime (skills declared in frontmatter only)
- TodoWrite tool semantics (use `.cognitive-os/tasks/active-tasks.json` directly)
- Session transcript format of `~/.claude/projects/*.jsonl` (we use our own Engram/metrics JSONLs)
- Native Agent() inside the loop (no recursive sub-agents; the loop is flat)

### Using the official Claude Agent SDK

When the operator needs Claude-semantics WITHOUT Claude Code (e.g., in a
CI job, in a cron script, in a container where Claude Code CLI isn't
installed), we adopt `@anthropic-ai/claude-agent-sdk` directly:

- Install via `npm i @anthropic-ai/claude-agent-sdk` (Node) or the
  Python equivalent when stable.
- Wrapper at `lib/providers/claude_sdk.py` (new) that exposes the same
  interface as other providers.
- Uses the direct Anthropic API credential (pay-per-token) — opt-in per ADR-060 doctrine.

**Operator preference 2026-04-24**: "evitando usar las API keys de claude
ya que son carísimas las consultas via api". So Claude-SDK via API
remains OPT-IN ONLY. The primary cascade stays with Qwen / OpenRouter /
Gemini / Ollama (ADR-062 tier 1-4); Claude is only tier-5 last-resort
AND prefers Claude Code native (subscription-billed) over API (token-billed).

## Consequences

### Positive
- Avoid ~6 sessions of reverse-engineering + maintenance burden
- Track Anthropic's SDK evolution automatically
- Pragmatic: replicate what we use, not what we theoretically could
- ADR-056 L3 opt-in mechanism already handles the "I'm OK with feature loss"
  case cleanly

### Negative
- Cannot offer "Claude Code but fully local" to users who want zero Anthropic dependency — they must accept the Claude Code CLI is proprietary
- Skills using MCP cannot run via the replica loop (ADR-062). Must stay on Claude Code native.
- `@anthropic-ai/claude-agent-sdk` changes track Anthropic's roadmap, not ours

### Neutral
- This ADR is a SCOPE decision, not a code change. ADR-062 implementation
  is what executes it.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Full Agent() clone from scratch | ~6 sessions work, perpetual maintenance, ToS-adjacent, no clear ROI over ADR-062 |
| Adopt claude-agent-sdk as PRIMARY | Pay-per-token; operator rejected (costs) |
| Ignore Agent() semantics entirely and use only generic OpenAI tool calling | Loses governance context injection + trust-report patterns already aligned with Claude Code |
| Fork Claude Code | Proprietary, ToS, maintenance nightmare |

## Action items

1. **Research agent** to inventory `@anthropic-ai/claude-agent-sdk` surface:
   - What primitives it exposes
   - Which of our features are already covered there vs new code needed
   - Installation path (Node-only? Python wrapper available?)
   - Pricing model (free SDK + user's Anthropic API key = pay per token)
   → Report goes to `.cognitive-os/reports/claude-agent-sdk-surface-<date>.md`.

2. **ADR-062 Phase 3** adds `providers/claude_sdk.py` as opt-in provider
   (only when the direct Anthropic API credential is set and current policy allows it). Default cascade does NOT
   include it.

3. **No further Agent() replication work** beyond ADR-062 phases.

## Verification

- `docs/adrs/ADR-063-*.md` exists and states the decision.
- Research report lands within 1 week (blocked on research agent output).
- `lib/providers/claude_sdk.py` added as part of ADR-062 Phase 3 (opt-in).
- No file in `lib/` attempts to reimplement MCP protocol or Claude Code
  session transcript format.

## Related

- ADR-049 — Provider cascade (qwen,claude today)
- ADR-051 — Qwen agent loop (Phase 1-4 shipped)
- ADR-056 — Adaptive dispatch (L3 per-skill opt-in)
- ADR-060 — Local-only policy (paid/cloud providers opt-in)
- ADR-062 — Multi-provider agent loop (the executor of this scope decision)
- `@anthropic-ai/claude-agent-sdk` — upstream SDK

## Open questions

1. **Python wrapper for claude-agent-sdk**: Anthropic's SDK is
   Node-primary. A Python wrapper would reduce runtime complexity for
   our stack. Status TBD — check in research phase.
2. **MCP-heavy skills future**: if a skill we want to run via ADR-062
   loop needs MCP, we either re-write the skill to not need MCP, or
   route through Claude Code native. Default = Claude Code native.
