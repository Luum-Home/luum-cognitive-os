# OpenClaw Patterns -- Implementation Roadmap

> Este documento describe un plan priorizado de 12 semanas para adoptar los 25 patrones restantes de OpenClaw.
> Ordenado por criticidad y cadena de dependencias.
> Documento companero: [openclaw-remaining-patterns.md](openclaw-remaining-patterns.md)

---

## Phase 1 -- Fintech Core (Weeks 1-3)

> Foundation patterns required for financial operations monitoring and compliance.

### 1.1 Hooks Lifecycle (Pattern 7)

Expand the existing hook system to support 10+ event types with priority ordering.

- [ ] Define event type enum: `command:new`, `session:start`, `session:compact`, `session:end`, `agent:bootstrap`, `message:send`, `message:receive`, `error:*`, `tool:before`, `tool:after`
- [ ] Implement priority-based hook ordering (numeric priority, lower runs first)
- [ ] Add sync vs async hook execution modes
- [ ] Create hook registry with enable/disable per hook
- [ ] Write hook execution engine with error isolation (one hook failure does not block others)
- [ ] Add hook execution logging for audit trail
- [ ] Document hook authoring guide

**Success criteria:** All 10+ event types fire correctly, hooks execute in priority order, failures are isolated and logged.

**Dependencies:** None (foundational).

**Estimated effort:** 5-7 days.

### 1.2 Heartbeat System (Pattern 1)

Periodic wake mechanism for monitoring and threshold checking.

- [ ] Define `HEARTBEAT.md` schema (interval, payload template, delivery channel, enabled flag)
- [ ] Implement heartbeat scheduler using Claude Code scheduled tasks as backend
- [ ] Create channel delivery abstraction (console, engram, webhook)
- [ ] Add heartbeat state persistence (last-run, next-run, consecutive failures)
- [ ] Implement configurable intervals (minimum 1 minute, default 5 minutes)
- [ ] Wire heartbeat events into hooks lifecycle (`heartbeat:fire`, `heartbeat:complete`)
- [ ] Add health check for heartbeat system itself

**Success criteria:** Heartbeat fires at configured intervals, delivers payloads to channels, survives restarts via persistent state.

**Dependencies:** Hooks lifecycle (1.1).

**Estimated effort:** 4-5 days.

### 1.3 Session Compaction Hooks (Pattern 24)

Pre/post compaction hooks to preserve compliance-critical context.

- [ ] Register `session:compact:before` and `session:compact:after` hook events
- [ ] Extract compaction metadata (token count before/after, messages dropped, context retained)
- [ ] Implement pre-compaction state saver (dump active transaction IDs, audit state to engram)
- [ ] Implement post-compaction recovery (restore critical context from engram)
- [ ] Add compaction event logging for debugging
- [ ] Test with simulated compaction scenarios

**Success criteria:** Compliance-critical state (transaction IDs, audit context) survives compaction events without manual intervention.

**Dependencies:** Hooks lifecycle (1.1).

**Estimated effort:** 3-4 days.

### 1.4 Webhook System (Pattern 3)

Bidirectional webhook infrastructure for bank and provider integrations.

- [ ] Design inbound webhook listener (NestJS controller with route registration)
- [ ] Implement signature verification (HMAC-SHA256, configurable per provider)
- [ ] Build outbound webhook dispatcher with retry logic (exponential backoff, max 5 retries)
- [ ] Create dead letter queue for failed deliveries (store in MongoDB)
- [ ] Add webhook registration API (register/unregister/list endpoints)
- [ ] Implement idempotency checking (dedup by webhook ID)
- [ ] Wire webhook events into hooks lifecycle (`webhook:receive`, `webhook:deliver`, `webhook:fail`)
- [ ] Add webhook delivery logging for audit trail

**Success criteria:** Inbound webhooks verified and routed, outbound delivered with retry, failures captured in dead letter queue, all events auditable.

**Dependencies:** Hooks lifecycle (1.1).

**Estimated effort:** 6-8 days.

---

## Phase 2 -- Automation Layer (Weeks 4-6)

> Scheduled execution, credential management, and alert management.

### 2.1 Cron Jobs with 3 Execution Models (Pattern 4)

Three-model scheduled execution for different isolation needs.

- [ ] Define cron job configuration schema (name, schedule, model, enabled, last-run, state)
- [ ] Implement Model 1: main-session cron (runs in current agent session)
- [ ] Implement Model 2: isolated cron (spawns new session per run, clean context)
- [ ] Implement Model 3: custom-session cron (reuses named session for state continuity)
- [ ] Add persistent JSON state store per cron job (survives restarts)
- [ ] Implement failure recovery (retry count, backoff, alert on repeated failures)
- [ ] Wire cron events into hooks lifecycle (`cron:start`, `cron:complete`, `cron:fail`)
- [ ] Create cron job management commands (list, enable, disable, run-now, view-state)

