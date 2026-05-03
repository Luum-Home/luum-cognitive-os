---
adr: 132
title: Solo-Swarm vs Multi-Maintainer Fork — Documenting the Pending Strategic Decision
status: exploration
date: 2026-05-03
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: [strategy, adoption, governance, future-work, architecture-fork]
---

# ADR-132: Solo-Swarm vs Multi-Maintainer Fork — Documenting the Pending Strategic Decision

## Status

**Exploration.** This ADR does not commit to an architectural change.
It captures a decision that is **pending** so future-self has a
starting point instead of re-deriving the question from scratch.

The decision should be made deliberately, with a rested head, and
when the trigger condition (below) actually fires — not on the same
night the question was raised.

## Context

The Cognitive OS is the work of a single maintainer over roughly
4–6 months. The architecture has been built, refined, and audited
against itself. It is operationally sound for the maintainer's
workflow. Specific design decisions visible in the codebase make
the single-maintainer assumption explicit:

- ADR-131 declares the maintainer's machine as the SPOF and
  defers multi-maintainer concerns explicitly: *"acceptable for
  solo dev; revisit when a second maintainer joins"*.
- The `maintainer` adoption tier in `manifests/primitive-lifecycle.yaml`
  is named *solo-swarm mode for the SO maintainer running multiple
  IDEs / sessions / agents*.
- 1,580 silent-failure occurrences across 201 files are accepted
  in the current allowlist; this baseline was set by the maintainer
  after auditing them personally. A second maintainer cannot inherit
  that mental cache.
- 162 skills, 116 hooks, 131 ADRs (this is 132). The cognitive load
  to navigate is currently held in one person's head, supported by
  Engram and the Boring Reliability dashboard.
- The boring-reliability doctrine assumes one person decides what
  qualifies for `core` vs `team` vs `lab`. There is no formal review
  process, code-owners file, or ADR review quorum.

The system is **healthy under these assumptions**. The 2026-05-03
boring-reliability audit confirms 8/10 control-plane tools are REAL,
and the conversion of the 2026-05-02 DX assessment "no-movement"
items into instrumented signals is traceable. Nothing about the
current state requires the fork below.

The fork question arises from the parallel question of expandability
(see the conversation that produced this ADR). Specifically: at what
point does this system need to split into two consumption shapes?

## The Two Shapes

### Shape A — Solo-Swarm COS (current)

The shape the maintainer uses today. Optimised for one person
running multiple IDEs, multiple sessions, multiple background
agents, all on one or two machines they personally control.

Characteristics:

- Engram daemon per machine, no federation protocol beyond rsync
- Locks are local files in `.cognitive-os/runtime/`, no cross-machine
  consensus
- Skill registry has no version-pinning
- ADR review is *the maintainer thinks about it*
- The `maintainer` adoption tier is the default
- Boring-reliability dashboard is operator-pull, not consumer-push
- Documentation assumes the reader knows the maintainer's history

This shape **scales to**: 2 machines, 2–3 harnesses, N concurrent
sessions on one machine, semi-autonomous agents bounded by the
control plane, increasingly capable models (which reduce, not
increase, the governance training-wheels needed).

This shape **does not scale to**: 3+ machines with concurrent
writes, 4+ harnesses without portability bleed, 10+ truly
unsupervised autonomous agents, any multi-maintainer scenario.

### Adoption boundary

`core` and `team` are the externally adoptable product surfaces. They must stay
small, evidence-backed, and understandable without the original maintainer's
mental cache.

`maintainer` is different. It is explicitly **not transferable today**. It is
the solo-swarm operating envelope: one maintainer, multiple IDEs, multiple
sessions, multiple agents, and a large amount of tacit context externalised only
partially through Engram, ADRs, metrics, and the boring-reliability dashboard.

This is not a defect under Shape A. It is the honest trust boundary. A second
human maintainer should not be onboarded directly into `maintainer` mode until
this ADR moves out of `exploration` and the Shape B fork plan exists. Before
that, any contributor consumes `core` or `team`; the original maintainer remains
the only `maintainer` operator.

`scripts/cos-tier-claim-audit` is the first instrument that makes this boundary
less philosophical: ADRs that claim `tier: core` or `tier: team` must now carry a
`cos-boring-reliability` evidence block. That covers decision documents, not the
runtime inventory. The manifest-level companion is
`scripts/cos-manifest-tier-claim-audit`, which audits
`manifests/primitive-lifecycle.yaml` for:

