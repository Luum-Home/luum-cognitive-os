# ADR-028a — Addendum: Reconciliation with pre-existing plans

**Status**: Addendum to ADR-028
**Date**: 2026-04-18
**Amends**: ADR-028 D1.A, D1.C, D4

## Why this addendum exists

ADR-028 was authored on 2026-04-17 without consulting `.cognitive-os/plans/features/self-optimizing-pipeline.md`
or the work-queue at `.cognitive-os/work-queue.json`. The reconciliation analysis (Engram #11552,
`gaps/adr-027-028-reconciliation-analysis`) identified two structural conflicts that must be resolved
before any ADR-028 execution phase begins: WS11's anti-confirmation-bias goal is left unaddressed
by ADR-028's D4 `test_run_inside_hook` fix, and ADR-028 D1.C's agent heartbeat partially overlaps
with WS13's already-committed state-snapshot heartbeat (`lib/state_heartbeat.py`, commit `65e4d0c`)
without defining consumer boundaries.

---

## 1. D4 — WS11 replacement (anti-confirmation-bias)

### Problem

ADR-028 identifies WS11's session-init pytest baseline (authored in commit `1b755cf`,
`feat(ws11): test baseline diff hook for anti-confirmation-bias`) as the direct root cause of
Bug 1 — 190 orphaned `session-init.sh` processes and 187 orphaned `pytest` processes. ADR-028
D4 includes `test_run_inside_hook` as a canonical fix class that removes pytest invocations from
hooks. Applied to `session-init.sh:120-128`, this disables WS11 entirely.

ADR-028 does not provide a replacement for the anti-confirmation-bias goal WS11 was built to
serve. That goal is documented in `self-optimizing-pipeline.md` §WS11:

> The orchestrator repeatedly assumed test failures were "pre-existing" before verifying.
> This happened 3 times in one session (+12 failures attributed to "probably pre-existing"
> when they were all ours). The orchestrator has the same minimum-output bias as sub-agents —
> quality gates must apply to the orchestrator too.

Disabling WS11 without a replacement re-opens this quality gap.

### Replacement approach

`hooks/global-verify.sh` (ADR-027 Phase 1) is the canonical landing site for test execution
removed from hooks. Its before/after diff verification model naturally satisfies the
anti-confirmation-bias requirement: when an agent claims "tests pass", `global-verify.sh`
records the before-state and the after-state, making it structurally impossible to attribute
new failures to "pre-existing" without a diff to prove it.

The replacement is a configuration decision, not a new implementation. When ADR-027 Phase 1
lands, `hooks/global-verify.sh` must be configured to:
1. Capture a pre-change test summary to `.cognitive-os/sessions/{id}/test-baseline.txt`
   (same path WS11 used — maintaining recovery path compatibility with WS13).
2. On agent completion claims, compare post-change summary against that baseline.
3. Block claims of "tests pass" when `failed_after > failed_before` or
   `errors_after > errors_before`, citing the delta explicitly.

This is behaviourally equivalent to WS11's `hooks/test-baseline-diff.sh` proposal, using
`global-verify.sh` as the executor instead of a background process in `session-init.sh`.
No orphans, no background subprocess, same guarantee.

### Amendments to ADR-028

**D4 open questions — add item 9:**

> 9\. **WS11 anti-confirmation-bias replacement.** The `test_run_inside_hook` fix for
> `session-init.sh:120-128` disables WS11 (commit `1b755cf`). Before closing Phase D, confirm
> that ADR-027 Phase 1's `global-verify.sh` is configured to capture a test baseline at session
> start and block "tests pass" claims without a before/after diff. If ADR-027 Phase 1 has not
> yet landed, add an interim advisory in `hooks/session-init.sh` pointing to this requirement.
> Self-certification without diff = anti-pattern.

**D4 acceptance criteria — add:**

> After WS11 disable lands, random sampling of 5 agent completions that include "tests pass"
> claims shows every claim accompanied by `global-verify.sh` diff output, not a bare assertion.
> If any sampled completion lacks the diff output, ADR-027 Phase 1 integration is incomplete.

### File disposition

`hooks/session-init.sh` lines 120–128: keep the block **disabled** (as done in this session).
The existing pointer comment referencing ADR-027 Phase 3 must be updated to reference this
addendum:

```bash
# WS11 baseline capture DISABLED — orphaning bug, see ADR-028 (commit 1b755cf = Bug 1 source).
# Anti-confirmation-bias goal preserved via global-verify.sh; see docs/adrs/ADR-028a.md §1.
```

Do not delete the block. Its presence as a commented-out section with explanation serves as
documentation for why `( python3 -m pytest ) &` is the canonical example of
`bg_without_pid_track` in contract tests.

---

## 2. Coordinate D1.C agent heartbeat with WS13 state-snapshot

### Two partially overlapping heartbeats

