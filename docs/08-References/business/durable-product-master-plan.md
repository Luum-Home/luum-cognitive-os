# Durable Product Master Plan

> How Cognitive OS becomes a durable product instead of an ever-expanding system of interesting subsystems.

## Executive Summary

Cognitive OS has real technical depth, but its current strategic risk is not primarily code quality. It is focus drift.

The repository currently presents multiple centers of gravity at once:

- package manager
- dispatch engine
- hook operating system
- persistent memory layer
- observability stack
- dashboard
- auto-repair runtime
- agent teams and squads

Each of those can be valuable. Together, they create a risk: the project starts looking like a total system before it has nailed one unmistakable wedge.

This master plan defines how to reduce that risk and turn the repository into a durable product with a clearer user promise, a smaller core, better validation discipline, and more visible proof that the system is real.

## The Core Product Thesis

The best version of Cognitive OS is not:

**"the system that does everything for AI agents."**

It is:

**"the most reliable operational layer for coding agents working in real repositories."**

That means the product should optimize for:

- governance
- verification
- portability
- durability under provider change
- visible evidence of reliability

It should de-emphasize:

- breadth for its own sake
- architecture tourism
- subsystems that are more impressive than adopted
- optional capabilities presented as if they were the product itself

## The Wedge

The wedge should be narrow, defensible, and demonstrable in minutes.

Recommended wedge:

**Cognitive OS makes coding agents more governable, verifiable, and portable across providers in real repositories.**

This wedge is strong because:

- it is specific
- it is compatible with the current architecture
- it survives model churn
- it is testable
- it can be shown in a short workflow

### What the wedge is not

The wedge is not:

- agent society infrastructure
- a general multi-agent platform
- an all-in-one AI developer cloud
- a dashboard-first product
- a research playground for every interesting agent pattern

Those may still exist, but they should feel like extensions, not like the center of gravity.

## Competitive Reality

Cognitive OS is not only competing against single-tool coding assistants.

It is also competing against:

- agent runtimes
- agent orchestration layers
- agent infrastructure frameworks
- autonomous software-engineering platforms

In practice, that means the comparison set includes systems such as Agent Zero,
OpenClaw, Hermes, and similar agent-management or agent-infrastructure
projects.

That matters because those systems often look stronger on first contact in at
least one of these dimensions:

- simpler onboarding
- more obvious autonomy
- broader runtime scope
- more visible orchestration features
- stronger perception of "complete system" ambition

If Cognitive OS tries to beat them by looking even larger or more totalizing,
it will likely become harder to maintain before it becomes easier to adopt.

The better strategy is different:

- be narrower
- be more credible
- be easier to verify
- be easier to port across providers and harnesses
- be more operationally trustworthy in real repositories

### Strategic implication

The product should not present itself as:

- the biggest agent platform
- the broadest autonomous framework
- the most feature-complete agent society

It should present itself as:

**the governance and operational reliability layer that makes coding agents safe, portable, and measurable in real repositories**

That framing creates a more durable position against broader systems.

Agent Zero, OpenClaw, Hermes, and similar systems may win on breadth,
interface, or perceived autonomy. Cognitive OS should aim to win on:

- governance
- verification
- execution discipline
- portability
- measurable reliability

Those are harder to fake, easier to test, and more durable under ecosystem
change.

## The Five Product Corrections

### 1. Reduce visible centers of gravity

The user should not need to mentally process eight products at once.

#### Product-facing center

The visible center should be:

- canonical hook/runtime integration
- policy and quality enforcement
- capability-centric execution
- provider portability
- outcome measurement

#### Extension-facing center

These should be presented as optional or secondary:

- advanced dashboard
- squads and organizational orchestration
- experimental auto-repair depth
- broad package ecosystem
- infrastructure-heavy observability layers

### 2. Align CI with actual repository complexity

The current CI surface does not represent the actual test surface of the repo.

Observed issue:

- `.github/workflows/ci.yml` runs shell loops over `tests/unit/test-*.sh` and `tests/integration/test-*.sh`
- the repository contains hundreds of Python tests
- the repo appears heavily tested, but the default CI path does not reflect that reality

This creates a credibility gap between:

- what the repo claims
- what the default automation proves

#### Required correction

The default CI path should validate the real product core:

- kernel contract tests
- capability-centric routing tests
- provider compatibility tests
- manifest/package contract tests
- representative Python unit tests
- representative behavior tests
- Go kernel/provider tests

