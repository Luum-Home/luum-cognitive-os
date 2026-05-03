# Boring Reliability Control Plane

## Goal

Make Cognitive OS adoptable in layers and keep governance honest with small,
operator-readable signals. The point is not more ceremony; the point is to know
whether the SO is reducing damage and friction.

## Adoption layers

| Layer | Purpose | Budget |
|---|---|---|
| `core` | 5-10 killer safety primitives for most projects. | Small default-visible surface and low preamble. |
| `team` | Collaboration and claim coordination for shared repos. | More gates, still bounded. |
| `maintainer` | Solo-swarm mode for the SO maintainer running multiple IDEs/sessions/agents. | Larger surface accepted, but measured. |
| `lab` | Experimental/meta-governance primitives. | Not product default; no shame in keeping things here. |

## Tools

| Tool | Signal |
|---|---|
| `scripts/cos-adoption-profile --profile core` | Counts primitives/hooks/default-visible/blocking by adoption layer. |
| `scripts/cos-preamble-budget --profile core` | Estimates token tax for a profile. |
| `scripts/cos-default-visible-reducer` | Proposes demotions from core/team to lab. |
| `scripts/cos-false-positive-ledger` | Reads metrics for bypass/false-positive signals. |
| `scripts/cos-wip-safety-score` | Scores dirty WIP, stashes, and pre-agent snapshot markers. |
| `scripts/cos-recovery-drill --scenario all` | Runs non-destructive recovery drill tests. |
| `scripts/cos-runtime-hook-reality --fail-on-findings` | Proves runtime hooks match lifecycle and observable behavior. |
| `scripts/cos-boring-reliability --profile core` | Aggregates the operator dashboard. |

## North-star metrics

- false-positive events decrease;
- WIP loss/stash orphan risk decreases;
- preamble tokens decrease;
- readiness gets more honest, not merely greener;
- default-visible hooks decrease for `core`;
- recovery drill pass rate increases;
- runtime reality coverage remains 100%.

## Operating doctrine

A gate is allowed to be default-visible only when it is:

1. **real** — observable runtime behavior matches metadata;
2. **measurable** — it emits or declares metrics;
3. **reversible** — rollback/repair command is present;
4. **documented honestly** — docs claim level does not exceed maturity;
5. **evidence-backed** — core/team/blocking entries have executable evidence.

If a primitive cannot satisfy the contract, it belongs in `lab` or `candidate`,
not in the product default.
