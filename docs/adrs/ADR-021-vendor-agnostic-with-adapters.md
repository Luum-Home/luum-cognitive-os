# ADR-021: Vendor-Agnostic State with Provider Adapters

**Date:** 2026-04-16
**Status:** Accepted
**Commits:** (documents existing pattern + prescribes adapter approach)
**Supersedes:** None
**Related:** ADR-008 (Multi-Tool Support), ADR-012 (Prompt-Driven Governance)

## Context

The Cognitive OS maintains its own state for many concepts that Claude Code also tracks natively:

| Concept | COS state | Claude Code native |
|---------|-----------|---------------------|
| Active tasks | `.cognitive-os/tasks/active-tasks.json` | Task panel (Agent + Bash) |
| Todo lists | Engram `work_queue` | TodoWrite tool |
| Session memory | Engram `session_summary` | `~/.claude/memory/` |
| Skill catalog | `skills/CATALOG.md` + skill_router | Native skill system |

This is intentional duplication per ADR-008 (multi-tool support). If we used Claude Code's native APIs directly, the OS would only work in Claude Code and break in Codex/Gemini/Cursor/Windsurf.

However, the duplication has a cost: users running in Claude Code don't see our OS-managed state in the native Task panel, TodoWrite UI, or memory browser. It feels disconnected.

## Decision

**Maintain vendor-agnostic state as the source of truth. Add thin provider adapters that expose our state to each tool's native UIs when the tool is active.**

Specifically:
1. `.cognitive-os/` directory remains the canonical state (works in any tool)
2. For each supported provider (Claude/Codex/Gemini/Cursor/Windsurf), implement an adapter that:
   - Reads from our canonical state
   - Syncs relevant pieces to the provider's native APIs/UIs
   - One-way sync: our state → provider UI (provider UI changes don't override our state)
3. Adapters live in the provider package (`internal/provider/claude.go`, etc.)
4. Adapters are activated only when the provider is detected (Auto detection)

## Alternatives Considered

### Alt 1: Use Claude Code native APIs directly
- Pro: Full integration with Claude Code UI
- Pro: Less code to maintain
- Con: Breaks multi-tool support (ADR-008)
- Con: Breaks if Claude Code API changes
- Con: Can't share state across tools

### Alt 2: Keep total isolation (current state)
- Pro: No vendor coupling at all
- Pro: Simplest to maintain
- Con: Poor UX — features invisible to users in Claude Code UI
- Con: Loses the value proposition "best of both worlds"

### Alt 3: Adapter pattern (chosen)
- Pro: Keeps vendor-agnostic core
- Pro: Integrates with native UI when available
- Pro: Adapters are small, testable, per-provider
- Con: More code (1 adapter per provider)
- Con: Dependency on each provider's API stability

## Consequences

### Positive
- Users in Claude Code see OS-managed tasks in the native Task panel
- Users in Codex see them in Codex's UI
- Switching tools doesn't lose state — canonical state travels with the repo
- Provider APIs can evolve independently — we only update the adapter

### Negative
- Need to implement 5 adapters (Claude/Codex/Gemini/Cursor/Windsurf)
- Each provider API change requires adapter update
- Slight state sync overhead (our state → provider UI)

### Implementation

Tasks:
1. Define adapter interface in `internal/provider/provider.go`:
   ```go
   type Provider interface {
       // ... existing methods ...
       SyncTaskPanel(tasks []Task) error         // NEW
       SyncTodoList(todos []TodoItem) error      // NEW
       SyncMemory(summary string) error          // NEW
   }
   ```
2. Implement for Claude first (it has the most mature APIs)
3. Add SessionStart hook that runs initial sync
4. Add PostToolUse hook that updates on state change

### Migration

Existing OS agentic primitives stay as-is. Adapters are added incrementally:
- Phase A: Claude Task panel sync (highest user visibility)
- Phase B: Claude TodoWrite sync
- Phase C: Claude memory sync
- Phase D: Other providers

## Features that should use this pattern

| OS primitive | Claude Code equivalent | Status |
|---|---|---|
| `.cognitive-os/tasks/active-tasks.json` | Task panel | To adapt (Phase A) |
| Engram `work_queue` | TodoWrite | To adapt (Phase B) |
| Engram `session_summary` | `~/.claude/memory/` | To adapt (Phase C) |
| `skills/CATALOG.md` | Native skill system | To evaluate |
| Hooks in settings.json | — (we already use these) | N/A — already integrated |

## References

- [Claude Code Hooks](https://code.claude.com/docs/en/hooks)
- ADR-008: Multi-Tool Support — the reason we duplicate state
- ADR-012: Prompt-Driven Governance — similar pattern for rules