**Success criteria:** All 3 models execute correctly, state persists between runs, failures trigger alerts, jobs manageable via commands.

**Dependencies:** Hooks lifecycle (Phase 1), heartbeat (Phase 1) for scheduling.

**Estimated effort:** 7-9 days.

### 2.2 Auth Monitoring (Pattern 15)

Proactive credential expiration tracking and alerting.

- [ ] Create credential inventory schema (service, type, expiry, rotation-url, alert-days-before)
- [ ] Inventory all current credentials: auth server tokens, payment provider API keys, identity verification API keys, SSL certs, cloud provider credentials
- [ ] Implement expiration tracker (daily check via heartbeat)
- [ ] Configure alert thresholds (30 days, 7 days, 1 day, expired)
- [ ] Add rotation workflow triggers (notify + link to rotation procedure)
- [ ] Wire into hooks lifecycle (`auth:expiring`, `auth:expired`, `auth:rotated`)
- [ ] Dashboard view of credential health (via engram or canvas)

**Success criteria:** No credential expires without 7-day advance warning, rotation procedures are linked, credential health is visible.

**Dependencies:** Heartbeat (Phase 1) for periodic checks.

**Estimated effort:** 5-6 days.

### 2.3 Message Debouncing (Pattern 6)

Batch alerts to prevent notification flooding during high-activity periods.

- [ ] Design debouncer configuration (batch window, max queue depth, drop strategy)
- [ ] Implement time-window batching (collect alerts, emit summary after window closes)
- [ ] Add queue depth cap with configurable drop strategies: oldest-first, lowest-priority, newest
- [ ] Create per-channel debounce configs (financial alerts: short window; info: longer window)
- [ ] Implement summary generator (batch of 50 price alerts becomes one summary)
- [ ] Add bypass for CRITICAL severity (never debounced)
- [ ] Wire into hooks lifecycle (`alert:batched`, `alert:dropped`)

**Success criteria:** During simulated high-alert scenarios (100+ alerts in 1 minute), output is batched into manageable summaries. Critical alerts always pass through immediately.

**Dependencies:** Channel/notification abstraction.

**Estimated effort:** 3-4 days.

### 2.4 Standing Orders (Pattern 2)

Persistent condition-action rules that survive restarts.

- [ ] Design standing order schema (id, condition, action, type: one-shot/recurring, expiry, priority, enabled)
- [ ] Implement condition DSL (field, operator, value — e.g., `btc_price > 100000`)
- [ ] Build condition evaluator (runs on each heartbeat tick)
- [ ] Add durable persistence (engram or JSON file, survives restarts)
- [ ] Implement order lifecycle (create, activate, deactivate, expire, trigger, delete)
- [ ] Add trigger logging for audit trail (which order fired, when, what action taken)
- [ ] Support action types: notify, execute-command, webhook-call
- [ ] Wire into hooks lifecycle (`order:triggered`, `order:expired`, `order:created`)

**Success criteria:** Standing orders persist across restarts, conditions evaluate correctly, triggered actions execute reliably, full audit trail.

**Dependencies:** Heartbeat (Phase 1) for evaluation scheduling, persistent storage.

**Estimated effort:** 8-10 days.

---

## Phase 3 -- User Experience (Weeks 7-9)

> Visual output, user profiles, and onboarding improvements.

### 3.1 Canvas System (Pattern 5)

HTML-based visual output for dashboards and reports.

- [ ] Implement embedded HTTP server (lightweight, localhost only)
- [ ] Create HTML template engine for common patterns (tables, charts, forms)
- [ ] Add WebSocket for live reload when content changes
- [ ] Implement Canvas Actions API: `present`, `hide`, `navigate`, `eval`, `snapshot` (Pattern 12)
- [ ] Create chart library integration (lightweight, no heavy deps)
- [ ] Add snapshot capability (capture canvas state as image for compliance evidence)
- [ ] Security: ensure localhost-only binding, no external access

**Success criteria:** Agent can generate and serve interactive HTML dashboards, update them in real-time, and capture snapshots.

**Dependencies:** None.

**Estimated effort:** 8-10 days.

### 3.2 BOOTSTRAP.md (Pattern 8)

First-run workspace initialization ritual.

