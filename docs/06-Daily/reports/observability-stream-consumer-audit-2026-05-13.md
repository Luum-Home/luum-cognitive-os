# Observability Stream-Consumer Audit — 2026-05-13

Post-mortem follow-up: `docs/06-Daily/reports/postmortem-observability-data-lake-without-consumers-2026-05-13.md` action items #7 + #8.

## TL;DR

The post-mortem said "~7 emitter streams, 1 consumer". The real numbers are far worse:

| Metric | Post-mortem estimate | Real (this audit) |
|---|---:|---:|
| Central telemetry streams (excl. per-tool agent-bus / archives) | ~7 | **194** |
| Streams with a known consumer | 1 (closure-trail) | **5 (2.6 %)** |
| Orphaned streams (no read path) | ~6 | **189 (97.4 %)** |
| Remediation queue entries | "100+ blocks" | **12 505 (72 blocks, 12 433 warns)** |
| Distinct finding codes in queue | n/a | 21 |
| Single audit dominating the queue | n/a | `subprocess-run-without-timeout` → **12 013 of 12 505 entries (96 %)** — noise audit |
| Total data lake size | n/a | **99 MB across 844 files** (counting per-tool agent-bus dirs) |

## 1. Stream-consumer matrix (central streams only)

### Streams WITH a known consumer (5 / 194 = 2.6 %)

| Stream | Records | Consumer |
|---|---:|---|
| `.cognitive-os/audit/closure-trail.jsonl` | varies | `session-wrapup` projector (manual operator invocation only) |
| `.cognitive-os/metrics/hook-timing.jsonl` | 74 444 | ADR-304 aggregator + `scripts/hook_timing_report.py` (manual) |
| `.cognitive-os/metrics/startup-benchmark.jsonl` | small | `tests/unit/test_startup_budget.py` (when pytest runs) |
| `.cognitive-os/metrics/agent-spawn-benchmark.jsonl` | small | `tests/unit/test_agent_spawn_budget.py` (ADR-303) |
| `.cognitive-os/metrics/llm-routing.jsonl` | varies | ADR-304 aggregator |
| `.cognitive-os/metrics/llm-dispatch.jsonl` | varies | ADR-304 aggregator (added by SLO manifest) |

### Top-15 ORPHANED streams (no consumer at all — sample of 189)

| Stream | Records | Size | What it should fund |
|---|---:|---:|---|
| `.cognitive-os/metrics/hook-health.jsonl` | 19 256 | 1.9 MB | hook reliability SLO |
| `.cognitive-os/runtime/processes.jsonl` | 12 045 | 3.8 MB | orphan process detection (ADR-279 exists; not wired to this stream) |
| `.cognitive-os/sessions/events.jsonl` | 11 687 | 4.8 MB | session-level analytics; nothing reads |
| `.cognitive-os/metrics/lethal-trifecta.jsonl` | 5 144 | 1.7 MB | safety incident telemetry |
| `.cognitive-os/metrics/tool-sequences.jsonl` | 5 023 | 1.3 MB | sequence-pattern mining for skill discovery |
| `.cognitive-os/metrics/agent-trajectory.jsonl` | 5 015 | 1.4 MB | agent decision telemetry |
| `.cognitive-os/metrics/aci-observations.jsonl` | 5 015 | 11.3 MB | autonomous-context-injection observations |
| `.cognitive-os/metrics/skill-archive.jsonl` | 4 503 | 1.2 MB | skill churn |
| `.cognitive-os/metrics/consequence-history.jsonl` | 4 503 | 1.2 MB | post-action outcome telemetry |
| `.cognitive-os/metrics/cwd-enforcer.jsonl` | 4 391 | 0.4 MB | cwd-violation rate |
| `.cognitive-os/metrics/agent-heartbeat.jsonl` | 3 784 | 1.0 MB | agent-liveness signal |
| `.cognitive-os/metrics/session-watchdog.jsonl` | 3 417 | 1.3 MB | session-timeout detection |
| `.cognitive-os/metrics/context-watchdog.jsonl` | 3 145 | 0.3 MB | context-bloat detection |
| `.cognitive-os/metrics/aspirational-audit.jsonl` | 2 500 | 0.9 MB | ADR-031 audit (the audit-side equivalent of this whole audit) |
| `.cognitive-os/metrics/license-audit-trivy-*.jsonl` | 2 500 | small | license scan history (timestamped per run — accumulating) |

