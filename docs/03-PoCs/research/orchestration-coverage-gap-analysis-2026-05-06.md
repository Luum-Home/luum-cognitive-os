# Orchestration Coverage Gap Analysis — 2026-05-06

**Status**: Active — research-driven; per-gap deep-dives spawned in parallel
**Author**: Operator session 2026-05-06 (inline assessment, follow-up agents launched into `docs/03-PoCs/research/orchestration-gaps/`)
**Trigger**: Operator question — *"are we sure that, for orchestration, we cover everything other tools cover in their latest versions?"*
**Companion**: [`multi-agent-orchestration-prior-art-2026-05-06.md`](multi-agent-orchestration-prior-art-2026-05-06.md) — 79-source research focused on git/concurrency/stash. This document is wider: covers orchestration as a whole, not just the slice that produced the bug.

---

## Honest answer to the question

**No, we are not fully covered.** The first research report (concurrency + stash) closed one specific gap. Orchestration is broader. Best estimate of coverage breadth against the 2026 frontier: **~60–65%**.

This document categorizes the 2026 orchestration surface area into three buckets — **covered**, **partial**, **missing** — and spawns one research agent per gap to build implementation guidance.

The frontier we're comparing against (versions current as of May 2026):

- Claude Code 2.x (Anthropic) — built-in worktrees, Skills, sub-agents, agent teams
- Cursor 3.0 — Background Agents in Ubuntu VMs, Composer Agent
- Codex App + CLI (OpenAI) — native sandboxes, max_threads, approval-policy.yaml
- GitHub Copilot CLI + Cloud Agent — worktree isolation, Actions ephemeral runners
- Devin 2.x (Cognition) — VM hypervisor snapshots, replay timeline, scrub
- Replit Agent — block-level CoW snapshots, manifest pointers
- OpenCode (sst) — provider-agnostic terminal-first orchestrator
- GitButler — virtual branches in single workspace, agent assist
- Aider 0.6x+ — single-process git-aware coder
- OpenHands SDK — `BaseWorkspace` SDK abstraction
- AutoGen / CrewAI / LangGraph — message-passing multi-agent frameworks
- MCP (Model Context Protocol) — emerging de-facto agent↔tool / agent↔agent bus

---

## Coverage map

### ✅ Covered (parity or near-parity)

| Area | COS surface | Industry analogue |
|---|---|---|
| Worktree-per-agent isolation | ADR-220 + `lib/worktree_audit.py` + `cos worktree audit` | Claude Code 2.x `isolation: "worktree"`, Cursor 3, Copilot CLI |
| Sub-agents within a session | ADR-203 subagent capability contract, skill registry per agent | Claude Code `Agent` tool, OpenCode `general`/`plan`, Codex `agents.*` |
| Per-agent permission/tool gating | Skill registry + hook-enforced gates | OpenCode allow/ask/deny per subagent, Codex sandbox policy |
| Pre/post tool hooks | ADR-099 + hook layer (~20 hooks) | Claude Code hooks (mismo patrón), Anthropic SDK |
| Persistent memory layer | Engram (file-backed, cross-session) | Devin vectorized memory, Letta, Mem0, LangGraph checkpointers |
| Manifest-driven validation primitives | ADR-212/215/217/218 (cross-stack pattern) | ConTree config, Replit manifest pointers |
| Quality gates / DoD framework | trust-score, DoD levels, adversarial-review | Nobody else has this formalized at the orchestrator layer |
| Operator-in-loop for destructive ops | ADR-055b destructive-git-blocker, ADR-089 commit scope guard | Claude Code permission gates, Cline YOLO-mode warning |
| Phase-aware harness behavior | reconstruction vs production phase modes | No published prior art (defensible bet) |

### ⚠️ Partial coverage (gap exists, not catastrophic)