- `core` / `team` primitives without strong distribution evidence;
- `maintainer` primitives whose placement still depends on maintainer knowledge;
- candidates to move to `lab` / `advisory`;
- candidates for a future second semantic demotion under ADR-126.

Together these audits turn ADR-132 from an open philosophical concern into a
measurable adoption-boundary backlog.

The same principle now applies to the silent-failure allowlist. The 1,580
accepted `|| true` / `|| :` / `2>/dev/null` occurrences are no longer an opaque
maintainer memory cache:

- every allowlist entry declares `owner`, `reviewed_on`,
  `transferability_state`, and `shape_b_action`;
- `transferability_state: maintainer_cache` is allowed under Shape A but emits a
  `shape-b-transferability-debt` warning;
- missing owner/review metadata is a hard failure in
  `scripts/cos-silent-failure-audit`;
- architecture readiness propagates the warning so the debt is visible before a
  second maintainer appears.

As of 2026-05-03 the allowlist is fully owned and dated, but still contains
`maintainer_cache` entries. That is deliberate immaturity, not hidden maturity:
Shape A can operate with those entries; Shape B cannot claim transferability
until they are re-reviewed or moved to `externally_reviewed`.

### Shape B — Multi-Maintainer COS (hypothetical)

The shape the system would need if a second human contributor
joined who is not the original maintainer. This is **not the
current shape and explicitly not what is being built today**.

What changes:

- Engram needs scoped permissions (per-maintainer namespaces) and
  a real federation protocol with conflict resolution
- Lock service moves out of filesystem to a real coordinator
  (Redis / Valkey / equivalent)
- Skill registry pinned and versioned, with a SHA-locked install
  manifest
- ADR review process with quorum, code-owners file, formal merge
  approval rules
- The `team` adoption tier becomes the default for new
  contributors, not `maintainer`
- Documentation rewrite: every doc that assumes maintainer
  context becomes context-free
- Onboarding flow that does not require pairing with the
  original maintainer
- Boring-reliability dashboard becomes consumer-push (every
  contributor's environment runs it; the failure surface is
  shared)

This shape **scales to**: small team (2–5 people), distributed
agents across multiple environments, organisational adoption with
defined responsibilities.

This shape **costs**: roughly the same amount of work as the
current system to build. Forking too early means doing this work
before there is anyone to use it.

## The Decision That Is Pending

Not "fork or do not fork", but **"what is the trigger that
justifies the fork?"**

Candidate triggers, ordered weakest to strongest:

1. **A second person expresses interest in contributing.** Weak:
   interest is cheap, sustained contribution is what matters.
2. **A second person submits a non-trivial PR that lands.** Stronger:
   demonstrates capability and willingness.
3. **The maintainer wants to take a meaningful break and have the
   system continue.** Strong: the SPOF problem becomes concrete.
4. **A specific organisation or contributor asks to *consume* the
   COS in a way that does not require the maintainer's pairing.**
   Strongest: real demand exists.

Until trigger 3 or 4 fires, **Shape A is correct**. Building
Shape B speculatively burns cycles that should go to consolidating
Shape A.

## Provisional Constraints (so we do not paint into a corner)

While operating in Shape A, observe these constraints so that
forking later is possible without rebuilding from scratch:

1. **No new feature should hard-code the maintainer's filesystem
   layout.** Use `$COGNITIVE_OS_PROJECT_DIR` / `$CLAUDE_PROJECT_DIR`,
   not absolute paths.
2. **Every new hook MUST declare its harness portability** in
   frontmatter (`harness_specific: true | false | partial`).
   Today this is honor-system; ADR-132 makes it visible. A future
   audit script can enforce.
3. **Every ADR claiming `tier: core` or `team` MUST include
   evidence-block** linked to `cos-boring-reliability` output.
   This already happens informally; ADR-132 names the requirement.
   ADR-133 implements this as `scripts/cos-tier-claim-audit`.
   Runtime manifest claims are tracked by
   `scripts/cos-manifest-tier-claim-audit`.
4. **Engram-stored knowledge MUST use `topic_key`** so namespacing
   per-maintainer is mechanically possible later (the keys become
   prefixes when scopes are introduced).
