# Product Zones

> The operating taxonomy for keeping Cognitive OS focused, durable, and honest about what is real today.

## Why This Exists

Cognitive OS has enough surface area to become either a durable product or an unfocused "system that does everything."

The product zone taxonomy prevents that drift.

It classifies repository surfaces into four zones:

- `core`: the stable product center
- `compatibility`: adapters and projections that absorb ecosystem churn
- `extensions`: optional capabilities that add value without defining the kernel
- `experimental`: future-facing work that needs proof before product-center promotion

The machine-readable source of truth is [manifests/product-zones.yaml](../manifests/product-zones.yaml).

## Zone Definitions

### Core

Core surfaces directly support the product promise:

**governable, verifiable, portable coding agents in real repositories.**

Core includes the canonical hook context, policy engine, package spec, capability profiles, outcome metrics, bootstrap synchronization, settings-driver resolution, and compact governance index.

Core should be small. If everything is core, nothing is protected.

### Compatibility

Compatibility surfaces absorb churn from providers, IDEs, gateways, tool schemas, and harness settings formats.

Provider adapters, harness projections, MCP registration drivers, and driver-specific script surfaces belong here.

Compatibility can be critical without being kernel. That distinction is what lets the product age well as vendors and tools change.

### Extensions

Extensions are useful optional capabilities: skills, broader rule packs, packages, dashboards, workflows, MCP helpers, templates, examples, and presets.

Extensions should be easy to install, disable, ignore, or replace. They should strengthen adoption without crowding the first-contact product story.

### Experimental

Experimental surfaces are high-variance or future-facing: squads, organization modeling, production control-plane infrastructure, generated artifacts, and roadmap material.

Experimental does not mean bad. It means not yet a product guarantee.

## Promotion Rules

A surface can move closer to core only when it earns the promotion:

- It strengthens governance, verification, or portability in real repositories.
- It has automated tests and a manual proof path.
- It does not require a specific vendor unless that dependency is isolated behind a compatibility driver.
- It can be explained to a new user without requiring them to understand the whole OS.

## Operating Rule

When adding or changing a major runtime surface, classify it first.

If the classification is unclear, default away from core. Put the work in compatibility, extensions, or experimental until evidence proves it belongs closer to the product center.

## Root Guardrails

The taxonomy also defines root-level guardrails in [manifests/product-zones.yaml](../manifests/product-zones.yaml). These guardrails do not classify every file one by one. Instead, they set the default expectation for new work under major roots:

- `hooks`, `lib`, `scripts`, `cmd/cos`, and `pkg` are treated as protected runtime surfaces.
- `internal` is treated as the compatibility boundary for provider and adapter churn unless a stable contract is explicitly promoted.
- `skills`, `rules`, `templates`, `packages`, `dashboard`, and `workflows` are extension-first.
- `squads`, `agents`, and future control-plane surfaces stay experimental until they have repeatable operator workflows, tests, and proof paths.

The contract test fails if those root guardrails disappear. This keeps new work from quietly drifting into the product center without an explicit decision.

## Current Product Interpretation

The top-level product should be described as:

**Cognitive OS is the operational layer for coding agents that makes governance, verification, and portability work in real repositories.**

Everything else should support that promise from its proper zone.

## Validation

The taxonomy is backed by:

- [manifests/product-zones.yaml](../manifests/product-zones.yaml)
- [tests/contracts/test_product_zones.py](../tests/contracts/test_product_zones.py)
- [docs/business/feature-reality-audit.md](business/feature-reality-audit.md)
- [docs/business/master-plan-checklist.md](business/master-plan-checklist.md)