| Area | What we have | What we lack | Industry full version |
|---|---|---|---|
| Cross-session multi-agent | sub-agents within session; coordination service-mode (ADR-211) is partial | Clean contract distinguishing in-session subagents from cross-session "agent teams" | Claude Code separates `subagents` (1 session) from `agent teams` (N sessions) explicitly |
| Tool discovery / dynamic registration | `/tool-discovery` skill (ADR-216), tool gate | Runtime MCP-based dynamic tool registration mid-session | Codex MCP integration, Claude Code MCP, OpenCode dynamic |
| Approval policies as code | Hooks-as-policy distributed across files | Single unified policy file/manifest with declarative semantics | Codex `approval-policy.yaml` |
| Cost-aware routing | Model-routing rules per skill, capability tiers | Per-session/per-agent budget enforcement with backpressure | Anthropic SDK budget hooks, OpenCode permission grades |
| Streaming / event-driven coord | `session_bus.py` event log | Full event-sourced orchestrator state with replay | LangGraph events, OpenCode session_bus end-to-end |

### ❌ Missing (real gaps)

| Area | Industry version | Our position |
|---|---|---|
| **Replay timeline + restore-by-checkpoint** | Devin "scrub timeline + restore checkpoint icon"; Replit time-travel via manifest version | Engram captures memory; nothing for "rewind and re-execute" |
| **Background / cloud agents** | Cursor BA (Ubuntu VMs), Devin (cloud IDE per agent), Copilot Cloud Agent (Actions runners) | Local-only by design; no equivalent path |
| **Sandbox/microVM as opt-in primitive** | E2B Firecracker, Daytona, Modal Sandboxes, ConTree | No SDK integration; no abstraction layer to plug one in |
| **Agent-to-agent handoff protocol** | OpenAI Swarm, AutoGen GroupChat, CrewAI hierarchical, LangGraph supervisor, MCP A2A | Agents don't talk to each other; orchestrator is sole hub |
| **Native scheduling of orchestrations** | Cursor BA cron, Replit Agent scheduled, Copilot issue-triggered | `CronCreate` exists for tasks but no orchestration semantics |
| **MCP as orchestration bus** | Anthropic MCP becoming de-facto agent↔tool and agent↔agent protocol | Ambiguous positioning; no MCP-bus consumption strategy |
| **Replay determinism** | Devin 100% replay, Replit checkpoint+restore | Engram is read-only memory, no re-execute |
| **Parallel-with-shared-workspace** | GitButler virtual branches in single WT | We force isolation or single-thread; no middle path |
| **Distributed multi-machine** | Devin cloud, Replit cloud | Local-only by deliberate choice (not a bug; document explicitly) |
| **Failure recovery semantics** | Codex `agents.max_depth` retry, LangGraph retry policies, Anthropic SDK retry | Retry logic distributed across hooks; not unified |

---

## Verdict by category

### Critical gaps to close (competitive)

1. **Replay timeline + restore-by-checkpoint** — Devin's signature feature. If we sell ourselves as a governance layer, replay+restore is governance. We have the substrate (Engram event log) but lack the UX/CLI/restore semantics.
2. **Background agents (some path)** — even if we stay local-first, we need a story. Either an opt-in cloud-runner integration, or a "headless orchestration mode" that runs locally without a TTY. Cursor BA and Copilot Cloud Agent set the bar.
3. **Agent-to-agent handoff** — if we ship "agent teams" (and we already mention them in ADR-211 service mode), we need a protocol. Currently the orchestrator is the only conduit. The field uses Swarm-style or supervisor-style; we have neither.
4. **MCP as orchestration bus** — MCP is the standard. Not adopting it puts us outside the agent ecosystem. We need at minimum: MCP server endpoints for our primitives + MCP client capability to consume external tools.

### Decisions we should explicitly make (not necessarily close)

5. **Sandbox/microVM** — opt-in integration with E2B or Daytona is high-leverage low-effort. Document the choice; ship a thin adapter.
6. **Tool discovery dynamic** — currently OK; but if MCP adoption advances, this becomes urgent.
7. **Approval policies as code** — could unify the 20+ hooks into a single `policy.yaml`. Big refactor; defer until ADR-211 service mode hardens.
8. **Cost routing + budgets** — `lib/cost_predictor.py` exists; need to wire to per-session enforcement.

### Conscious non-coverage (document, don't pursue)

9. **Multi-machine cloud orchestration** — local-first is positioning, not a gap.
10. **CRDT-based merging** — the prior research said no.
11. **Hypervisor sandboxes as primary** — operationally expensive; opt-in only.

### Partial → cleanup

12. **Cross-session multi-agent contract** — Claude Code's terminology (subagents vs teams) is clean. Adopt it. ADR-203 covers subagent contract; we need an analogous "agent teams" ADR.

---

