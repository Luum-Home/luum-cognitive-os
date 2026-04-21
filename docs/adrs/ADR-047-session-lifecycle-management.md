# ADR-047 — Session Lifecycle Management

## Status

Proposed — 2026-04-20. Author: Agent E (software-architect). Coordinates with
ADR-045 (hook execution model, Agent A) and ADR-046 (rule classification,
Agent B). Targets the active breach of `rules/so-slo.md` SLO 4
("0 orphans / session").

### Phase status (updated 2026-04-21)

| Phase | Status | Evidence |
|-------|--------|----------|
| Phase A (log-only) | **DELIVERED** | `lib/session_watchdog_lib.py`, `scripts/so-session-watchdog.py`, 50 unit tests pass |
| Phase B (enforce) | **BLOCKED by gate — DO NOT ENABLE** | See §"Phase B gate evaluation 2026-04-21" below |

### Phase B gate evaluation — 2026-04-21

Measured via `scripts/so-session-watchdog.py --gate-report` against
`.cognitive-os/metrics/session-watchdog.jsonl` (162 records collected
2026-04-21 14:03Z → 21:03Z).

| Gate criterion | Threshold | Observed | Pass? |
|---|---|---|---|
| False-positive rate | `< 1.00%` | **100.00%** (2/2 flagged PIDs resumed within 24h) | ❌ |
| Sample size (flagged detections) | `≥ 50` | **42 flagged records across 2 distinct PIDs** | ❌ |
| Observation span | `≥ 336 h` (2 weeks) | **7.0 h** | ❌ |

**Verdict**: Phase B enforcement **MUST NOT** activate. All three gate
criteria fail. A flagged PID re-appearing with `classification=HEALTHY`
or `cpu_percent > 0` within 24h counts as a false positive per the
definition in §"Gate metric to unlock Phase B" below; both of the two
currently-flagged PIDs meet that criterion (PID 51546 returned with
CPU=11.8%; PID 21079 oscillates between IDLE_OVER_TTL and HEALTHY on
successive scans). This is consistent with the expected Phase A behavior
on a live dev host where the operator routinely resumes sessions.

**What's needed to unblock Phase B**:

1. Run Phase A for at least 2 weeks (currently: 7 h). The ADR explicitly
   calls for "Phase A (log-only, 2 weeks)".
2. Accumulate at least 50 distinct flagged detections. The 7-hour window
   produced only 2 distinct flagged PIDs; longer observation is required.
3. The false-positive rate must drop below 1% — if 100% FP persists, the
   classifier thresholds need retuning (raise `ttl_hours` above 6h; raise
   `idle_cpu_threshold` above 5.0%) before attempting Phase B again.

**Enforcement hardening shipped 2026-04-21** (refuses Phase B while
gate fails, with or without config changes):

- `lib/session_watchdog_lib.py::compute_gate_metric()` — pure computation
  of the gate metric from a list of watchdog records.
- `scripts/so-session-watchdog.py::evaluate_gate()` — reads the live JSONL
  and returns a `GateMetric` dataclass.
- CLI: `--gate-report` (prints report, exits 2 on FAIL), `--kill-mode`
  (requests Phase B; refused with log-only fallback while gate fails).
- `run_once(config, kill_mode=True)` — evaluates the gate; on FAIL logs
  `Phase B REFUSED: ...` to stderr and falls through to log-only. Even
  if `cognitive-os.yaml` has `mode: enforce`, no kills are performed
  while the gate fails.
- 8 new unit tests in `tests/unit/test_session_watchdog.py`
  (`TestGateMetric*`, `TestLoadWatchdogJsonl`, `TestKillModeRefusal`).

**Re-evaluation protocol**: once Phase A has run for 2 weeks on a
production host, run `uv run python3 scripts/so-session-watchdog.py
--gate-report`. If the report prints `GATE: PASS`, the owner may
proceed to wire the actual kill implementation (not yet coded — the
current code only logs the refusal).

---

## Context

### Evidence of breach

- **Process list evidence (2026-04-20, macOS dev host)**: 5+ abandoned `claude`
  sessions detected, each older than 3 hours, each holding exactly one
  `engram mcp --tools=agent` child. Total engram MCP processes observed: 8+,
  contending against a single central `engram serve` daemon.
- **Diagnostic output**: `scripts/session-leak-diagnostic.sh` flags the
  orphans by command-line signature (not by interpreter path — important for
  cross-platform: `python` vs `python3`, `/opt/homebrew/bin/claude` vs
  `/usr/local/bin/claude`).
- **Metrics stream**: `.cognitive-os/metrics/session-leak.jsonl` contains one
  record per detected orphan with PID, age, ppid, command-line, and mcp-child
  count. This file IS the SLO 4 evidence ledger.
