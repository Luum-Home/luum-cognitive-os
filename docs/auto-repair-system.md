# Auto-Repair System

## Overview

The Auto-Repair System is a MAPE-K (Monitor-Analyze-Plan-Execute-Knowledge) loop that enables Cognitive OS to autonomously detect, classify, and repair errors across all system layers.

## Architecture

```
                    ┌─── MAPE-K Auto-Repair Loop ───┐
                    │                                 │
  Error occurs ──→ Monitor (error-learning.sh)        │
                    │                                 │
                    ▼                                 │
              Analyze (auto-repair-dispatcher.sh)     │
                    │                                 │
              ┌─────┴──────┐                          │
              ▼            ▼                          │
         Registry     LLM repair                      │
         lookup       (async, worktree)               │
              │            │                          │
              ▼            ▼                          │
         Execute (worktree isolation)                 │
              │                                       │
              ▼                                       │
         Verify (build + test + lint)                 │
              │                                       │
         ┌────┴────┐                                  │
         ▼         ▼                                  │
      Success    Failure                              │
         │         │                                  │
         ▼         ▼                                  │
    Register    Circuit breaker                       │
    in registry  (2 strikes → OPEN)                   │
         │                                            │
         └──── Knowledge (Engram + JSONL) ────────────┘

  + Metrics auto-calibration (weekly)
  + Conversation memory (every session)
  + Tool discovery (weekly GitHub scan)
```

## Components

### Shared Libraries (hooks/_lib/)

| Library | Purpose |
|---------|---------|
| `safe-jsonl.sh` | flock-protected JSONL writes + hook heartbeat trap |
| `circuit-breaker.sh` | Per error_type:service circuit breaker (2 strikes, 1h cooldown, 10/hr global cap) |
| `remediation.sh` | Remediation registry: register fixes, O(1) lookup, failure tracking, garbage collection |
| `execute-repair.sh` | Worktree-isolated repair execution (deterministic + LLM paths) |

### Hooks

| Hook | Trigger | Role in MAPE-K |
|------|---------|---------------|
| `error-learning.sh` | PostToolUse/Bash | **Monitor** — captures errors to JSONL |
| `auto-repair-dispatcher.sh` | PostToolUse/Bash | **Analyze + Plan** — classifies error, looks up registry, decides action |
| `execute-repair.sh` (lib) | Called by dispatcher | **Execute** — applies fix in worktree, verifies, merges or discards |
| `remediation.sh` (lib) | Called on success/failure | **Knowledge** — updates registry with outcomes |
| `metrics-rotation.sh` | SessionStart | Prevents unbounded JSONL growth |
| `metrics-calibrator-trigger.sh` | SessionStart | Triggers weekly KPI calibration |
| `conversation-capture.sh` | Stop | Indexes session for conversation memory |
| `session-knowledge-extractor.sh` | Stop | Mines patterns from session data |
| `tool-discovery-trigger.sh` | SessionStart | Triggers weekly tool discovery scan |

### Skills

| Skill | Purpose |
|-------|---------|
| `/repair-status` | Report repair system health, circuit breaker states, registry stats |
| `/metrics-calibrator` | Analyze KPI distributions, auto-adjust thresholds, propose derived metrics |
| `/conversation-memory` | Search past sessions, surface patterns, self-referential learning |
| `/tool-discovery` | Scan GitHub for new open-source tools, classify, evaluate, propose |

### Rules

| Rule | Type | Purpose |
|------|------|---------|
| `auto-repair` | Always-active | Governs repair behavior: phase gates, circuit breaker, never-auto-repair list |
| `metrics-calibration` | Contextual | Threshold calibration protocol and derived metrics |

## Remediation Registry

The registry stores known error→fix mappings at `metrics/remediation-registry.jsonl` with an O(1) index at `metrics/remediation-index.json`.

### Entry schema
```json
{
  "id": "uuid",
  "fingerprint": "md5 of first 200 chars",
  "error_type": "BUILD|TEST|LINT|RUNTIME|INFRA",
  "service": "string",
  "error_pattern": "first 200 chars of error",
  "root_cause": "description",
  "fix_type": "command|code_change|config_change|restart",
  "fix_command": "string",
  "success_rate": 0.95,
  "times_applied": 12,
  "times_failed": 1,
  "auto_applicable": true,
  "confidence": 0.92
}
```

