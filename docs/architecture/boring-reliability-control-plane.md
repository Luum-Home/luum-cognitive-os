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
| `scripts/cos-session-start-budget --profile core` | Measures SessionStart hook count, lifecycle tiers, p50/p95 timing, and core lab-hook drift. |
| `scripts/cos-default-visible-reducer` | Proposes demotions from core/team to lab. |
| `scripts/cos-false-positive-ledger` | Reads metrics for bypass/false-positive signals. |
| `scripts/cos-wip-safety-score` | Scores dirty WIP, stashes, and pre-agent snapshot markers. |
| `scripts/cos-recovery-drill --scenario all` | Runs non-destructive recovery drill tests. |
| `scripts/cos-runtime-hook-reality --fail-on-findings` | Proves runtime hooks match lifecycle and observable behavior. |
| `scripts/cos-silent-failure-audit --fail-on-findings` | Fails if shell error-swallowing patterns grow without classification. |
| `scripts/cos-dispatch-smoke --json` | Exercises dispatch metrics and task-history without external provider calls. |
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

## Ready bar

The SO can be treated as ready for the next serious adoption push when these
local signals are true on the branch being released:

```text
scripts/cos-runtime-hook-reality --fail-on-findings   # pass
scripts/cos-silent-failure-audit --fail-on-findings  # pass; no unclassified growth
scripts/cos-adoption-profile --profile core          # pass; core <=10 hooks, <=7 blocking
scripts/cos-preamble-budget --profile core           # pass; core <3000 tokens
scripts/cos-session-start-budget --profile core      # pass; core boot path <=5 hooks, no lab hooks
python3 scripts/active_primitive_index.py --json     # pass; no active/default-visible findings
scripts/cos-wip-safety-score                         # pass or explicit archived WIP exception
scripts/cos-dispatch-smoke --json                    # creates dispatch/task-history evidence locally
bash scripts/cos-ci-local.sh quick                   # pass before push
```

A release may still carry maintainer-mode warnings, but the consumer `core`
profile must be small, truthful, reversible, and executable.

## Control-plane lifecycle

The reliability tools above are registered as maintainer-layer agentic
primitives in `manifests/primitive-lifecycle.yaml`. They are not runtime hooks:
`runtime_projection: false` is intentional. Their job is to keep the runtime
primitives honest.

The local CI runner is the exception: `scripts/cos-ci-local.sh` is also a
maintainer primitive, but it is declared `maturity: blocking` because the
tracked pre-push hook uses it as the local landing gate.

## Silent failure classes

`manifests/silent-failure-allowlist.yaml` is not allowed to be a blind
`legacy_audited` bucket. Each audited shell degradation is classified as one of:

- `metrics_best_effort` — telemetry must not break the guarded user action;
- `optional_dependency` — optional tools/providers may be absent;
- `cleanup_best_effort` — cleanup/reaper paths are retried or surfaced later;
- `probe_best_effort` — read-only probes can fail without mutating state;
- `legacy_audited` — bounded legacy debt that still needs manual classification.

`legacy_audited` is tolerated as debt, not as a permanent explanation. The
trend should move entries from `legacy_audited` into concrete classes or remove
the swallowed failure entirely.

## SessionStart runtime diet

Preamble diet and runtime boot diet are separate. `cos-preamble-budget` measures
text/token load; `cos-session-start-budget` measures the actual Claude Code
`SessionStart` projection.

`core` projection intentionally keeps only the consumer boot hooks needed for
state initialization and WIP/recovery safety:

- `hooks/session-init.sh`
- `hooks/validation-lock-cleanup.sh`
- `hooks/session-start-stash-reapply.sh`

The maintainer/default projection preserves the full self-hosting startup
surface. This lets the SO maintainer keep solo-swarm tooling without forcing it
onto consumer installs.
