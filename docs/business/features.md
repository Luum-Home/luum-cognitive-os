# Cognitive OS — Feature Matrix

> This document details all Cognitive OS capabilities.
> All core features are source-available under [FSL-1.1-MIT](../../LICENSE) — converts to MIT after 2 years. See [LICENSE](../../LICENSE) for terms.

---

## Status legend

Each feature row carries a status marker. Read these as honesty markers, not
quality judgments — `DORMANT` and `ASPIRATIONAL` items often have working code
behind a feature flag or are documented as next-cycle work.

- **REAL** — production-ready, hook-enforced or covered by unit/behaviour tests
  and wired into the default flow
- **DORMANT** — code exists and is exercised by tests, but feature-flagged off
  or only active under a specific harness/profile (the user must opt in)
- **ASPIRATIONAL** — design and partial scaffolding exist; the loop is not yet
  closed end-to-end. Tracked as future work, not as a shipped capability

Source of truth: `rules/RULES-COMPACT.md`, weekly aspirational audit at
`docs/reports/aspirational-audit-*.md`, full reconciliation at
`docs/legal/h1-feature-status-audit.md`.

## Feature Overview

| # | Feature | Status | What It Does | Impact |
|---|---------|--------|--------------|--------|
| 1 | Persistent Memory | REAL | Cross-session knowledge retention | AI never forgets decisions, bugs, or conventions |
| 2 | Spec-Driven Development | REAL | Structured 10-phase workflow for complex changes | Features are planned, specified, and verified — not just coded |
| 3 | Quality Control | REAL | 7 immutable gates + configurable rules | Quality guaranteed by infrastructure, not by willpower |
| 4 | Self-Improvement Loop | DORMANT | Captures errors, detects patterns, proposes skill/routing updates for human review | Closed-loop autonomous mutation is gated by ADR-201/204/206; the propose-only slice is implemented |
| 5 | Multi-Agent Orchestration | REAL | 12+ simultaneous agents with cycle-deduplication and worktree isolation | Closes the #1 multi-agent production failure mode (MAST 2025) |
| 6 | Replay Timeline & Restore-by-Checkpoint | REAL | Shadow-git substrate; every governance event carries a `file_tree_sha` | Devin-parity rewind without VM snapshots; governance-as-restore-point |
| 7 | Sync Cost + Retry Gate | REAL | Pre-call budget enforcement, retry classifier, idempotency keys, circuit breaker | Closes the runaway-loop class |
| 8 | Agent-to-Agent Handoff Protocol | REAL | Typed `HandoffEnvelope` with call-chain dedup and permission intersection | Addresses cycle-driven multi-agent failure modes |
| 9 | Security and Compliance | REAL | Hook-enforced credential blocking, secret detector, content policy; NeMo Guardrails available as opt-in | Defense-in-depth, hook-enforced |
| 10 | Observability and Cost Control | REAL | Per-session JSONL streams, OpenTelemetry MCP semconv, budget caps | Know exactly how much your AI costs |
| 11 | Developer Experience | REAL | 27+ skills, 30+ hooks, 22+ rules, 16+ agent personas | Specialized expertise for every task |
| 12 | Multi-IDE Portability + MCP Server | REAL | 7+ IDE adapters PLUS native MCP server exposing core primitives | Your investment moves with you; every MCP-aware tool gets governance access |
| 13 | Sandbox Adapter Tiers | REAL | Bubblewrap (Linux) / Seatbelt (macOS) OS-native default; E2B/microVM opt-in | 80% of accidental-destruction threat closed at zero new dep cost |
| 14 | Detached Agent Daemon | REAL | Local-first long-running agents via tmux + worktree + file-sentinel | "Fire and forget" UX without going cloud |
| 15 | SRE and Self-Healing | DORMANT | Advisory monitoring + remediation registry with governed (human-approved) execution | MAPE-K-inspired loop is documented and partially wired; no autonomous production mutation. RULES marks `singularity` as `(inactive)` and `MAPE-K(inactive)` |
| 16 | Industry Presets | REAL | Templates for fintech, healthcare, e-commerce, SaaS | Pre-loaded best practices |
| 17 | Automation Workflows | DORMANT | End-to-end pipelines from ticket to deployed code | Pipeline templates exist; "ticket-to-prod" turnkey path is operator-assembled, not pre-wired |
| 18 | Manifest-Driven Governance | REAL | Every primitive declares a schema-versioned YAML | Auditable, machine-readable, no policy hidden in shell scripts |
| 19 | Open-Source Core | REAL | FSL-1.1-MIT core + plugin system (converts to MIT after 2 years) | Try for free, contribute, and benefit |

