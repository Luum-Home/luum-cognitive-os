<!-- SCOPE: both -->
# Context7 Auto-Trigger — Library Documentation Lookup

## Purpose

Before implementing with any external library, agents should check Context7 for up-to-date documentation. This prevents hallucinated APIs, deprecated patterns, and version mismatches.

## Rule (Always Active)

When an agent task involves using an external library (npm package, Python package, Go module, etc.), the agent SHOULD:

1. Resolve the library in Context7: use the `context7` MCP tool to find current docs
2. Check version compatibility with the project's dependencies
3. Use the documented API, not assumed patterns

## Auto-Trigger Signals

The rule activates when agent prompts or code contain:
- `import` / `require` / `from X import` statements for unfamiliar libraries
- Package installation commands (`npm install`, `pip install`, `go get`)
- References to library APIs the agent hasn't verified

## Integration

Context7 is available as an MCP server. No additional installation needed if already configured.

## Caching

Frequently-used library docs should be cached in Engram under topic key `docs/libraries/{library-name}` to avoid repeated lookups.

## Graceful Degradation

If Context7 is unavailable, the agent proceeds with its training knowledge but notes the uncertainty in the Trust Report.
