# Execution Discipline

> Rules for keeping the master plan real, non-duplicative, and durable across sessions.

## Why This Exists

The master plan only matters if it changes day-to-day execution.

This document makes three expectations explicit:

- build what is real, not what only sounds advanced
- avoid duplicating logic when a shared contract or resolver should exist
- preserve session continuity through durable memory instead of relying on recall

## 1. Real Over Aspirational

Every new change should be evaluated against a simple question:

**Does this produce a real capability, or only a plausible story?**

A change is real when at least one of these becomes true:

- code behavior changes in a verifiable way
- a test locks the new contract
- a check or audit can observe the new state
- a document now reflects a real constraint, invariant, or workplan

Avoid these failure modes:

- describing portability that is not yet tested
- documenting a future subsystem as if it were part of the current product
- creating wrappers, layers, or abstractions without a real consumer
- adding “support” for a harness that still depends on another harness behind the scenes

## 2. Shared Logic Before Duplicate Logic

When a behavior needs to exist in more than one place, prefer:

1. a shared contract
2. a shared resolver
3. a shared helper
4. duplicated logic only as a temporary, explicitly documented exception

This rule is especially important for:

- runtime path resolution
- settings projection
- artifact discovery
- installer target resolution
- portability checks and release checks

The standard is not “no duplication ever.”

The standard is:

**do not let the same rule silently fork across Bash, Python, Go, and docs without declaring the shared source of truth.**

## 3. Durable Memory Hierarchy

Session continuity must not depend on remembering the repository from scratch.

The memory hierarchy is:

1. **Repository artifacts**  
   Docs, checklists, contracts, tests, and workplans are the primary durable memory.
2. **Compressed operator memory in `.codex/`**  
   Use compact maps, test matrices, and change-zone guides to avoid re-reading the whole repo.
3. **Engram or other MCP-backed memory when actually available**  
   Use MCP memory for cross-session continuity, decisions, and discoveries only when the tool is surfaced in the current environment.
4. **Conversation recall**  
   Lowest-trust layer. Useful, but never the only source of truth.

## 4. Engram Rule

Engram is part of the intended Cognitive OS memory model, but it must be treated honestly.

- If Engram is available in the current session, use it to persist important discoveries, decisions, and work handoffs.
- If Engram is not surfaced as an available MCP tool, do not pretend the memory was saved.
- In that case, save the same information into repository artifacts and `.codex/` compressed memory instead.

The rule is:

**memory claims must match actual available tooling.**

## 5. Session Handoff Rule

Before ending a significant work session:

- update the active workplan or checklist
- document any new analysis that changes understanding of the product or architecture
- record the next safe step and the still-dangerous step
- prefer linking the exact artifact that preserves that state

If MCP memory is available, mirror the same conclusions there.

If it is not available, the repository artifacts remain the authoritative handoff.

## 6. Practical Standard

Good execution in this repository means:

- the product gets more believable as it grows
- the contracts get clearer as portability expands
- future sessions need less rediscovery, not more
- the system becomes easier to change because the logic is more centralized, not more copied

The goal is not maximum abstraction.

The goal is:

**a product that keeps getting more real, more portable, and easier to continue without losing the thread.**