Each represents a feature ADR that emitted but did not consume. The pattern is endemic.

## 2. Remediation backlog triage

`.cognitive-os/tasks/control-plane-remediation.jsonl` has **12 505 entries** total since 2026-05-11. All are status `queued` — none have been actioned.

### By severity

| Severity | Count |
|---|---:|
| block | 72 |
| warn | 12 433 |

### By finding code (top 10 = 99 % of the queue)

| Code | Count | Audit |
|---|---:|---|
| `subprocess-run-without-timeout` | **12 013** | subprocess-timeout-coverage |
| `operational-guide-missing` | 196 | operational-guide-coverage |
| `adr-partial-missing-remaining` | 130 | adr-partial-lifecycle |
| `accepted-adr-uncovered` | 29 | capability-coverage |
| `registration-checker-classification-disagreement` | 26 | primitive-coherence |
| `operational-guide-partial` | 22 | operational-guide-coverage |
| `unaudited-closure` | 21 | closure-trust-signal |
| `unclassified-unregistered-hook` | 19 | primitive-coherence |
| `adr-partial-close-candidate` | 16 | adr-partial-lifecycle |
| `adr-partial-stale-without-followup` | 9 | adr-partial-lifecycle |

### Diagnosis

**One audit (`subprocess-timeout-coverage`) produces 96 % of all remediation entries.** Almost all are warns (12 013 vs 72 blocks). This pattern is what makes the queue useless as a signal — the loud-warn audit drowns out the 72 block findings that actually need attention.

Recommended actions in priority order:

1. **Snooze the `subprocess-run-without-timeout` audit OR move it from per-run write to per-quarter snapshot.** It generates 12 013 duplicate-ish entries that nobody reads.
2. **Resolve the 72 `block` findings** — these are the real backlog.
3. **Add a `cos-remediation-queue` skill** that buckets the queue by code, suppresses duplicates by `stable_id`, and presents the operator a triage view. The raw JSONL is unreadable at 12 k entries.

## 3. Post-mortem action item update

| # | Action | Original estimate | Real scope |
|---|---|---|---|
| 1 | Telemetry Aggregator | "all .jsonl streams" | 194 central streams + 650 per-tool agent-bus = 844 files |
| 7 | Per-stream consumer audit | done in post-mortem? | done HERE (this doc) |
| 8 | Pre-existing remediation backlog triage | "100+ findings" | 12 505 entries; 72 blocks; one audit emitting 96 % of entries |
| (new) | Audit-noise suppression | not listed | Rate-limit / dedup the `subprocess-timeout-coverage` audit before any aggregator can produce signal-from-noise |

## 4. Coverage delta after ADR-304

ADR-304 added 3 named consumers via SLO manifest (`session-start-blocking-total`, `llm-dispatch-success-ratio`, `skill-enrichment-success-ratio`) and 2 declared-but-no-data SLOs (`subagent-spawn-p95/p99`). Effective coverage:

- Pre-ADR-304: 5 / 194 streams (2.6 %)
- Post-ADR-304: ~8 / 194 streams (4 %)
- After landing the no-data SLO fix: ~10 / 194 (5 %)

The structural fix isn't "add another consumer per stream" — it's a CONSUMER CONTRACT for the next feature ADR: any new emitter must declare its consumer in the same commit, or the stream gets garbage-collected.

Proposed: `manifests/observability-emitter-contracts.yaml` — every `.jsonl` path under `.cognitive-os/` must appear with a declared consumer (or `transient: true` for short-lived per-tool streams). A hook `telemetry-orphan-stream-detect.sh` refuses commits that introduce a new `.jsonl` not declared in the manifest. ADR-306 candidate.

## Related

- `docs/06-Daily/reports/postmortem-observability-data-lake-without-consumers-2026-05-13.md` (the parent post-mortem)
- ADR-028 — SLO catalogue (declares; rarely enforces)
- ADR-031 — Continuous aspirational/dormant/real audit (`.cognitive-os/metrics/aspirational-audit.jsonl` is orphaned)
- ADR-086 — Hook execution observability (emitter side of `hook-timing.jsonl`)
- ADR-247 — Postmortem regression audit (this audit eventually feeds that)
- ADR-275 — Closure & projection primitives (the one functional pre-existing consumer)
- ADR-304 — Telemetry Aggregator (just landed; adds 3 consumers)
- ADR-306 candidate — Observability emitter contracts (gate new `.jsonl` paths on declared consumer)
