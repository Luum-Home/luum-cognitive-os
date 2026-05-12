# Cognitive OS Core Preamble

Use this profile when adopting Cognitive OS as a small guardrail layer instead of
the full maintainer operating system.

## Contract

- Keep agents from leaking secrets, destroying work, writing on protected main,
  or editing files concurrently without coordination.
- Prefer repair-first messages over abstract policy.
- Do not load maintainer/lab governance unless explicitly requested.
- Treat all non-core primitives as opt-in.

## Core primitives

- secret detection
- destructive git/rm protection
- direct-main guard
- concurrent write guard
- edit lock guard
- symlink mutation guard
- scope marker portability guard

## Operator rule

If a gate blocks legitimate work, repair the unsafe state first. Demote or bypass
only with an explicit operator decision and leave an audit trail.