- **Test contract**: `tests/unit/test_session_leak_detection.py` — 5 tests
  pass, 1 `xfail` marker documents the active SLO 4 breach (the xfail is the
  specification of "no orphans allowed"; it flips to pass when SLO 4 is
  restored).

### Root cause (four contributing failures)

1. **Reaper blind spot** — `scripts/so-reaper.sh` only kills PIDs registered
   in `lib/process_registry.py`. Main `claude` process PIDs are **never**
   registered (the registry is for hook/subagent spawns, not for the harness
   itself). A crashed or `SIGHUP`-detached terminal leaves the main claude
   intact and unreapable.
2. **Engram MCP proliferation** — each session spawns its own
   `engram mcp --tools=agent` as a stdio child. With no shared transport,
   N sessions → N MCP children → N × heartbeat load on a single
   `engram serve` backend. Observed contention: 8+ MCP children against one
   serve daemon → lock contention on SQLite, slow `mem_search`.
3. **No hard TTL per session** — a session can live indefinitely. There is no
   "max wall-clock time" enforced anywhere; we rely on the user closing the
   tab cleanly, which silently fails on crash / `SIGKILL` / lid-close.
4. **No TTFT (time-to-first-token) watchdog** — a session stuck in an Opus
   reasoning loop with no output is invisible. The user perceives a hang, but
   supervision has no signal: no Bash call, no Agent launch, no
   `PostToolUse` event fires. The session is "alive" from the OS perspective
   and "silent" from the hook perspective simultaneously.

### Cross-reference

- `rules/so-slo.md` SLO 4, SLO 9 (heartbeat staleness) — both touched by
  this decision.
- ADR-045 (hook execution model) — defines parallelism class for new hooks.
- ADR-046 (rule classification) — new rules introduced here need tier
  assignment.

---

## Decision

Introduce a **Session Lifecycle Management (SLM) subsystem** comprising:

1. A long-running Python daemon (`scripts/so-session-watchdog.py`, psutil-based,
   cross-platform) that enforces TTL + idle heuristics + TTFT alerts.
2. A session registry (`.cognitive-os/state/sessions.jsonl`) populated by a
   new `SessionStart` hook.
3. A pair of lightweight `UserPromptSubmit`/`PreToolUse` hooks that stamp
   pending-prompt timestamps, enabling TTFT detection without modifying the
   harness.
4. A shared shell library (`hooks/_lib/portable.sh`) that standardises
   GNU-vs-BSD command drift.
5. An engram-MCP contention mitigation (semaphore, deferred shared-socket
   investigation).

Rollout is two-phase:

- **Phase A (log-only, 2 weeks)**: the watchdog observes, logs to
  `.cognitive-os/metrics/session-watchdog.jsonl`, and **never kills**.
  The gate metric (false-positive rate < 1 %, defined below) determines
  whether Phase B activates.
- **Phase B (enforce)**: auto-kill on TTL breach, with safeguards.

---

## Components

### 1. `scripts/so-session-watchdog.py` — **Phase A: DELIVERED** / Phase B: pending Phase A gate

Python 3 daemon using `psutil` (already a project dependency). Runs as a
launchd/systemd user service, or on-demand via `scripts/so-vitals.sh`
postamble.

**Responsibilities**:

- Scan every `WATCHDOG_POLL_INTERVAL_SEC` (default 60).
- Enumerate candidate sessions by:
  - Reading `.cognitive-os/state/sessions.jsonl` (registered sessions).
  - Scanning `psutil.process_iter()` for command-line signature matches
    (same heuristic as `session-leak-diagnostic.sh` — the signature list is
    extracted into `hooks/_lib/session_signatures.txt` for reuse).
- For each candidate:
  - Compute `age_sec = now - start_time`.
  - Read pending-prompt stamp from
    `.cognitive-os/state/ttft/<pid>.json` (if present).
  - Apply rules (see below).

**Rules (evaluated in order)**:

| Rule | Signal | Phase A action | Phase B action |
|------|--------|----------------|----------------|
| R1 TTL breach | `age_sec > COS_SESSION_TTL_SEC` (default 6 h) | log `ttl_breach` | kill after grace |
| R2 Idle | last_tool_event > `COS_SESSION_IDLE_SEC` (default 90 min) AND no pending prompt | log `idle_candidate` | kill after grace |
| R3 TTFT alert | pending_prompt_age > `COS_TTFT_MAX_SEC` (default 8 min) | log `ttft_alert` | alert user; do NOT kill (user may be reading) |
| R4 Orphan engram child | parent claude PID absent but `engram mcp` child alive | log `orphan_mcp` | kill orphan child only |

