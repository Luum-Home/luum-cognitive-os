# Master Plan Execution Requirements

> What must become true for the durable product master plan to become product discipline instead of documentation.

## Why This Document Exists

The durable product master plan is a strategic direction. This document turns
that direction into execution requirements.

The goal is simple:

**Cognitive OS should become easier to understand, easier to adopt, easier to verify, and harder to invalidate as the AI ecosystem changes.**

That requires enforcement in code, automation, onboarding, and product
structure, not just agreement in documents.

## The Seven Requirements

## 1. An Inviolable Product Promise

The entire repository should align around one product promise:

**Cognitive OS is the operational layer that makes coding agents more governable, verifiable, and portable in real repositories.**

This promise should act as a filter.

If a subsystem does not strengthen that promise, it should not become part of
the visible product center.

### Enforcement standard

- README and onboarding should express the same promise
- architecture decisions should be explainable through the same promise
- new features should justify how they strengthen governance, verification, portability, or real-repository reliability

## 2. A Small and Protected Core

The core should include only the durable system nucleus:

- canonical hooks
- context model
- policy engine
- package specification
- capability profiles
- outcome metrics

Everything else should default to one of these zones:

- adapter
- package
- plugin
- experimental

The boundary already started in:

- [docs/kernel-contract.md](../kernel-contract.md)
- [manifests/kernel-contract.yaml](../../manifests/kernel-contract.yaml)

The next step is to make that boundary enforceable across more of the runtime.

### Enforcement standard

- kernel contracts remain explicit and machine-readable
- non-core subsystems are not hardcoded into central runtime paths by default
- new additions must declare whether they belong to core, compatibility, extension, or experimental scope

## 3. Strategy Must Become Enforcement

Capability-centric design cannot stop at `lib/model_router.py`.

It must propagate into:

- dispatch
- gateway selection
- skill routing
- execution records
- metrics and evaluation

The system should reason in terms of capabilities before it reasons in terms of
vendors, model names, or benchmark-era aliases.

### Enforcement standard

- routing paths use execution profiles or capability contracts first
- provider-specific choices remain adapter decisions where possible
- logs and metrics stay meaningful when model vendors change

## 4. CI Must Prove the Real Product

The repository currently claims more than default automation proves.

That gap must close.

The default CI path should cover the real product core with:

- representative Python unit tests
- Go tests for kernel and provider layers
- contract tests
- key behavior tests
- documentation integrity checks

If a claim appears in the product story, README, or pitch, there should be a
test or verification path that backs it up.

### Enforcement standard

- CI represents the default product narrative
- broken documentation references are treated as defects
- core claims cannot drift away from automation coverage

## 5. Onboarding and Operation Must Feel Simple on the Outside

If the product is meant to be accessible to real teams and not only agent
infrastructure specialists, the operational experience must reflect that.

That means:

- one-pass installation
- strong defaults
- autodetection where possible
- clear user-facing messages
- minimal required configuration
- visible performance characteristics

`hooks/self-install.sh` should feel like product behavior, not an internal
implementation detail.

### Enforcement standard

- first-run setup is fast and predictable
- non-experts can reach a working baseline without learning the whole architecture
- performance-sensitive setup flows have explicit budgets and tests

## 6. Complexity Must Be Deliberately Compressed

The repository should be classified into four explicit zones:

- core
- compatibility
- extensions
- experimental

That taxonomy only matters if it changes decisions.

The repo should archive, freeze, or de-emphasize agentic primitives that compete for
attention with the main wedge without strengthening it directly.

### Enforcement standard

- major docs reflect the taxonomy clearly
- non-core systems are presented as optional or secondary
- the visible product story is shorter than the subsystem inventory

## 7. Superiority Must Be Visible

Architecture by itself is not enough.

The product needs proof points that a new user, evaluator, or adopter can see
quickly.

Those proof points should include:

- switching providers without rewriting the system
- running real quality gates
- showing provider-agnostic outcome metrics
- installing and using the core in minutes
- demonstrating resilience to ecosystem churn

### Enforcement standard

- the repo contains demos or verification artifacts for core claims
- provider portability is demonstrated, not merely described
- reliability and governance are visible to someone who is new to the project

## Execution Order

Recommended sequence:

1. Fix documentation drift and redefine README plus CONTRIBUTING around the product core.
2. Redesign CI around the actual core product surface.
3. Extend capability-centric routing and the compatibility layer across the runtime.
4. Optimize self-install and onboarding flows.
5. Classify and de-center non-core subsystems.
6. Prepare a canonical five-minute demo.

## Success Condition

The product is succeeding when:

- a new user can understand it quickly
- installation is low-friction
- core value is visible through real evidence
- the system is useful without requiring agent infrastructure expertise
- advanced depth remains available as the user grows into it

The standard is not maximum breadth.

The standard is:

**a product that is easy to start, serious enough to trust, and durable enough to grow with the ecosystem instead of aging into irrelevance**
