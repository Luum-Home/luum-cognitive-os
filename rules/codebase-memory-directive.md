# Structural Code Discovery — conditional, never unconditional

> **The directive fires only when the graph can answer.** An order to consult a
> knowledge graph "FIRST" is worth something when the graph holds this project,
> and is worth less than nothing when it does not: the agent spends a tool call
> to learn the graph is empty, then greps anyway. The precondition is not
> etiquette — it is the whole content of the rule.

**Status:** advisory (ADR-343). Recommend-only. This repo does not install
`codebase-memory-mcp`, does not write MCP config for any harness, and does not
require the server to be present.

## The rule

Before using `codebase-memory-mcp` tools (`search_graph`, `query_graph`,
`trace_path`, `get_architecture`, `search_code`, ...) for structural code
discovery, both conditions must hold:

1. the server is reachable on this machine, **and**
2. **this project** is present in its graph.

Check with one command:

```bash
python3 scripts/check_codebase_memory_readiness.py     # 0 READY / 1 NOT_READY / 2 ERROR
python3 scripts/check_codebase_memory_readiness.py --json
python3 scripts/check_codebase_memory_readiness.py --explain
```

| Result | What the agent does |
|---|---|
| `READY` (exit 0) | Graph tools are a legitimate first move for "who calls X", "what depends on Y", impact radius, dead code. |
| `NOT_READY` (exit 1) | **Do not call the MCP tools.** Use `Grep`/`Glob`/`Read`. Do not index on your own initiative — indexing is an operator action. |
| `ERROR` (exit 2) | Treat as `NOT_READY` and say the check failed. |

## Measured state of this repo (2026-08-15)

`NOT_READY` — server reachable, 8 projects in the graph, none of them this one.
So an unconditional "graph FIRST" directive, applied here today, points at
nothing. Reproduce with the command above.

## What this rule is not

- **Not an adoption.** Nothing from the upstream project is vendored, ported, or
  reimplemented here. The server is an optional external tool the operator may
  or may not have. See ADR-343 for how this sits against the external-tool
  adoption freeze.
- **Not a replacement for Graphify.** `manifests/primitive-lifecycle.yaml`
  requires, for Graphify sunset, "an owned COS context graph primitive with
  equivalent receipts". A third-party MCP is not owned and has shown no
  equivalent receipts, so this rule does not authorise retiring anything.
  Measured overlap is 3 of 11 capabilities; the other 8 do not compete.
- **Not an efficiency claim.** Nobody has measured graph-vs-grep on *this*
  repository. This rule does not assert the MCP is faster, cheaper, or more
  accurate here; it only prevents a directive from firing into an empty graph.
  Any future claim that it is better needs its own benchmark and its own command.
- **Not an installer.** If the operator wants the server, the vendor ships its
  own multi-harness installer (`codebase-memory-mcp install`, which auto-detects
  the supported agents). The Cognitive OS does not reimplement that contract.

## Contextual trigger

Structural code questions — "who calls this", "trace the call chain", "what
depends on", "impact analysis", "dead code", "explore the architecture" — and
any moment an agent is about to reach for `codebase-memory-mcp` tools.