**Grace-period + safeguard sequence (Phase B only)** applied to R1/R2:

1. Log `kill_pending` with reason.
2. Send `SIGTERM` and start `COS_SESSION_GRACE_SEC` timer (default 30 s).
3. Apply layered activity probe (see "Liveness Signal Specification" above).
   If `all_activity_stale` is false, cancel kill and bump `ttl_reset_count`
   (max 2 per session → no infinite extensions).
   NOTE: TTY atime is NOT used — see AMENDMENT §A.
4. After grace: `SIGKILL` only if still alive.
5. Emit `killed` record to `.cognitive-os/metrics/session-watchdog.jsonl`
   with full diagnostic payload (argv, start_time, last_event, reason).

### 2. `hooks/_lib/portable.sh` — **Phase A: DELIVERED**

Mandatory for ALL new hooks. Provides these helpers, each with documented
GNU + BSD command equivalents:

| Helper | GNU command | BSD command | Fallback |
|--------|-------------|-------------|----------|
| `portable_date_minus <N> <unit>` | `date -d "-N unit"` | `date -v-Nu` (u = M/H/d) | `python3 -c "import datetime,sys;print((datetime.datetime.now()-datetime.timedelta(**{sys.argv[1]:int(sys.argv[2])})).isoformat())"` |
| `portable_sed_inplace <file> <expr>` | `sed -i -e <expr> <file>` | `sed -i '' -e <expr> <file>` | `python3 -c 'import re,sys,pathlib; p=pathlib.Path(sys.argv[1]); p.write_text(re.sub(sys.argv[2], sys.argv[3], p.read_text()))'` |
| `portable_stat_mtime <file>` | `stat -c %Y <file>` | `stat -f %m <file>` | `python3 -c 'import os,sys;print(int(os.path.getmtime(sys.argv[1])))'` |
| `portable_readlink <path>` | `readlink -f <path>` | `greadlink -f` or manual loop | `python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))'` |
| `portable_timeout <sec> <cmd>` | `timeout <sec> <cmd>` | `gtimeout <sec> <cmd>` | background + `kill` via `$!` with sleep-based reaper |
| `portable_sha256 <file>` | `sha256sum <file>` | `shasum -a 256 <file>` | `python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())'` |

The library detects the OS once (`uname -s`) and exports function bodies
that dispatch to the correct implementation. Python fallback is the
universal escape hatch — always available because psutil is already
required.

### 3. `hooks/session-ttl-register.sh` (SessionStart) — **Phase A: PENDING (deferred to Phase A follow-up PR)**

> Status: NOT YET IMPLEMENTED. Phase A currently operates via process-signature enumeration
> only (`session-leak-diagnostic.sh` heuristic). Registry-driven enumeration is a Phase A
> enhancement, not a blocker. The watchdog works without it; records just lack explicit
> `session_id` correlation.

One-shot hook on `SessionStart`. Writes a JSONL line:

```json
{"session_id":"<from env>","pid":<main_claude_pid>,"start_time":"<ISO-8601>","ttl_sec":21600,"host":"<hostname>","user":"<login>","cwd":"<pwd>"}
```

to `.cognitive-os/state/sessions.jsonl`. Uses `portable.sh` helpers.
Idempotent — if a record for this PID already exists (session resume), it
updates `last_resume_time` instead of appending.

### 4. `hooks/ttft-watchdog-prompt.sh` (UserPromptSubmit) — **Phase B scope**

> Status: NOT YET IMPLEMENTED. TTFT alerts are Phase B — they only produce value
> once the watchdog is authorized to signal the user. `hooks/session-heartbeat.sh`
> (ADR-047 Phase B liveness signal) is already delivered and writes similar state;
> the TTFT variant will reuse its directory layout.

Stamps `.cognitive-os/state/ttft/<pid>.json` with:

```json
{"prompt_submit_time":"<ISO-8601>","prompt_length":<chars>}
```

### 5. `hooks/ttft-watchdog-tool.sh` (PreToolUse, any tool) — **Phase B scope**

> Status: NOT YET IMPLEMENTED. See component 4 — paired hook.

Clears (deletes) `.cognitive-os/state/ttft/<pid>.json`. First tool call after
a prompt submit = first observable activity = TTFT satisfied.

### 6. Engram MCP contention mitigation — **Phase B scope (separate workstream)**

> Status: NOT YET IMPLEMENTED. This is an independent workstream that can proceed
> in parallel with Phase A or Phase B. Feasibility research landed in
> `docs/research/engram-mcp-sharing-feasibility-2026-04-20.md` (verdict: shared-socket
> INFEASIBLE with current binary — semaphore approach remains the chosen path).