| System | File | Cadence | Consumer | Purpose |
|---|---|---|---|---|
| WS13 (committed `65e4d0c`) | `.cognitive-os/sessions/{id}/state-snapshot.json` | every 10 tool calls | `hooks/crash-recovery.sh` | Session-level state persistence — todos, active agents, decisions, pending user requests |
| ADR-028 D1.C | `.cognitive-os/tasks/{agent_id}.heartbeat` | every 60 s | `scripts/agent-watchdog.sh` (new, Phase A) | Agent liveness monitoring — detect hung agents, trigger reaper |

Both write data that could be called "heartbeat data". Neither references the other. Without
coordination, future tooling will conflate them or build parallel query paths.

### Decision: KEEP BOTH

They serve different failure modes and different consumers:

- **WS13 state-snapshot** answers "What was the session doing when it died?" — crash recovery
  after a Claude Code process crash, macOS suspend, context compaction, or user kill. Consumer
  is `crash-recovery.sh`. Granularity is session-level (all agents, all todos, all decisions).
- **ADR-028 D1.C heartbeat** answers "Is this specific agent still alive right now?" — liveness
  monitoring for in-flight agents. Consumer is `agent-watchdog.sh`. Granularity is
  per-agent (one file per `{agent_id}`).

The two mechanisms are complementary. Removing either leaves a gap:
- Remove WS13: crash recovery loses rich session state; next session starts blind.
- Remove D1.C: watchdog cannot detect hung agents; reaper cannot act on individual agents.

### Coordination required

**ADR-028 D1.C scope note (add to §D1.C before Phase A execution):**

> WS13 (`lib/state_heartbeat.py`, `hooks/state-heartbeat.sh`, committed `65e4d0c`) provides
> session-level state persistence every 10 tool calls to
> `.cognitive-os/sessions/{id}/state-snapshot.json`. This is NOT a substitute for the D1.C
> agent heartbeat. WS13 answers "what was the session doing?" (crash recovery); D1.C answers
> "is this agent alive right now?" (liveness watchdog). The two mechanisms MUST coexist.

**`hooks/auto-checkpoint.sh` docstring (add before Phase A execution):**

```bash
# Complements ADR-028 D1.C agent heartbeat; see docs/adrs/ADR-028a.md §2.
# This hook persists session-level state (WS13). D1.C writes per-agent liveness
# files under .cognitive-os/tasks/. Both are required; neither replaces the other.
```

**Canonical consumer mapping:**

| Question | Canonical answer source | File |
|---|---|---|
| "Is this session still alive?" | WS13 snapshot timestamp | `.cognitive-os/sessions/{id}/state-snapshot.json` |
| "Is agent X still running?" | D1.C heartbeat file | `.cognitive-os/tasks/{agent_id}.heartbeat` |
| "What was in progress when the session died?" | WS13 snapshot content | `.cognitive-os/sessions/{id}/state-snapshot.json` |
| "Which agents are hung right now?" | D1.C watchdog scan | all `.heartbeat` files with `last_beat` > 5 min |

`agent-watchdog.sh` (Phase A artefact) MUST NOT read `state-snapshot.json`. It reads only
`.cognitive-os/tasks/*.heartbeat`. `crash-recovery.sh` MUST NOT read `.heartbeat` files
as its primary source. It reads only `state-snapshot.json`.

---

## 3. D1.A — Rotation threshold precedence (already amended, formalized here)

ADR-027 D3 (line 215 at time of authoring) set the JSONL rotation threshold at `>2 MiB`.
ADR-028 D1.A sets it at `>1 MiB` and explicitly states it amends ADR-027's threshold.
ADR-028 D1.A is the authoritative source.

**Formal precedence declaration:** All `.cognitive-os/metrics/*.jsonl` files rotate at
**1 MiB** (size) or **7 days** (age), whichever comes first. The 1 MiB threshold supersedes
the 2 MiB figure in any earlier document, script comment, or work-queue description.

Any script, hook, or plan that references `2 MiB`, `2 * 1024 * 1024`, or `2097152` in the
context of JSONL rotation MUST be updated to `1 MiB` / `1048576` before ADR-028 Phase A exits.

Verification command (run before Phase A exit criteria are declared met):

```bash
grep -rn '2 \* 1024 \* 1024\|2097152\|2 MiB\|2MiB' \
  hooks/ lib/ scripts/ .cognitive-os/ docs/adrs/ \
  --include='*.sh' --include='*.py' --include='*.md' --include='*.json'
```

Expected result: zero matches in rotation-related context. Any match found is a Phase A blocker.

---

## 4. Work-queue coordination

Items from `.cognitive-os/work-queue.json` that overlap with ADR-028 phases, requiring
sequencing or reference updates (do not modify `work-queue.json` here — action items below):