### Economics
- Known fix (registry hit): **0 tokens** — deterministic, instant
- Unknown fix (LLM repair): **$0.01-2.00** — async, worktree-isolated
- The registry grows over time, making more repairs free

## Circuit Breaker

| Parameter | Value | Configurable via |
|-----------|-------|-----------------|
| Max consecutive failures | 2 | `COGNITIVE_OS_CB_MAX_FAILURES` |
| Cooldown | 1 hour | `COGNITIVE_OS_CB_COOLDOWN` |
| Global hourly cap | 10 | `COGNITIVE_OS_CB_HOURLY_CAP` |

States: CLOSED (allow) → OPEN (block) → HALF-OPEN (allow 1 attempt)

## Phase Autonomy

| Phase | Code repair | LLM repair | Infra repair |
|-------|------------|------------|-------------|
| reconstruction | Yes | Yes | Yes |
| stabilization | Yes | Yes | Yes |
| production | No | No | Yes (restart, cache) |
| maintenance | No | No | Yes (restart, cache) |

## Never Auto-Repaired
- Database migrations
- Authentication/authorization changes
- Payment/billing code
- Environment variables (.env files)
- Docker compose configuration
- Git history (rebase, force push)
- Security-sensitive files
- Third-party API integration changes

## Infrastructure

### License-Safe Stack (SaaS-compatible)
| Service | License | Replaces |
|---------|---------|----------|
| Valkey 8 | BSD-3-Clause | Redis (AGPL) |
| SeaweedFS | Apache 2.0 | MinIO (AGPL) |

## Metrics & Observability

| File | Contents |
|------|----------|
| `metrics/repair-outcomes.jsonl` | All repair attempts with outcomes |
| `metrics/remediation-registry.jsonl` | Known fix database |
| `metrics/remediation-index.json` | O(1) lookup index |
| `metrics/circuit-breaker/*.json` | Per error:service breaker state |
| `metrics/hook-health.jsonl` | Hook heartbeats (exit code, duration) |
| `metrics/calibration-history.jsonl` | KPI calibration snapshots |
| `metrics/knowledge-graph.jsonl` | Cross-session pattern detections |
| `metrics/tool-discovery.jsonl` | Tool scan results |
| `transcripts/transcript-index.jsonl` | Session transcript index |

## Configuration

In `cognitive-os.yaml`:
```yaml
auto_repair:
  enabled: true
  circuit_breaker:
    max_consecutive_failures: 2
    cooldown_seconds: 3600
    global_hourly_cap: 10
  phase_gates:
    reconstruction: [code, lint, test, infra, llm]
    stabilization: [code, lint, test, infra, llm]
    production: [infra]
    maintenance: [infra]
  remediation:
    confidence_threshold: 0.8
    gc_after_days: 30
```

## Performance Characteristics

In isolated, first-time benchmarks, vanilla Claude Code can outperform Cognitive OS due to hook overhead. However, the system is designed for **total cost of ownership**, not single-shot speed.

| Scenario | Claude Code vanilla | Cognitive OS |
|---|---|---|
| 1st fix of a new error | **85s** | 109s (hook overhead ~24s) |
| 2nd fix of the SAME error | 85s (no memory) | **~10s** (registry hit, $0) |
| 10th fix of the same error | 85s × 10 = **850s, ~$5** | **~10s** (1 lookup, $0) |
| Fix in production code | Applies to main directly (risky) | **Worktree + verify first** (safe) |
| After 6 months of use | Nothing learned | **Registry with 500+ known fixes, auto-calibrating metrics** |

**The benchmark is biased toward "first time, no history."** It's like benchmarking a junior developer vs a senior on their first day — the junior might be faster because they skip safety checks, but the senior doesn't repeat mistakes.

### Cost model

```
Vanilla: N × avg_fix_time × token_cost = linear cost growth
COS:     first_fix_cost + (N-1) × registry_lookup_cost ≈ constant after learning
```

At N=10 identical errors, Cognitive OS is ~85x faster and ~50x cheaper.

### Key advantages over time

1. **Compound learning**: Every fix that succeeds gets registered. The 2nd occurrence is free ($0, ~10s).
2. **Safety**: Worktree isolation means a bad fix never touches your working branch.
3. **Circuit breaker**: After 3 failed attempts, stops trying and escalates (vanilla would keep wasting tokens).
4. **Cross-session memory**: Engram carries knowledge across sessions. Vanilla starts blind every time.
5. **Metrics**: You know your repair success rate, cost per fix, most common errors. Vanilla gives you nothing.