**Decision**: adopt a **semaphore** limiting concurrent `engram mcp` children,
AND open an investigation ticket for the shared-socket approach.

**Rationale**: a shared-socket path (one `engram mcp` proxy serving all
sessions over a UNIX domain socket) is architecturally superior but
requires engram upstream to support multi-client stdio multiplexing. I did
not verify such support exists. Assuming it does would be speculation.
The semaphore is pessimistic-but-safe and shippable today; the socket
investigation is a parallel, deferrable workstream.

**Semaphore design**:

- File-based lock at `.cognitive-os/state/engram-mcp.sem` (flock).
- Wrapper script `scripts/engram-mcp-wrapper.sh` that sessions spawn
  instead of `engram mcp --tools=agent` directly.
- Wrapper waits up to `COS_ENGRAM_MCP_WAIT_SEC` (default 15) for a slot
  (max slots = `COS_ENGRAM_MCP_MAX`, default 4).
- On timeout: log `mcp_slot_denied` to
  `.cognitive-os/metrics/engram-contention.jsonl` and exit 1 — the session
  continues without engram (degraded mode) rather than blocking.
- On semaphore acquisition: exec the real `engram mcp`, holding the lock
  for the child's lifetime.

**Deferred investigation** (tracked separately, not in this ADR):
"Does engram CLI support stdio multiplexing or `--socket <path>` mode? If
yes, rewire wrapper to spawn-or-attach. Expected savings: N sessions
reduced to 1 MCP child."

---

## Phases

### Phase A — Log-only (2 weeks)

**Activates when**: `cognitive-os.yaml` gains
`runtime.session_watchdog.enabled: true` AND
`runtime.session_watchdog.mode: "log"`.

**Watchdog behaviour**: emits records to
`.cognitive-os/metrics/session-watchdog.jsonl` for every rule hit but
**never signals**. All four rules (R1–R4) evaluate; the hypothetical kill
is logged with a `would_kill: true` boolean.

**Gate metric to unlock Phase B**:

```
false_positive_rate =
    count(records WHERE reason ∈ {"ttl_breach","idle_candidate"}
                   AND session_resumed_within_24h == true)
  / count(records WHERE reason ∈ {"ttl_breach","idle_candidate"})
```

A session is "resumed" if the user issues any tool call from the same
session_id within 24 h of the log entry. The check is performed by the
Phase A review script (`scripts/session-watchdog-phase-a-report.sh`) at
the 2-week mark.

**Gate threshold**: `false_positive_rate < 0.01` (< 1 %). If the rate is
higher, re-tune the thresholds (TTL up, idle up) and re-run Phase A for
another week before considering Phase B. Ship only when the gate is clean
AND the engram-MCP contention stream shows recovery (fewer than 3 slot
denials per week).

### Phase B — Enforce

**Activates when**: `cognitive-os.yaml` sets
`runtime.session_watchdog.mode: "enforce"`. All safeguards listed below
become load-bearing.

---

## Liveness Signal Specification

> This section is the normative definition for the layered predicate used in Phase B.
> Implementation target: `scripts/so-session-watchdog.py` → `should_kill()`.
> Phase B is **blocked** until the predicate and its tests land (see acceptance criteria below).

### Kill Predicate (AND/OR composition)

```
should_kill(session) =
  parent_dead_or_orphaned(session)          # NECESSARY short-circuit
  OR
  (ttl_exceeded(session) AND all_activity_stale(session))

all_activity_stale(session) =
    heartbeat_stale(session, threshold=15min)   # PRIMARY: hook-written signal
  AND metric_writes_stale(session, threshold=5min)  # SECONDARY: defense in depth
  AND cpu_idle_sustained(session, samples=3, window_s=30, threshold_pct=5.0)  # TERTIARY
```

### Signal Rationale

| Signal | Mechanism | Rationale |
|--------|-----------|-----------|
| `parent_dead_or_orphaned` | `os.kill(ppid, 0)` → `ProcessLookupError` | POSIX-standard, 0% false positive. If Claude.app wrapper (or tmux/terminal parent) is dead, the session is orphaned by definition — nobody can see its output. Kill regardless of TTL. |
| `heartbeat_stale` | `stat(session_dir/heartbeat).mtime` | Written by `hooks/session-heartbeat.sh` on every `UserPromptSubmit` and `PreToolUse`. Directly controlled by us; deterministic; cross-platform. Missing file treated as stale. |
| `metric_writes_stale` | max mtime across `.cognitive-os/metrics/*.jsonl` | Defense in depth: if the heartbeat hook failed for any reason, other hooks (error-pipeline, auto-checkpoint, etc.) still write metrics. Freshest metrics file acts as an indirect liveness signal. |
| `cpu_idle_sustained` | `psutil.Process(pid).cpu_percent()` sampled 3× over `window_s` | Critical guard: an Opus session in a long reasoning loop may go minutes without tool calls. Without this guard, the watchdog would kill a legitimately-working session. If ANY sample exceeds `threshold_pct`, the session is NOT idle. |