## Research agendas spawned (12 parallel agents)

Each agent produces one report under `docs/03-PoCs/research/orchestration-gaps/`. Constraints: no code modifications, ≥10 sources per agent, honest about uncertainty, save discoveries to engram before returning.

| # | Topic | Output file |
|---|---|---|
| 1 | Replay timeline + restore-by-checkpoint architectures | `replay-timeline-architectures.md` |
| 2 | Background/cloud agent execution patterns | `background-agent-patterns.md` |
| 3 | Agent-to-agent handoff protocols | `agent-to-agent-handoff.md` |
| 4 | MCP as orchestration bus | `mcp-as-orchestration-bus.md` |
| 5 | Sandbox primitive integrations (E2B/Daytona/Modal/Firecracker) | `sandbox-primitives-integration.md` |
| 6 | Cross-session multi-agent contracts | `cross-session-agent-teams.md` |
| 7 | Approval policies as code | `approval-policies-as-code.md` |
| 8 | Cost-aware routing + budget enforcement | `cost-aware-routing.md` |
| 9 | Streaming / event-driven orchestrator state | `event-driven-orchestrator-state.md` |
| 10 | Failure recovery / retry semantics | `failure-recovery-retry-semantics.md` |
| 11 | Local-first equivalent of cloud-agent capability | `local-first-background-agents.md` |
| 12 | Tool discovery + dynamic registration patterns | `tool-discovery-dynamic-registration.md` |

After all 12 agents return, the synthesis pass produces:
- `docs/03-PoCs/research/orchestration-gaps/SYNTHESIS-2026-05-06.md` — ranked implementation plan
- ADR proposals for the top 4 critical gaps
- A "we don't pursue this" appendix listing the conscious non-coverage with rationale

---

## Synthesis constraints (binding for SYNTHESIS-2026-05-06.md)

These are operator-set non-negotiables. The synthesis pass and any ADR
candidates emerging from the 11 research reports MUST honor them. If a
research report's top recommendation violates these, the synthesis MUST
either (a) propose a constraint-respecting alternative or (b) explicitly
mark the area as "rejected — constraints conflict" with rationale.

### C1. Adopt over build — permissive licenses only

- **First reflex**: search for an existing tool / library / spec that solves
  the gap. Adoption is preferred to in-house implementation in every case
  where a well-maintained option exists.
- **License allowlist**: MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC,
  MPL-2.0 (file-level copyleft, OK), Unlicense, 0BSD, Zlib.
- **License blocklist** (cannot adopt as runtime dependency or vendored
  code): AGPL-3.0 / AGPL-3.0-or-later, SSPL, BSL / Business Source License
  in any pre-Change-Date state, Commons Clause additions, EPL-2.0 (only
  by case review), GPL-2.0 / GPL-3.0 (only as separate-process tools called
  via subprocess/IPC, never linked or vendored).
- **Patterns / ideas / specs** can be borrowed from any license, including
  blocklisted ones — it's the *code* that has the contagion. Read the AGPL
  source, document the pattern, write a clean-room implementation under
  our license.
- Each research report MUST cite license for every tool it recommends
  adopting. If unknown, mark "license: unverified — requires triage."

### C2. Footprint discipline — do not overload any consumer surface

The OS exists in four consumer contexts. Each has its own footprint budget.
Adopting a tool that overloads any of them is grounds for rejection.

