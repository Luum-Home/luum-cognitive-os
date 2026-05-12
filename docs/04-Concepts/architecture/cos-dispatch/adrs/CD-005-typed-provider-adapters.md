# ADR-005: Typed Provider Adapters over Generic JSON Mapper

## Status

Accepted

## Context

Each AI coding agent has a different JSON format for hook events. We need to normalize these into a canonical format. Options:
1. Generic JSON-to-JSON mapper using JSONPath expressions or transformation rules
2. Typed Go adapters per provider (~60-80 lines each)

The generic approach is more flexible but loses type safety and makes debugging harder. The typed approach requires code changes for new providers but each adapter is small, testable, and explicit.

## Decision

Typed Go adapters per provider. klaudiush already has Claude, Codex, and Gemini adapters. We extend with Cursor and Windsurf.

Each adapter implements the `Provider` interface:
- `Detect()`: check env vars to identify the active agent
- `Parse([]byte)`: convert agent-specific JSON to canonical `hook.Context`
- `BuildResponse()`: convert validation results back to agent-specific format
- `ConfigPaths()`: return paths to the agent's config files

## Consequences

- Each adapter is 60-80 lines of Go, fully testable in isolation
- Type safety prevents runtime JSON mapping surprises
- Adding a new provider is explicit: create a file, implement 4 methods, add to registry
- The trade-off versus a generic mapper is that new providers require code changes, but the code is trivial
- Provider-specific quirks (Cursor uses camelCase events, Windsurf has cascade context, Gemini uses GEMINI_PROJECT_DIR) are handled in one place per provider
- Provider detection is deterministic: check env vars in order, fall back to Claude Code
