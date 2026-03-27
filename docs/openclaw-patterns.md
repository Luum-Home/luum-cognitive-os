# OpenClaw Patterns Adopted into Cognitive OS

> Patterns analyzed from the OpenClaw codebase and adapted for Cognitive OS.

## What is OpenClaw?

OpenClaw is an open-source AI agent framework that demonstrates production-grade patterns for LLM agent reliability, self-improvement, and operational resilience. We analyzed its codebase to extract the best patterns applicable to our Cognitive OS.

## Adopted Patterns

### 1. Pre-Compaction Memory Flush

**Source**: OpenClaw's session lifecycle management
**Implementation**: `.claude/hooks/pre-compaction-flush.sh` (PreCompact hook)

**Why**: Before context compaction, the agent's working memory is about to be truncated. Without a flush, decisions and discoveries made during the session are lost forever. The hook emits a system message reminding the agent to save to Engram before compaction.

**Impact**: Eliminates the "amnesia problem" where sessions restart without knowledge of what happened before.

### 2. SOUL.md + IDENTITY.md

**Source**: OpenClaw's agent personality definition pattern
**Implementation**: `.claude/SOUL.md`, `.claude/IDENTITY.md`

**Why**: Agents without explicit behavioral boundaries tend toward performative helpfulness instead of genuine competence. SOUL.md defines core principles and communication style. IDENTITY.md defines the agent's role and specialization.

**Impact**: More consistent agent behavior -- direct answers, proactive risk flagging, honest uncertainty.

### 3. Progressive Disclosure for Skills

**Source**: OpenClaw's `references/` pattern for skill documentation
**Implementation**: `references/` subdirectories in sre-agent and systematic-debugging skills

**Why**: Loading all skill documentation into context at invocation wastes tokens when only a subset is needed. Moving reference docs to a `references/` directory lets the SKILL.md serve as a navigation hub -- the agent loads detailed docs only when needed.

**Impact**: Reduced token consumption per skill invocation. The main SKILL.md stays focused on execution protocol while detailed reference material is loaded on demand.

### 4. Tool Loop Detection

**Source**: OpenClaw's tool usage monitoring
**Implementation**: `.claude/hooks/tool-loop-detector.sh` (PostToolUse hook, matcher: `*`)

**Why**: Agents sometimes get stuck in loops -- calling the same tool with the same arguments, or ping-ponging between two tools without making progress. This wastes tokens and time. The hook tracks the last 10 tool calls and detects three patterns:
- `generic_repeat`: Same tool+args 3+ times in a row
- `ping_pong`: Two tools alternating (A->B->A->B)
- `no_progress`: Same Read/Grep on same file 3+ times

**Impact**: Early detection of unproductive loops, saving tokens and reducing session time.

### 5. 4-Tier Resilience Model

**Source**: OpenClaw's multi-tier fault tolerance architecture
**Implementation**: `.claude/rules/fault-tolerance.md` (updated)

**Why**: Our original fault tolerance covered agent task recovery but lacked structure around connection resilience, LLM call resilience, and context resilience. OpenClaw's 4-tier model provides a comprehensive framework:
- **Tier 1**: Connection resilience (reconnection, heartbeat, graceful shutdown)
- **Tier 2**: LLM call resilience (model fallback, rate limiting, retry budgets)
- **Tier 3**: Context resilience (pre-compaction flush, session summaries)
- **Tier 4**: Agent resilience (orphan detection, task recovery, idempotent re-launch)

**Impact**: Structured approach to reliability at every layer of the agent stack.

### 6. Cost Tracking Protocol

**Source**: OpenClaw's per-agent cost awareness
**Implementation**: `.claude/rules/cost-tracking.md`

**Why**: Without cost awareness, agents default to the most capable (and expensive) model for every task. The cost tracking protocol establishes a model selection matrix, budget alerts, and optimization strategies.

**Impact**: Right-sized model selection reduces cost without sacrificing quality. Alerts prevent runaway spending.

### 7. Credential Management

**Source**: OpenClaw's credential matrix pattern
**Implementation**: `.claude/rules/credential-management.md`

**Why**: Consolidates credential handling rules that were previously spread across constitutional-gates.md and services-config.md. Adds explicit validation patterns, rotation guidance, and prohibited patterns.

**Impact**: Single source of truth for credential handling. Startup validation patterns catch missing credentials before they cause runtime errors.

## Patterns Considered but Not Adopted

| Pattern | Reason |
|---------|--------|
| Multi-agent supervisor tree | Our Agent Teams + SDD workflow already covers this |
| Custom MCP transport layer | Not needed -- we use standard MCP servers (Engram, Context7) |
| Agent personality hot-swap | Single-domain agent (fintech) -- personality consistency is more important |
| Custom prompt caching | Delegated to Claude's built-in caching mechanism |

## Files Created/Modified

| File | Action | Category |
|------|--------|----------|
| `.claude/hooks/pre-compaction-flush.sh` | Created | Hook |
| `.claude/hooks/tool-loop-detector.sh` | Created | Hook |
| `.claude/SOUL.md` | Created | Identity |
| `.claude/IDENTITY.md` | Created | Identity |
| `.claude/rules/fault-tolerance.md` | Updated | Rule |
| `.claude/rules/cost-tracking.md` | Created | Rule |
| `.claude/rules/credential-management.md` | Created | Rule |
| `.claude/skills/sre-agent/references/` | Created | Skill structure |
| `.claude/skills/systematic-debugging/references/` | Created | Skill structure |
| `.claude/settings.local.json` | Updated | Config |
| `docs/ai-ecosystem/openclaw-patterns.md` | Created | Documentation |
| `docs/ai-ecosystem/INDEX.md` | Updated | Documentation |