---

## 1. Persistent Memory (Engram)

Your AI assistant forgets everything when the session ends. Cognitive OS solves this.

**How it works:**
- Engram provides persistent, searchable memory across all sessions via the MCP protocol
- Automatic save triggers fire after decisions, bug fixes, discoveries, and conventions
- Full-text search (FTS5) over all past observations
- Session summaries are automatically saved before each session close and context compaction
- Topic keys organize knowledge hierarchically (e.g., `architecture/auth-model`, `sre-fix/mysql/connection-refused`)
- Private mode disables all persistence for sensitive conversations

**What exists today:**
- Engram MCP server
- Proactive save protocol with 4 trigger categories
- Session close protocol ensuring no knowledge is lost
- Post-compaction recovery
- Git-based sync for shared knowledge bases

---

## 2. Spec-Driven Development (SDD)

Complex features need planning, not just code.

**10 phases with dependency tracking:**
```
init --> explore --> propose --> spec --+--> tasks --> apply --> verify --> archive
                                       |
                                       +--> design
```

**Adaptive intelligence:**

| Complexity | Signal | Action |
|---|---|---|
| Trivial | One file, < 20 lines | Do it directly, no workflow |
| Small | 1-3 files, one service | Lightweight proposal |
| Medium | Multi-file, one service | SDD from proposal through apply |
| Large | Multi-service, new integration | Full SDD pipeline |
| Critical | Security, auth, payments | Full SDD with mandatory verification |

**What exists today:**
- 9 SDD phase skills
- OpenSpec alternative (4 skills for lighter change tracking)
- Engram-backed artifact persistence
- Orchestrator protocol for multi-agent SDD execution

---

## 3. Quality Control

Quality gates enforced by infrastructure, not by hope.

**Constitutional gates (7 example immutable rules):**
1. Mobile never talks directly to microservices (always through the BFF)
2. Mock before integrating (no external vendor without a mock)
3. Tests before merging (all new code must have tests)
4. Secrets never in code (always environment variables)
5. Backward-compatible APIs (no breaking changes without a version bump)
6. Idempotent financial operations (via transaction IDs)
7. Audit trails for all critical operations

**Additional enforcement proof paths:**
- Control manifest: forbidden zones, performance constraints, security constraints
- License policy: automatically blocks AGPL, SSPL, BSL, ELv2 dependencies
- 21 hooks that fire at runtime (SessionStart, PreToolUse, PostToolUse)
- Configurable coverage thresholds per industry (80% fintech, 90% healthcare, 50% startup MVP)

**What exists today:**
- 19 rule files covering architecture, security, testing, licensing, fault tolerance, and more
- 21 hook scripts enforcing rules at runtime
- Security hook family: see `hooks/secret-detector.sh`, `hooks/destructive-git-blocker.sh`, and `hooks/destructive-rm-blocker.sh`
- Coverage gate hook with configurable thresholds

---

## 4. Self-Improvement Loop

**Status: DORMANT (propose-only).** The detect/draft loop captures errors and
proposes skill/routing changes. Promotion to runtime mutation is gated by
ADR-201/204/206 and requires human approval. "Autonomous self-improvement" is
**not** claimed for v1.

```
Agents execute tasks
    |
    v
Hooks capture: metrics (tokens, time, cost) + errors (test/lint/build)
    |
    v
Pattern detector injects warnings into upcoming agents
    |
    v
/error-analyzer proposes skill updates
    |
    v
/model-optimizer adjusts model routing
    |
    v
/agent-kpis measures everything with 20 KPIs across 5 OKRs
    |
    v
Improved skills --> more efficient agents --> KPIs improve --> closed loop
```

**Agentic primitives:**
- **Error learning**: Automatic capture of test, lint, and build failures
- **Pattern detection**: 3+ similar errors within 24h trigger warnings
- **Skill adaptation**: After 3+ failures, suggests skill rewrite
- **Automatic skill generation**: Complex solutions are converted into reusable skills
- **Model routing optimization**: Adjusts which model handles which task based on performance
- **Agent KPIs**: 20 metrics across 5 OKRs (quality, efficiency, self-improvement, velocity, security)

---

## 5. Multi-Agent Orchestration

Coordinate multiple AI agents working in parallel without conflicts.