### Acceptance Criteria for Phase B Activation

1. `grep -c "parent_dead_or_orphaned" docs/adrs/ADR-047-session-lifecycle-management.md` ≥ 2
2. `hooks/session-heartbeat.sh` exists, is executable, and is registered in `scripts/apply-efficiency-profile.sh`
3. `should_kill()` exported from `scripts/so-session-watchdog.py` with all 4 checks
4. All 6 new unit tests pass: `python3 -m pytest tests/unit/test_session_watchdog.py -v`
5. `SO_WATCHDOG_DRY_RUN=1` defaults to true (no actual kills in Phase A)

---

## Consequences

### Positive

- SLO 4 ("0 orphans / session") restored; the `xfail` in
  `tests/unit/test_session_leak_detection.py` flips to `pass`.
- Engram MCP contention bounded by the semaphore (max 4 concurrent
  children) → SQLite lock pressure drops.
- TTFT watchdog provides the first supervision signal for silent reasoning
  loops — a previously invisible failure class.
- `hooks/_lib/portable.sh` pays compounding dividends: every future hook
  that touches dates/files is forced to be portable.

### Negative — data-loss risk and safeguards

Killing an **active** user session = potential loss of uncommitted work
(agent transcripts, partial edits in the harness). This is the single
highest-severity risk in this ADR.

**Safeguards (all must be present in Phase B)**:

1. **Grace period**: 30 s `SIGTERM` → `SIGKILL` window (tunable via
   `COS_SESSION_GRACE_SEC`). The harness gets a chance to flush state.

2. **Layered activity probe** (replaces the original TTY-atime design;
   see AMENDMENT §A below for context). A session is considered ACTIVE
   — and therefore NOT killable — if ANY of the following three signals
   indicates recent activity, unless the session is also orphaned:

   ```
   should_kill(s) = parent_dead(s)
                OR (ttl_exceeded(s) AND all_activity_stale(s))

   all_activity_stale(s) =
         heartbeat_stale(s, threshold = 15 min)
     AND metric_writes_stale(s, threshold = 5 min)
     AND cpu_idle_sustained(s, samples = 3, threshold_pct = 5.0)
   ```

   > **CPU threshold invariant (both phases use 5.0 %)**:
   > Phase A (`classify_session`) and Phase B (`cpu_idle_sustained`) MUST use the same
   > CPU threshold, or the Phase B threshold must be lower than Phase A. Otherwise the
   > set of sessions Phase A logs as `would_kill=true` is NOT a superset of the sessions
   > Phase B would actually kill — and the false-positive gate metric measures the wrong
   > population. Unified default: **5.0 %**. Invariant asserted in
   > `test_session_watchdog.py::test_phase_a_threshold_superset_of_phase_b`.

   - **Parent-liveness probe (HARD signal)**: `kill -0 $SESSION_PPID`.
     If the Claude.app disclaimer wrapper (or tmux/terminal parent) is
     dead, the session is orphaned by definition — nobody can see its
     output. Always kill on this signal, regardless of TTL. POSIX, zero
     false-positive rate.
   - **Heartbeat file (PRIMARY)**: the new `hooks/session-heartbeat.sh`
     (registered under `UserPromptSubmit` AND `PreToolUse`) writes
     `.cognitive-os/sessions/{session_id}/heartbeat` on every user turn
     and every tool call. Watchdog stats its mtime via
     `portable_stat_mtime`. Directly controlled by us; does not depend
     on filesystem atime or TTY semantics.
   - **Metric-write freshness (SECONDARY)**: if the heartbeat hook
     failed for any reason, we fall back to the mtime of the latest
     JSONL under `.cognitive-os/metrics/*.jsonl` that this session
     wrote. Defense in depth.
   - **CPU-sustained-active (TERTIARY)**: if CPU has been > 5 % across
     the last 3 samples, the session is probably in an expensive
     reasoning or tool loop. Do NOT kill even if heartbeat is stale —
     a long Opus turn looks idle by heartbeat but is legitimately
     working. This tertiary signal prevents killing mid-reasoning.

3. **Opt-out env var**: `COS_SESSION_WATCHDOG_DISABLE=1` in the session's
   environment disables all kill actions for THAT session (logging still
   occurs). Meant for long-running research sessions.
4. **Per-session TTL-reset cap**: a session can extend its TTL at most
   2 times via continued activity, preventing runaway "immortal" sessions.
