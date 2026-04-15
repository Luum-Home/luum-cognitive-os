# ADR-001: Reuse klaudiush Predicate System

## Status

Accepted

## Context

We need a way to match validators to hook events. Options:
1. Build our own predicate/matcher system from scratch
2. Adopt klaudiush's predicate combinator system (MIT license)
3. Use a generic rule engine (OPA/Rego, Cedar)

klaudiush has a mature predicate system with composable combinators (`And`, `Or`, `Not`, `EventIs`, `ToolTypeIs`, `CommandContains`, `GitSubcommandIs`, `FilePathMatches`, etc.) backed by 400+ lines of tested Go code including Bash AST parsing via `mvdan.cc/sh/v3`.

## Decision

Adopt klaudiush's `validator.Registry` and predicate system wholesale. Copy the source code (MIT license permits this) rather than importing as a Go module dependency, since we will extend the type system with additional canonical events and provider types.

## Consequences

- We gain 400+ lines of tested predicate logic immediately
- Bash AST parsing gives us accurate git subcommand detection across `&&` chains
- We are coupled to klaudiush's naming conventions (CanonicalEvent, ToolFamily), but these are sensible
- Future klaudiush improvements require manual cherry-picking since we copied rather than imported
- The predicate combinator pattern composes cleanly and is the strongest part of klaudiush's design