- [ ] Define BOOTSTRAP.md schema (steps, validators, cleanup-action)
- [ ] Implement bootstrap detector (check if BOOTSTRAP.md exists and has not run)
- [ ] Build step executor with validation (each step must pass before next)
- [ ] Add completion marker (flag file or engram entry to prevent re-run)
- [ ] Create default bootstrap template (verify toolchain, seed DBs, configure mocks)
- [ ] Wire into hooks lifecycle (`agent:bootstrap` event)

**Success criteria:** New workspace initializes automatically on first agent run, steps validated, never re-runs after completion.

**Dependencies:** Hooks lifecycle (Phase 1).

**Estimated effort:** 2-3 days.

### 3.3 USER.md (Pattern 9)

Per-user profile loaded every session.

- [ ] Define USER.md schema (name, role, timezone, preferences, notification-channels, risk-profile)
- [ ] Implement profile loader (parse at session start, inject into agent context)
- [ ] Add role-based behavior adaptation (compliance officer sees different defaults than developer)
- [ ] Support timezone-aware scheduling (market hours, settlement windows)
- [ ] Create profile template for common roles (developer, compliance, product)

**Success criteria:** Agent adapts behavior based on user profile, timezone-aware operations work correctly.

**Dependencies:** None.

**Estimated effort:** 2-3 days.

### 3.4 Envelope System (Pattern 13)

Rich metadata wrapping for all agent messages.

- [ ] Define envelope schema (sender, timestamp, severity, correlation-id, compliance-tags, format-hints)
- [ ] Implement envelope builder (auto-wraps outgoing messages)
- [ ] Add classification system (info, warning, alert, critical)
- [ ] Create compliance tag vocabulary (transaction-id, amount, counterparty, authorization)
- [ ] Implement downstream routing based on envelope metadata (critical to SMS, info to in-app)
- [ ] Wire into hooks lifecycle (auto-envelope on `message:send`)

**Success criteria:** All agent messages carry metadata envelopes, routing works based on severity, compliance tags are searchable.

**Dependencies:** Hooks lifecycle (Phase 1).

**Estimated effort:** 3-4 days.

### 3.5 BOOT.md (Pattern 11)

Startup checklist on every agent restart.

- [ ] Define BOOT.md schema (checks with expected outcomes)
- [ ] Implement boot sequence runner (execute all checks, report status)
- [ ] Create default boot checklist (service health, DB connectivity, credential validity, mock flags)
- [ ] Add failure handling (warn vs block depending on check criticality)
- [ ] Wire into hooks lifecycle (`agent:boot` event, distinct from `agent:bootstrap`)

**Success criteria:** Every agent restart validates environment health, critical failures prevent operation, warnings are logged.

**Dependencies:** Auth monitoring (Phase 2) for credential checks.

**Estimated effort:** 2-3 days.

---

## Phase 4 -- Platform (Weeks 10-12)

> Extensibility, distribution, and operational tooling.

### 4.1 Plugin Architecture (Pattern 14)

Modular extension system for integrations.

- [ ] Design plugin SDK (lifecycle hooks: install, enable, disable, uninstall)
- [ ] Implement plugin registry (discover, list, enable, disable plugins)
- [ ] Add dependency resolution between plugins
- [ ] Create configuration schema validation per plugin
- [ ] Build plugin isolation (plugins cannot interfere with each other)
- [ ] Create 2-3 reference plugins (e.g., notification channel, provider mock)
- [ ] Document plugin authoring guide

**Success criteria:** Third-party plugins can be installed, configured, and run without modifying core code. Reference plugins work as documentation.

**Dependencies:** Hooks lifecycle (Phase 1), testing framework (4.4).

**Estimated effort:** 10-12 days.

### 4.2 Hook Packs (Pattern 25)

npm-distributable collections of hooks.

- [ ] Define hook pack manifest schema (name, version, hooks, dependencies, config schema)
- [ ] Implement pack installer (npm install + register hooks)
- [ ] Create activation/deactivation commands
- [ ] Build compliance hook pack (audit logging, transaction tracking, access logging)
- [ ] Build security hook pack (auth monitoring, credential rotation, access alerts)
- [ ] Add pack conflict detection (two packs registering same hook event)

**Success criteria:** Hook packs installable via npm, activate/deactivate cleanly, no conflicts between packs.

**Dependencies:** Hooks lifecycle (Phase 1), plugin architecture (4.1).

**Estimated effort:** 5-7 days.

### 4.3 Migration Tools (Pattern 23)

Workspace portability and state export/import.