**`smoke-test-e2e` (P3):** The work-queue item describes a full end-to-end session simulation
test. ADR-028 D6 builds a chaos engineering suite (`tests/chaos/`) with 5 targeted failure
injection tests. These share intent (does the system degrade gracefully?) but differ in scope.
`smoke-test-e2e` MUST be updated to reference ADR-028 D6 as its infrastructure — it should
consume the D6 chaos harness rather than build a parallel test harness. Sequencing: implement
after D6 lands (Phase E exit criteria met).

**`test-quality-audit` (P2):** ADR-028 D2 adds contract tests for runtime hygiene
(orphans, FDs, RAM, SLO). The work-queue item audits functional test quality — whether tests
actually exercise the code paths they claim to cover. These are different concerns. However,
running a functional test quality audit before D2's contract layer exists means auditing against
an incomplete enforcement baseline. Correct sequencing: execute `test-quality-audit` after
ADR-028 D2 lands (Phase B exit criteria met). The audit's findings on functional coverage
will then be grounded in a codebase that also passes structural contract tests.

**`os-visual-ui` (P2):** ADR-028 D1.D specifies `scripts/so-vitals.sh` as a CLI dashboard
for SO runtime hygiene. The work-queue item describes a browser-based dashboard. These are
complementary: `so-vitals.sh` is the machine-parseable source of truth; a browser UI would
consume it. No conflict, no sequencing dependency. Keep as independent deliverable.

---

## 5. Census findings (2026-04-18) — scope changes to D1.A

Metrics census (docs/reports/metrics-census.md, 447 files enumerated, 45 logical identities) produced findings that invalidate ADR-028 D1.A baseline and add new scope.

### 5.1 F-1: ADR-028 hook-health "~40% unparseable" claim is false

ADR-028 line 105-106 states hook-health.jsonl mixes `duration_ms` and `elapsed_ms` with ~40% unparseable rows. Actual state:
- 7,692 rows, 0 bad JSON
- Uniform schema `{timestamp, hook, exit_code, duration_ms}` on 100% of rows
- `elapsed_ms` field does not appear anywhere
- `safe-jsonl.sh` already standardised the schema

Action: Remove the ~40% claim from ADR-028 D1.A text. The schema drift cited as motivation for the MetricEvent migration does not exist in this file. The MetricEvent schema is still valuable (cost-events.jsonl has real drift per F-3) but the justification in ADR-028 needs updating.

### 5.2 F-3: cost-events.jsonl has real schema drift (2 incompatible shapes)

- Shape A (62%, 100 rows): {agent, estimated_cost_usd, is_estimate, model, timestamp, tokens_estimated}
- Shape B (38%, 60 rows): Shape A + {branch, change_id, session_id, sprint_id}

Cause: audit-id-enricher.sh enriches only when an active audit_id exists. Consumers silently drop missing fields.

Action: First concrete migration target for lib/metric_event.py. Define fields as Optional where Shape-B-exclusive; backfill Shape-A rows with nulls on write through MetricEvent.validate().

### 5.3 F-4: 7 files missing from disk despite active writers — D1.A.0 prerequisite

The following files are referenced by 20+ hooks and libraries but do not exist on disk:
- error-learning.jsonl (6 readers, 3 writers)
- repair-outcomes.jsonl (3 readers, 2 writers)
- remediation-registry.jsonl (3 readers, 2 writers)
- repair-queue.jsonl, repair-dispatch.jsonl
- session-audit.jsonl
- singularity-events.jsonl

Impact: auto-repair system accumulates no history; error-pattern-detector never fires; singularity never triggers; cognitive-os-health shows empty data silently.

Root cause hypothesis: `COGNITIVE_OS_SESSION_ID` is unset when the writing hooks fire, so they write to session-scoped `$SESSION_DIR/metrics/` which is never created, or `session-cleanup.sh` exits at line 23 without merging because the session directory is missing.

Scope change: Add D1.A.0 as a PREREQUISITE to D1.A. Before writing `lib/metric_event.py` or extending rotation, diagnose and fix the write path for these 7 files. Without this, the new MetricEvent schema will also never land on disk.

D1.A.0 acceptance:
- [ ] Root cause of missing-file pattern documented (likely SESSION_ID propagation)
- [ ] Fix applied (probable: writers fall back to `$PROJECT_DIR/.cognitive-os/metrics/` when `$SESSION_DIR` unset)
- [ ] All 7 files exist on disk with at least 1 row after one normal session
- [ ] Regression test: `tests/contracts/test_metric_file_existence.py` asserts each file is writable+exists

### 5.4 F-5: 5 reader-without-writer files silently zero KPIs

Files with readers but no writers anywhere in the codebase:
- trust-scores.jsonl (kpi_collector.py)
- escalation-events.jsonl (kpi_collector.py)
- coverage-history.jsonl (singularity.py)
- stale-docs.jsonl (singularity.py)
- error-skill-correlations.jsonl (learning_pipeline.py)