5. **Hard denial list**: any PID whose argv contains `--no-reap` or whose
   cwd matches `COS_SESSION_WATCHDOG_IGNORE_CWDS` regex is skipped.
6. **Feature flag kill-switch**: setting
   `runtime.session_watchdog.mode: "off"` in `cognitive-os.yaml` disables
   the daemon globally without redeploy.

### AMENDMENT §A — TTY atime probe invalidated (2026-04-20)

Empirical verification on macOS showed that Claude sessions spawned by
Claude.app GUI have no controlling TTY (`ps -o tty` reports `??`). Their
STDIN is a unix socket (`lsof` confirms), not a tty device with
stat-able atime. The original "TTY activity" safeguard designed for this
ADR is therefore invalid for the dominant launch mode.

The replacement is the **layered activity probe** described above, which
uses three orthogonal signals (heartbeat, metric-writes, CPU) combined
with a hard orphan signal (parent-liveness). Robustness comes from the
layered combination: each signal can fail independently without losing
the safeguard.

### Unknowns

- The 6 h TTL default is a guess without historical session-duration
  telemetry. Phase A (log-only) is intended to calibrate this; the
  `would_kill:true` rate per cohort will reveal whether 6 h is too
  aggressive. Re-evaluate before shipping Phase B.
- Engram shared-socket path is not verified. Agent F's research
  confirmed that v1.10.2 is stdio-only but the data layer is ALREADY
  shared through `engram serve`, so the per-session MCP children are
  pure OS overhead (not a data-contention problem). Orphan reaping of
  those children at session-kill time is the cheap fix. Shared-socket
  is aspirational and gated on engram v1.12.0+ exposing
  `--transport=http`.
- Heartbeat hook latency contribution: the new hook fires on every
  `UserPromptSubmit` and `PreToolUse` — Phase A must measure its p95
  latency contribution; if > 50 ms it must be demoted to Wave 3 or
  rewritten to be lock-free.

---

## Rollback

Ordered by blast radius (least-destructive first):

1. **Soft disable**: set `runtime.session_watchdog.enabled: false` in
   `cognitive-os.yaml`. Daemon stops on next reload. Hooks still register
   sessions but take no action. No code revert needed.
2. **Mode regression**: flip `mode: "enforce"` → `mode: "log"` to retreat
   to Phase A behaviour while keeping observability.
3. **Hook removal**: delete entries from `.claude/settings.json` for
   `session-ttl-register.sh`, `ttft-watchdog-prompt.sh`,
   `ttft-watchdog-tool.sh`. These hooks are idempotent and stateless — safe
   to un-register without cleanup.
4. **Semaphore bypass**: delete
   `.cognitive-os/state/engram-mcp.sem` and point sessions back at
   `engram mcp` directly (env var
   `COS_ENGRAM_MCP_WRAPPER_DISABLE=1`).
5. **Full uninstall**: delete `scripts/so-session-watchdog.py`,
   `scripts/engram-mcp-wrapper.sh`, `hooks/_lib/portable.sh`,
   hooks 3/4/5 above, and the three `runtime.*` feature flags from
   `cognitive-os.yaml`.

Each step is independently reversible. There is no schema migration — all
state lives in append-only JSONL files that can be truncated without side
effects.

---

## Regression tests

Concrete test cases, all to be placed under `tests/unit/` or
`tests/integration/` following ADR-045's parallelism class assignments.

### T1 — `test_ttl_kill_on_breach` (integration, Phase B)

Fixture: fork a process that sleeps for 2 × TTL, register it in
`sessions.jsonl` with `ttl_sec=5`. Run watchdog in enforce mode with
grace=1. Expect: PID absent from `psutil.pids()` within 10 s,
`session-watchdog.jsonl` contains one `killed` record with
`reason: "ttl_breach"`.

### T2 — `test_idle_kill_respects_grace` (integration, Phase B)

Fixture: process is idle (no `PreToolUse` events) beyond
`COS_SESSION_IDLE_SEC`. Controlling TTY is quiescent. Expect: `SIGTERM`
fires first, `SIGKILL` only fires if process ignores TERM within grace
window. `kill_pending` and `killed` records both present; `grace_honored:
true`.

### T3 — `test_ttft_alert_fires_without_kill` (unit, Phase A+B)

Fixture: stamp `.cognitive-os/state/ttft/<pid>.json` with
`prompt_submit_time` > `COS_TTFT_MAX_SEC` ago. Run watchdog. Expect:
`ttft_alert` record present in metrics, process still alive in both
modes. TTFT must NEVER kill — only alert.

### T4 — `test_portable_sh_crossplatform` (unit, always)