5. **The maintainer's mental cache** — the things that are obvious
   only because the maintainer wrote them — should be progressively
   externalised into ADRs, the boring-reliability dashboard, and
   `docs/architecture/`. Goal: the gap between what is documented
   and what is true should keep shrinking.
6. **Silent-failure allowances MUST carry transferability metadata.**
   An allowance owned only by the original maintainer is permitted in
   Shape A, but it must say so mechanically. Missing owner/review
   metadata fails; `maintainer_cache` entries warn until reviewed by a
   second maintainer or equivalent external process.

Following these constraints does not commit to Shape B; it keeps
the door open at low cost.

## Acceptance Criteria

This ADR is `exploration` — it has no implementation acceptance
criteria. It satisfies its purpose if:

1. A future maintainer (or future-self) reading this ADR can pick
   up the decision space without re-deriving it.
2. The provisional constraints become visible enough to influence
   day-to-day choices (a new hook's frontmatter, a new ADR's tier
   claim).
3. When trigger 3 or 4 fires, this ADR moves from `exploration`
   to `accepted`, the fork plan is written as ADR-132b or a new
   ADR, and Shape B implementation begins from a known-good
   starting point.

## Border Cases

- **Multiple Claude Code sessions on the same machine** (already
  happening). This is **Shape A**, not Shape B. The
  `cos-session-branch.sh` + branch-writer-lease primitives already
  cover this. No fork needed.
- **A single contributor running on a different machine but still
  it being one human**. Shape A with rsync of `.engram/`. Acceptable
  but degraded; not a fork trigger.
- **An autonomous agent that is not a human**. This is the most
  ambiguous case. If the agent is bounded by the control plane and
  reports back to the maintainer, it is Shape A. If the agent has
  its own approval authority over `core` admissions, it requires
  Shape B governance.
- **A fork happens by mistake** (someone clones the repo and starts
  contributing without coordination). Provisional constraints above
  ensure this is recoverable; the maintainer can absorb their work
  via normal review without an architectural emergency.

## Consequences

**Of writing this ADR (positive).**

- The decision space is named and documented. Future-self does
  not start from zero.
- The five provisional constraints above become explicit, and a
  follow-up audit can check compliance.
- Contributors evaluating the project can read this ADR and
  understand the maintainer's posture without ambiguity.

**Of writing this ADR (negative / risk).**

- Naming the decision creates pressure to act on it. The point of
  status `exploration` is to resist that pressure: not yet.
- Some readers may interpret this as an invitation to contribute.
  It is not. Contribution is welcome but not optimised for.

**Of NOT eventually forking, when the trigger fires.**

- The single-maintainer assumption hardens further. Some Shape B
  changes become more expensive the longer they are deferred
  (Engram federation, in particular).
- Genuine demand for multi-maintainer adoption goes unmet, and the
  system stays implicitly closed.

**Of forking too early.**

- Doubles the maintenance surface immediately. Every change has to
  be evaluated against both shapes.
- Builds infrastructure for users who do not exist. Classical
  speculative-generality failure mode.

## Recommendation

**Stay in Shape A.** Apply the five provisional constraints as soft
discipline. Re-read this ADR when a real trigger fires. Do not
implement Shape B until trigger 3 or 4 happens.

The Cognitive OS is, at the moment, an unusual artefact: a
governance system written by one person that demonstrates how one
person plus disciplined dogfooding plus modern AI tools can produce
the output of a small team. Its singularity is part of its value.
Premature multi-maintenance optimisation would dilute that without
a clear beneficiary.

## Cross-references

- ADR-126 — agentic primitive lifecycle governor (informs the
  demotion discipline that keeps Shape A from monsterising)
- ADR-127 — active primitive index (the runtime-coverage gate that
  Shape B would need to be per-environment, not per-maintainer)
- ADR-130 / ADR-131 — local-CI migration (locks the system into
  Shape A explicitly: maintainer's machine is the SPOF)
- `docs/architecture/boring-reliability-control-plane.md` — the
  doctrine that prevents Shape A from monsterising, and the spine
  of any future Shape B
- `docs/reports/dx-assessment-2026-05-02.md` — the assessment that
  surfaced the question this ADR answers (or rather: defers
  honestly)
- `docs/reports/boring-reliability-audit-2026-05-03.md` — baseline
  metrics that would need parity in any Shape B
