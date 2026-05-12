# ADR Index

## How to Use This Index

This table is the navigable entry point to all 280 Architecture Decision Records (ADRs).
Active and Proposed ADRs are listed first for day-to-day reference. Superseded and Deprecated
records are collapsed below to reduce noise while preserving full history. Each row links to
the full ADR file under `docs/adrs/ADR-NNN-*.md`. Status is extracted from each file's
front-matter or heading section.

## Active

| # | Title | Status | Date | One-line Summary |
|---|-------|--------|------|------------------|
| 001 | A+B+C parallel — dedup, fix broken infra, add global-verify | Active |  | Draft |
| 002 | docker-pip localhost envs + targeted_test_resolver + redis dep | Active |  | Draft |
| 006 | AGPL License Compliance -- Replace Redis and MinIO | Active |  | Cognitive OS was being prepared for SaaS distribution. A full license audit of the Docker infrastructure stack revealed  |
| 007 | Rebrand from Agent OS to Cognitive OS | Active |  | The project was originally called "Agent OS." As the architecture matured, it became clear that the system manages cogni |
| 008 | Multi-Tool Support -- Not Claude Code-Only | Active |  | The AI coding tool ecosystem was fragmenting rapidly in early 2026. Users were choosing between Claude Code, OpenCode, A |
| 009 | Package Architecture -- 375 Agentic Primitives Reclassified | Active |  | Cognitive OS had grown to 375+ agentic primitives (72+ skills, 55+ rules, 57+ hooks, 40+ libs) all stored flat in their  |
| 010 | Hook Architecture v2 -- 10 Event Types, 3 Security Profiles | Active |  | Cognitive OS was using approximately 10% of Claude Code's hook capabilities. The initial hook architecture supported onl |
| 011 | Dual Gateway -- Bifrost Primary, LiteLLM Fallback | Active |  | Cognitive OS used LiteLLM as its sole AI gateway/LLM proxy. In March 2026, LiteLLM was compromised in the TeamPCP supply |
| 012 | Prompt-Driven Governance -- Declarative Hook Logic | Active |  | Five governance hooks (clarification-gate, assumption-tracker, prompt-quality, scope-creep-detector, blast-radius) perfo |
| 013 | Security Stack -- 8 Layers, 32 Tools | Active |  | The existing safety-mesh.md documented a 12-layer hook pipeline for internal safety checks, but it was incomplete. It co |
| 014 | SDD Fast Path -- Skip Phases for Capable Models | Active |  | Spec-Driven Development (SDD) followed a fixed 8-phase pipeline: explore, propose, spec, design, tasks, apply, verify, a |
| 015 | Rules-to-Hooks Migration -- From Context to Enforcement | Active |  | Cognitive OS loaded ~94 rules as markdown files into the agent's context window, consuming approximately 73,000 tokens p |
| 016 | Context Diet -- Token Optimization Strategy | Active |  | Each sub-agent launch loaded approximately 100,000 tokens of context: 20K system prompt, 5K CLAUDE.md, 73K rules, plus t |
| 017 | Stabilization Freeze -- No New Features Until Wiring Complete | Active |  | After 18 days of rapid development, the OS had accumulated 375+ agentic primitives but many were not wired into the runn |
| 018 | Docker-to-pip Migration -- Service Infrastructure Change | Active |  | ADR-018 is canonical for the 2026-04 infrastructure migration away from mandatory Docker services. Its statements about  |
| 019 | Scope Tagging -- Agentic Primitive Audience Classification | Active |  | Cognitive OS agentic primitives serve two distinct audiences: the OS itself (internal tooling for development and mainte |
| 020 | Contamination Fix -- Remove Project-Specific Code from OS | Active |  | During the rapid development of Cognitive OS, some agentic primitives accumulated project-specific references -- hardcod |
| 021 | Vendor-Agnostic State with Provider Adapters | Active |  | The Cognitive OS maintains its own state for many concepts that Claude Code also tracks natively: |
| 022 | Prompt-Type Hooks Adoption (Haiku-Evaluated Advisories) | Active |  | The Cognitive OS ships several **advisory hooks** that judge the *quality* of an |
| 023 | Mutate, Don't Block — `updatedInput` for PreToolUse Hooks | Active |  | Several PreToolUse hooks in the Cognitive OS interrupt agent execution |
| 024 | Task Panel Bridge — Correlate COS Tasks with Claude Code tool_use_id | Active |  | The Cognitive OS maintains its own task state in `.cognitive-os/tasks/active-tasks.json` (ADR-008 multi-tool support req |
| 025 | Install/Update Loop — Closing the Advisory-Only Gap | Active |  | Until v0.10.0 the install/update pipeline was advisory-only: `install.sh` and |
| 026 | R2 and R3 Consolidation — Design Review | Active |  | > **R3 audit item — CLOSED 2026-04-17**: Investigated in ADR-026; modules have |
| 026 | ADR-026a: R2 and R3 Design Review — Proposed Decisions (Addendum) | Active |  | ADR-026 laid out options for R2 (`cognitive-os.yaml` readers) and R3 (`safe_engram` ↔ `engram_client`) and listed 7 open |
| 027 | SO Slimming — Test Strategy, Context Overhead, Resource Consumption | Active |  | ACCEPTED (2026-04-21) — WS1-WS3 shipped, included in v0.12.0 release. Implementation commits: 8dc4a6e, 9bd895b, 15d67eb. |
| 028 | SO Reliability & Observability Framework | Active |  | ACCEPTED (2026-04-21) — Full 6-pillar framework CLOSED. Addenda ADR-028a/b/c resolved all PENDING items (commit 423bd86) |
| 028 | ADR-028c — Addendum: MetricEvent schema versioning + migration strategy | Active | 2026-04-20 | MetricEvent.schema_version is a monotonically-increasing integer starting at 1. |
| 029 | — Anti-reinvention gate (reinvention-check.sh wired) | Active | 2026-04-20 | This session produced `lib/agent_heartbeat.py` (reverted in a prior commit), which |
| 029 | ADR-029b — Reinvention gate Phase B: semantic similarity | Active | 2026-04-20 | Phase A (`hooks/reinvention-check.sh`, ADR-029) catches reinvention only when the |
| 030 | — Auto-trigger session-wrapup (Q1 prompt-match + Q2 commit banner) | Active | 2026-04-20 | Today the orchestrator has 7 session lifecycle skills (`/session-wrapup`, `/session-backlog`, `/session-report-executive |
| 031 | — Continuous Aspirational/Dormant/Real Audit | Active | 2026-04-20 | Manual forensic audits showed a persistent gap between the agentic primitives we build and the agentic primitives |
| 032 | — Orchestrator-side trap awareness before Agent launch | Active | 2026-04-20 | The COS currently operates in FIRE_AND_FORGET mode (banner: "Valkey ✅, Executor ❌"). In this mode: |
| 033 | — Harness-agnostic event capture layer | Active | 2026-04-20 | The Cognitive OS observes agent activity through two JSONL streams: |
| 033 | ADR-033b — Duration Correlation and Aider Version Dispatch Hardening | Active | 2026-04-20 | ADR-033 established the harness-agnostic event capture ABC and shipped working |
| 034 | — Harness-Agnostic Live Agent Streaming | Active |  | - **Status**: Proposed |
| 035 | — Worktree CWD Enforcement: 3-Layer Defense | Active | 2026-04-20 | Claude Code sub-agents inherit the current working directory (cwd) from the |
| 036 | Sprint orchestration primitives | Active |  | Proposed — MVP implemented 2026-04-20 (CLI skeleton + manifest + canonical events + example spec). Wave 1 test aggregati |
| 037 | — Self-Knowledge Base | Active | 2026-04-20 | Sub-agents spend 3-10K tokens per session grepping source files to answer basic questions: |
| 038 | — Preamble v2: Industry-Aligned Contract | Active |  | > Originally drafted in `.cognitive-os/pending-tasks/adr-038-preamble-v2-industry-aligned.md`; canonical location is `do |
| 039 | — Reinvention Phase B-β (semantic embeddings) | Active |  | > Originally drafted in `.cognitive-os/pending-tasks/adr-039-reinvention-phase-b-beta.md`; canonical location is `docs/a |
| 040 | — Query-Tailored Context Injection | Active | 2026-04-30 | `additionalContext` injected into sub-agents via the `SubagentStart` hook and the existing `PreToolUse:Agent` hooks is * |
| 041 | — Exercised Coverage Pipeline (MVP) | Active | 2026-04-20 | As of 2026-04-20, the aspirational-audit reports: |
| 042 | Valkey Local Daemon — Extract from Docker (D34 Partial) | Active | 2026-04-20 | This ADR is a continuation of ADR-018 phase 3, not a reversal of the Docker-to-pip migration. Valkey is treated as a loc |
| 045 | PostgreSQL Local Daemon — Extract from Docker (D34) | Active | 2026-04-30 | This ADR is a continuation of ADR-018 phase 3, not a reversal of the Docker-to-pip migration. PostgreSQL is treated as a |
| 047 | — Session Lifecycle Management | Active |  | Proposed — 2026-04-20. Author: Agent E (software-architect). Coordinates with |
| 048 | — Docker Container Image Freshness | Active |  | ADR-048 does not make Docker mandatory again. It governs the freshness and recreation contract for any Docker containers |
| 049 | — LLM Gateway Selection + Overflow Provider Strategy | Active |  | in `docker-compose.cognitive-os.yml` since ADR-022-era) and establishes the |
| 050 | — Per-Skill Routing Policy | Active |  | ADR-049 (Qwen primary cascade) and unblocked by ADR-051 Phase 3 (agent loop |
| 051 | — Qwen Agent Loop (Tool-Use Parity with Claude Code Agent) | Active |  | - **Status**: Accepted (2026-04-21) — Phases 1, 2, 3, 4 all DELIVERED this session. Commits: MVP phase 1, 1e6542c (phase |
| 054 | — Project Documentation Convention (10 Categories) | Active |  | + `scripts/project_scaffold.py` + `skills/project-scaffold/`. Behavior |
| 055 | — Docs Convention Enforcement + Skill Writers | Active |  | `lib/docs_writer.py`, `scripts/security_audit_writer.py`, |
| 055 | ADR-055b — Destructive Git Op Block (User Context Elevation) | Active | 2026-04-21 | for user/orchestrator context (previously documented as "warn-only by design" |
| 056 | — Adaptive Agent() dispatch: 3-tier auto-switch Claude → Qwen | Active |  | - **Status**: L1 IMPLEMENTED (advisory-only). L2/L3 DEFERRED. |
| 057 | Cross-Harness Authoring and Driver Projection | Active |  | Date: 2026-04-23 |
| 058 | — Observability Migration: Langfuse → Arize Phoenix | Active |  | - **Status**: Accepted |
| 059 | — SO Existential Validation: Prune, Install Timing, Core-vs-Extensions Split | Active |  | tracked in `.cognitive-os/plans/features/so-existential-validation-2026-04-24.md`. |
| 060 | — Local-Only Policy for Optional Services | Active |  | After Langfuse was fully purged (ADR-058, commit 38147ae), the operator |
| 061 | — Focus Narrative and External Evidence | Active |  | validation check (ADR-059) that ADR-059 Phase 1-3 does NOT cover. |
| 062 | — Multi-Provider Agent Loop | Active |  | (Qwen agent loop) to any OpenAI-compatible provider. |
| 063 | — Agent() Tool Replication Strategy | Active |  | rejects a full Claude Code Agent() clone. |
| 064 | — Harness-Agnostic Cognitive OS | Active |  | event capture), ADR-062 (multi-provider agent loop), and ADR-063 (Agent() |
| 065 | — Tech Radar Curation Pipeline (`/radar-update`) | Active |  | <!-- SCOPE: os-only --> |
| 066 | — Polyglot Language Boundaries & Migration Pressure | Active |  | Proposed — 2026-04-24. |
| 067 | — Defense-in-Depth for SKILL.md Frontmatter Quality | Active |  | Proposed — 2026-04-24. Implementation tracked separately as Phase 1 of this ADR. |
| 068 | Adaptive Test Runner Capacity Detection | Active |  | Today (2026-04-24), the shard-B test suite was launched without `-n auto` and ran serially. |
| 069 | Research-First Protocol for High-Risk Changes | Active |  | spawned in this same session. Implementation phases tracked in §8. |
| 070 | Convention Enforcement — From Documentation to Mechanism | Active |  | `bugfix/decision-triage-systemic-2026-04-27` engram observation. Pairs with |
| 071 | — Engram Lifecycle Evolution via Wrapper Layer | Active |  | Engram (v1.14.5, third-party Go binary at `<engram-bin>`, exposed via MCP) is the project's persistent memory backend. I |
| 072 | Test Lane Taxonomy & Escalation Ladder | Active |  | > **Numbering note**: the proposal/spec/design (Engram observations #14951, #14953, |
| 073 | Test Architecture Role Registry | Active |  | ADR-072 made `cos-test focused / cluster / broad` the canonical execution ladder, |
| 074 | Tier-0 Learning-Loop Closure | Active |  | Accepted. |
| 075 | Stage 2 Selective Expansion — Tier-Based Ref-Key Filtering | Active | 2026-04-30 | Accepted. |
| 076 | SKILL.md Frontmatter Alignment with Hermes Spec | Active | 2026-04-30 | Accepted. |
| 077 | Peer-Card Local User-Memory Model (Replaces Honcho) | Active | 2026-04-30 | Accepted on 2026-05-01. Phase 1 is explicitly **no-embeddings v1 / FTS5-only**. Update cadence and `/peer-card` UX are a |
| 078 | Mid-Task Memory Tool (Port from Hermes) | Active | 2026-04-30 | Accepted. |
| 079 | — CORE_RULES applies to self-hosting mode | Active | 2026-04-30 | <!-- SCOPE: OS --> |
| 080 | Hermes Cross-Harness Adoption (Umbrella) | Active | 2026-04-30 | <!-- SCOPE: OS --> |
| 081 | — Codex Harness Adapter | Active | 2026-04-30 | <!-- SCOPE: OS --> |
| 082 | — Plan Location Convention | Active | 2026-04-30 | <!-- SCOPE: OS --> |
| 083 | — Governed Self-Improvement Loop | Active | 2026-04-29 | <!-- SCOPE: OS --> |
| 086 | Hook Execution Observability | Active |  | <!-- Renumbered-from: attempted ADR-085 during the ADR reservation race documented in ADR-089. --> |
| 087 | — ADR Namespace Consolidation | Active | 2026-04-30 | <!-- SCOPE: OS --> |
| 088 | — Provenance trailer attribution via PPID chain | Active |  | Accepted. |
| 089 | — Multi-Session Git Coordination | Active | 2026-04-30 | <!-- SCOPE: OS --> |
| 090 | Auto-skill repair via failure-threshold signals | Active | 2026-04-30 | Accepted. |
| 091 | Headless and Clustered Runtime Direction | Active |  | <!-- Renumbered-from: ADR-027 (docs/architecture/adrs/027-headless-clustered-runtime-direction.md) --> |
| 092 | Harness Skills Sync Path — Add `.claude/skills/` as Second Sync Destination | Active |  | <!-- Renumbered-from: ADR-001 (docs/architecture/harness-adoption-gap/ADR-001-harness-skills-sync-path.md) --> |
| 093 | Simplify Install Profiles — Collapse 3-Tier System to `default` + `--full` | Active |  | <!-- Renumbered-from: ADR-002 (docs/architecture/harness-adoption-gap/ADR-002-simplify-profiles.md) --> |
| 094 | Agent Git Operations Safety — Layered Prevention of Destructive Git Ops | Active |  | <!-- Renumbered-from: ADR-003 (docs/architecture/harness-adoption-gap/ADR-003-agent-git-safety.md) --> |
| 095 | Skill synthesis driven by success patterns | Active | 2026-04-30 | Accepted. |
| 096 | Review-agent pattern (Hermes-style audit loop) | Active | 2026-05-01 | Accepted. |
| 097 | Documentation Execution Audit | Active |  | - Status: Accepted |
| 098 | — Multi-Agent File Coordination | Active | 2026-04-30 | <!-- SCOPE: OS --> |
| 099 | — Pre-agent snapshot: copy-on-untracked instead of stash-sweep | Active | 2026-04-30 | <!-- SCOPE: OS --> |
| 100 | — Resource-Governed Test Execution | Active | 2026-04-30 | <!-- SCOPE: OS --> |
| 101 | — Intent-Aware Rate Limiter Flow Control | Active | 2026-05-01 | <!-- SCOPE: OS --> |
| 102 | — Task tracker lifecycle: pending → in_progress → terminal, with PID capture and zombie reaper | Active |  | Accepted. |
| 103 | Audit and contract lane recovery before parallel flip | Active |  | Accepted. |
| 104 | — Startup Circuit Breaker and Safe Mode | Active | 2026-05-01 | <!-- SCOPE: OS --> |
| 106 | — Multi-Session Safety Primitives | Active | 2026-05-02 | <!-- SCOPE: OS --> |
| 107 | — Human-Approved Rollback Boundary | Active | 2026-05-02 | <!-- SCOPE: both --> |
| 108 | — Concurrent Agent Safety Layer | Active | 2026-05-02 | <!-- SCOPE: OS --> |
| 109 | Validation Capsule Worktree Isolation | Active |  | Accepted — 2026-05-02. |
| 110 | — Preserve Branch Governance | Active | 2026-05-02 | <!-- SCOPE: OS --> |
| 111 | Core/Consumer Boundary for Concurrent-Agent Safety | Active |  | Accepted — Implemented 2026-05-02. Related: ADR-108, ADR-110. |
| 112 | — Codex Governed Tool Layer | Active |  | <!-- SCOPE: OS --> |
| 113 | Validation Capsule Liveness Primitives | Active |  | <!-- SCOPE: os-only --> |
| 114 | — Hook Quality System | Active |  | <!-- SCOPE: OS --> |
| 115 | Safe Worktree Sweeper | Active |  | Accepted — 2026-05-02. Scope: OS core. Related: ADR-109, ADR-111, ADR-113. |
| 116 | Multi-Session Coordination Primitives | Active | 2026-05-02 | adr: 116 |
| 117 | — Stash Mutation Must Be Reversible-by-Design | Active |  | Proposed (2026-05-02). R1 has landed; R2-R4 remain in flight and are governed by this reversibility contract. |
| 118 | — Multi-IDE Swarm Safety Testbed | Active | 2026-05-02 | <!-- SCOPE: OS --> |
| 120 | Conversation-to-Primitive Harvester | Active |  | Accepted — 2026-05-02 |
| 121 | Foundation Hardening Program | Active | 2026-05-02 | adr: 121 |
| 122 | — Preflight Gate Refinements | Active | 2026-05-02 | <!-- SCOPE: OS --> |
| 124 | COS Distribution Boundaries — Core, Team, Maintainer, Lab | Active |  | Proposed — 2026-05-02 |
| 125 | Governance Tools Value Boundary | Active |  | Proposed — 2026-05-02 |
| 126 | Agentic Primitive Lifecycle Governor | Active |  | Proposed — 2026-05-02 |
| 127 | Active Primitive Index | Active |  | Accepted for Phase 1 DX. |
| 128 | — Data Layer Integrity Fixes | Active |  | Proposed — 2026-05-03 |
| 129 | Safe Worktree Removal — No Silent rm -rf Fallback | Active | 2026-05-02 | adr: 129 |
| 130 | Suspend All GitHub Actions Workflows — Preserve as .disabled Until Local-CI Migration | Active | 2026-05-03 | adr: 130 |
| 131 | Local-CI Migration — Three-Layer Architecture to Replace GitHub Actions | Active | 2026-05-03 | adr: 131 |
| 133 | Expansion Without Monsterization | Active |  | Accepted — 2026-05-03 |
| 134 | — Headless Self-Improvement Proposer | Active | 2026-05-03 | <!-- SCOPE: OS --> |
| 135 | — Self-Evolving Doctrine Proposals | Active | 2026-05-03 | <!-- SCOPE: OS --> |
| 136 | — Cross-Instance Learning Runway | Active | 2026-05-03 | <!-- SCOPE: OS --> |
| 137 | Operational Trajectory — From Governance Layer Over Agents to Embedded Runtime | Active | 2026-05-03 | adr: 137 |
| 138 | Flow Contract Schema — Required Shape for Cloud Flow Manifests | Active | 2026-05-03 | adr: 138 |
| 140 | Cross-OS Containerized Deployment via Docker Compose | Active | 2026-05-04 | adr: 140 |
| 143 | Closure Discipline Gate — Validation Nervous System Must Close With the Change | Active | 2026-05-04 | adr: 143 |
| 144 | Hook-Enforced Rule Projection Contract | Active | 2026-05-04 | adr: 144 |
| 145 | — Split heavy optional dependencies into explicit dependency lanes | Active |  | Date: 2026-05-04 |
| 146 | Primitive Readiness Ledger | Active |  | Accepted — 2026-05-04 |
| 147 | Agent Capability Coverage Pipeline | Active |  | Accepted — 2026-05-04 |
| 148 | ADR Authoring Primitive | Active | 2026-05-04 | adr: 148 |
| 149 | Primitive Duplication Audit | Active | 2026-05-04 | adr: 149 |
| 150 | ACC Projection Profiles and Expanded Harness Registry | Active | 2026-05-04 | adr: 150 |
| 153 | ACC Fail-New Gate and Harness Proof Boundary | Active | 2026-05-04 | adr: 153 |
| 155 | Shell CI Formal Harness Projection | Active | 2026-05-04 | adr: 155 |
| 158 | AI Agent Harness Landscape and Proof Backlog | Active | 2026-05-04 | adr: 158 |
| 159 | AGENTS.md-native Structural Harness Batch and Kiro Lifecycle Investigation | Active | 2026-05-05 | adr: 159 |
| 163 | Cognitive OS Instance Installer | Active | 2026-05-05 | adr: 163 |
| 169 | — Dashboard Formal Demotion | Active | 2026-05-05 | adr: 169 |
| 171 | Reject Paperclip Integration — API was Aspirational, Multi-Surface Replaces It | Active | 2026-05-05 | adr: 171 |
| 172 | Multi-Surface UI Architecture - CLI + Phoenix + Engram Cloud + Obsidian | Active | 2026-05-05 | adr: 172 |
| 173 | Surface 5 Research Gate — No Custom TUI/UI Adoption Without Source-Level Proof | Active | 2026-05-06 | adr: 173 |
| 174 | Auto-Derived Primitive Routing for Skills (and Rules) | Active | 2026-05-05 | adr: 174 |
| 175 | Research-quality enforcement for audit reports | Active | 2026-05-05 | adr: 175 |
| 176 | SkillStore SQLite Schema Adoption + Post-Execution Analysis Trigger (Discipline-Gated) | Active | 2026-05-05 | adr: 176 |
| 177 | Activate Skill Lifecycle Promotion Ladder | Active | 2026-05-06 | adr: 177 |
| 178 | — OpenHarness Primitive Adoption (HttpHookDefinition, PromptHookDefinition, ProviderProfile) | Active | 2026-05-05 | - ADR-171 (removed-integration lesson — verify upstream source before adopting) |
| 179 | Auto-Derived Rule Routing for Agent-Instruction Rules | Active | 2026-05-05 | adr: 179 |
| 180 | Lifecycle Promotion Activation — Concrete Proposers and Hook Wiring | Active | 2026-05-05 | adr: 180 |
| 181 | ADR Relevance Suggester — Lightweight Routing for Architecture Decisions | Active | 2026-05-05 | adr: 181 |
| 182 | Branch Ownership Lock — Single-Writer Surface for Concurrent Orchestrators | Active | 2026-05-05 | adr: 182 |
| 183 | Cross-Session Event Log — Append-Only Visibility for Peer Orchestrators | Active | 2026-05-05 | adr: 183 |
| 184 | Manager-of-Managers Daemon — Authoritative Single-Writer for Critical Surfaces | Active | 2026-05-05 | adr: 184 |
| 185 | Cross-Agent Audit Findings Queue — Auditor → Implementer Directive Channel | Active | 2026-05-05 | adr: 185 |
| 186 | Context Budget Enforcement — Activate the ADR-038 Wave 3 Limits | Active | 2026-05-05 | adr: 186 |
| 188 | Mandatory Skill Invocation at High Router Confidence | Active | 2026-05-06 | adr: 188 |
| 189 | Surface Implementation Coverage for Agentic Primitives | Active |  | Accepted — 2026-05-06 |
| 190 | Harness Action Receipts and VCS Event Telemetry | Active |  | Accepted — 2026-05-06 |
| 191 | COS Binary Release Pipeline | Active |  | Accepted — 2026-05-06 |
| 192 | Surface 5 Bubble Tea Adoption | Active |  | Accepted — 2026-05-06 |
| 193 | cosd Local Network API | Active |  | Accepted — 2026-05-06 |
| 194 | cosd Secure Remote API Guardrails | Active |  | Accepted — 2026-05-06 |
| 195 | Surface 5 Operable TUI Contract | Active |  | Accepted — 2026-05-06 |
| 196 | cosd Task API and Provider Boundary | Active |  | Accepted — 2026-05-06 |
| 197 | Surface 5 Operable Actions | Active |  | Accepted — 2026-05-06 |
| 198 | Release External Readiness Gate | Active |  | Accepted — 2026-05-06 |
| 199 | State Retention Policy and Reaper Protocol | Active |  | Accepted — 2026-05-06 |
| 200 | State Retention Controller | Active |  | Accepted — 2026-05-06 |
| 201 | — Maintainer Agent and Telemetry Promotion Loop | Active | 2026-05-06 | <!-- SCOPE: OS --> |
| 202 | — Private Content Cross-Harness Portability Boundary | Active | 2026-05-06 | <!-- SCOPE: OS --> |
| 203 | — Subagent Capability Contract and Launch Preflight | Active | 2026-05-06 | Accepted |
| 204 | — Signal Quality and Reward Integrity Boundary | Active | 2026-05-06 | Accepted — implemented |
| 205 | — Cross-Stream Trace Joiner and Flight Recorder | Active | 2026-05-06 | Accepted — implemented |
| 206 | — Aspirational Claim Decommission Gate | Active | 2026-05-06 | Accepted |
| 207 | — Skill Ecosystem Performance and Lifecycle Closure | Active | 2026-05-06 | Tombstone |
| 208 | — Imported Pattern Closure Contract | Active | 2026-05-06 | Accepted |
| 209 | — Maintainer Reconciler Experiment Contract | Active | 2026-05-06 | Accepted |
| 210 | — Fleet-Aggregated Confidence Boundary | Active | 2026-05-06 | Accepted — Slice A dry-run exporter implemented |
| 211 | — Service-Mode Readiness Gate | Active | 2026-05-06 | Accepted — initial readiness gate implemented |
| 212 | — Cross-Stack License Audit Toolchain | Active | 2026-05-06 | Accepted |
| 213 | — Agent Preflight Before Stash Snapshot | Active | 2026-05-06 | Accepted |
| 215 | — Cross-Stack Secret Audit Toolchain | Active | 2026-05-06 | Accepted |
| 216 | — Tool Discovery Pre-Use Gate | Active | 2026-05-06 | Accepted |
| 217 | — Cross-Stack Adoption Truth Audit Toolchain | Active | 2026-05-06 | Accepted |
| 218 | — History Sanitization Toolchain | Active | 2026-05-06 | Accepted |
| 219 | Work Ownership Liveness Preflight | Active | 2026-05-06 | Accepted |
| 220 | — Worktree Divergence Audit Toolchain | Active | 2026-05-06 | Accepted |
| 221 | — Stash References by SHA, Not by Position | Active | 2026-05-06 | Accepted |
| 222 | — Pre-Agent Stash Deferred Until Agent Launch Confirmed | Active | 2026-05-06 | Accepted |
| 223 | — Agent Lifecycle Reconstruction: Worktree-Per-Write-Agent | Active | 2026-05-07 | Accepted |
| 225 | — Branch-Per-Task Mode | Active | 2026-05-07 | Accepted |
| 226 | — Event-Sourced Session Bus | Active | 2026-05-06 | Accepted |
| 227 | — Shadow-Git Checkpoint Substrate | Active | 2026-05-06 | Accepted |
| 228 | — Retry Contract + Cost Session Budget (consolidated) | Active | 2026-05-06 | Accepted — Slices A–F implemented (2026-05-07) |
| 230 | — Agent Handoff Envelope + Call-Chain Deduplication | Active | 2026-05-06 | Accepted |
| 231 | — MCP Server Surface for COS Primitives | Active | 2026-05-07 | Accepted |
| 232 | — Sandbox Adapter Tiers | Active | 2026-05-07 | Accepted |
| 233 | — Cross-Session Agent-Team File IPC | Active | 2026-05-07 | Accepted |
| 234 | — Approval Policies as Code | Active | 2026-05-07 | Accepted |
| 235 | — Detached Agent Daemon | Active | 2026-05-07 | Accepted |
| 236 | — Deferred Tool Loading + ToolSearch Adoption | Active | 2026-05-07 | Accepted |
| 237 | — Test Execution Efficiency Protocol | Active | 2026-05-07 | Accepted |
| 239 | Isolated Worktree Default for Write Agents | Active | 2026-05-08 | adr: 239 |
| 240 | Primitive Coherence Audit and Ownership Manifest | Active | 2026-05-08 | status: accepted |
| 241 | Consolidate Hook-Bypass Envs into a Single COS_BYPASS Allowlist | Active | 2026-05-08 | adr: 241 |
| 242 | git-filter-repo Wrapper Preserves Remote and Refuses Non-Idempotent Re-Runs | Active | 2026-05-08 | adr: 242 |
| 243 | Post-Rewrite Push-Collision Check Exception | Active | 2026-05-08 | adr: 243 |
| 244 | Trust Report Claim-Validator Must Enforce, Not Advise | Active | 2026-05-08 | adr: 244 |
| 245 | Chaos Tests Run with Read-Only Production Source | Active | 2026-05-08 | adr: 245 |
| 246 | Release Transaction Freeze for Destructive and Public-State Operations | Active | 2026-05-08 | adr: 246 |
| 247 | Manifest-Driven Postmortem Regression Audits and External Tool Adapters | Active | 2026-05-08 | adr: 247 |
| 248 | Control-Plane Audit Loop for ADR-239+ Primitive Drift | Active | 2026-05-08 | adr: 248 |
| 249 | Primitive Behavioral Proof and Anti-Overfit Testing | Active | 2026-05-08 | adr: 249 |
| 250 | Skill Router Retrieval Adapter Boundary | Active | 2026-05-08 | adr: 250 |
| 251 | Agent Orchestration Adapter Boundary | Active | 2026-05-08 | adr: 251 |
| 252 | Capability Coverage Matrix and Feature Reality Ledger | Active | 2026-05-08 | adr: 252 |
| 254 | — External Tool Intelligence Plane and Project Overlays | Active | 2026-05-08 | status: accepted |
| 255 | — Feature-to-External-Tool Due Diligence | Active | 2026-05-08 | Accepted — Slice A implemented |
| 256 | — Primitive Contract Registry and Runtime Evidence Ledger | Active |  | Accepted — implemented through Phases 1–6; all primitive-lifecycle rows are registry-backed; OpenCode signed smoke cover |
| 257 | — Primitive Contract Registry Phase 1 | Active |  | Accepted — implemented |
| 258 | — Portable `.ai` Overlay for Agentic Primitives | Active |  | Accepted — generated overlay implemented; canonical migration intentionally deferred |
| 259 | — holaOS Adoption Posture: Patterns-Only Library with Clean-Room Rewrite | Active |  | Accepted |
| 260 | — Grant-Signed cosd API: HMAC + Nonce + TTL + Scope Binding | Active |  | Accepted |
| 261 | — Memory Governance v2: Typed Memory with Verification & Staleness Policies | Active |  | Accepted |
| 262 | — Evolve Loop Spike: Task Proposal Queue + LLM-driven Skill Candidates | Active |  | ADR-049 (LLM dispatch), ADR-259, ADR-260 |
| 263 | — Tool-Replay Budget Ledger: Per-Session Cap + Preview/Reference-Only Modes | Active |  | Accepted |
| 264 | — Tool Result Envelope: Compact Envelope Format for Large Tool Outputs | Active |  | Accepted |
| 265 | — Mandatory-minimum inspection caps for COS eval surfaces | Active |  | Proposed (2026-05-11) |
| 267 | — License-Compliance Enforcement Architecture | Active |  | Accepted (2026-05-11) |
| 268 | — Defensive history sanitization for external-pattern attribution | Active |  | Accepted (2026-05-11) |
| 269 | Mandatory ADR Reference for History Rewrites | Active | 2026-05-11 | adr: 269 |
| 270 | Legal Compliance Workflow Automation | Active | 2026-05-11 | adr: 270 |
| 271 | — Clean-Room Detection Tier 2: AST-Normalized Similarity | Active |  | Proposed (2026-05-11) |

## Proposed

| # | Title | Status | Date | One-line Summary |
|---|-------|--------|------|------------------|
| 266 | Extend protected-config-write-guard to intercept Bash file-write commands | Proposed |  | `hooks/protected-config-write-guard.sh` blocks writes to agent control-plane paths (hooks, rules, skills, manifests, etc |

<details>
<summary>Superseded ADRs (collapsed — click to expand)</summary>

## Superseded

| # | Title | Status | Date | One-line Summary |
|---|-------|--------|------|------------------|
| 084 | — Headless and Clustered Runtime Shape | Superseded | 2026-04-30 | <!-- SCOPE: OS --> |
| 170 | Operator-CLI as Primary UI Surface — No Web Dashboard Until a Real Driver Exists | Superseded | 2026-05-05 | adr: 170 |
| 187 | Surface 5 Adoption Proof Contract — Source-Level Gate for Custom TUI/UI | Superseded | 2026-05-06 | adr: 187 |

</details>

## Other

| # | Title | Status | Date | One-line Summary |
|---|-------|--------|------|------------------|
| 003 | Reserved architecture decision slot | Tombstone | 2026-05-05 | adr: 3 |
| 004 | Reserved architecture decision slot | Tombstone | 2026-05-05 | adr: 4 |
| 005 | Reserved architecture decision slot | Tombstone | 2026-05-05 | adr: 5 |
| 027 | ADR-027a — Addendum: Reconciliation with main baseline | Addendum | 2026-04-18 | ADR-027 was written on 2026-04-17 without verifying the actual state of `main` — specifically, |
| 028 | ADR-028a — Addendum: Reconciliation with pre-existing plans | Addendum | 2026-04-18 | ADR-028 was authored on 2026-04-17 without consulting `.cognitive-os/plans/features/self-optimizing-pipeline.md` |
| 028 | ADR-028b — Addendum: D1.C Replanned Around agent_bus | Addendum | 2026-04-20 | ADR-028 D1.C proposed a parallel heartbeat system writing |
| 043 | Removed local-daemon integration decision | Tombstone | 2026-05-05 | adr: 43 |
| 044 | Context Payload Slimming — Non-Rule Startup Payloads | Phase | 2026-04-20 | Session-start TTFT is ~3 minutes. The first model turn must ingest a payload composed of: |
| 046 | Reserved architecture decision slot | Tombstone | 2026-05-05 | adr: 46 |
| 052 | Provider Benchmark Harness | Implemented |  | adr: 52 |
| 053 | Dispatch Auto-Optimizer | Implemented |  | adr: 53 |
| 085 | Reserved architecture decision slot | Tombstone | 2026-05-05 | adr: 85 |
| 105 | Bilateral Claim Verification Contract | Implemented | 2026-05-02 | adr: 105 |
| 119 | Session Filesystem Reaper | Implemented | 2026-05-02 | adr: 119 |
| 123 | Operational Stability and Friction Reduction Program | Implemented | 2026-05-02 | adr: 123 |
| 132 | Solo-Swarm vs Multi-Maintainer Fork — Documenting the Pending Strategic Decision | Exploration | 2026-05-03 | adr: 132 |
| 139 | Account-Agnostic Multi-Provider Runtime | Implemented | 2026-05-04 | adr: 139 |
| 141 | Engram Cloud as Cross-Instance Replication Transport | Implemented | 2026-05-04 | adr: 141 |
| 142 | Compliance, Audit, and Air-Gapped Surface (SOC 2 / ISO 27001 / GDPR) | Implemented | 2026-05-04 | adr: 142 |
| 151 | Consumer Availability Classification Manifest | Implemented | 2026-05-04 | adr: 151 |
| 152 | Shell CI Projection and Local Surface Defaults | Implemented | 2026-05-04 | adr: 152 |
| 154 | Multi-IDE Structural Harness Projection | Implemented | 2026-05-04 | adr: 154 |
| 156 | Qwen Code Structural Harness Projection | Implemented | 2026-05-04 | adr: 156 |
| 157 | Kimi Code CLI Structural Harness Projection | Implemented | 2026-05-04 | adr: 157 |
| 160 | Rules/MCP Structural Harness Batch and Kiro Adapter Design | Implemented | 2026-05-05 | adr: 160 |
| 161 | Remote Control Plane and Provider Adapter Boundary | Implemented | 2026-05-05 | adr: 161 |
| 162 | Task Lifecycle, Interruption, Question, Worktree, and PR Protocol | Implemented | 2026-05-05 | adr: 162 |
| 164 | Host CLI Bridge Security Boundary | Implemented | 2026-05-05 | adr: 164 |
| 165 | Proof Drill and Smoke Opt-In Agentic Primitives | Implemented | 2026-05-05 | adr: 165 |
| 166 | Expected Skip Registry and Opt-In Test Lanes | Implemented | 2026-05-05 | adr: 166 |
| 167 | Proof Drill Selector and ACC Evidence Adapter | Implemented | 2026-05-05 | adr: 167 |
| 168 | Cross-Device Dependency Installation Contract | Implemented | 2026-05-05 | adr: 168 |
| 174 | Routing-Pattern Prevention Followup — Auto-Generation and Soak-Driven Promotion |  | 2026-05-05 | adr: "174-bis" |
| 214 | Reserved — vacated by parallel-session number collision | Tombstone | 2026-05-06 | adr: 214 |
| 224 | — Tombstone (consolidated into ADR-227) | Tombstone | 2026-05-07 | status: tombstone |
| 229 | — Tombstone (consolidated into ADR-228) | Tombstone | 2026-05-06 | status: tombstone |
| 238 | — Tier 1-4 Follow-Up Bug Tracking | Resolved | 2026-05-07 | Resolved |
| 253 | — Tombstone (squads orchestration superseded by ADR-251) | Tombstone | 2026-05-08 | <!-- ADR_RELATION_CHAIN_EXEMPT: tombstone pointer to ADR-251; not a new implementation scope chain. --> |

