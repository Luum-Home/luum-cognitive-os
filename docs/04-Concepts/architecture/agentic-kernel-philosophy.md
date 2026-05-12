# Agentic Kernel Philosophy

## Thesis

Cognitive OS should be treated as an **agentic kernel**, not as a bundle of
prompts, hooks, and dashboards. Its job is to make coding agents safe enough to
compose, parallelize, and recover in real repositories without relying on agent
memory or operator heroics.

The product goal is not "more governance". The product goal is a small,
reliable kernel that lets many agents work without silently corrupting state.

## Kernel shape

```text
agentic kernel
├── safety primitives       # block destructive or unsafe actions
├── scheduler/coordination  # claims, branch leases, merge queue, session events
├── memory subsystem        # persistent decisions, bugfixes, discoveries
├── drivers                 # Claude Code, Codex, Bare CLI, future harnesses
├── telemetry               # timing, false positives, WIP safety, dispatch/cost
└── optional modules        # maintainer and lab features, not boot-critical
```

The analogy is deliberate: a robust OS kernel does not load every possible
driver into the critical boot path. Cognitive OS should not load every hook,
rule, skill, and meta-governance tool into the default agent path.

## Design law

A primitive may be default-visible only when it is:

1. **real** — implementation and runtime behavior agree;
2. **measurable** — it emits evidence or has executable proof;
3. **reversible** — rollback or repair is explicit;
4. **honest** — docs claim level does not exceed maturity;
5. **evidence-backed** — tests or smoke commands prove the behavior.

Anything else belongs in `maintainer`, `lab`, `candidate`, or `archived` until it
earns promotion.

## Small core, rich modules

The core is not the whole SO. The core is the part that must be boringly
reliable for a new user:

- secret protection;
- destructive git/rm protection;
- concurrent write safety;
- WIP/stash visibility;
- runtime reality checks;
- local landing gate;
- minimal onboarding path.

Maintainer mode can keep heavier tools for solo-swarm development: deeper
readiness dashboards, primitive lifecycle analytics, false-positive ledgers,
recovery drills, self-improvement loops, and cross-session orchestration.

Lab mode can keep ambitious experiments without pretending they are product
promises.

## Boot path doctrine

`SessionStart` is the kernel boot path. It must be treated as scarce.

A hook should run at `SessionStart` only if at least one of these is true:

- it repairs or prevents immediate WIP/state loss;
- it initializes state required by the next user action;
- it starts a daemon that cannot be lazily started safely;
- it verifies a critical invariant that would be dangerous to discover later.

Everything else should move to one of:

- lazy on first relevant tool use;
- scheduled/weekly audit;
- explicit maintainer command;
- background monitor outside the synchronous boot path;
- lab-only projection.

This is the next maturity frontier after the Boring Reliability Control Plane:
measuring cold-start is not enough; the runtime projection must make the core
boot path smaller.

## Driver doctrine

The kernel owns canonical intent. Harness drivers translate that intent into
Claude Code, Codex, Bare CLI, and future IDE surfaces.

Drivers must not overclaim parity. Each driver should publish capability status:

- `production` — implemented and covered by tests;
- `production_with_gaps` — implemented, but constrained by harness events;
- `poc` — useful but not product-grade;
- `enum_only` — named but not implemented;
- `unsupported` — explicit non-goal for now.

Cross-harness credibility comes from honest capability declarations, not from
listing IDE names in manifests.

## Culture

The cultural rule is stricter than the technical one:

> If it does not compile, prove, or recover, it does not enter the kernel path.

The SO can contain experiments, but the kernel path should stay small,
boring, and fiercely defended. That is how Cognitive OS becomes a durable layer
for agentic development rather than another overgrown framework.

## Current execution implications

1. Keep `core` small and enforceable.
2. Reduce `SessionStart` for core instead of only measuring preamble tokens; enforce it with `scripts/cos-session-start-budget --profile core`.
3. Keep control-plane tools as maintainer primitives with `runtime_projection:
   false` unless they truly belong in the runtime path.
4. Treat `legacy_audited` silent failures as visible debt that should shrink.
5. Do not claim Cursor/Continue/OpenCode parity until driver status is stronger
   than `enum_only`.
6. Prefer demotion over deletion: move features out of the kernel path before
   deciding whether to archive them.

## Related artifacts

- [Boring Reliability Control Plane](boring-reliability-control-plane.md)
- [Kernel Contract](../kernel-contract.md)
- [COS Distribution Boundaries](../adrs/ADR-124-cos-distribution-boundaries.md)
- [Agentic Primitive Lifecycle Governor](../adrs/ADR-126-agentic-primitive-lifecycle-governor.md)
- [Core 30-Minute Onboarding](../getting-started/core-30-minute-onboarding.md)