Parameterized over `(os, helper)` pairs. For each of the 6 helpers in
`portable.sh`, on both GNU (via docker `alpine:gnu-coreutils`) and BSD
(via host macOS or docker `bsd-minimal`), assert the helper produces the
same output for a canonical input (e.g., `portable_date_minus 2 H`
returns an ISO-8601 string dated 2 hours ago, parseable by `datetime`).
This test enforces the cross-platform invariant at CI time.

### T5 — `test_heartbeat_fresh_cancels_kill` (integration, Phase B)

DEPRECATED (TTY-based): The original T5 relied on TTY atime, which is invalid
for Claude.app sessions (see AMENDMENT §A). Replaced by:

Fixture: session breaches TTL, but heartbeat file was written within the last
5 minutes. Expect: `all_activity_stale` returns False, watchdog logs
`kill_cancelled_activity_detected`, process stays alive, `ttl_reset_count`
increments by 1. See `tests/unit/test_session_watchdog.py::test_heartbeat_fresh_prevents_kill`.

### T6 — `test_engram_mcp_semaphore_limits` (integration)

Fixture: spawn `COS_ENGRAM_MCP_MAX + 2` wrapper invocations
concurrently. Expect: first N acquire slots and spawn real MCP; last 2
log `mcp_slot_denied` and exit 1 within the wait timeout.

### T7 — `test_opt_out_env_var_honored` (unit, Phase B)

Fixture: session with `COS_SESSION_WATCHDOG_DISABLE=1` in its environ
breaches TTL. Expect: `ttl_breach` logged with `kill_suppressed: true,
reason: "opt_out"`. Process untouched.

---

## Integration with existing infrastructure

### `scripts/so-reaper.sh`

The reaper remains the authority for **registered** PIDs (hook/subagent
spawns tracked in `lib/process_registry.py`). The watchdog is the
authority for **unregistered** main-claude PIDs. They are complementary:

```
┌─────────────────────┐       ┌──────────────────────────┐
│  so-reaper.sh       │       │  so-session-watchdog.py  │
│  (SessionEnd)       │       │  (daemon, every 60 s)    │
│  kills registered   │       │  kills main claude +     │
│  hook/subagent PIDs │       │  orphan engram children  │
└─────────┬───────────┘       └────────────┬─────────────┘
          │                                │
          │  shares .cognitive-os/state/   │
          │  + metrics/*.jsonl             │
          └────────┬───────────────────────┘
                   ▼
           no overlap, no races
```

No modifications to `so-reaper.sh` itself. We add a one-line hand-off:
when the watchdog kills a main claude, it first calls `so-reaper.sh
--session <id>` to clean up that session's registered children in the
correct order.

### `lib/process_registry.py`

No API changes. The watchdog reads the registry in read-only mode to
build the "known-safe" set (registered PIDs are managed by the reaper
and skipped by the watchdog).

### `cognitive-os.yaml` — feature flags

Add to `runtime`:

```yaml
runtime:
  reaper:
    enabled: true   # existing
  session_watchdog:
    enabled: false          # new — default OFF until Phase A
    mode: "log"             # new — "log" | "enforce" | "off"
    ttl_sec: 21600          # 6 h
    idle_sec: 5400          # 90 min
    grace_sec: 30
    ttl_reset_cap: 2
  ttft_watchdog:
    enabled: false          # new — default OFF
    max_sec: 480            # 8 min
  engram_mcp:
    wrapper_enabled: false  # new — default OFF, opt-in
    max_concurrent: 4
    wait_sec: 15
```

All three new flags default OFF so the ADR is strictly additive in its
first shipping state.

### ADR-045 (hook execution model) coordination

- `session-ttl-register.sh`: `SessionStart`, **Wave 1** (Critical Barrier)
  — must complete before first prompt; fast, single JSONL append.
- `ttft-watchdog-prompt.sh`: `UserPromptSubmit` — not a SessionStart hook,
  runs per-prompt. Non-blocking (≤1 ms file write).
- `ttft-watchdog-tool.sh`: `PreToolUse` (all tools) — not a SessionStart
  hook, runs per-tool. Non-blocking (≤1 ms file delete).

Terminology aligned with ADR-045: Wave 1 (Critical Barrier), Wave 2
(Parallel Fast Group), Wave 3 (Async Deferred). Only `session-ttl-register.sh`
runs at SessionStart and thus needs a wave assignment; the TTFT hooks fire
on `UserPromptSubmit` and `PreToolUse` which are outside the SessionStart
parallelisation plan. ADR-045's SessionStart table gains one row:
`session-ttl-register.sh` → Wave 1.

### ADR-046 (rule classification) coordination

New rule documents this ADR will produce (as companions):

- `rules/session-lifecycle.md` — tier: **Always Active**
  (it governs kill authority and safeguards).
