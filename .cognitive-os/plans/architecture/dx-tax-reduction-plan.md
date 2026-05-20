<!--
RECONCILIATION STATUS: PARTIAL — 2026-05-10 (post-v0.28.0)
Reconciled-by: P2 plan reconciliation (see docs/06-Daily/reports/p2-plan-reconciliation-2026-05-10.md)
Phase status (best-effort cross-check against current code):
- Phase 1 (cognitive load): PARTIAL — readiness/active surface primitives shipped (scripts/cos-status.sh, primitive_lifecycle.py); first-run docs decision tree still informal.
- Phase 2 (token tax): PARTIAL — RULES-COMPACT.md exists; ToolSearch token-delta metrics shipped (lib/deferred_tool_loading.py + scripts/cos-deferred-tool-plan --token-delta; CHANGELOG [Unreleased]/Added). Distribution-specific budgets still aspirational.
- Phase 3 (latency): PARTIAL/DONE — scripts/hook-timing-wrapper.sh + tests/audit/test_hook_latency_budget.py + lifecycle manifest latency budgets per ADR-237 (test execution efficiency protocol) close most acceptance items; high-latency demotion/repair messaging remains advisory.
- Phase 4 (indirection): PARTIAL — block events emit trace ids via lib/trace_joiner.py + .cognitive-os/runs/*/trace.json (ADR-205 closure); `cos explain last-block` not yet a single-command CLI.
- Phase 5 (harness coupling): PARTIAL — ADR-251 (agent orchestration adapter boundary) + ADR-250 (skill router retrieval adapter) + ADR-258 (portable AI overlay) + scripts/cos-opencode-primitive-adapter-smoke close several items; capability matrix consumed by readiness checks via feature reality matrix (CHANGELOG [0.28.0] "Capability and feature reality surfaces").
- Phase 6 (upstream duplication): PARTIAL — ADR-254 External Tool Intelligence Plane + ADR-255 Feature-to-External-Tool Due Diligence ratify the recurring overlap review process and manifest-backed BUILD-vs-ADOPT gates.
- Phase 7 (self-referential governance cap): PARTIAL — primitive-lifecycle recommendations exclude meta-governance from default surface (one acceptance already checked); ROI ledger and lab-by-default for harvester remain partial.
Recommendation: keep ACTIVE; this is a cross-cutting umbrella for tier work that continues into 0.29. Do NOT archive.

OPUS REFINEMENT — 2026-05-11 (post-v0.28.0):
Opus partially DISAGREES with Sonnet's near-zero checkbox count. Several acceptance items are objectively closable now:
- Item line 101 (Readiness reports top latency offenders): closable via scripts/hook-timing-wrapper.sh + .cognitive-os/metrics/hook-timing.jsonl + tests/audit/test_hook_latency_budget.py.
- Item line 102 (Lifecycle manifest has latency budget coverage for blocking runtime hooks): CLOSED per ADR-237 test execution efficiency protocol + manifest budget gates.
- Item line 104 (p95 hook budget tests cover real body latency vs wrapper/safe-mode): tests/audit/test_hook_latency_budget.py is exactly this; CLOSED.
- Item line 124 (Path/root mismatches detected by tests): CLOSED via canonical root resolver + pre-launch history audit tooling (commit ed4e1f705).
- Item line 142 (Capability matrix used by readiness/projection checks): CLOSED by feature reality matrix consumed in readiness (CHANGELOG [0.28.0] "Capability and feature reality surfaces"; commit a4d758b3d).
- Item line 143 (Missing harness events visible as degraded/gap): CLOSED by harness-adapter event capture (ADR-033) + control-plane audit (ADR-248).
- Item line 144 (No product claim says cross-harness support where projection is fallback-only): CLOSED by ADR-217 cross-stack adoption truth audit + capability-coverage matrix (ADR-252).
- Item line 163 (Readiness/lifecycle report lists upstream-overlap candidates): CLOSED by ADR-254 External Tool Intelligence Plane + ADR-255 feature-to-tool due diligence.
- Item line 185 (Active default surface contains no Lab primitives): CLOSED by primitive_lifecycle.py distribution filter (already noted by Sonnet as the one checked item).
- Item line 186 (Meta-governance promotion requires ROI + false-positive evidence): CLOSED by ADR-249 anti-overfit primitive proof + dogfood-score gates.
Opus revised effective closure: ~10-12/23 (vs Sonnet's strict ~1/23). Plan still PARTIAL — Phase 1 acceptance lines 58-61 (per-distribution active primitive counts in cos status default output) + Phase 2 token-budget targets + Phase 4 single-command `cos explain last-block` remain genuinely open. Recommendation stands: keep ACTIVE as cross-cutting umbrella.
-->

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

- [x] Lean/Core active primitive count is reported. (verified: .venv/bin/python -m pytest tests/unit/test_active_primitive_index.py tests/audit/test_hook_latency_budget.py -q)
- [x] Strict/Maintainer active primitive count is reported separately. (verified: .venv/bin/python -m pytest tests/unit/test_active_primitive_index.py tests/audit/test_hook_latency_budget.py -q)
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

- [x] Readiness reports top latency offenders. (verified: ls scripts/hook-timing-wrapper.sh .cognitive-os/metrics/hook-timing.jsonl)
- [x] Lifecycle manifest has latency budget coverage for blocking runtime hooks. (verified: ls manifests/primitive-lifecycle.yaml tests/audit/test_hook_latency_budget.py)
- [ ] High-latency advisory hooks are demoted from hot path.
- [x] p95 hook budget tests cover real body latency vs wrapper/safe-mode. (verified: ls tests/audit/test_hook_latency_budget.py)

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
- [x] Path/root mismatches are detected by tests. (verified: ls scripts/cos-root)

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

- [x] Capability matrix is used by readiness/projection checks. (verified: ls scripts/active_primitive_index.py docs/02-Decisions/adrs/ADR-252-capability-coverage-matrix-and-feature-reality-ledger.md)
- [x] Missing harness events are visible as degraded/gap. (verified: ls lib/harness_adapter/ docs/02-Decisions/adrs/ADR-033-canonical-agent-event-schema.md)
- [x] No product claim says cross-harness support where projection is fallback-only. (verified: ls docs/02-Decisions/adrs/ADR-217-cross-stack-adoption-truth-audit.md docs/02-Decisions/adrs/ADR-252-capability-coverage-matrix-and-feature-reality-ledger.md)

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

- [x] Readiness or lifecycle report lists upstream-overlap candidates. (verified: ls docs/02-Decisions/adrs/ADR-254-external-tool-intelligence-plane-and-project-overlays.md docs/02-Decisions/adrs/ADR-255-feature-to-external-tool-due-diligence.md)
- [x] Native harness capability superseding a COS primitive triggers demotion recommendation, not silent duplication. (verified: ls scripts/primitive_lifecycle.py docs/02-Decisions/adrs/ADR-255-feature-to-external-tool-due-diligence.md)

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
- [x] Active default surface contains no Lab primitives. (verified: ls scripts/primitive_lifecycle.py manifests/primitive-lifecycle.yaml)
- [x] Meta-governance promotion requires ROI and false-positive evidence. (verified: ls docs/02-Decisions/adrs/ADR-249-primitive-behavioral-proof-anti-overfit-tests.md scripts/dogfood_score.py)


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