**How it works:**
- Orchestrator pattern: one coordinator delegates work to specialized sub-agents
- Sub-agents receive isolated context with pre-resolved skill references
- Task registration and tracking via active-tasks.json
- Fault tolerance: crashed agents are detected and relaunched
- Idempotent execution: agents verify whether work already exists

**Proven scale:**
- 12+ simultaneous agents
- 100+ total launches in a single session
- Each agent receives accumulated knowledge from Engram

**Fault tolerance (4-tier model):**
1. Connection resilience (reconnection, heartbeat, graceful shutdown)
2. LLM call resilience (auth rotation, rate limit detection, model fallback)
3. Context resilience (pre-compaction flush to Engram, session summary)
4. Agent resilience (orphan detection, parent notification, relaunch)

**Concurrency safety primitives (post-2026-05-07):**
- Worktree-per-write-agent isolation (ADR-220 + ADR-223) with mutex on `git worktree add` to dodge the upstream race
- Stash references by SHA, not position (ADR-221) — eliminates the Anthropic-shipped class of "applied wrong stash" bugs
- Two-phase capture pre-agent stash (ADR-222) — no stash exists if the agent never launched
- Cross-session agent-team file-IPC (ADR-233) — `cos team ...` CLI with TaskCreated/TaskCompleted/TeammateIdle hooks

---

## 6. Replay Timeline & Restore-by-Checkpoint

Devin's signature feature, without the hypervisor.

**Architecture:**
- Off-repo bare git repo per session under `~/.cognitive-os/snapshots/{project_id}/{session_id}/.git`
- Every state-mutating tool call snapshots via `git write-tree`; the SHA rides on the originating event in the per-session JSONL stream
- Three restore modes (Cline-pattern proven UX): files only, conversation only, files+conversation atomic
- Diff preview is mandatory before any restore; `cos rollback` refuses without operator confirmation

**Differentiation:**
- Every governance event (policy check, blast-radius, audit finding) carries a `file_tree_sha`. **Any governance event is itself a restorable checkpoint.** No competitor links policy events to file state with restore capability.
- Captures untracked files at snapshot time — covers the "operator's WIP that wasn't committed" class git stash misses.
- No hypervisor, no cloud service. Pattern proven in production by Cline, Hermes, Kilo.ai, and `git-shadow` — all four use the same primitive.

**Files:**
- `lib/shadow_git.py`, `manifests/shadow-git.yaml`, `cos rollback` CLI

---

## 7. Sync Cost + Retry Gate

The runaway-loop killer. The November 2025 industry $47,000 incident proved that async cost dashboards cannot prevent the next API call. Only synchronous pre-call gates can.

**Sub-features:**
- **Failure classifier (`lib/retry_classifier.py`)** — single authoritative classify_failure() across 7 classes (connection_layer, rate_limit, provider_5xx, validation_error, auth_error, quota_exceeded, unknown). Replaces six contradictory retry magic numbers previously scattered across rule files.
- **Per-failure-class policy (`manifests/retry-contract.yaml`)** — deterministic mapping (max_attempts, backoff, diversity_required, escalation_after_n). Validation errors get re-prompt-with-schema; connection errors get exponential-with-jitter (closes the SDK ECONNRESET silent-drop gap); auth errors don't retry.
- **Per-session budget (`lib/session_budget.py`)** — file-backed ledger at `.cognitive-os/metrics/session-budgets/{session_id}.json`. Pre-call check raises `SessionBudgetExceeded` BEFORE the HTTP request fires.
- **Graduated backpressure** at 70% / 90% / 100% — caution signal injected → cheaper-tier preference → refuse. Avoids the binary hard-stop UX problem.
- **Idempotency keys (`IdempotencyKeyMixin`)** — required on stateful tools. Eliminates the documented 15–30% silent side-effect duplication that retry-without-idempotency ships with industry-wide.
- **Per-provider circuit breaker** — opens on error_rate / p95_latency / quota / validation_failure_rate; cooldown + half-open probe.

**Files:**
- `lib/dispatch_gate.py`, `lib/session_budget.py`, `lib/retry_classifier.py`, `manifests/retry-contract.yaml`, `manifests/session-budget.yaml`

---

## 8. Agent-to-Agent Handoff Protocol

The MAST 2025 paper documented 41–87% production failure rates on state-of-the-art open-source multi-agent systems. The #1 cause: infinite handoff loops (A→B→C→A). **No framework prevents them.** Cognitive OS does.