- `rules/cross-platform-shell.md` — tier: **Always Active** for any agent
  touching shell (it mandates `portable.sh` usage).
- `rules/engram-mcp-contention.md` — tier: **Contextual** (loaded only
  when engram operations are happening).

Agent B must slot these into the tier taxonomy and update
`rules/RULES-COMPACT.md` accordingly.

### Portable.sh migration list (15 existing files, priority order)

Grepping for BSD-only `date -v`, `sed -i ''`, `stat -f` signatures
produced this prioritised migration list. Each migration = replace
direct invocation with the `portable_*` helper:

| # | File | Signature found | Priority | Reason |
|---|------|-----------------|----------|--------|
| 1 | `scripts/so-reaper.sh` | `date -v`, `stat -f` | P0 | Runs every SessionEnd; wrong on Linux |
| 2 | `scripts/so-vitals.sh` | `date -v`, `stat -f` | P0 | Reports SLO metrics |
| 3 | `scripts/session-leak-diagnostic.sh` | `date -v` | P0 | This ADR's evidence source |
| 4 | `scripts/so-slo-report.sh` | `date -v` | P0 | SLO cadence tool |
| 5 | `hooks/session-end-reap.sh` | `stat -f` | P1 | Per-session, high-freq |
| 6 | `hooks/pre-compaction-flush.sh` | `date -v` | P1 | Critical safety net |
| 7 | `hooks/auto-refine.sh` | `sed -i ''` | P1 | Per-failure, high-freq |
| 8 | `hooks/state-heartbeat.sh` | `date -v` | P1 | Per PostToolUse Agent |
| 9 | `hooks/audit-id-enricher.sh` | `date -v` | P2 | Per Agent launch |
| 10 | `hooks/git-context-capture.sh` | `date -v`, `stat -f` | P2 | Stop event, lower freq |
| 11 | `hooks/session-changelog.sh` | `date -v` | P2 | Stop event |
| 12 | `hooks/metrics-rotation.sh` | `stat -f`, `find -mtime` | P2 | Rotation logic |
| 13 | `scripts/extract-agent-output.sh` | `sed -i ''` | P3 | Manual tool |
| 14 | `scripts/compose-agent-prompt.py` (shell fallback) | `sed -i ''` | P3 | Has Python path already |
| 15 | `hooks/large-file-advisor.sh` | `stat -f` | P3 | Advisory only |

Migration is mechanical: source `portable.sh`, replace the call, add a
regression row to T4. Doing this in dependency order (P0 → P3) prevents
cascading breakage on Linux VM port.

---

## Migration plan for the 5 zombie sessions currently alive

Immediate (pre-Phase-A), one-time cleanup:

1. Run `scripts/session-leak-diagnostic.sh --dry-run` and capture output
   to `.cognitive-os/metrics/session-leak-cleanup-2026-04-20.jsonl`.
2. For each zombie PID:
   - Record `argv`, `cwd`, and `start_time` in the cleanup ledger.
   - Check if any child `engram mcp` is in the middle of a
     `mem_save` (flock on SQLite db). If yes, wait up to 30 s.
   - Send `SIGTERM` to the main claude PID. Wait 30 s.
   - If still alive: `SIGKILL`.
3. Run `so-reaper.sh` with `--orphan-mcp-only` to clean residual engram
   children.
4. Verify `tests/unit/test_session_leak_detection.py` — the xfail should
   flip to pass momentarily (will flip back to xfail until Phase B
   prevents recurrence; that flip is expected and documents the gap).
5. Commit the cleanup ledger so the audit trail is preserved.

This cleanup is a **manual operator action**, not a code change. It is
explicitly scoped to this ADR's design stream.

---

## Open trade-offs (reviewer: please challenge)

- **TTL default (6 h)** vs the 24 h observed. 6 h is aggressive but matches
  the user's working-session norm; 24 h would tolerate the current
  breach. The Phase A gate metric will reveal whether 6 h is tight enough
  to hit SLO 4 without over-killing.
- **Semaphore (4) vs shared socket (1)** for engram MCP. 4 is a
  fat-fingered "enough slack for power users" number. If Phase A shows
  slot denials > 3/week, we tune up rather than jumping straight to the
  socket redesign.
- **TTFT default (8 min)** is a guess. Opus reasoning in `sdd-propose` has
  been observed to run 4-6 min silently. 8 min leaves headroom without
  masking true hangs. Revisit after Phase A data.
- **Python daemon vs shell cron** for the watchdog. Python is heavier but
  `psutil` gives us cross-platform process introspection for free; a
  shell cron implementation would re-invent it badly (and would not be
  portable per rule #4 of this ADR). Python wins on cost-of-mistakes.