- [ ] Design export format (JSON/YAML bundle of configs, memory, state)
- [ ] Implement exporter (selective: choose which workspace assets to export)
- [ ] Implement importer with conflict resolution (skip, overwrite, merge)
- [ ] Add dry-run mode (show what would change without applying)
- [ ] Support partial migration (only hooks, only cron jobs, only standing orders)
- [ ] Add validation (verify imported state is consistent)

**Success criteria:** Agent configuration portable between environments, conflicts handled gracefully, dry-run prevents accidents.

**Dependencies:** Persistent storage layer.

**Estimated effort:** 5-7 days.

### 4.4 Testing Framework (Pattern 18)

Comprehensive test infrastructure for agent behaviors.

- [ ] Set up Vitest with V8 coverage for agentic primitives
- [ ] Create test categories: unit (isolated), integration (with services), live (against real APIs)
- [ ] Implement test generators from API schemas (auto-create basic tests)
- [ ] Add coverage enforcement (minimum thresholds per agentic primitive)
- [ ] Create mock service helpers (spin up mock providers for testing)
- [ ] Integrate with CI pipeline

**Success criteria:** All agentic primitives have tests, coverage meets thresholds, CI blocks merges below threshold.

**Dependencies:** None.

**Estimated effort:** 6-8 days.

### 4.5 Remaining Patterns (Parallel Track)

Lower-priority patterns to implement as capacity allows.

- [ ] **TOOLS.md** (Pattern 10) — Environment-specific tool config. 1-2 days.
- [ ] **Gmail PubSub** (Pattern 16) — Real-time email processing. 4-5 days.
- [ ] **Polling System** (Pattern 17) — Webhook alternative. 4-5 days.
- [ ] **Release Workflow** (Pattern 19) — Automated releases. 4-5 days.
- [ ] **Coding Agent Delegation** (Pattern 20) — Background PTY execution. 6-8 days.
- [ ] **Video/Audio Processing** (Pattern 21) — Multimodal inputs. 8-10 days.
- [ ] **Onboarding Wizard** (Pattern 22) — Guided CLI setup. 4-5 days.

---

## Dependency Graph

```
Phase 1 (Foundation)
  Hooks Lifecycle ──────────────────────────────────────────┐
       │                                                     │
       ├── Heartbeat System                                  │
       │       │                                             │
       │       ├── Session Compaction Hooks                  │
       │       │                                             │
       │       └── Webhook System                            │
       │                                                     │
Phase 2 (Automation)                                         │
       │                                                     │
       ├── Cron Jobs (needs Hooks + Heartbeat)               │
       ├── Auth Monitoring (needs Heartbeat)                 │
       ├── Message Debouncing (needs Channels)               │
       └── Standing Orders (needs Heartbeat + Storage)       │
                                                             │
Phase 3 (UX)                                                 │
       ├── Canvas System + Canvas Actions (standalone)       │
       ├── BOOTSTRAP.md (needs Hooks)                        │
       ├── USER.md (standalone)                              │
       ├── Envelope System (needs Hooks)                     │
       └── BOOT.md (needs Auth Monitoring)                   │
                                                             │
Phase 4 (Platform)                                           │
       ├── Plugin Architecture (needs Hooks + Testing) ──────┘
       ├── Hook Packs (needs Hooks + Plugins)
       ├── Migration Tools (needs Storage)
       └── Testing Framework (standalone)
```

## Effort Summary

| Phase | Weeks | Patterns | Total Effort |
|-------|-------|----------|--------------|
| Phase 1 — Fintech Core | 1-3 | 4 patterns | 18-24 days |
| Phase 2 — Automation | 4-6 | 4 patterns | 23-29 days |
| Phase 3 — User Experience | 7-9 | 5 patterns | 17-23 days |
| Phase 4 — Platform | 10-12 | 5 patterns + 7 parallel | 26-34 days + parallel |

**Total:** 25 patterns across 12 weeks (assuming parallel work on lower-priority items in Phase 4).

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Hooks lifecycle scope creep | Delays all downstream phases | Timebox to 7 days max, ship MVP event types first |
| Standing orders condition DSL complexity | Over-engineering | Start with simple field-operator-value, extend later |
| Canvas system browser dependency | Platform portability issues | Use standard HTML, no framework lock-in |
| Plugin architecture over-design | Weeks of SDK work with no users | Ship with 2 reference plugins, iterate based on real usage |
| Credential inventory incomplete | Auth monitoring misses expirations | Audit all .env files and docker-compose configs for credentials |
| Phase 2-4 dependencies on Phase 1 | Single point of delay | Hooks lifecycle is the critical path — prioritize and protect it |
