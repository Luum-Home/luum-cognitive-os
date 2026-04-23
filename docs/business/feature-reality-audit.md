# Feature Reality Audit

> A feature-by-feature audit of where Cognitive OS is genuinely portable and valuable, where it is still Claude-advantaged, and where complexity is outrunning product proof.

## Executive Summary

Cognitive OS is not empty overengineering. There is a strong and defensible
product core inside the repository.

That core is:

- governance for coding agents
- verification and quality gates
- portability across providers and harnesses
- a runtime contract that survives ecosystem churn better than vendor-first tools

The main risk is not that the system lacks substance.

The main risk is that a valuable product core can get buried under too many
adjacent subsystems, future-facing control-plane ideas, and top-level narratives
that imply more runtime maturity than the current product really delivers.

The practical goal of this audit is to separate:

- what should stay in the core
- what should remain but be treated as a driver or optional package
- what should be demoted from product-center messaging

## Taxonomy

The durable repository taxonomy is defined in [Product Zones](../product-zones.md)
and [manifests/product-zones.yaml](../../manifests/product-zones.yaml).

This audit uses an additional feature-level lens to evaluate portability,
current product value, and complexity risk.

### Portability State

- `core-agnostic`: works through stable internal contracts and does not depend on a specific harness capability
- `driver-projected`: the core behavior is portable, but installation, settings, or UX require a harness-specific driver
- `claude-advantaged`: the feature can exist elsewhere, but Claude Code currently provides a meaningfully better host
- `claude-only`: the feature depends on harness behavior that is not currently portable in practice

### Product Value

- `high`: directly strengthens the wedge of governable, verifiable, portable coding agents
- `medium`: useful support capability, but not the reason the product wins
- `low`: interesting or potentially strategic, but not proven as part of the current wedge

### Complexity Risk

- `low`: cost is proportional to current product value
- `medium`: useful, but can drift into platform sprawl if left unbounded
- `high`: likely to dilute focus unless tightly scoped or demoted

## Audit Table

| Feature Area | Portability State | Product Value | Complexity Risk | Assessment | Recommendation |
|---|---|---:|---:|---|---|
| Canonical hook context and provider normalization | `core-agnostic` | High | Low | This is one of the strongest parts of the repo. It is the right abstraction boundary for future-proofing. | Keep in core and keep hardening. |
| Runtime bootstrap and settings projection | `driver-projected` | High | Medium | This is essential product work, not peripheral plumbing. Until this layer is strong, portability claims remain partial. | Keep in core. Continue explicit harness drivers. |
| Rules, skills, and hook governance | `driver-projected` | High | Medium | Strong differentiator when framed as operational discipline rather than “lots of files.” | Keep in core, but package optional rule packs more aggressively. |
| Capability-centric routing and outcome metrics | `core-agnostic` | High | Low | This is central to aging well across model churn. It supports the durable-system thesis directly. | Keep in core and expand enforcement. |
| Quality gates and verification flows | `driver-projected` | High | Medium | This is one of the clearest reasons teams would adopt Cognitive OS. | Keep in core. Make proof paths easier to demonstrate. |
| Package manager and package ecosystem (`cmd/cos`) | `driver-projected` | Medium | Medium | Valuable, but secondary to the main product promise. It should support adoption, not become the product story. | Keep, but de-emphasize in top-level messaging. |
| Memory and Engram-backed recall | `claude-advantaged` | Medium | Medium | Useful and strategically interesting, but not yet the safest wedge to lead with. | Keep as optional/advanced capability. |
| Session lifecycle, checkpointing, crash recovery | `claude-advantaged` | Medium | Medium | Real value exists, but some of the host signals still depend on richer harness behavior. | Keep, but market as “best on supported hosts,” not universally equal. |
| Auto-repair, rollback, and SRE-style remediation loops | `driver-projected` | Medium | High | Useful in principle, but very easy to oversell. Needs visible proof and bounded scope. | Keep as advanced package surface, not primary story. |
| Observability dashboards and control-plane style monitoring | `core-agnostic` | Medium | High | Helpful for mature teams, but currently too easy to position as more central than it should be. | Demote from top-level narrative. Keep as optional operational layer. |
| Squads, organizations, and software-factory framing | `claude-only` to `claude-advantaged` | Low to Medium | High | This is where the repo most strongly risks feeling larger than the proven product. | Demote heavily. Treat as future architecture, not current wedge. |
| Full “13-layer operating system” framing | `n/a` | Low | High | Architecturally interesting, but too expansive for the current product maturity. | Replace with a simpler product story in top-level surfaces. |

## What Looks Like Real Product Core

The most credible durable product core today is:

- canonical event and context normalization
- portability layer and harness drivers
- policy and quality-gate enforcement
- capability-centric execution decisions
- provider-agnostic outcome metrics
- installation and onboarding that make those capabilities usable in real repos

This is enough to be a serious product thesis.

It does not need a large organization/control-plane narrative to be valuable.

## What Currently Feels Overengineered

The repository starts to feel overengineered when it presents the following as
co-equal parts of the current product:

- squads and organization modeling
- software-factory framing
- broad control-plane language
- dashboards and observability as top-level identity
- advanced remediation loops without a short proof path

These are not necessarily bad ideas.

They become overengineering when they consume narrative weight, maintenance
budget, and mental overhead before the core wedge is undeniably proven.

## Product Truths To Keep

- The repo already contains real infrastructure, not just aspirational docs.
- The portability thesis is directionally correct.
- The system can become unusually durable if it keeps treating vendors and models as drivers, not as the product center.
- The strongest moat is operational discipline for coding agents, not “being the biggest system.”

## Product Truths To Stop Hiding From

- Some major surfaces are still Claude-advantaged or Claude-only in practice.
- Not every advanced subsystem should be in the top-level story.
- The current documentation still exposes more architectural ambition than product proof.
- The product will likely improve by subtraction as much as by addition.

## Recommended Product Boundary

The product should currently be presented as:

**Cognitive OS is the operational layer for coding agents that makes governance, verification, and portability work in real repositories.**

Everything else should be framed as one of:

- core runtime support
- harness driver
- optional package
- future architecture

## Immediate Actions

1. Keep the kernel, portability, routing, and verification surfaces at the center of docs and demos.
2. Move squads, organization language, and large control-plane metaphors out of first-contact documentation.
3. Mark advanced remediation, dashboards, and memory-heavy flows as optional or advanced.
4. Audit feature claims so portability language only covers `core-agnostic` and `driver-projected` surfaces.
5. Build demos around the real wedge: install, govern, verify, switch harness/provider, inspect outcomes.

## Success Condition

This audit is succeeding when:

- new users can identify the core product in minutes
- portability claims are narrower but more believable
- advanced subsystems still exist without crowding the wedge
- the repository feels more like a durable product and less like a totalizing agent platform