#### Principle

If a subsystem is important enough to appear in the product story, it must be represented in default automation.

### 3. Remove documentation drift

Trust erodes quickly when docs reference missing files or outdated commands.

Observed issues already found:

- `README.md` references `docs/benchmark-results.md`, which does not exist
- `CONTRIBUTING.md` references `tests/run-all-tests.sh`, while the actual script is `scripts/run-all-tests.sh`

This is small in isolation but large in meaning. Drift signals that the system is growing faster than it is being curated.

#### Required correction

Every product-facing doc should be treated as executable documentation:

- links must resolve
- commands must exist
- paths must exist
- setup steps must be runnable
- examples must reflect the current repo

### 4. Make performance debt visible and non-aspirational

A durable product cannot hide behind architecture while core flows are slow.

Observed issue:

- the self-hosting performance test expects `<2s`
- `hooks/self-install.sh` exceeded that expectation and hit a 5-second timeout in behavior testing

This is exactly the kind of issue that separates a credible product from an ambitious framework.

#### Required correction

Performance-sensitive flows should have:

- explicit budgets
- automated enforcement
- regression tests
- visible reporting

If a hook or initialization path is core, it must be treated like a product performance feature, not like an implementation detail.

### 5. Separate defensible core from template/scaffold surface

The repository contains a meaningful amount of scaffold/template/document-heavy material. That is not inherently bad. It helps adoption and packaging.

The risk is interpretive:

- the visible size of the repo can make the core feel less sharp
- the code-to-scaffold ratio can make the system look more complete than it is
- optional packages may look like product commitments instead of extensions

#### Required correction

The project should clearly distinguish:

- **kernel**
- **core product runtime**
- **compatibility layer**
- **extension packages**
- **scaffolding/templates**
- **experiments / roadmaps**

That makes the defendable product nucleus easier to understand and harder to dilute.

## Three Strategic Bets

These are the three bets most likely to convert the repository from “ambitious platform” to “durable product.”

### Bet 1: Reliability over breadth

Invest more in making the core operational layer undeniable than in broadening the universe of features.

Examples:

- stronger contract tests
- stronger behavior tests
- narrower but more credible CI
- better performance budgets
- fewer undocumented exceptions

Success condition:

The product becomes trusted because it fails less, proves more, and is easier to reason about.

### Bet 2: Capability-centric portability

The product should become known for surviving provider change gracefully.

Examples:

- execution profiles instead of model-first policy
- explicit compatibility inventory
- outcome metrics that remain meaningful regardless of provider
- reduced provider-specific assumptions in user-facing logic

Success condition:

Switching providers changes adapters and policy tuning, not the product identity.

### Bet 3: Product clarity as architecture discipline

A clear product story should constrain architecture.

If a subsystem does not strengthen the wedge directly, it should be:

- optional
- deprioritized
- moved to extension status
- documented as experimental

Success condition:

Users can explain the product in one sentence and find the proof for that sentence inside the repo quickly.

## What To Cut Back

This is not a statement that these areas are worthless. It is a statement about product sequencing.

### De-emphasize for now

- dashboard-first messaging
- organization/squad-heavy messaging
- infrastructure-heavy observability as part of the main promise
- advanced auto-repair narratives that exceed proven behavior
- broad package ecosystem messaging before core adoption exists

### Keep, but frame as extension

- packages beyond core quality and compatibility
- advanced business/vision docs
- experimental ADR roadmaps
- niche or domain-specific scaffolding
- advanced automation or orchestration patterns

### Make central

- kernel contract
- capability-centric execution
- compatibility layer
- outcome metrics
- provider portability
- real repository workflows
- tangible verification artifacts

## Acceptance Criteria For “Less Aspirational, More Real”

The product is moving in the right direction when the following become true.

### Core clarity

- a new user can identify the product wedge within 2 minutes
- the kernel and extension boundary is explicit
- the product promise is shorter than the subsystem inventory

### Validation integrity

- default CI covers real Python and Go product surfaces
- product-facing claims map to automated tests
- broken references and stale commands are treated as defects

### Performance credibility

- self-hosting initialization and core hooks have explicit budgets
- performance regressions fail visibly
- “must be fast” claims are backed by tests

### Portability credibility

- provider compatibility is represented explicitly
- capability-centric routing remains test-covered
- outcome metrics do not collapse when providers change

