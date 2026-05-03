# DX Tax Reduction Plan

## Goal

Reduce the developer-experience cost that makes Cognitive OS feel heavier than
vanilla Claude Code/Codex while preserving the strict runtime needed for the solo
maintainer swarm and headless cloud-worker personas.

This plan addresses seven explicit DX costs:

1. cognitive load;
2. token tax;
3. added latency;
4. excessive indirection;
5. harness coupling;
6. upstream feature duplication;
7. self-referential governance overhead.

## Principle

The fix is not to delete safety. The fix is to make cost proportional to risk:

- Lean/Core: minimal runtime-safety, almost no meta-governance.
- Standard/Team: coordination and repair primitives.
- Strict/Maintainer: multi-agent, multi-IDE, cloud/headless controls.
- Lab: experiments, harvesters, scorecards, and self-audits.

## Phase 1 — Cognitive load reduction

### Problem

Operators currently need to understand too many layers, hooks, commands, rules,
and contextual procedures before they can predict behavior.

### Deliverables

- One active primitive index filtered by distribution/profile.
- `cos status`/readiness output shows only active primitives by default.
- Lab/meta-governance hidden unless explicitly requested.
- First-run docs point to one decision tree and one command path.

### Acceptance

- [ ] Lean/Core active primitive count is reported.
- [ ] Strict/Maintainer active primitive count is reported separately.
- [ ] `cos governance readiness` warns when discovery overload exists.
- [ ] A new operator can identify the active safety layer without reading ADRs.

## Phase 2 — Token tax reduction

### Problem

Always-active rules, long instructions, skill catalogs, and protocol text consume
context before the user problem starts.

### Deliverables

- Token budget report for startup/session context.
- Always-active rule set split by distribution/profile.
- Skills/rules lazy-loaded by trigger and tier.
- Compact maintainer-mode preamble for Strict without loading Lab by default.

### Acceptance

- [ ] `cos governance readiness --json` includes token/context tax estimate or
      an explicit unavailable signal.
- [ ] Lean/Core startup payload has a target budget.
- [ ] Strict/Maintainer startup payload has a separate target budget.
- [ ] Lab/meta docs are not injected into normal sessions by default.

## Phase 3 — Latency reduction

### Problem

Every Bash/Edit/Write can pay hook overhead. Trivial work should not feel like a
release pipeline.

### Deliverables

- Top hook latency sources feed readiness and ADR-123 telemetry.
- Advisory hooks run async or out of the hot path.
- Blocking hooks must declare latency budget in the lifecycle manifest.
- High-latency blockers require repair-first messaging and false-positive tests.

### Acceptance

- [ ] Readiness reports top latency offenders.
- [ ] Lifecycle manifest has latency budget coverage for blocking runtime hooks.
- [ ] High-latency advisory hooks are demoted from hot path.
- [ ] p95 hook budget tests cover real body latency vs wrapper/safe-mode.

## Phase 4 — Indirection/debuggability reduction

### Problem

Behavior often crosses hook → script → lib → yaml → rule → skill, making “why did
this block?” too hard to answer.

### Deliverables

- Every block emits a trace id and direct evidence path.
- `cos explain last-block` or equivalent reads the latest block and shows the
  exact primitive, policy, input, evidence, and repair command.
- Canonical project-root resolution used by hooks and doctors.

### Acceptance

- [ ] A blocked action can be explained with one command.
- [ ] Block reports include repair command and owning ADR.
- [ ] Path/root mismatches are detected by tests.

## Phase 5 — Harness coupling reduction

### Problem

Despite adapter work, many surfaces remain Claude-Code-shaped: slash commands,
settings projection, hook event shape, and skill discovery.

### Deliverables

- Harness capability matrix drives projection, not assumptions.
- Driver-specific gaps shown as degraded/unsupported, not silently promised.
- Codex/Cursor/OpenCode paths use canonical primitives where harness events exist
  and explicit fallback checkers where they do not.

### Acceptance

- [ ] Capability matrix is used by readiness/projection checks.
- [ ] Missing harness events are visible as degraded/gap.
- [ ] No product claim says cross-harness support where projection is fallback-only.

## Phase 6 — Upstream duplication review

### Problem

Claude Code/Codex upstreams add skills, scheduled tasks, subagents, plan mode,
and other primitives. COS must not duplicate what upstream now does better.

### Deliverables

- Upstream overlap review per release window.
- Each overlapping COS primitive gets `keep`, `wrap`, `delegate`, `demote`, or
  `delete` recommendation.
- Lifecycle manifest records sunset criteria for primitives likely to be replaced
  by upstream.

### Acceptance

- [ ] Readiness or lifecycle report lists upstream-overlap candidates.
- [ ] Native harness capability superseding a COS primitive triggers demotion
      recommendation, not silent duplication.

## Phase 7 — Self-referential governance cap

### Problem

A large share of the repo governs the repo itself. Useful for maintainers, but
noise for users and dangerous if it becomes default runtime.

### Deliverables

- Meta-governance stays `maintainer` or `lab` unless it directly protects WIP,
  secrets, main landing, or cloud/headless operation.
- ROI dashboard excludes dogfood/self-use as standalone productivity proof.
- Primitive harvester and scorecards remain out of default projection until they
  show precision/ROI.

### Acceptance

- [x] Lifecycle recommendations keep sandbox meta-governance out of default.
- [ ] Active default surface contains no Lab primitives.
- [ ] Meta-governance promotion requires ROI and false-positive evidence.


## 2026-05-03 SR review update

Read-only senior/Solutions Architect reviews confirmed the design direction and
identified the next execution risk: the active primitive index currently reads
`manifests/primitive-lifecycle.yaml`, which has only four primitives, while the
real Claude runtime projects 120 hook entries. That means readiness can report a
small active surface before ADR-126 metadata covers the real runtime.

Updated load-bearing priorities:

1. ADR-126 must cover projected hooks from `cognitive-os.yaml` and
   `manifests/hook-quality.yaml`, not only a hand-maintained seed manifest.
2. ADR-127 must report runtime coverage: projected hook count, lifecycle-covered
   hook count, and coverage status.
3. ADR-124 must become projection behavior, not only tier documentation.
4. ADR-125 must become enforceable metadata: every projected hook gets a
   governance class and `meta-governance` stays out of default projection.
5. Core proof must demonstrate the wedge in under ten minutes without dashboards,
   squads, dogfood scorecards, or maintainer audits.

DX KPIs adopted for the next implementation phase:

| KPI | Initial target |
|---|---:|
| Core active hooks/primitives | <= 12 default-visible |
| Core empty-session context tax | < 3K tokens |
| Hook-chain p95 | core < 300ms; team < 800ms; maintainer < 1500ms |
| False-positive block rate | core < 5%; maintainer < 10% |
| Lab active by default | 0 |
| Claim verification integrity | > 95% evidence-backed done claims |
| Portability parity | core smoke proof green on every advertised harness |

## Exit criteria

External reviewers should no longer be able to object that COS is indiscriminately heavy when:

- Lean/Core has a documented low-friction budget;
- Strict/Maintainer proves its added cost prevents multi-agent/headless damage;
- readiness reports cognitive/token/latency/indirection/harness/upstream/meta
  costs explicitly;
- lifecycle recommendations demote low-ROI primitives before users pay for them.
