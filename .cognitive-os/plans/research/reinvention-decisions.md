# Reinvention Decisions — Post-Audit Documentation

## Purpose
Documents decisions that were made implicitly during initial development (March 27-31, 2026)
and were identified by the reinvention audit as lacking justification.

## 1. Engram vs Honcho (Hermes Memory Layer)

### What they have
Honcho by Plastic Labs — MIT licensed, HTTP API, dialectic reasoning about users,
cross-session persistence, profile segmentation.

### What we built
Engram — Go binary, SQLite+FTS5+WAL, topic key prefix system, MCP server,
deduplication via normalized_hash, sync infrastructure.

### Why we kept Engram (post-hoc justification)
- Engram is a local Go binary with zero external dependencies. Honcho requires an API server.
- Engram's SQLite+FTS5 gives us 8ms query latency with no network hop.
- Our topic_key prefix system (planning/, implementation/, bugfix/) is more structured than Honcho's categories.
- Engram's sync infrastructure enables team sharing via git — Honcho uses cloud sync.
- However: Honcho's dialectic user modeling is superior. We're building lib/user_model.py to close this gap.

### Future action
- KEEP Engram as primary storage
- ADOPT Honcho's user modeling concept via lib/user_model.py (done)
- ADOPT Hermes's holographic hybrid retrieval via lib/memory_retriever.py (done)
- EVALUATE Honcho as an optional plugin if more sophisticated user modeling is needed
- ADD to adoption-registry.yaml: document this decision

## 2. Squad System vs Composio Fleet Management

### What they have
Composio — 43K lines, 3,288 tests, git worktree per agent, planner/executor dual-layer,
JIT context management, agent-agnostic (Claude, Codex, Aider), runtime-agnostic (tmux, Docker).

### What we built
Squad system — squads/*.yaml, ManagerAgent, squad-protocol.md, workload scheduler,
orchestrator mode with ClaudeExecutor.

### Why we kept our system (post-hoc justification)
- COS is Claude Code-native. Composio is agent-agnostic but that generality adds complexity we don't need.
- Our squad system integrates with Engram, phase-aware behavior, and SDD pipeline.
- However: Composio's JIT context management (routing only relevant tool definitions) is superior.
  We partially address this with context-optimization.md but not at Composio's level.

### Future action
- KEEP squad system for Claude Code-native orchestration
- ADOPT Composio's JIT context pattern: only route relevant tools per agent task
- EVALUATE Composio's worktree-per-agent pattern for high-blast-radius tasks
- Document this in competitive-landscape.md evaluation section

## 3. SDD Artifacts vs Spec Kit Compatibility

### What they have
GitHub Spec Kit — 72K stars, 22+ agent platform support, 3-phase spec (requirements/design/tasks),
cross-platform compatibility.

### What we built
SDD 7-phase pipeline with custom artifact format (proposal/spec/design/tasks/apply/verify/archive).

### Why we kept our format (post-hoc justification)
- Our 7-phase pipeline is more rigorous than Spec Kit's 3 phases.
- Retry loops, adversarial review, and consequence tracking are unique to our pipeline.
- However: our artifacts are NOT compatible with Spec Kit, meaning we can't leverage their 22-platform ecosystem.

### Future action
- KEEP our 7-phase pipeline for internal rigor
- ADD Spec Kit export: a converter that outputs our specs in Spec Kit format
- This enables: using Spec Kit-compatible agents for implementation while keeping our review rigor
- Priority: LOW (do when we need cross-platform support)

## 4. Pattern: "Documented But Never Executed"

The audit revealed a recurring pattern: evaluate → recommend → never execute.
This happened with:
- Spec Kit compatibility (recommended, never done)
- SWE-bench calibration (recommended, never done)
- Antigravity cherry-picking (recommended, never done)
- Aguara activation (implemented, never enabled)
- Trail of Bits wiring (installed, never routed)

### Prevention mechanism
Created lib/reinvention_guard.py + hooks/reinvention-check.sh that:
1. Checks upstream submodules before building new features
2. Checks docs/ for evaluated-but-not-adopted tools
3. Checks adoption-registry.yaml for already-adopted features
4. Adds "suggest web search for new alternatives" as step 5

Additionally, added to rules/reinvention-prevention.md:
- Every "recommended" action gets a tracking issue or engram observation
- Recommendations without execution within 2 sprints are escalated