## Implementation Phases

### Phase 1 — Product boundary cleanup

Goals:

- declare kernel and core product boundaries
- document the wedge clearly
- classify extension zones
- reduce ambiguous messaging

Deliverables:

- kernel contract
- durable product docs
- visible core-vs-extension language in docs

### Phase 2 — Validation realignment

Goals:

- make CI reflect the actual repository
- define representative default test suites
- treat doc drift as a real failure mode

Deliverables:

- updated CI workflows
- doc integrity checks
- representative Python + Go + behavior coverage in default automation

### Phase 3 — Reliability hardening

Goals:

- fix self-hosting performance debt
- add budgets and regression tests
- promote core operational paths over expansion

Deliverables:

- performance baselines
- regression thresholds
- visible runtime reliability metrics

### Phase 4 — Product compression

Goals:

- compress the external story into a smaller, clearer promise
- demote non-core narratives
- make the repo easier to navigate for first-time adopters

Deliverables:

- simplified top-level docs
- sharper contributor path
- clearer extension taxonomy

### Phase 5 — Orchestration substrate (landed 2026-05-06/07)

Goals:

- close the orchestration coverage gap against the May 2026 frontier (Claude Code 2.x, Cursor 3, Codex App, Devin 2, Replit Agent, Copilot CLI/Cloud, OpenCode, GitButler, Aider, OpenHands)
- promote constraints (license, footprint, test-tier matrix, verdict block) from chat directives to a versioned, machine-readable manifest
- ship 14 ADRs (220–236, ADR-229 tombstone) under that contract
- preserve honest 🟡 status for slices not yet hardened

Deliverables (all in `main`):

- evaluation contract: `manifests/orchestration-research-evaluation.yaml`
- substrate (Tier 1): ADR-220/221/222/223/226/227/228/230 — `lib/{session_bus, event_wrap, shadow_git, dispatch_gate, retry_classifier, session_budget, handoff_envelope, handoff_dispatcher}.py` + 11 schema-versioned manifests + 20+ test files
- consumers (Tier 2): ADR-225/231/233 — branch-per-task, MCP server (FastMCP, 8 tools), cross-session agent-team file-IPC
- opt-in adapters (Tier 3): ADR-224/232/234/235/236 — shadow-state safety net, sandbox tiers (Bubblewrap/Seatbelt), policy-as-code, detached-agent daemon, deferred tool loading
- substrate-consumer guardrail: `scripts/validate_substrate_consumers.py` (14/14 PASS on 2026-05-07)
- public tracking: `docs/research/orchestration-gaps/IMPLEMENTATION-CHECKLIST-2026-05-07.md`
- second case study: `docs/business/case-study.md` §"Case Study 2"

Posture: Phase 5 closed the orchestration coverage gap structurally, but T6 (perf budget multi-platform), T7 (chaos), T8 (cross-harness end-to-end), T9 (adoption truth re-run), T10 (audit invariants extension) are explicit hardening pendings. Phase 6 picks those up.

### Phase 6 — Hardening across the substrate (next)

Goals:

- multi-platform perf baselines for the event-sourced bus (Linux + Docker, currently macOS+APFS only)
- chaos tier coverage for kill-mid-dispatch on the handoff path
- cross-harness end-to-end (Codex / OpenCode round-trip for ADR-228/230/233)
- ADR-217 adoption-truth re-run with the new dependencies (FastMCP, OTel MCP semconv)
- ADR-211 service-mode readiness gate re-audit against the post-Phase-5 substrate
- IMPLEMENTATION-CHECKLIST 🟡 → ✅ migration for the first 4 substrate ADRs

This phase does not add new ADRs; it closes the explicit pendings the Phase-5 checklist tracks.

## Immediate Next Actions

1. Fix known documentation drift in `README.md` and `CONTRIBUTING.md`.
2. Redesign default CI so it exercises representative Python and Go product surfaces.
3. Triage `hooks/self-install.sh` against its behavior-test performance budget.
4. Publish a simple “what is core vs extension” taxonomy.
5. Keep broad subsystems, but stop presenting them as the product center.

## Final Principle

The durable version of Cognitive OS is not the repo that contains the most ideas.

It is the repo where the most important ideas are:

- easiest to identify
- easiest to verify
- easiest to maintain
- hardest to invalidate as the AI ecosystem changes

That is the standard for good aging.
