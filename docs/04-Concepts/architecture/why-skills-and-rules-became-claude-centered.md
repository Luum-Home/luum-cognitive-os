# Why Skills and Rules Became Claude-Centered

This document explains why Cognitive OS ended up with skills and rules so
closely tied to `.claude/`, and why that state is a mix of valid historical
design and current portability debt.

The goal is not to blame the earlier architecture. The goal is to understand
which parts were rational, which parts became sticky, and which parts must now
change.

## Short Answer

Skills and rules became Claude-centered because Claude Code was the first
complete host environment that offered all of these at once:

- recursive rule loading
- project-level skill discovery
- project-level hook registration
- user + project configuration accumulation
- a shared repo-local `.claude/` convention

That made `.claude/` the cheapest place to get a working operating system with
real governance, real discoverability, and low setup friction.

So the current state did not happen by accident. It happened because:

- Claude offered the best native execution substrate
- Cognitive OS optimized hard for practical adoption inside that substrate
- the multi-harness story came later than the first operational architecture

## The Historical Layers

### 1. Claude was the first full-fidelity host

Early Cognitive OS was not choosing between several equally mature harnesses.
It was building on the one environment that already provided:

- hooks
- rules
- skills
- project-scoped instructions
- user/project accumulation behavior

That meant the fastest path to a real, working system was to leverage
`.claude/` directly instead of inventing a parallel abstraction for everything.

At that stage, this was the right tradeoff.

## 2. `.claude/` solved both discovery and team-sharing

Using `.claude/` was not only about Claude itself. It also solved important
product problems:

- project-level behavior could live in the repo
- teams could commit shared rules and skills
- discovery happened natively
- the OS could piggyback on the host tool instead of shipping a custom loader

This dramatically lowered the amount of custom infrastructure required for the
first useful versions of the system.

## 3. The three-layer model reinforced the pattern

The repo's own architecture documented a three-layer model:

- `.cognitive-os/` for universal OS agentic primitives
- `{project}/.claude/` for project extensions
- generated project artifacts under `.claude/`

That was a coherent model for a Claude-first operating system:

- universal logic in `.cognitive-os/`
- project-specific exposure and native host integration in `.claude/`

The problem is not that this model was incoherent. The problem is that it was
never fully re-founded once portability became a first-class goal.

## 4. Rules optimization happened inside Claude's loading model

When ADR-015 migrated many rules into hooks and compressed the always-loaded
surface into `RULES-COMPACT`, the optimization still assumed Claude's recursive
rule loading behavior under `.claude/rules/`.

That means rule architecture improved significantly, but within a Claude-native
contract:

- fewer loaded rules
- more hook enforcement
- better token budgets

All of that was real progress, but it did not yet replace Claude's rule-loading
surface with a Cognitive OS-native discovery contract.

## 5. Skills followed the same path for a different reason

Skills became Claude-centered for slightly different reasons:

- Claude already had a recognizable project skill surface
- user/project skill accumulation was useful
- the harness could discover and expose those skills naturally

The repo did add `.cognitive-os/skills/cos/` as a kernel path, but the harness
visible path remained `.claude/skills/`.

So skills ended up in a split state:

- partially canonical in storage
- still Claude-centered in discovery

## 6. Multi-harness support started by adapting edges, not redefining artifacts

ADR-008 correctly identified the need for multi-tool support, but the first
portability moves focused on:

- provider adapters
- hook adapters
- rule format transforms
- MCP surfaces

That was a sensible place to start because it created portability quickly at
the runtime edge.

But it did not redefine the deeper artifact contract for skills and rules.

So the architecture evolved like this:

- first: make the Claude-based system real
- then: make runtime behavior less Claude-only
- now: realize that skills/rules still inherit the old center of gravity

## What Was Correct Then

These were not mistakes:

- exploiting Claude's native loading/discovery surfaces
- using `.claude/` to reduce custom infrastructure
- shipping project-shared rules and skills through repo-local conventions
- optimizing rule loading inside the host tool that actually ran the system
- introducing `.cognitive-os/` incrementally instead of pausing delivery for a
  total rewrite

Those decisions made the OS tangible.

## What Became Debt Later

These are now the problematic leftovers:

- `.claude/` still acts as the implied source of truth for too many artifacts
- installer/export logic still resolves skills and rules directly to
  Claude-facing paths
- docs and tooling still explain discovery in Claude terms first
- portability claims can outrun the actual artifact contract
- the system has a canonical runtime area, but not yet a fully canonical
  discovery contract for skills and rules

This is the real debt:

**the system gained a portability ambition larger than the artifact contract it
originally grew on.**

## The Important Nuance

Not everything Claude-centered is wrong.

There are two different kinds of `.claude/` usage:

### Legitimate driver projection

When `.claude/` is used because Claude genuinely needs a driver-facing surface.

### Undeclared source-of-truth behavior

When `.claude/` is used because the system still implicitly thinks in Claude's
artifact model.

The first is healthy.
The second is the problem.

## What Has To Change Now

The next phase is not "delete `.claude/`".

It is:

1. define a Cognitive OS-native canonical contract for skills and rules
2. keep `.claude/` as an explicit driver projection where needed
3. update tooling, installer logic, and tests to understand that hierarchy
4. only then demote `.claude/` from implicit center to explicit harness layer

## Strategic Conclusion

Skills and rules became Claude-centered because Claude was the first place
where Cognitive OS could become real without inventing a complete new runtime
ecosystem first.

That was a rational founding move.

But the repo is now aiming for something bigger:

- a portable operating layer
- durable across harness changes
- not trapped inside the conventions of any one tool

That means the architecture must now do the harder second step:

**separate "what made the system possible first" from "what should remain the
source of truth going forward."**

## References

- `docs/02-Decisions/adrs/ADR-008-multi-tool-support.md`
- `docs/02-Decisions/adrs/ADR-015-rules-to-hooks-migration.md`
- `docs/04-Concepts/root/rules-loading-architecture.md`
- `docs/04-Concepts/root/global-vs-project-config.md`
- `docs/04-Concepts/root/os-vs-project-separation.md`
- `docs/04-Concepts/architecture/skills-rules-portability-gap.md`
- `docs/04-Concepts/architecture/skills-rules-canonicalization-risk-analysis.md`