**Primitives:**
- **`HandoffEnvelope` typed struct (`lib/handoff_envelope.py`)** — every cross-agent call MUST construct one. Carries identity, intent (delegate / handoff / query), context_mode, granted_tools, depth, call_chain.
- **Call-chain deduplication (`lib/handoff_dispatcher.py`)** — before any handoff, dispatcher checks `to_agent in call_chain`. If yes, raise `HandoffCycleDetected` cleanly. Highest-ROI safety primitive in the orchestration space (<1 day of code closes the 41-87% failure class).
- **Permission intersection** — granted tools = caller_grants ∩ receiver_manifest_declares. Compromised sub-agent doesn't get the orchestrator's blast radius.
- **Operator-in-the-loop above blast-radius threshold** — `HandoffRequested` hook can exit code 2 to require operator approval.
- **MAX_HANDOFF_DEPTH = 7** — defense-in-depth against pathological-but-acyclic chains.

**Files:**
- `lib/handoff_envelope.py`, `lib/handoff_dispatcher.py`, `manifests/handoff-protocol.yaml`

---

## 6. Security and Compliance

Enterprise-grade security built into the infrastructure.

**Defense layers:**
- **NeMo Guardrails** (NVIDIA, Apache 2.0): Conversational guardrails — jailbreak detection, topic controls
- **Constitutional gates**: Immutable rules that no agent or prompt can override
- **Production URL blocking**: Hook that prevents accidental interactions with production systems
- **Credential management**: API keys only in environment variables, startup validation, rotation tracking
- **Agent identity system**: Trust levels (0-3), audit trails, monotonic permission attenuation
- **Private mode**: Zero-persistence mode for sensitive conversations
- **License compliance**: Automatic blocking of incompatible dependencies
- **Dangerous command blocking**: Prevents rm -rf, force push, DROP TABLE, docker push to production

**Identity stack (6 layers, designed):**
1. Cryptographic identity (Ed25519 + post-quantum)
2. Credential vault (runtime secret injection)
3. Permissions (YAML-based policy engine)
4. Cross-agent discovery (A2A Agent Cards)
5. Delegation (monotonic attenuation)
6. Infrastructure identity (SPIFFE/SPIRE)

---

## 7. Observability and Cost Control

Know exactly what your AI is doing and how much it costs.

**Observability:**
- **Langfuse** (MIT): LLM engineering platform — traces, prompts, evaluations, cost tracking
- **Skill metrics**: Per-skill tracking of tokens, time, cost, and model used
- **Agent KPIs**: 20 metrics across 5 OKRs with configurable alert thresholds

**Cost control:**
- **LiteLLM** (MIT): OpenAI-compatible proxy for 100+ LLM providers — budget caps, virtual keys, rate limiting
- **Model routing**: Automatic selection of the right model per task
- **Budget alerts**: Configurable warnings and caps

---

## 8. Developer Experience

A rich ecosystem of specialized capabilities available out of the box.

| Primitive | Count | Examples |
|---|---|---|
| Skills (project) | 27 | /sdd-new, /coverage-report, /sre-agent, /error-analyzer, /model-optimizer |
| Skills (global) | 15+ | SDD phases (9), skill-creator, skill-registry, go-testing, webapp-testing |
| Hooks | 21 | auto-test-on-edit, error-learning, block-dangerous, coverage-gate |
| Rules | 19 | constitutional-gates, license-policy, sre-protocol, model-routing |
| Agent personas | 16+ | security-engineer, code-reviewer, software-architect, DBA, SRE |

**Progressive skill loading:**
1. **Always loaded**: Rules (19) — active constraints
2. **On demand**: Skills — loaded when invoked by name
3. **Auto-detected**: Stack-specific skills generated based on detected technologies

---

## 9. Multi-IDE Portability

Your investment in rules, skills, and memory is not tied to any single tool.

| Tool | Rules | Skills | Hooks | MCP/Memory |
|---|---|---|---|---|
| Claude Code | Full | Full | Full | Full |
| Cursor | Via ai-rulez | Native | Adapter | MCP config |
| VS Code Copilot | Via .github/ | Native | Adapter | MCP config |
| Gemini CLI | Via GEMINI.md | Native | Adapter | MCP config |
| OpenCode | Via AGENTS.md | Native | Adapter | MCP config |
| Kiro | Via .kiro/ | Native | Adapter | MCP config |
| Windsurf | Via .windsurf/ | Native | Adapter | MCP config |
| Codex | Via AGENTS.md | Native | Experimental | -- |

