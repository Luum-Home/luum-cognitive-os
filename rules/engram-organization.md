<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Engram Organization — Path Segregation (BMAD v6 Pattern 8)

## Purpose

Organize Engram topic keys into a structured prefix system so that different types of knowledge are segregated, searchable, and don't collide.

## Topic Key Prefix System

All Engram topic keys MUST use one of these prefixes:

| Prefix | Purpose | Examples |
|--------|---------|----------|
| `planning/{change-name}/...` | Proposals, specs, designs, task breakdowns | `planning/auth-refactor/proposal`, `planning/auth-refactor/spec` |
| `implementation/{service-name}/...` | Code decisions, patterns used, implementation notes | `implementation/<consumer-codename-b>/pagination-pattern`, `implementation/bff/caching-strategy` |
| `docs/{topic}/...` | Documentation decisions, doc structure, writing conventions | `docs/api-reference/structure`, `docs/changelog/format` |
| `agent/{agent-name}/sidecar` | Per-agent persistent memory (Pattern 4 sidecar) | `agent/sre-agent/sidecar`, `agent/squad-manager/sidecar` |
| `sre/{container}/{error-type}` | Operational learnings, fixes, incident patterns | `sre/api-server/oom-kill`, `sre/mongodb/connection-timeout` |
| `architecture/{topic}` | Architectural decisions, ADRs, system-wide patterns | `architecture/auth-model`, `architecture/event-bus-design` |
| `sprint/{sprint-id}/...` | Sprint goals, status, retros | `sprint/2026-w12/goal`, `sprint/2026-w12/retro` |
| `config/{topic}` | Configuration decisions, env setup, infrastructure | `config/docker-compose/ports`, `config/auth/realm-setup` |
| `bugfix/{service}/{issue}` | Bug investigations and fixes | `bugfix/gateway/jwt-expiry-race`, `bugfix/api/db-reconnect` |

## Migration from Legacy Flat Keys

Old SDD flat keys (`sdd/{change}/...`) map to the new prefix system:

| Old Key | New Key |
|---------|---------|
| `sdd/{change}/proposal` | `planning/{change}/proposal` |
| `sdd/{change}/spec` | `planning/{change}/spec` |
| `sdd/{change}/design` | `planning/{change}/design` |
| `sdd/{change}/tasks` | `planning/{change}/tasks` |
| `sdd/{change}/apply-progress` | `implementation/{change}/apply-progress` |
| `sdd/{change}/verify-report` | `planning/{change}/verify-report` |
| `sdd/{change}/archive-report` | `planning/{change}/archive-report` |
| `sdd/{change}/explore` | `planning/{change}/explore` |
| `sdd/{change}/state` | `planning/{change}/state` |
| `sdd-init/{project}` | `config/{project}/sdd-init` |
| `sre-fix/{container}/{error}` | `sre/{container}/{error}` |

### Migration Guide

1. **No bulk migration needed** — old keys remain readable via `mem_search`
2. **New writes use new prefixes** — all `mem_save` calls from this point forward use the prefix system
3. **When reading old data**: if `mem_search` with new prefix returns nothing, fall back to old prefix
4. **Gradual migration**: when an old-prefix observation is read and updated, save it under the new prefix (upsert with new `topic_key`)
5. **SDD phases**: The SDD sub-agent context protocol now uses `planning/` prefix instead of `sdd/`

## Rules

### Naming Conventions

- Use lowercase kebab-case for all path segments: `planning/auth-refactor/spec` (not `Planning/AuthRefactor/Spec`)
- Service names match directory names: `<consumer-codename-b>`, `<consumer-codename-a>`, `onboarding`, `payments-service`
- Change names match what the user calls them: `add-biometrics`, `refactor-payments`
- Agent names match their definition in `agents/`: `sre-agent`, `squad-manager`

### Branch-Aware Topic Keys (Optional)

For feature branches, topic keys can include a `@branch` suffix to scope observations:

```
planning/auth-refactor/spec               # Main branch (default)
planning/auth-refactor/spec@feature/auth   # Feature branch specific
```

**When to use branch scoping:**
- Working on a feature branch with experimental decisions
- Multiple people working on different branches of the same change
- Decisions that only apply to the branch, not the main codebase

**When NOT to use:**
- Architectural decisions (always project-scoped)
- Bug fixes (usually apply globally)
- Learnings and discoveries (shared knowledge)

**Search protocol with branches:**
1. Search with branch suffix: `planning/{change}/spec@{branch}`
2. Fall back to unscoped: `planning/{change}/spec`
3. Fall back to legacy: `sdd/{change}/spec`

### Search Strategy

When searching for an artifact in Engram:

1. Search with the full prefixed topic key: `mem_search(query: "planning/auth-refactor/spec")`
2. If not found, search with legacy key: `mem_search(query: "sdd/auth-refactor/spec")`
3. If not found, search by keywords: `mem_search(query: "auth refactor spec")`

### Branch-Aware Topic Keys (Optional)

For feature branches, topic keys can include a `@branch` suffix to scope observations:

```
planning/auth-refactor/spec               # Main branch (default)
planning/auth-refactor/spec@feature/auth   # Feature branch specific
```

**When to use branch scoping:**
- Working on a feature branch with experimental decisions
- Multiple people working on different branches of the same change
- Decisions that only apply to the branch, not the main codebase

**When NOT to use:**
- Architectural decisions (always project-scoped)
- Bug fixes (usually apply globally)
- Learnings and discoveries (shared knowledge)

**Search protocol with branches:**
1. Search with branch suffix: `planning/{change}/spec@{branch}`
2. Fall back to unscoped: `planning/{change}/spec`
3. Fall back to legacy: `sdd/{change}/spec`

### Write Rules

- Always include `topic_key` in `mem_save` calls
- Use `mem_suggest_topic_key` if unsure about the right prefix
- Different topics MUST NOT share the same topic key
- Same topic evolving over time MUST use the same topic key (upsert, not duplicate)

### Agent Sidecar Memory

Each agent can maintain persistent state under `agent/{agent-name}/sidecar`:

```
mem_save(
  title: "SRE Agent — known container health patterns",
  topic_key: "agent/sre-agent/sidecar",
  content: "...",
  type: "pattern",
  scope: "project"
)
```

This allows agents to accumulate learnings across sessions without polluting the shared namespace.

## Configuration

In `cognitive-os.yaml`, add under `memory`:

```yaml
memory:
  provider: engram
  organization:
    enforce_prefixes: true       # Warn on writes without valid prefix
    valid_prefixes:
      - planning
      - implementation
      - docs
      - agent
      - sre
      - architecture
      - sprint
      - config
      - bugfix
    legacy_fallback: true        # Search old sdd/ prefix as fallback
    migrate_on_read: true        # Re-save under new prefix when old data is read
```
