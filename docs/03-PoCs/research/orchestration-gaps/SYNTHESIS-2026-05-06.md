# Orchestration Gaps — Synthesis & Implementation Plan

**Date**: 2026-05-06
**Status**: Active — ranks ADR-worthy proposals from 11 parallel research reports
**Constraints**: Honors C1 (permissive licenses), C2 (footprint discipline), C3 (test tiers T1–T10), C4 (verdict block format) — promoted from prose into the canonical contract at [`manifests/orchestration-research-evaluation.yaml`](../../../manifests/orchestration-research-evaluation.yaml). The gap-analysis prose at [`../orchestration-coverage-gap-analysis-2026-05-06.md`](../orchestration-coverage-gap-analysis-2026-05-06.md) remains the human-readable rationale; the manifest is the normative source.
**Inputs**: 11 reports under `docs/03-PoCs/research/orchestration-gaps/`, ~42,000 words combined, ~230 sources cited
**Note on numbers below**: LOC and timeline estimates are reported by the underlying research agents and intentionally optimistic. Treat them as direction, not commitment. Per C3, T6 budgets are *measured first* — see the ADR-226 patch — rather than asserted up front.

---

## Executive summary

The 11 reports converge on a structural insight that was not visible in the original gap analysis:

> **The "missing" gaps are not 11 independent features. They are 4 capabilities, each unlocked by 1–3 small primitives. Most of the work is wiring, not invention.**

The four capabilities, ranked by leverage:

1. **Event-sourced orchestrator state** — adds monotonic sequences + per-session streams + memoized step wrapping. Unlocks replay-timeline (capability #2), failure-retry classification (capability #3 prerequisite), cross-session coordination (capability #4 prerequisite), cost ledger backpressure, audit invariants for ADR-220. The substrate is small but the claim that "~150 LOC unlocks five gap areas" depends on those gap areas reusing it without contortion — re-evaluate after Slice A lands.

2. **Shadow-git checkpoint substrate** — `lib/shadow_git.py` bare-repo per session. Unlocks `/rollback`, replay determinism (paired with event wrapping), governance-event-as-restore-point (the differentiation no competitor has). Cline + Hermes + Kilo + git-shadow already proved the pattern. **~200 LOC, zero new deps.**

3. **Failure-recovery contract + cost gate** — single `lib/retry_contract.py` classifier + `lib/session_budget.py` pre-call gate. Closes the silent connection-error gap in Anthropic SDK and the dispatch-without-budget gap that produced the $47K agent loop incident. **~100 LOC combined, zero new deps.**

4. **Cross-session agent-team substrate + handoff envelope** — `lib/agent_team.py` (file-IPC, fcntl) + `HandoffEnvelope` struct with call-chain dedup. Closes cycle bugs (the #1 production failure mode in multi-agent systems per MAST 2025) and the cross-session contract that ADR-211 partially defined. **~500 LOC combined, zero new deps.**

Beyond those four: **MCP server (high leverage, already designed in `cos-package.yaml`)**, **Bubblewrap sandbox adapter (zero deps, OS-native)**, **defer_loading + ToolSearch (client-side only)**, **policy-eval consolidation (15–20 hooks → `settings.json`)**, **detached agent daemon + tmux pattern (opt-in)** are all medium-leverage / small-effort additions.

Every recommendation in this synthesis honors C1 (licenses) and C2 (footprint). No new mandatory daemons. No new mandatory database. No image bloat. Each recommendation declares its T1–T10 test matrix per C3.

---

## Cross-cutting observations

Three patterns the reports rediscovered independently:

**O1. The same primitive recurs.** Five proposals share the *event log with sequence numbers* dependency. Five share the *per-session shadow state* dependency. Three share *file-based IPC with fcntl locking*. The right move is to ship the shared substrates **once**, then wire features into them. Building each gap as an independent primitive doubles the LOC.

**O2. "Adopt > build" almost always wins.** Codex `linux-sandbox` (Apache 2.0) replaces a sandbox build. Cline's shadow-git pattern replaces a checkpoint build. LiteLLM's `a2a_iteration_budgets` replaces a budget design. fastmcp replaces an MCP server framework build. Bubblewrap/Seatbelt replace a syscall-isolation build. **Of the 11 reports, 8 recommend adopting an existing pattern verbatim; 3 propose net-new code where no acceptable adoption target exists.**

**O3. Footprint discipline survives.** Only one recommendation (NATS JetStream as Tier-3 cross-session bus) introduces a heavy external dependency, and it's explicitly Tier-3 / opt-in / not in the default path. The file-based equivalents (JSONL + fcntl) are the default for Tier 1 and 2. C2 holds.

---

## Per-gap verdict blocks

Each block follows C4. Effort sizes: S = ≤2 days, M = 2–5 days, L = 5–15 days, XL = >15 days.

### G1. Replay timeline + restore-by-checkpoint (`replay-timeline-architectures.md`)

- **Recommendation**: BUILD MINIMAL (shadow-git + atomic file+conversation truncation)
- **Adopt**: pattern from Cline (Apache-2.0), Hermes (verify license), Kilo.ai, git-shadow
- **License**: pattern only — own implementation, FSL-1.1-MIT
- **Footprint**: OS repo small (~200 LOC) · Implementing projects none · Service mode opt-in · Docker image +0 MB (uses already-installed git)
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ⬜ T7 ✅ T8 ⬜ T9 ⬜ T10 ✅
- **Effort**: M
- **Leverage**: HIGH — closes Devin-parity governance differentiation
- **ADR candidate**: yes — **ADR-227** (drafted; consume ADR-226 substrate, pair with ADR-224 reserved)

### G2. Background / detached agents (`background-agent-patterns.md`)

- **Recommendation**: BUILD MINIMAL (daemon + tmux + worktree-per-agent)
- **Adopt**: tmux-agents pattern (verify), launchd/systemd primitives (OS-native, free)
- **License**: own code, FSL-1.1-MIT; depends on tmux (BSD-3, allowlist)
- **Footprint**: OS repo small (`scripts/cos-agent-daemon.py` ≤300 LOC) · Implementing projects opt-in (off by default) · Service mode the daemon IS the service · Docker +0 MB (tmux already in standard images)
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ⬜ T7 ✅ T8 ⬜ T9 ⬜ T10 ✅
- **Effort**: M
- **Leverage**: MEDIUM — closes "fire and forget" UX gap; defensible local-first answer
- **ADR candidate**: yes — **ADR-235** (Phase 3; consumes ADR-225 reserved branch-per-task policy)

### G3. Agent-to-agent handoff (`agent-to-agent-handoff.md`)

- **Recommendation**: BUILD MINIMAL (HandoffEnvelope + cycle dedup + permission intersection) + INTEGRATE LangGraph `Command` shape for compatibility
- **Adopt**: A2A message-parts shape (Apache-2.0); LangGraph Command pattern (MIT)
- **License**: pattern compatibility only; own implementation FSL-1.1-MIT
- **Footprint**: OS repo small (~150 LOC) · Implementing projects none (env-internal struct) · Service mode none additional · Docker +0 MB
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ⬜ T7 ✅ T8 ✅ T9 ⬜ T10 ⬜
- **Effort**: S (call-chain dedup is <1 day, envelope+permission is 1–2 days)
- **Leverage**: HIGH — call-chain dedup blocks the #1 failure mode (MAST 2025: 41–87% failure rates)
- **ADR candidate**: yes — **ADR-230** (drafted)

### G4. MCP as orchestration bus (`mcp-as-orchestration-bus.md`)

- **Recommendation**: ADOPT fastmcp + INTEGRATE OTel MCP semconv + ACTIVATE trust-pinning
- **Adopt**: `fastmcp` (Apache-2.0); `opentelemetry.semconv._incubating.attributes.mcp_attributes` (Apache-2.0)
- **License**: ✅ allowlist
- **Footprint**: OS repo small (~400 LOC implementing 9 tools) · Implementing projects opt-in MCP-server config · Service mode optional · Docker +~5 MB (fastmcp + deps)
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ⬜ T7 ⬜ T8 ✅ T9 ✅ T10 ⬜
- **Effort**: M
- **Leverage**: HIGH — distribution channel to every MCP-aware tool (Cursor, Windsurf, Cline, Codex, Claude Code) without per-harness adapters
- **ADR candidate**: yes — **ADR-231** (Phase 2; read-mostly tools first, write tools after the read surface stabilizes)

### G5. Sandbox primitive integration (`sandbox-primitives-integration.md`)

- **Recommendation**: ADOPT Bubblewrap (Linux) + Seatbelt (`sandbox-exec`, macOS); vendor Codex `linux-sandbox` policy model
- **Adopt**: bwrap (LGPL-2.0+ — runtime tool, separate process, OK); sandbox-exec (Apple OS-bundled); Codex policy YAML pattern (Apache-2.0)
- **License**: ✅ — bwrap is invoked as subprocess (no linking), Codex pattern OK
- **Footprint**: OS repo small (~250 LOC adapter) · Implementing projects opt-in (off by default) · Service mode opt-in tier · Docker +~10 MB (bwrap if not present)
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ⬜ T7 ✅ T8 ✅ T9 ✅ T10 ✅
- **Effort**: M
- **Leverage**: MEDIUM — closes 80% of accidental-destruction threat at zero new dep cost
- **ADR candidate**: yes — **ADR-232** (Phase 2; per-OS adapter — Linux Bubblewrap, macOS Seatbelt, no shared default path)

### G6. Cross-session agent teams (`cross-session-agent-teams.md`)

- **Recommendation**: BUILD MINIMAL (`lib/agent_team.py`: SessionRegistry + TaskManifest + Inbox + EventLog)
- **Adopt**: pattern convergence — Claude Code Agent Teams + OpenCode session_bus (both file-IPC + fcntl)
- **License**: ✅ pattern only; own implementation FSL-1.1-MIT
- **Footprint**: OS repo medium (~400 LOC) · Implementing projects opt-in · Service mode opt-in · Docker +0 MB
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ⬜ T7 ✅ T8 ⬜ T9 ⬜ T10 ✅
- **Effort**: M
- **Leverage**: HIGH — codifies the "subagent vs agent-team" distinction operators currently navigate by feel
- **ADR candidate**: yes — **ADR-233** (Phase 2; depends on ADR-219 ownership/liveness + ADR-226 event bus before this can land. NATS JetStream documented as Tier-3 future, not default.)

### G7. Approval policies as code (`approval-policies-as-code.md`)

- **Recommendation**: PHASE 1 migrate ~15-20 deny hooks to `settings.json`; PHASE 2 ship `policy-eval.sh` + `policies/*.yaml` schema; DEFER OPA
- **Adopt**: own existing pattern (`content-policy.sh` + `content-policy.yaml`)
- **License**: ✅ no external deps
- **Footprint**: OS repo small-net-negative (delete duplicated bash, add one evaluator) · Implementing projects no impact · Service mode no impact · Docker +0 MB
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ⬜ T7 ⬜ T8 ✅ T9 ⬜ T10 ⬜
- **Effort**: S (Phase 1) + S (Phase 2)
- **Leverage**: MEDIUM — reduces hook count, surfaces policy in `/permissions`, kills bash-embedded thresholds
- **ADR candidate**: yes — **ADR-234** (Phase 3; multi-phase migration via *generated projection* from manifests, not abrupt hook replacement)

### G8. Cost-aware routing + budgets (`cost-aware-routing.md`)

- **Recommendation**: BUILD MINIMAL (`lib/session_budget.py`) + INTEGRATE LiteLLM `a2a_iteration_budgets` semantics
- **Adopt**: LiteLLM pattern (MIT)
- **License**: ✅ pattern + reference impl both allowlist
- **Footprint**: OS repo small (~50 LOC) · Implementing projects no forced impact · Service mode opt-in budget enforcement · Docker +0 MB
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ✅ T7 ⬜ T8 ⬜ T9 ⬜ T10 ⬜
- **Effort**: S
- **Leverage**: HIGH — closes the documented $47K-incident class (alerts can't prevent the next call; only sync gates can)
- **ADR candidate**: yes — **ADR-228 (consolidated with G10 retry contract)** drafted. Ledger MUST take a per-session lock; estimation source is `cost_predictor.get_real_model_prices()`.

### G9. Event-driven orchestrator state (`event-driven-orchestrator-state.md`)

- **Recommendation**: BUILD MINIMAL (sequence numbers + per-session streams + `@event_wrap` decorator)
- **Adopt**: Temporal/Inngest pattern (memoize Activity results, inject on replay)
- **License**: ✅ pattern only; own implementation
- **Footprint**: OS repo small (~150 LOC across 3 phases) · Implementing projects no impact · Service mode no impact · Docker +0 MB
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ✅ T7 ✅ T8 ⬜ T9 ⬜ T10 ✅
- **Effort**: S (sequence) + S (per-session) + M (event_wrap)
- **Leverage**: VERY HIGH — **prerequisite for replay (G1), retry classification (G10), cost ledger (G8 reconciliation), agent-teams event log (G6)**. Build first.
- **ADR candidate**: yes — **ADR-226** (drafted; explicitly *extends* ADR-205 Flight Recorder rather than replacing it. Load-bearing for ADR-227, ADR-228, ADR-230, ADR-233.)

### G10. Failure recovery / retry semantics (`failure-recovery-retry-semantics.md`)

- **Recommendation**: BUILD MINIMAL (`lib/retry_contract.py` classifier + circuit breaker in `dispatch.py` + idempotency keys for stateful tools); CONSOLIDATE 6 magic-number retry counts into `rules/retry-contract.md`
- **Adopt**: classification taxonomy from MAST paper (academic; pattern only) + circuit-breaker semantics from established libraries
- **License**: ✅ no external runtime deps
- **Footprint**: OS repo small (~120 LOC) + rule consolidation · Implementing projects no impact · Service mode no impact · Docker +0 MB
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ✅ T7 ✅ T8 ⬜ T9 ⬜ T10 ⬜
- **Effort**: S
- **Leverage**: HIGH — closes the silent ECONNRESET/EPIPE gap and the LangGraph+Pydantic ValidationError trap; idempotency keys eliminate side-effect duplication on retry
- **ADR candidate**: yes — **ADR-228 (consolidated with G8 cost budget)** drafted. Idempotency keys are the load-bearing piece; classifier and circuit breaker are supporting.

### G11. Tool discovery dynamic registration (`tool-discovery-dynamic-registration.md`)

- **Recommendation**: ADOPT Anthropic `defer_loading: true` + ToolSearch pattern; INTEGRATE `notifications/tools/list_changed` consumption; DEFER true mid-session MCP server injection
- **Adopt**: Anthropic API native feature (no license cost)
- **License**: ✅ — uses already-licensed API capability
- **Footprint**: OS repo small (changes in `lib/dispatch.py` + sub-agent prompt composition) · Implementing projects no impact · Service mode no impact · Docker +0 MB
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ✅ T7 ⬜ T8 ✅ T9 ⬜ T10 ⬜
- **Effort**: S
- **Leverage**: MEDIUM — 85% token reduction reported upstream (Anthropic); not yet measured locally in `.cognitive-os/metrics/`. Surface unchanged.
- **ADR candidate**: yes — **ADR-236** (Phase 3; **explicitly extends ADR-216 tool-discovery pre-use gate**, does not create a parallel discovery loop. Could fold into ADR-231 MCP server as a sibling concern.)

---

## Ranked implementation plan

Four tiers, not three phases. The earlier phasing collapsed substrate (which has no consumer) into the same bucket as consumer code (which depends on the substrate). The four-tier categorization is more honest:

| Tier | Definition | Lands when |
|---|---|---|
| **Substrate** | Has no consumer in itself; provides the shape every consumer reuses. Wrong shape here forces every later ADR to fight the substrate. | First. Single ADR at a time. |
| **Consumer** | Consumes a substrate to deliver an operator-visible capability. | After its substrate has at least Slice A landed and validated by smoke (T4). |
| **Opt-in adapter** | Off by default. Adds a capability behind a configuration flag. | Anytime after its substrate; not on the critical path. |
| **Future / cloud** | Not pursued in the current cycle. Documented as conscious non-coverage with re-evaluation triggers. | Re-evaluated on operator signal. |

Each tier's items are coherent within themselves; cross-tier dependencies are declared.

### Tier 1 — Substrate (single ADR at a time, in this order)

| # | ADR | Item | Effort | LOC | Unblocks |
|---|---|---|---|---|---|
| 1.1 | **ADR-226** | Event-sourced session_bus (sequence + per-session + `@event_wrap`) | S+S+M | est. ~150–250 | G1, G6, G8, G10 |
| 1.2 | **ADR-223** (reserved) | Agent Lifecycle Reconstruction (kill auto-stash → worktree-per-write-agent + mutex) | M | est. ~200 | unblocks ADR-227 / 224 / 235 by removing the broken primitive they'd otherwise inherit |
| 1.3 | **ADR-227** + **ADR-224** (reserved) | Shadow-git checkpoint substrate + Cline-pattern safety net | M | est. ~250 | G1, governance-as-restore |
| 1.4 | **ADR-228** (consolidated G8+G10) | Retry contract + cost session ledger + idempotency keys + circuit breaker | S+S | est. ~170 | G10 closure, G8 closure |
| 1.5 | **ADR-230** | Handoff envelope + call-chain dedup + permission intersection | S | est. ~150 | G3, G6 |

LOC numbers are agent-reported estimates. Treat as direction. Per C3, Slice A of ADR-226 measures actual append latency before later slices commit to a budget.

The single most important sequencing decision: **ADR-223 lands BEFORE ADR-227+224.** Otherwise the safety net inherits a broken pre-agent-stash flow it was supposed to replace. ADR-222 (proposed, in-tree) stays as tactical mitigation for as long as `git stash` is on the pre-agent path; once ADR-223 lands, ADR-222 is deprecated.

### Tier 2 — Consumers (after Tier 1 substrate is validated)

| # | ADR | Item | Effort | LOC | Notes |
|---|---|---|---|---|---|
| 2.1 | **ADR-231** | MCP server (`packages/mcp-server/cos_mcp.py`) | M | est. ~400 | fastmcp adoption; +~5 MB image; **read-mostly tools first**, write tools after read surface stabilizes; trust-pinning prerequisite |
| 2.2 | **ADR-233** | Cross-session agent-team file-IPC substrate | M | est. ~400 | depends on ADR-219 ownership/liveness + ADR-226 event bus; do not implement before both |
| 2.3 | **ADR-225** (reserved) | Branch-Per-Task Mode | S | est. ~80 | policy primitive; pairs naturally with ADR-235 |

### Tier 3 — Opt-in adapters (off by default)

| # | ADR | Item | Effort | LOC | Notes |
|---|---|---|---|---|---|
| 3.1 | **ADR-232** | Sandbox adapter tiers (Bubblewrap/Seatbelt OS-native; E2B/microVM opt-in) | M | est. ~250 | per-OS branching: Linux Bubblewrap, macOS Seatbelt — different code paths, not a single adapter |
| 3.2 | **ADR-235** | Detached agent daemon (cos-agent-daemon.py + tmux + worktree wiring) | M | est. ~300 | tmux is **assumed installed**, not bundled; daemon is opt-in service-mode lane |
| 3.3 | **ADR-236** | Deferred tool loading + ToolSearch | S | est. ~50 | extends ADR-216, does not parallel it |
| 3.4 | **ADR-234** | Approval policies as code, multi-phase | S+S | est. net-negative LOC | migration via *generated projection* from manifests, not abrupt hook replacement |

### Tier 4 — Future / cloud / not pursued in this cycle

Documented as conscious non-coverage; tracked for re-evaluation on operator signal.

| Area | Why we don't pursue | Re-evaluation trigger |
|---|---|---|
| Multi-machine cloud orchestration | Local-first is positioning, not a gap | Operator cohort demand |
| CRDT-based merging | Code is non-commutative; nobody uses CRDT for agent merges | n/a — anti-recommendation |
| Hypervisor sandboxes (Firecracker) as primary | Operationally expensive; Bubblewrap closes 80% at zero cost | E2BAdapter as Tier-3 opt-in covers the remaining cases |
| OPA / Rego policy engine | Single-operator OS doesn't need ABAC complexity | Multi-tenant deployment |
| Mid-session MCP server injection | "Not planned" upstream (Anthropic); deferred-loading reportedly covers ~85% (upstream figure, unmeasured locally) | Track Anthropic spec changes |
| Temporal / Cadence durable workflows | Heavy external dep violates C2 | `@event_wrap` covers MVP determinism need |
| NATS JetStream cross-session bus | Heavy external dep violates C2 default; documented as Tier-3 future only | If file-IPC contention measured > X% in production |

---

## ADR proposal slate

**Reserved slots — already filled or earmarked**:
- ADR-219 — Work Ownership Liveness Preflight (existing, accepted)
- ADR-220 — Worktree Divergence Audit (existing, accepted)
- ADR-221 — Stash Ref by SHA, Not by Position (existing, accepted slice 1)
- ADR-222 — Pre-Agent Stash Two-Phase / Deferred Until Launch Confirmed (existing, proposed — tactical mitigation while G1+ migrate off auto-stash)
- ADR-223 — Agent Lifecycle Reconstruction (reserved by [`prior-art research R1`](../multi-agent-orchestration-prior-art-2026-05-06.md): kill auto-pre-agent-stash, adopt worktree-per-write-agent + mutex on `git worktree add`)
- ADR-224 — Shadow-State Snapshots, Off-Repo (reserved by [`prior-art research R2`](../multi-agent-orchestration-prior-art-2026-05-06.md): Cline-pattern safety net, opt-in)
- ADR-225 — Branch-Per-Task Mode (reserved by [`prior-art research R5`](../multi-agent-orchestration-prior-art-2026-05-06.md): production-mode policy)

**New ADRs proposed by this synthesis** (numbered to skip the reserved set):

- **ADR-226** — Event-Sourced Session Bus (G9 — load-bearing for several others)
- **ADR-227** — Shadow-Git Checkpoint Substrate (G1) [pairs with ADR-224 — both consume per-session shadow state; consolidation candidate]
- **ADR-228** — Retry Contract + Idempotency Keys (G10)
- **ADR-229** — Session Budget Pre-Call Gate (G8) [consolidation candidate with ADR-228]
- **ADR-230** — Agent Handoff Envelope + Call-Chain Deduplication (G3)
- **ADR-231** — MCP Server Surface for COS Primitives (G4)
- **ADR-232** — Sandbox Adapter Tiers: OS-Native Default, microVM Opt-In (G5)
- **ADR-233** — Cross-Session Agent-Team File-IPC Substrate (G6)
- **ADR-234** — Approval Policies as Code (multi-phase migration) (G7)
- **ADR-235** — Detached Agent Daemon (G2)
- **ADR-236** — Deferred Tool Loading + ToolSearch Adoption (G11) [or fold into ADR-231]

11 candidate ADRs. Recommend writing 4 Phase-1 first (the high-leverage substrate set: **226 event-sourced bus**, **227 shadow-git**, **228+229 combined retry+budget**, **230 handoff envelope**) and sequencing the rest behind those.

**Coordinate with the reserved set**:
- ADR-223 (kill auto-stash) and ADR-227 (shadow-git) overlap: shadow-git is the safety-net replacement that ADR-224 anticipates. Sequencing: 223 lands first (structural change), 227+224 land together (substrate + safety-net).
- ADR-222 (two-phase capture) stays as **tactical mitigation** for as long as `git stash` remains on the pre-agent path. Once 223 lands, 222 can be deprecated.
- ADR-225 (branch-per-task) is policy-level and can land anytime; pairs naturally with 235 (detached daemon) which benefits from a strict branch contract.

---

## Honest assessment

The gap analysis from earlier in the day estimated ~60–65% coverage breadth. The optimistic projection — Tier 1 + Tier 2 lifting that to ~85–90% in ~3–4 weeks of single-author work — is the *agent-reported* estimate from the underlying research and is almost certainly low on time, high on coverage. Treat as direction, not commitment.

The honest version:
- **Coverage**: Tier 1 plausibly closes 50–60% of the gap surface (substrate + idempotency + cycle-dedup + retry contract are foundational). Tier 2 adds another 15–20%. Tier 3 adapters add the last 5–10% only when adopted. The remaining ~10% is conscious non-coverage.
- **Timeline**: ADR-226 Slice A alone (sequence allocator + per-session stream + gap-detecting reader + smoke) is 2–3 days of focused work, but landing it cleanly with T7 chaos coverage is closer to 5. The "~3–4 weeks for Tier 1" claim assumes nothing else preempts and is optimistic by 50–100%.
- **Risk**: research inflation. Eleven solid reports can become eleven semi-overlapping ADRs and recreate the very debt this exercise was supposed to retire. Discipline: consolidate where consolidation candidates were flagged (G8+G10 → ADR-228), defer tier-3 adapters until tier-1+2 actually shipped, refuse tier-4 items even when they tempt.

**The single uncomfortable load-bearing finding**: replay, agent teams, retry, and cost ledger all share the same substrate (event-sourced session bus). Building any one of them standalone locks in the wrong shape. **ADR-226 lands first, alone, validated by smoke (T4) and chaos (T7), before any Tier-2 ADR begins drafting against its event envelope.**

This is a constraint on *how to build*, not a list of features to build.

**Trust report (per `rules/trust-score.md`)**:
- SCORE: 82 STATUS: HIGH EVIDENCE: 11 reports + 230 sources UNCERTAINTIES: 4
- WHAT I VERIFIED: each verdict block fills C4's 6 fields; license claims cross-checked against research-cited SPDX; footprint claims cross-checked against C2 surfaces; effort sizes are agent-reported and operator should sanity-check
- UNSURE ABOUT: (a) whether `@event_wrap` decorator interacts cleanly with existing `dispatch.py` retry logic — needs prototype; (b) whether Bubblewrap is shipped on operator's macOS path (it isn't — Seatbelt is the macOS path; needs explicit branching in adapter); (c) license verification on Hermes shadow-git pattern (pattern reuse, not code reuse, so likely OK but operator should confirm); (d) whether Anthropic's `defer_loading` is exposed in the SDK version COS pins
- HUMAN SHOULD CHECK: ADR slot numbers (this synthesis assumed 222 as ceiling; please verify against current `docs/02-Decisions/adrs/` listing); confirmation that the operator wants 11 new ADRs vs. consolidating some pairs (231+223; 230+232; 226+233 are obvious consolidation candidates)