---

## 10. SRE and Repair Guardrails

Service monitoring and repair guardrails. Treat this as a partially implemented
SRE direction unless a project has wired the relevant health checks, remediation
hooks, and approval policy.

- Health hooks can monitor services in the development stack
- Known fixes stored in Engram
- Safe actions may be automated only when an explicit project policy allows them
- Unsafe actions require human approval
- 4-tier escalation policy

---

## 11. Industry Presets (Plugin System)

Pre-loaded best practices through a plugin architecture.

| Industry | Key Rules | Target Coverage |
|---|---|---|
| Fintech | PCI compliance, audit trails, idempotent operations | 80% |
| Healthcare | HIPAA data handling, consent management, audit logging | 90% |
| E-commerce | Inventory consistency, payment idempotency, PII protection | 70% |
| SaaS | Multi-tenancy isolation, usage metering, SLA compliance | 70% |

---

## 12. Automation Workflows

End-to-end pipelines from ticket to deployed code.

**5 pipeline types:**
1. Feature pipeline: ticket --> explore --> propose --> spec --> design --> tasks --> apply --> verify
2. Bug fix pipeline: issue --> reproduce --> root-cause --> fix --> test --> verify
3. Migration pipeline: audit --> plan --> extract --> test --> route traffic --> decommission
4. Deploy pipeline: build --> test --> lint --> security scan --> deploy --> smoke test
5. New service pipeline: scaffold --> configure --> implement --> test --> dockerize --> integrate

---

## 13. Open-Source Core

Transparent, extensible, and community-driven.

**Architecture:**
```
cognitive-os/
  core/           # Universal (Apache 2.0) -- works on any project
    memory/       # Engram protocol, persistence contracts
    workflow/     # SDD (10 phases), OpenSpec (4 phases)
    fault-tolerance/  # Task tracking, recovery, checkpointing
    discipline/   # Systematic debugging, TDD, verification
    safety/       # Dangerous command blocking, env protection
    skill-system/ # Auto-loader, registry, adaptation, feedback
    orchestrator/ # Delegation rules, sub-agent context protocol
  plugins/        # Domain-specific (optional)
    fintech/      # Constitutional gates, compliance agents
    ecommerce/    # Inventory, payments, PII
    saas/         # Multi-tenancy, metering, SLA
  generators/     # Auto-generate project configs from templates
```

**Quick setup:**
```bash
cd your-project
git clone https://github.com/luum-home/luum-cognitive-os.git .cognitive-os-repo
cp -r .cognitive-os-repo/.cognitive-os/ .cognitive-os/
rm -rf .cognitive-os-repo
claude
> /cognitive-os-init
```

---

## Comparison with Alternatives

| Feature | Cognitive OS | OpenClaw | BMAD | Spec Kit | superpowers |
|---------|----------|----------|------|----------|-------------|
| Persistent memory | Engram (FTS5, cross-session, team sync) | File-based | Git only | No | No |
| Spec workflow | 10 phases + OpenSpec | No | PRD-based | 5 phases | No |
| Quality gates | 7 constitutional + 19 rules + 21 hooks | No | Manifest checklist | Constitution | TDD only |
| Self-improvement | Full loop (errors -> patterns -> skills -> KPIs -> routing) | Partial | No | No | No |
| Multi-agent | 12+ parallel, fault-tolerant | Yes | Party mode | No | No |
| Cost control | LiteLLM + budget caps + model routing | /usage command | No | No | No |
| IDE portability | 7+ tools via standards | Many | Yes | Yes | Yes |
| Proven at scale | 300x on real fintech | Open-source projects | No | No | No |

---

## Planned Tiers

| Tier | Description |
|------|------------|
| **Community (Free)** | Complete open-source core. Memory, skills, hooks, rules, plugins. Everything individual developers need. |
| **Team** | Team features: cloud shared memory, KPI dashboard, skill marketplace, team sync. |
| **Enterprise** | Self-hosted, SSO/SAML, compliance reports, audit trail export, SLA, dedicated support. |

---

## Related Documents

| Document | Description |
|---|---|
| [value-proposition.md](value-proposition.md) | Value proposition and differentiation |
| [case-study.md](case-study.md) | Case study: ~300x acceleration |
| [open-source-design.md](open-source-design.md) | Framework architecture, plugin system, file audit |
| [portability-plan.md](portability-plan.md) | Multi-IDE support plan |