| Consumer surface | Budget signal |
|---|---|
| **The OS itself** (this repo) | New required runtime deps ≤ 1 per ADR; new optional opt-in deps OK; no mandatory daemon process unless it is the feature itself |
| **Projects that install the OS** (the user's repo) | Zero forced new toolchains; everything that touches the user's repo MUST be opt-in via cognitive-os.yaml flag; default-off for anything that runs a process |
| **The OS as a service** (cosd, ADR-211 service mode) | No new long-lived processes per session; bounded memory; bounded disk; no required network egress |
| **Docker / container runtime** (current and future packaging) | Image size delta < 50 MB per adopted dependency; alpine-compatible preferred; multi-arch (arm64+amd64) support required; no dependency that requires privileged mode |

Specific anti-patterns to avoid in recommendations:
- "We'll add a Postgres / Redis / RabbitMQ requirement." Hard no unless
  it's an opt-in adapter, default off, with a SQLite/file/in-process
  fallback.
- "We'll require the user to install a kernel module / Docker / Firecracker."
  Hard no for any default path. Allowed as an opt-in tier.
- "We'll vendor a 200 MB Go binary." Hard no.
- "We'll add a background daemon to every project." Hard no — daemonization
  is opt-in service mode only.
- "We'll tightly couple to one cloud provider's SDK." Hard no — abstract
  behind an adapter or don't ship.

### C3. Test coverage tiers — every recommendation declares its tiers

Every implementation recommendation in the synthesis MUST declare a test
matrix across at least the following tiers. The synthesis cannot accept
a recommendation that says "tests TBD."

| Tier | What it proves | Trigger |
|---|---|---|
| **T1 — Unit** | Functions / classes work in isolation against documented inputs | Every function with branching logic |
| **T2 — Integration** | Modules interact correctly within one process | Any feature spanning ≥2 modules |
| **T3 — Behavior / contract** | The CLI / API / hook contract behaves as advertised end-to-end | Every CLI flag, hook, manifest schema |
| **T4 — Smoke** | Happy-path end-to-end on a clean env produces the documented user-visible result in <60s | Every ADR — non-negotiable |
| **T5 — Adversarial / negative** | Wrong inputs, missing files, race conditions, blocked preflight, permission denials all produce expected errors, not crashes | Every primitive with a security or correctness boundary |
| **T6 — Performance / load** | p50/p95 latency under N concurrent agents stays within budget | Any primitive on the hot path of agent launch / dispatch |
| **T7 — Failure injection / chaos** | Killing the agent mid-flight, dropping the network, full disk, all leave the system recoverable | Any primitive that mutates state |
| **T8 — Compatibility / cross-harness** | Works on Claude Code + Codex + OpenCode where applicable | Any primitive declared harness-agnostic |
| **T9 — Adoption truth (ADR-217 reuse)** | Anything claimed in NOTICE / docs / READMEs actually exists and runs | Any ADR introducing a new external tool |
| **T10 — Audit invariants (ADR-220 reuse)** | After a primitive runs, repo divergence / WT mutation / stash state stays within declared invariants | Any primitive that touches git or working tree |

Tier defaults:
- **Internal-only library** → T1 + T2 minimum, T4 strongly preferred.
- **Operator-facing primitive (CLI / hook / manifest)** → T1 + T2 + T3 + T4 + T5 minimum.
- **Anything touching git, working tree, stash, worktree** → add T7 + T10.
- **Anything in the agent-launch hot path** → add T6.
- **Anything claiming cross-harness** → add T8.
- **Anything adopting an external tool** → add T9.

The smoke tier (T4) is the constraint everyone cuts and shouldn't.
Smoke runs the actual feature end-to-end on the actual binary in a
clean fixture directory. It catches the "works in my context, breaks
in a fresh checkout" class that unit + integration miss.

### C4. Synthesis output requirements

For each of the 11 research areas, the synthesis MUST emit a structured
verdict block:

```
### <Gap area>
- Recommendation: ADOPT <tool> | INTEGRATE <spec> | BUILD MINIMAL | DEFER | REJECT
- License (if ADOPT/INTEGRATE): <SPDX id> — allowlist|blocklist|unverified
- Footprint impact:
    OS repo: <none|small|medium|large>
    Implementing projects: <none|opt-in|forced>
    Service mode: <none|opt-in|required>
    Docker image: <delta MB>
- Test tier matrix: T1 ✅ T2 ✅ T3 ✅ T4 ✅ T5 ✅ T6 ⬜ T7 ⬜ T8 ⬜ T9 ⬜ T10 ⬜
- Effort: <S | M | L | XL>
- Leverage: <high | medium | low>
- ADR candidate: <yes — number TBD | no | superseded by ADR-XXX>
```

A recommendation that cannot fill all six fields is incomplete and goes
back for refinement before being merged into the synthesis.

---

## What this document does NOT do

- It does not commit to implementing all 12 areas. It commits to *researching* them so the operator can decide.
- It does not benchmark performance, latency, or cost across systems. That is a separate evaluation.
- It does not assess our existing partial primitives in depth — only the field's. Internal assessment is a separate exercise (closer to a `/component-reality-check` run).
- It does not declare timelines. Implementation order is a follow-up decision after the 12 reports return.