Impact: trust-score KPI, escalation-rate KPI, and coverage trends are permanently zero. Consumers fail silently. This means dashboards and decision systems that rely on these KPIs have been making decisions on zeroed inputs.

Scope change: Add to D1.A.0. Each file needs EITHER a writer assigned OR the read-path removed. Default action: assign owner hooks (trust-score-validator.sh exists but only logs to stderr — make it write to trust-scores.jsonl). If no writer candidate exists within D1.A.0 scope, delete the read-path to stop silent zeroing.

### 5.5 F-6: agent-bus test-e2e cleanup

309 test-e2e-{hex}/ directories accumulate indefinitely in .cognitive-os/agent-bus/. No TTL, no cleanup.

Action: Add `find .cognitive-os/agent-bus -maxdepth 1 -name 'test-e2e-*' -mtime +7 -exec rm -rf {} \;` to `hooks/rotate-metrics.sh` or `session-cleanup.sh`. Minor, include in D1.A alongside the rotation extension.

### 5.6 F-7: metrics-rotation.sh path mismatch

ADR-028 D1.A specifies archive destination `.cognitive-os/metrics/archive/`. Current hook writes to `.cognitive-os/metrics/.archive/` (dot-prefix, hidden).

Action: Align path with ADR-028 spec when extending rotation for size+age thresholds.

### 5.7 Revised D1.A scope

Original D1.A artifacts (lib/metric_event.py, rotation policy enforcement, census) are unchanged. New sub-phase:

D1.A.0 (BLOCKS D1.A.1+):
- Diagnose+fix F-4 missing files (SESSION_ID propagation or fallback path)
- Resolve F-5 reader-without-writer (assign writers or remove reads)
- Add test-e2e directory cleanup per F-6
- Align archive path per F-7

D1.A.1: lib/metric_event.py (first migration target: cost-events.jsonl per F-3)
D1.A.2: Extend rotate-metrics.sh with 1 MiB size + 7 day age thresholds
D1.A.3: Update ADR-028 text to remove F-1 claim, reference this addendum

### 5.8 References to census

- Full census: docs/reports/metrics-census.md
- Engram: adr-028/metrics-census (search for summary + recommendations)

---

## 6. References

- Engram #11552, topic `gaps/adr-027-028-reconciliation-analysis` — full reconciliation table
  covering 20 plan docs and 14 work-queue items.
- `self-optimizing-pipeline.md` §WS11 (commit `1b755cf`) — source of ADR-028 Bug 1;
  anti-confirmation-bias design intent.
- `self-optimizing-pipeline.md` §WS13 (commit `65e4d0c`) — state-snapshot heartbeat,
  `lib/state_heartbeat.py`, `hooks/state-heartbeat.sh`.
- `docs/adrs/ADR-027a.md` — sibling addendum covering the slimming reconciliation (hook
  count direction contradiction with `hook-architecture-v2.md`; EXCLUDED_RULES mechanism
  already-committed state).
- `docs/reports/metrics-census.md` — D1.A metrics census (447 files, 45 logical identities);
  source of findings F-1 through F-7 documented in §5.

---

## Action items (for orchestrator before ADR-028 execution phases launch)

- [ ] Amend `hooks/session-init.sh` comment at lines 120–128 to reference this addendum §1
      (replace current ADR-027 Phase 3 pointer with ADR-028a §1 pointer).
- [ ] Add open question #9 (WS11 anti-confirmation-bias replacement) to ADR-028 D4 before
      Phase D agent prompts are drafted.
- [ ] Add D1.C scope note (WS13 coordination paragraph) to ADR-028 §D1.C before Phase A
      execution.
- [ ] Add `# Complements ADR-028 D1.C agent heartbeat; see docs/adrs/ADR-028a.md §2` to
      `hooks/auto-checkpoint.sh` docstring.
- [ ] Update `work-queue.json` entry `smoke-test-e2e`: add `"depends_on": "adr-028-phase-e"`
      and `"rationale": "consume ADR-028 D6 chaos infrastructure, not build parallel harness"`.
- [ ] Update `work-queue.json` entry `test-quality-audit`: add `"depends_on": "adr-028-phase-b"`
      and `"rationale": "audit after structural contract test layer exists"`.
- [ ] Before Phase A exit, run the §3 verification command and resolve any matches.
- [ ] Execute D1.A.0 before D1.A.1 (MetricEvent schema): diagnose missing-file write path
      (F-4), resolve reader-without-writer files (F-5), add test-e2e cleanup (F-6), align
      archive path (F-7).
- [ ] Amend ADR-028 D1.A text to remove the ~40% unparseable claim per §5.1; update
      justification to cite cost-events.jsonl shape drift (F-3) as the concrete migration
      motivation.
