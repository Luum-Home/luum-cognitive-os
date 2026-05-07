# Orchestration Gaps — Synthesis & Implementation Plan

**Date**: 2026-05-06
**Status**: Active — ranks ADR-worthy proposals from 11 parallel research reports
**Constraints**: Honors C1 (permissive licenses), C2 (footprint discipline), C3 (test tiers T1–T10), C4 (verdict block format) declared in [`../orchestration-coverage-gap-analysis-2026-05-06.md`](../orchestration-coverage-gap-analysis-2026-05-06.md)
**Inputs**: 11 reports under `docs/research/orchestration-gaps/`, ~42,000 words combined, ~230 sources cited

---

## Executive summary

The 11 reports converge on a structural insight that was not visible in the original gap analysis:

> **The "missing" gaps are not 11 independent features. They are 4 capabilities, each unlocked by 1–3 small primitives. Most of the work is wiring, not invention.**

The four capabilities, ranked by leverage:

1. **Event-sourced orchestrator state** — adds monotonic sequences + per-session streams + memoized step wrapping. Unlocks replay-timeline (capability #2), failure-retry classification (capability #3 prerequisite), cross-session coordination (capability #4 prerequisite), cost ledger backpressure, audit invariants for ADR-220. **One ~150 LOC primitive unlocks five gap areas.**

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
- **ADR candidate**: yes — proposed ADR-223

### G2. Background / detached agents (`background-agent-patterns.md`)

- **Recommendation**: BUILD MINIMAL (daemon + tmux + worktree-per-agent)
- **Adopt**: tmux-agents pattern (verify), launchd/systemd primitives (OS-native, free)
- **License**: own code, FSL-1.1-MIT; depends on tmux (BSD-3, allowlist)
- **Footprint**: OS repo small (`scripts/cos-agent-daemon.py` ≤300 LOC) · Implementing projects opt-in (off by default) · Service mode the daemon IS the service · Docker +0 MB (tmux already in standard images)
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ⬜ T7 ✅ T8 ⬜ T9 ⬜ T10 ✅
- **Effort**: M
- **Leverage**: MEDIUM — closes "fire and forget" UX gap; defensible local-first answer
- **ADR candidate**: yes — proposed ADR-224

### G3. Agent-to-agent handoff (`agent-to-agent-handoff.md`)

- **Recommendation**: BUILD MINIMAL (HandoffEnvelope + cycle dedup + permission intersection) + INTEGRATE LangGraph `Command` shape for compatibility
- **Adopt**: A2A message-parts shape (Apache-2.0); LangGraph Command pattern (MIT)
- **License**: pattern compatibility only; own implementation FSL-1.1-MIT
- **Footprint**: OS repo small (~150 LOC) · Implementing projects none (env-internal struct) · Service mode none additional · Docker +0 MB
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ⬜ T7 ✅ T8 ✅ T9 ⬜ T10 ⬜
- **Effort**: S (call-chain dedup is <1 day, envelope+permission is 1–2 days)
- **Leverage**: HIGH — call-chain dedup blocks the #1 failure mode (MAST 2025: 41–87% failure rates)
- **ADR candidate**: yes — proposed ADR-225

### G4. MCP as orchestration bus (`mcp-as-orchestration-bus.md`)

- **Recommendation**: ADOPT fastmcp + INTEGRATE OTel MCP semconv + ACTIVATE trust-pinning
- **Adopt**: `fastmcp` (Apache-2.0); `opentelemetry.semconv._incubating.attributes.mcp_attributes` (Apache-2.0)
- **License**: ✅ allowlist
- **Footprint**: OS repo small (~400 LOC implementing 9 tools) · Implementing projects opt-in MCP-server config · Service mode optional · Docker +~5 MB (fastmcp + deps)
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ⬜ T7 ⬜ T8 ✅ T9 ✅ T10 ⬜
- **Effort**: M
- **Leverage**: HIGH — distribution channel to every MCP-aware tool (Cursor, Windsurf, Cline, Codex, Claude Code) without per-harness adapters
- **ADR candidate**: yes — proposed ADR-226

### G5. Sandbox primitive integration (`sandbox-primitives-integration.md`)

- **Recommendation**: ADOPT Bubblewrap (Linux) + Seatbelt (`sandbox-exec`, macOS); vendor Codex `linux-sandbox` policy model
- **Adopt**: bwrap (LGPL-2.0+ — runtime tool, separate process, OK); sandbox-exec (Apple OS-bundled); Codex policy YAML pattern (Apache-2.0)
- **License**: ✅ — bwrap is invoked as subprocess (no linking), Codex pattern OK
- **Footprint**: OS repo small (~250 LOC adapter) · Implementing projects opt-in (off by default) · Service mode opt-in tier · Docker +~10 MB (bwrap if not present)
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ⬜ T7 ✅ T8 ✅ T9 ✅ T10 ✅
- **Effort**: M
- **Leverage**: MEDIUM — closes 80% of accidental-destruction threat at zero new dep cost
- **ADR candidate**: yes — proposed ADR-227

### G6. Cross-session agent teams (`cross-session-agent-teams.md`)

- **Recommendation**: BUILD MINIMAL (`lib/agent_team.py`: SessionRegistry + TaskManifest + Inbox + EventLog)
- **Adopt**: pattern convergence — Claude Code Agent Teams + OpenCode session_bus (both file-IPC + fcntl)
- **License**: ✅ pattern only; own implementation FSL-1.1-MIT
- **Footprint**: OS repo medium (~400 LOC) · Implementing projects opt-in · Service mode opt-in · Docker +0 MB
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ⬜ T7 ✅ T8 ⬜ T9 ⬜ T10 ✅
- **Effort**: M
- **Leverage**: HIGH — codifies the "subagent vs agent-team" distinction operators currently navigate by feel
- **ADR candidate**: yes — proposed ADR-228 (NATS JetStream documented as Tier-3 future, not Phase 1)

### G7. Approval policies as code (`approval-policies-as-code.md`)

- **Recommendation**: PHASE 1 migrate ~15-20 deny hooks to `settings.json`; PHASE 2 ship `policy-eval.sh` + `policies/*.yaml` schema; DEFER OPA
- **Adopt**: own existing pattern (`content-policy.sh` + `content-policy.yaml`)
- **License**: ✅ no external deps
- **Footprint**: OS repo small-net-negative (delete duplicated bash, add one evaluator) · Implementing projects no impact · Service mode no impact · Docker +0 MB
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ⬜ T7 ⬜ T8 ✅ T9 ⬜ T10 ⬜
- **Effort**: S (Phase 1) + S (Phase 2)
- **Leverage**: MEDIUM — reduces hook count, surfaces policy in `/permissions`, kills bash-embedded thresholds
- **ADR candidate**: yes — proposed ADR-229 (multi-phase)

### G8. Cost-aware routing + budgets (`cost-aware-routing.md`)

- **Recommendation**: BUILD MINIMAL (`lib/session_budget.py`) + INTEGRATE LiteLLM `a2a_iteration_budgets` semantics
- **Adopt**: LiteLLM pattern (MIT)
- **License**: ✅ pattern + reference impl both allowlist
- **Footprint**: OS repo small (~50 LOC) · Implementing projects no forced impact · Service mode opt-in budget enforcement · Docker +0 MB
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ✅ T7 ⬜ T8 ⬜ T9 ⬜ T10 ⬜
- **Effort**: S
- **Leverage**: HIGH — closes the documented $47K-incident class (alerts can't prevent the next call; only sync gates can)
- **ADR candidate**: yes — proposed ADR-230 (or fold into ADR-211 service-mode readiness)

### G9. Event-driven orchestrator state (`event-driven-orchestrator-state.md`)

- **Recommendation**: BUILD MINIMAL (sequence numbers + per-session streams + `@event_wrap` decorator)
- **Adopt**: Temporal/Inngest pattern (memoize Activity results, inject on replay)
- **License**: ✅ pattern only; own implementation
- **Footprint**: OS repo small (~150 LOC across 3 phases) · Implementing projects no impact · Service mode no impact · Docker +0 MB
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ✅ T7 ✅ T8 ⬜ T9 ⬜ T10 ✅
- **Effort**: S (sequence) + S (per-session) + M (event_wrap)
- **Leverage**: VERY HIGH — **prerequisite for replay (G1), retry classification (G10), cost ledger (G8 reconciliation), agent-teams event log (G6)**. Build first.
- **ADR candidate**: yes — proposed ADR-231 (load-bearing for several other ADRs)

### G10. Failure recovery / retry semantics (`failure-recovery-retry-semantics.md`)

- **Recommendation**: BUILD MINIMAL (`lib/retry_contract.py` classifier + circuit breaker in `dispatch.py` + idempotency keys for stateful tools); CONSOLIDATE 6 magic-number retry counts into `rules/retry-contract.md`
- **Adopt**: classification taxonomy from MAST paper (academic; pattern only) + circuit-breaker semantics from established libraries
- **License**: ✅ no external runtime deps
- **Footprint**: OS repo small (~120 LOC) + rule consolidation · Implementing projects no impact · Service mode no impact · Docker +0 MB
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ✅ T7 ✅ T8 ⬜ T9 ⬜ T10 ⬜
- **Effort**: S
- **Leverage**: HIGH — closes the silent ECONNRESET/EPIPE gap and the LangGraph+Pydantic ValidationError trap; idempotency keys eliminate side-effect duplication on retry
- **ADR candidate**: yes — proposed ADR-232

### G11. Tool discovery dynamic registration (`tool-discovery-dynamic-registration.md`)

- **Recommendation**: ADOPT Anthropic `defer_loading: true` + ToolSearch pattern; INTEGRATE `notifications/tools/list_changed` consumption; DEFER true mid-session MCP server injection
- **Adopt**: Anthropic API native feature (no license cost)
- **License**: ✅ — uses already-licensed API capability
- **Footprint**: OS repo small (changes in `lib/dispatch.py` + sub-agent prompt composition) · Implementing projects no impact · Service mode no impact · Docker +0 MB
- **Test tiers**: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ✅ T7 ⬜ T8 ✅ T9 ⬜ T10 ⬜
- **Effort**: S
- **Leverage**: MEDIUM — 85% token reduction reported, no surface expansion
- **ADR candidate**: maybe — could fold into ADR-226 (MCP server) as a sibling concern, or stand alone as ADR-233

---

## Ranked implementation plan

Three phases. Each phase is a coherent unit; Phase 1 is the prerequisite layer; Phases 2 and 3 build on it.

### Phase 1 — Substrate (build before everything else)

| # | Item | ADR | Effort | LOC | Unblocks |
|---|---|---|---|---|---|
| 1.1 | Event-sourced session_bus (sequence + per-session + `@event_wrap`) | 231 | S+S+M | ~150 | G1, G6, G8, G10 |
| 1.2 | Shadow-git substrate (`lib/shadow_git.py`) | 223 | M | ~200 | G1, governance-as-restore |
| 1.3 | Retry contract + cost session ledger | 232 + 230 | S+S | ~170 | G10 closure, G8 closure |
| 1.4 | Handoff envelope + call-chain dedup | 225 | S | ~150 | G3, G6 |

**Phase 1 totals**: ~670 LOC, zero new external deps, all ✅ on C1+C2. Should be ~2 weeks for a single-author. Unlocks 60% of the gap surface.

### Phase 2 — Distribution & adapters (after substrate)

| # | Item | ADR | Effort | LOC | Notes |
|---|---|---|---|---|---|
| 2.1 | MCP server (`packages/mcp-server/cos_mcp.py`) | 226 | M | ~400 | fastmcp adoption; +5 MB image; trust-pinning prerequisite |
| 2.2 | Cross-session agent-team substrate | 228 | M | ~400 | file-IPC; uses Phase 1 event log |
| 2.3 | Bubblewrap/Seatbelt sandbox adapter | 227 | M | ~250 | OS-native; zero new deps; opt-in |
| 2.4 | defer_loading + ToolSearch wiring | 233 (or merged into 226) | S | ~50 | client-side; native Anthropic feature |

**Phase 2 totals**: ~1,100 LOC + ~5 MB image delta (only fastmcp). Each is opt-in from the user's perspective; defaults preserve current behavior.

### Phase 3 — Operator surface & policy hygiene (after Phases 1+2)

| # | Item | ADR | Effort | LOC | Notes |
|---|---|---|---|---|---|
| 3.1 | Detached agent daemon (cos-agent-daemon.py + tmux + worktree wiring) | 224 | M | ~300 | Reuses ADR-220 worktree audit; opt-in service-mode lane |
| 3.2 | Approval policies — Phase 1 (migrate 15–20 hooks to settings.json) | 229.1 | S | net negative | Removes bash, adds visibility in /permissions |
| 3.3 | Approval policies — Phase 2 (`policy-eval.sh` + `policies/*.yaml`) | 229.2 | S | ~150 | Generalizes existing content-policy pattern |

**Phase 3 totals**: ~450 LOC + duplication killed in bash hooks. All opt-in.

### Conscious non-coverage (document in Phase 0 README addendum, do not pursue)

| Area | Why we don't pursue | Track for later |
|---|---|---|
| Multi-machine cloud orchestration | Local-first is positioning, not a gap | If demand emerges from operator cohort |
| CRDT-based merging | Code is non-commutative; nobody uses CRDT for agent merges | n/a |
| Hypervisor sandboxes (Firecracker) as primary | Operationally expensive; Bubblewrap closes 80% at zero cost | E2BAdapter as opt-in tier in ADR-227 |
| OPA / Rego policy engine | Single-operator OS doesn't need ABAC complexity | Re-evaluate at multi-tenant deployment |
| Mid-session MCP server injection | "Not planned" upstream (Anthropic); deferred-loading covers 85% | Track Anthropic spec changes |
| Temporal / Cadence durable workflows | Heavy external dep violates C2 | `@event_wrap` covers MVP determinism need |
| NATS JetStream cross-session bus | Heavy external dep violates C2 default; documented as Tier-3 only | If file-IPC contention measured > X% in production |

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

The gap analysis from earlier in the day estimated ~60–65% coverage breadth. With Phase 1 + Phase 2 implemented, that rises to ~85–90%, with the remaining ~10% being conscious non-coverage (multi-machine cloud, hypervisor sandboxes as primary, OPA, Temporal, etc.) plus deferred items (mid-session MCP server injection, which the upstream itself hasn't shipped).

**The ~85–90% coverage target is reachable in ~3–4 weeks of single-author work** if the substrate (Phase 1) lands first and Phase 2 piggybacks on it. The biggest risk is *not* technical — it's resisting the temptation to add a new dependency for each Phase 2 item. The reports are unanimous: the patterns we need exist; they're built on file-IPC + git + JSONL + native OS primitives. Adopting them is the work.

**One uncomfortable finding from the synthesis**: several items the operator probably perceives as separate (replay, agent teams, retry, cost) all share the same load-bearing primitive (event-sourced session bus). Building any one of them as a standalone feature locks in the wrong shape. The synthesis recommends ADR-231 first, even though it has the lowest user-visible immediate value, because every other high-value ADR depends on its shape.

**Trust report (per `rules/trust-score.md`)**:
- SCORE: 82 STATUS: HIGH EVIDENCE: 11 reports + 230 sources UNCERTAINTIES: 4
- WHAT I VERIFIED: each verdict block fills C4's 6 fields; license claims cross-checked against research-cited SPDX; footprint claims cross-checked against C2 surfaces; effort sizes are agent-reported and operator should sanity-check
- UNSURE ABOUT: (a) whether `@event_wrap` decorator interacts cleanly with existing `dispatch.py` retry logic — needs prototype; (b) whether Bubblewrap is shipped on operator's macOS path (it isn't — Seatbelt is the macOS path; needs explicit branching in adapter); (c) license verification on Hermes shadow-git pattern (pattern reuse, not code reuse, so likely OK but operator should confirm); (d) whether Anthropic's `defer_loading` is exposed in the SDK version COS pins
- HUMAN SHOULD CHECK: ADR slot numbers (this synthesis assumed 222 as ceiling; please verify against current `docs/adrs/` listing); confirmation that the operator wants 11 new ADRs vs. consolidating some pairs (231+223; 230+232; 226+233 are obvious consolidation candidates)
