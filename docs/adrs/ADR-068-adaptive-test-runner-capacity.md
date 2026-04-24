# ADR-068: Adaptive Test Runner Capacity Detection

## Status

**Proposed** — 2026-04-24. Implementation tracked separately as Phase 1 (see §8).

## Context

Today (2026-04-24), the shard-B test suite was launched without `-n auto` and ran serially.
Result: **21 minutes wall-clock vs. ~9 min baseline** with `pytest-xdist`'s `-n auto`. The
operator caught the regression at ~95% completion. Root cause: the human invocation forgot
the flag, and `scripts/pytest-with-summary.sh` does not choose a parallel mode by default —
it forwards whatever arguments arrive.

The hidden assumption in the current design is that every operator and every agent will
remember to pass `-n auto`. Reality, demonstrated today: forgotten. Twelve minutes of wall
clock burned for a single mistake that the wrapper could have prevented automatically.

Operator framing (Spanish, verbatim):

> "hay una forma de determinar segun la carga de la compu (cross-devices) si puede correr
> en paralelo o secuencial y que ajuste los argumentos segun ese dato?"
>
> "procede asi"

The constraint set is broader than "always parallelize":

- **Cross-platform**: macOS (operator's primary device), Linux (CI runners), Windows
  (potential future contributors). The detection helper must not assume POSIX-only APIs.
- **Battery awareness**: a laptop on low battery should NOT burn all cores for a quick
  test loop. UX courtesy, also thermal hygiene on Apple Silicon.
- **Container/CI awareness**: dedicated runners are usually small (2–4 vCPU) but they
  have nothing else competing — paralelo conviene casi siempre, even on a 2-core box.
- **Operator override**: any heuristic must be overridable. When the operator knows
  better than the heuristic (debugging, profiling), they need a one-line escape.

This ADR documents the policy. The implementation lands in a separate session per Phase 1.

## Decision — Adaptive heuristic table

The load-bearing artifact of this ADR. Conditions are evaluated **top-to-bottom; first
match wins**. A 2-core machine on full battery still gets `0` (serial), not `auto`,
because the cores-≤-2 row triggers first.

| # | Condition | Workers | Rationale |
|---|---|---|---|
| 1 | Cores ≤ 2 | `0` (serial) | Parallel overhead (worker startup, IPC, result collection) dominates per-test cost on tiny machines |
| 2 | `load_pct > 70%` (heavy work elsewhere) | `2` | Don't compound contention — leave headroom for whatever else is running |
| 3 | `mem_available < 2 GB` | `4` (cap) | Each pytest-xdist worker uses ~50–100 MB; OOM risk if we let `auto` pick 16 |
| 4 | Battery present AND `battery < 30%` AND not plugged in | `0` (serial) | Heat + drain on laptop; UX courtesy more than performance |
| 5 | `env CI=true` | `auto` | Dedicated runner, paralelo siempre vale, even on 2 vCPUs |
| 6 | Default (cores ≥ 4, load < 30%, no battery issue, not CI) | `auto` | Maximum throughput on a healthy dev machine |

Note row 5 (CI) intentionally appears *after* the resource-constraint rows. If the CI box
is somehow under 70% load from another tenant, row 2 fires first. CI containers are
usually idle when the test step starts, so in practice row 5 wins on runners.

**Threshold reasoning** (each number is defensible, not arbitrary):

- **Cores ≤ 2**: empirical xdist overhead is ~1–2 s of fixed cost per worker plus IPC
  per test boundary. On 2 cores, that overhead exceeds the savings for our suite size
  (~few hundred unit tests). Verified loosely; can be re-tuned with Phase 2 metrics.
- **load_pct > 70%**: the OS scheduler starts thrashing well before 100%. 70% gives
  enough headroom for whatever else is running (a backgrounded build, a dev server)
  without starving it.
- **mem_available < 2 GB**: pytest-xdist workers fork the parent's memory. Combined
  with imports (anthropic SDK, psutil, etc.) each worker realistically uses 50–100 MB.
  Capping at 4 keeps total worker memory ≤ 400 MB, leaving ~1.6 GB for the test
  process itself plus headroom.
- **battery < 30% AND not plugged in**: 30% is the "user-visible warning" threshold
  on most OSes. Below that, users feel time pressure; we shouldn't compound it with
  thermal throttling from a parallel test run.

## Decision — Override semantics

Operator must always be able to force a value. Precedence (highest first):

1. Explicit `-n` flag in the user's pytest command line — **always wins**
2. `COS_PYTEST_WORKERS` environment variable
3. Heuristic table (§3)
4. Default `auto`

| Env var value | Effect |
|---|---|
| `COS_PYTEST_WORKERS=auto` | Force `-n auto`, skip detection entirely |
| `COS_PYTEST_WORKERS=0` | Force serial (no `-n` flag added) |
| `COS_PYTEST_WORKERS=N` (integer) | Force exactly `-n N` |
| `COS_PYTEST_WORKERS=detect` (or unset) | Run heuristic table |

Rationale for the `0` semantic: pytest-xdist treats `-n 0` and "no `-n` flag at all" the
same way (serial). Choosing the absent-flag form keeps the command line minimal in logs.

## Decision — Cross-platform implementation

`psutil` is the cross-platform abstraction. The detection helper falls back gracefully
when capabilities are missing.

| Capability | macOS | Linux | Windows | Fallback when missing |
|---|---|---|---|---|
| CPU count | `os.cpu_count()` | `os.cpu_count()` | `os.cpu_count()` | None needed (always works) |
| Available memory | `psutil.virtual_memory().available` | same | same | If psutil missing → assume 8 GB |
| Load average | `os.getloadavg()` | `os.getloadavg()` | `psutil.cpu_percent(interval=1)` | psutil first, then assume 0% load |
| Battery | `psutil.sensors_battery()` | same (where available) | same | None → assume desktop (no battery row triggers) |
| CI environment | `os.environ.get('CI')` | same | same | Standard convention across runners |

If `psutil` is not installed, the helper falls back to a "best-effort" mode: detect cores,
default to `auto`, log a warning. Tests must NOT block on a missing dep — this is a
performance helper, not a correctness gate.

## Decision — Where the detection lives

- **`scripts/detect_runner_capacity.py`** (new). Self-contained Python helper.
  - Stdin: nothing.
  - Stdout (default): a single token — `auto`, `0`, or an integer like `4`.
  - Stdout (`--json`): full diagnostics dict (cores, mem, load, battery, ci, chosen,
    rule_fired) for debugging and post-hoc analysis.
  - Exit code: 0 on success; non-zero only on hard failures (e.g., Python broken). A
    missing `psutil` is a soft warning, not an error.
- **`scripts/pytest-with-summary.sh`** (edit). If the user's args do NOT contain `-n` or
  `--numprocesses`, call `detect_runner_capacity.py` and prepend `-n <value>` (or
  nothing, if the value is `0`) to the pytest invocation.
- **Logging**: each detection run appends to
  `.cognitive-os/metrics/test-runs/<timestamp>/capacity.json`. Schema includes detected
  values, chosen workers, and which rule fired. Enables post-hoc analysis: "are we
  hitting row 4 too often? Should the battery threshold be 25% instead of 30%?"

The split between scalar-stdout (default) and JSON-stdout (`--json`) keeps the bash
consumer trivial — a single `$(...)` substitution — while preserving rich diagnostics
for whoever debugs an unexpected workers choice. This mirrors ADR-066's prescription:
narrow stdout contract for callers, structured detail behind a flag for humans.

## What we replicate / what we don't

**Replicate**: the bash → python boundary contract from ADR-066. The script outputs a
scalar to stdout for trivial bash consumption; richer diagnostics live behind a `--json`
flag. Exit code signals errors, not policy decisions.

**Don't replicate**: a generic "adaptive resource manager" abstraction. Scope is pytest
only. Other tools (cos-init, dispatch, sdd-apply) may benefit later, but adding
capacity-awareness everywhere now is overkill — premature generalization. Phase 4
(below) handles the eventual extraction once a second consumer actually exists.

## Implementation phases

The actual implementation is out of scope for this ADR. This is the sketch:

| Phase | Scope | Cost estimate |
|---|---|---|
| 1 | `scripts/detect_runner_capacity.py` + `pytest-with-summary.sh` edits + 5 unit tests covering the heuristic table | ~30 min |
| 2 | Capacity logging to `.cognitive-os/metrics/test-runs/.../capacity.json` + a small dashboard viewer (read-only) | ~30 min |
| 3 | Cross-platform CI: add a Windows runner job that exercises the Windows fallback path (no `os.getloadavg`) | ~60 min |
| 4 | Generalize: extract the detection into `lib/runner_capacity.py` for reuse by other tools (cos-init, dispatch). Only do this once a second real consumer exists. | future |

**Phase 1 is the only deliverable for the immediate operator request.** Phases 2–4 are
queued, not committed. The split is deliberate: Phase 1 fixes today's specific pain
(forgotten `-n` flag) with the smallest viable code change; later phases earn their
keep only if real data shows them necessary.

**Out-of-scope for all phases**:
- Changing pytest-xdist itself (we consume it as-is)
- Choosing test selection (which tests run) — that's a different policy
- Cross-machine distribution via xdist `--tx` (we set worker count, not topology)
- Adaptive timeouts or retries (separate concern, separate ADR if needed)

## Consequences

**Positive**:
- Today's 21-minute incident becomes preventable for any operator or agent invoking the
  wrapper script — no need to remember `-n auto`.
- Battery-aware courtesy: laptops on low battery don't get hammered for a quick test run.
- Cross-platform-ready: psutil abstracts away macOS/Linux/Windows differences, with
  graceful fallbacks when dependencies are absent.
- Logged diagnostics enable evidence-based threshold tuning instead of guesswork.

**Negative**:
- Adds `psutil` as a (likely already transitive) dependency. The helper degrades
  gracefully without it, but the production path assumes it's installed.
- Detection adds ~50 ms to every pytest invocation. Worth it: today's mistake was
  12 minutes. The amortized math is overwhelmingly favorable, but this is a real cost.
- One more script to maintain. Mitigated by tight scope — pytest only, no abstraction
  yet — and by Phase 1 unit tests covering each heuristic row.

**Neutral**:
- Doesn't change WHICH tests run — only how many workers execute them. Test outcomes
  remain deterministic regardless of detected capacity. (Test order under xdist is
  already non-deterministic; that's an existing property, unchanged.)

## Alternatives rejected

1. **"Just always use `-n auto`"**. Broken on 2-core CI runners (parallel overhead >
   benefit) and on battery-drained laptops (heat + drain UX problem). Also masks
   contention when the box is already under load.
2. **"Always use `-n 0` (serial)"**. This is exactly what we did today, by accident.
   Costs ~12 minutes per shard-B run. The pain that triggered this ADR.
3. **"Hardcode `-n 8`"**. Arbitrary. Fails closed on 4-core machines (oversubscription)
   and fails open on 32-core machines (massive throughput left on the table). No way
   to be right on a heterogeneous device fleet.
4. **"Make operators always pass `-n` explicitly"**. Doesn't scale. Today's bug is the
   proof: a competent operator forgot it once, cost 12 minutes. Multiply by every
   future operator and every future agent that wraps pytest. The wrapper exists
   precisely to encode defaults — adding "remember the flag" to the human checklist
   is the opposite of what wrappers are for.
5. **"Use a third-party adaptive plugin (pytest-xdist already has `--tx` schemes)"**.
   Overkill. pytest-xdist's `--tx` is for distributing across machines (ssh, popen
   targets), not for choosing a worker count. The load-balancing inside xdist assumes
   you've already picked a worker count — which is the actual decision we're making.

## Verification

- `python3 scripts/detect_runner_capacity.py` outputs a single token (e.g., `auto`,
  `0`, `4`) — usable directly in bash command substitution.
- `python3 scripts/detect_runner_capacity.py --json` outputs a full diagnostics dict
  with at least: `cores`, `mem_available_gb`, `load_pct`, `battery_pct`, `on_ac`,
  `ci`, `workers`, `rule_fired`.
- `bash scripts/pytest-with-summary.sh -- tests/unit/ -q` (without `-n`) automatically
  receives `-n auto` on a healthy laptop, and `-n 0` on a stress-tested machine. The
  decision is logged.
- Phase 1 unit tests cover at minimum: 2-core case, low-memory case, on-battery-low
  case, `CI=true` case, and the default healthy-machine case.
- Override env var: `COS_PYTEST_WORKERS=4 bash scripts/pytest-with-summary.sh ...`
  produces `-n 4` regardless of detected state.
- Explicit `-n` flag wins over env var: `COS_PYTEST_WORKERS=4 bash
  scripts/pytest-with-summary.sh -- -n 8 tests/unit/` produces `-n 8`.

## Related

- ADR-066 (polyglot language boundaries — bash↔python boundary contract this ADR
  follows)
- `rules/python-naming.md` (snake_case for `detect_runner_capacity.py`)
- `scripts/pytest-with-summary.sh` (the wrapper being upgraded in Phase 1)
- Today's 21-minute shard-B incident — see engram topic
  `bugfix/post-refactor-cleanup-2026-04-24` (cleanup commits in flight as agent
  `a994bc70` at the time of writing)

## Open questions

1. **Should `--json` mode be the default and scalar mode the explicit option?** Default
   is scalar today so the bash consumer is a one-liner: `WORKERS=$(python3
   detect_runner_capacity.py)`. Flip the default if the dashboard (Phase 2) becomes
   load-bearing for daily use. Not worth changing now.
2. **How to handle Docker `cgroups` CPU quotas?** `os.cpu_count()` reports the host CPU
   count from inside a container, ignoring cgroup quotas. A 2-vCPU container on a
   32-core host will see 32 and try to spawn 32 workers. Defer until a real CI failure
   forces it; the standard fix is to read `/sys/fs/cgroup/cpu.max` and clamp.
3. **Battery awareness on M1/M2 Macs.** Does `psutil.sensors_battery()` return sensible
   values from Apple Silicon power management? Manual testing suggests yes, but Phase 3
   should explicitly verify on at least one M1/M2 machine. If broken, we fall back to
   "no battery detected" gracefully, which is the right failure mode.
4. **Should the heuristic learn from history?** Phase 2 logs every decision; in
   principle we could feed that into the next decision (e.g., "last 5 runs at this
   capacity took 8 minutes; are we sure parallel is winning?"). Defer until we have
   weeks of data — premature optimization until the simple table proves insufficient.
5. **Interaction with `pytest -x` (fail fast).** Should the heuristic prefer serial
   when fail-fast is on, since parallel makes the "first failure" point fuzzy? Probably
   yes, but waiting on a real complaint before adding a row.
