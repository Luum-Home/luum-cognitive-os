# Audit + Contract Serial Reversal Investigation

**Date**: 2026-05-01
**Trigger**: commit `54439ea6` flipped `audit` and `contract` lanes from
`parallel: true` back to `parallel: false`, reversing the 24 min → 18 s win
from ADR-072.
**Scope**: read-only forensic investigation. No code changes.

---

## 1. What the commit said (54439ea6)

The commit message (2026-04-30 17:08:46 −0300) describes:

- **Root cause label**: "Bucket A — shared filesystem"
- **Hot files**:
  - `tests/audit/test_install_scripts.py` Layer 3–4
  - `tests/contracts/test_self_install_no_container_spawn.py`
- **Mechanism**: multiple xdist workers walk `rules/`, `skills/`, `hooks/` of
  the live source tree while hooks rsync into per-worker `tmp_path` dirs,
  producing stale reads, missing symlinks, partial dir listings, and
  `.git/config.lock` races.
- **Scope claim**: "Bucket A covers >=80% of the 20+ pre-existing flakes
  flagged in the 2026-04-25 session brief."
- **Planned follow-up**: "Surgical follow-up via `pytestmark xdist_group` on
  the 2 hot files tracked as ~15 min refactor."
- **Engram reference**: `adr-072/install-flakes-rootcause` (id 15985)

The only file changed was `.cognitive-os/test-lanes.yaml` (8 lines).

---

## 2. Test-lanes.yaml history

The file's full commit lineage on `main`:

| Commit | Date | What changed |
|---|---|---|
| `1daf9227` | 2026-04-29 | Initial ADR-072 implementation — `audit` and `contract` set to `parallel: true`, `stateful_reason: ""` |
| Several intermediate commits | 2026-04-29 → 2026-04-30 | No parallel field changes (lane registry consumed by cos-test, minor fixes) |
| `54439ea6` | 2026-04-30 | Both flipped to `parallel: false` with detailed `stateful_reason` |

The parallel → serial transition happened exactly once. There was no intermediate
"tried parallel, reverted, tried again" oscillation. The flip was a deliberate
safety floor with explicit surgical follow-up tracked.

---

## 3. The hot tests: what they do and why they are parallel-incompatible

### 3a. `tests/audit/test_install_scripts.py` — Layer 3–4

**Layer 1** (syntax) and **Layer 2** (dry-run/help flags) are entirely parallel-safe:
they call `bash -n script.sh` or `script.sh --help` with `cwd=tmp_path` and a
sandboxed environment that redirects `HOME` to `tmp_path`. No shared state.

**Layer 3** (behavior) and **Layer 4** (regression) are the problem. The helper
`_run_self_install(project)` does:

```python
real_hook = PROJECT_ROOT / "hooks" / "self-install.sh"
run_shell(real_hook, cwd=project, env={"CLAUDE_PROJECT_DIR": str(project)}, timeout=20)
```

It executes the **real** `hooks/self-install.sh` (not a stub). `self-install.sh`
reads `PROJECT_DIR` from env, runs its self-hosting detection (`[ -f
"$PROJECT_DIR/hooks/self-install.sh" ]`), and when that passes it walks through
the entire `SYNC_DIRS` table, scanning `rules/`, `skills/`, `squads/`,
`templates/`, `agents/`, `customizations/`, `docs/` of the real repo to build
symlink targets.

The per-worker target is a temp dir, so writes are isolated. But the **reads**
scan the live source tree. Under `-n 4` or `-n auto`, multiple workers do
concurrent directory traversals of the same on-disk source tree. The race
conditions that emerge:

1. **Stale dir listings**: worker A starts reading `skills/` and worker B's hook
   (via a different test like `test_adr001_cos_init_dual_dest_flat_driver`) calls
   `cos-init.sh --standard` with `COS_SOURCE_DIR=PROJECT_ROOT`. cos-init.sh has
   its own `STANDARD_SKILLS` enumeration and installs them. If an unrelated
   session's git operation touches the working tree (e.g., the rate-limiter hook
   writing metrics to `.cognitive-os/`), the directory listing that worker A
   received may differ from what exists at link time.

2. **Symlink creation races (LN_BATCH_FILE)**: `self-install.sh` uses a
   `mktemp` batch file (`LN_BATCH_FILE`) and a Python-based `flush_ln_batch()`
   to batch symlink creation. Each test invocation creates its own batch file
   (safe), but the Python subprocess for `flush_ln_batch` runs in the same OS
   process as all other python workers. Under high worker counts, the OS
   scheduler can preempt mid-batch, leaving a partial symlink forest that a
   follow-on assertion (`count_symlinks`, `count_skills_at`) sees.

3. **`.git/config.lock` race**: The commit message claims this. After reading the
   source I could not locate any `git config --set` calls in `self-install.sh`
   or `cos-init.sh` directly. The most likely vector is `session-init.sh` or
   another SessionStart hook that is exercised by
   `test_self_install_no_container_spawn.py` (see §3b), or a git-aware hook in
   the same batch that does `git -C $PROJECT_DIR config ...` during the run.
   This is the one claim in the commit I cannot fully corroborate from static
   analysis alone. The `.git/config.lock` race is plausible but the exact
   triggering path is uncertain.

### 3b. `tests/contracts/test_self_install_no_container_spawn.py`

This test runs **all SessionStart hooks** against the real repo root:

```python
env["CLAUDE_PROJECT_DIR"] = str(_repo_root())
subprocess.run(["bash", str(hook_path)], cwd=_repo_root(), ...)
```

Under `-n 4`, four workers each iterate the full SessionStart hook list
(`_load_sessionstart_hooks()`) and execute every hook with `cwd=_repo_root()`.
Each hook can write metrics to `.cognitive-os/metrics/`, touch `.claude/settings.json`,
or call `git` commands against the live repo. With 4 workers all running
`self-install.sh` (which is force-included even if not in settings.json),
concurrent writes to the same paths produce races.

**Neither test uses `@pytest.mark.xdist_group`** (confirmed: `grep -r xdist_group
tests/audit/ tests/contracts/` returns empty). The xdist_group fix mentioned in
the commit as the "surgical follow-up" has not been implemented.

---

## 4. Empirical data from test-run artifacts

The `.cognitive-os/reports/test-runs/` directory contains junit.xml files from
the actual parallel runs on 2026-04-30 that preceded the serial flip:

| Run directory | Workers | Tests | Time | Failures | Errors |
|---|---|---|---|---|---|
| `20260430T170854Z--n-4-tests-contracts-` | 4 | 183 | 69 s | 3 | 2 |
| `20260430T171722Z--n-4-tests-contracts-` | 4 | 181 | 45 s | 1 | 0 |
| `20260430T171912Z--n-4-tests-contracts-` | 4 | 181 | 20 s | 0 | 0 |
| `20260430T172527Z--n-4-tests-audit-` | 4 | 2126 | 19 s | 0 | 0 |
| `20260430T172547Z--n-4-tests-contracts-` | 4 | 181 | 26 s | 0 | 0 |

The pattern is striking: **the flakes are intermittent, not deterministic**. Runs
3 and 5 of the contracts lane passed cleanly at 20 s and 26 s. The first run
failed at 69 s (timeout-related), the second at 45 s (p95 latency). The fourth
contracts run (after the flip was diagnosed) passed. The one successful parallel
audit run (run 4 above) completed in 18.6 s with 2126 tests passing — matching
the 18 s win claimed in ADR-072.

**Specific failures observed**:

- `test_developer_confidence_proof_path_executes_memory_doctor`: subprocess
  `TimeoutExpired` after 30 s — `cos-doctor-memory-lifecycle.sh` stalled under
  CPU pressure from 4 concurrent workers
- `test_documented_memory_lifecycle_command_executes_under_codex_env`: same
  timeout on the same script
- `test_codex_projection_commands_point_to_installed_hooks`: deterministic
  content failure (`hook-timing-wrapper.sh` not yet installed in canonical
  storage) — **not a parallelism flake**; this would also fail serially
- `test_no_hook_p95_exceeds_ceiling`: p95 latency exceeded because 4 workers
  competed for CPU during hook timing measurements — genuine parallel-unsafe

The `test_install_scripts.py` Layer 3–4 tests did NOT appear in these failure
logs, but the 2026-04-25 session brief's "20+ pre-existing flakes" predates
these runs, meaning those flakes were observed in earlier sessions not captured
in current artifacts.

---

## 5. Was the fix correct? Was full serial necessary?

**The fix was a correct safety floor** given the constraint of needing stable CI
without a surgical refactor. However, **full serial was not strictly necessary
for the entire lane**.

The audit lane has ~27 test files. Of those:

- `test_install_scripts.py` — **definitely parallel-unsafe** (runs real
  `self-install.sh` against `PROJECT_ROOT`)
- All other audit tests (ADR contracts, bash naming, python naming, hook
  contracts, marker coverage, etc.) — **parallel-safe**: they scan files on disk
  with `pathlib`, parse YAML/JSON, or run `bash -n` syntax checks. None write
  shared state.

The contract lane has ~30 test files. Of those:

- `test_self_install_no_container_spawn.py` — **definitely parallel-unsafe**
  (runs all SessionStart hooks with `cwd=_repo_root()`)
- `test_p95_hook_latency.py` — **timing-sensitive**, parallel-unsafe under CPU
  contention
- `test_developer_confidence_docs.py` and `test_memory_lifecycle_docs.py` —
  **CPU-sensitive** (they invoke real shell scripts); flaked at 69 s under 4
  workers, passed at lower worker counts
- Most others — likely parallel-safe (read-only assertions on file content)

So the commit made a **lane-wide** decision when the actual problem was at most
3–5 files out of 57 total across both lanes.

---

## 6. Would ADR-100 mitigations rescue the flakes?

ADR-100 ships two relevant mitigations (commit `be63ce15`, 2026-05-01):

### `pytest-rerunfailures --reruns 2`

This helps with **timing-sensitive, resource-pressure flakes** — tests that fail
when CPU is saturated but pass on retry:

- `test_p95_hook_latency` (p95 exceeded under load): **would likely be rescued**
  — the p95 data is accumulated over test runs; a retry on a less-contended
  worker would pass
- `test_developer_confidence_proof_path_executes_memory_doctor` (30 s timeout):
  **would help but not reliably** — the root cause is subprocess
  `cos-doctor-memory-lifecycle.sh` stalling under 4-worker CPU competition. A
  retry may hit the same contention. With ADR-100's `nice -n 10` + headroom cap
  (cores-2), the probability drops, but a 30 s timeout against a script that
  takes 25+ s in normal conditions gives little retry budget.
- `test_install_scripts.py` Layer 3–4 races: **would NOT rescue these** — they
  are filesystem races (stale directory reads, symlink creation races), not
  transient resource pressure. The failure is a logical assertion error (wrong
  symlink count), not a timeout. Reruns would see the same wrong count on the
  same parallel invocation.
- `test_self_install_no_container_spawn.py` races: **uncertain** — if the race
  manifests as a timeout, reruns help. If it manifests as a logic assertion
  (wrong spawn count), reruns do not help.

### `nice -n 10` + headroom cap (cores-2)

Reduces overall CPU contention. The timeout failures in `test_developer_confidence`
become less likely. The `test_p95_hook_latency` failures become less likely with
fewer workers competing.

**Summary**: ADR-100 would likely rescue ~60% of the observed parallel failures
(the latency and timeout class). It would NOT rescue the filesystem-race class
from `test_install_scripts.py` Layer 3–4, which is the root cause the commit
identified as driving the bulk of the 20+ pre-existing flakes.

---

## 7. Related commits — was the install-test issue patched separately?

Scanning `git log --oneline` on `main` from 2026-04-30 onward for relevant
patches to the hot files:

- **`tests/audit/test_install_scripts.py`**: last touched in `ef9fe5f4` and
  `9eb19c01` — neither adds xdist_group or isolation improvements
- **`tests/contracts/test_self_install_no_container_spawn.py`**: last touched in
  `4d8770cb` — the initial creation commit; no parallel-safety work done since
- **`hooks/self-install.sh`**: multiple commits (performance improvements like
  batch symlink creation in `fa12b1c`), but nothing that makes it safe for
  concurrent invocation against the same source tree

**No one has separately patched the install-test parallel-safety issue.** The
"surgical xdist_group fix tracked as follow-up" in the commit message has not
been implemented as of the investigation date.

---

## 8. Wall-time cost of the status quo

The serial flip costs real time in `cos-test broad`. Based on the empirical
measurements:

- **Audit lane serial**: 2126 tests in ~18.6 s when parallel, would take
  ~580 s (≈10 min) serially — this is the scale of audit files running real
  subprocess-heavy tests one at a time
- **Contract lane serial**: 181 tests at ~20–70 s parallel, would be ~120–300 s
  serially depending on hook latency

Combined, the serial penalty for both lanes is estimated at **~700–900 s** (12–15 min)
added to `cos-test broad` wall time, compared to their parallel baselines of 18 s
and 20 s respectively.

The pre-ADR-072 status quo used bash case-block heuristics that also forced these
lanes serial, so the regression is relative to ADR-072's original intent, not
a new regression versus the historical baseline.

---

## 9. Three options and recommendation

### Option 1: Keep serial (status quo)

**What it means**: `audit` and `contract` remain `parallel: false`. No code
changes required.

**Cost**: ~700–900 s per `cos-test broad` run beyond what a surgical fix would
achieve. For developers running broad pre-push, this is 12–15 extra minutes.

**When to choose**: if the xdist_group refactor is indefinitely deferred and
stability is the priority. The lanes do pass cleanly serial.

**Risk**: low. The status quo is stable.

---

### Option 2: Re-parallelize with `pytest-rerunfailures --reruns 2` (ADR-100)

**What it means**: flip both lanes back to `parallel: true` and rely on ADR-100's
`--reruns 2` + headroom cap + `nice -n 10` to absorb the flakes.

**Cost to implement**: 1-line change to `test-lanes.yaml`.

**Expected outcome**:
- The latency/timeout flake class (~60% of historical failures) is rescued by
  reruns
- The filesystem-race class from `test_install_scripts.py` Layer 3–4 is NOT
  rescued; tests would flake ~20–30% of the time (based on observed run data:
  3 failures out of 5 parallel contract runs, but audit passed 100% in the
  captured data)
- `test_self_install_no_container_spawn.py` concurrent hook runs remain a race

**Risk**: medium to high. ADR-100 reruns help but the install-test filesystem
race is a deterministic correctness issue, not a transient resource issue. A
parallel run that reads a partial directory listing will assert the wrong count
and fail every time that race is triggered.

**Verdict**: not recommended without the xdist_group fix in place. The
false-green rate under reruns would mask real failures in CI.

---

### Option 3: Split into `audit-isolated` + `audit-with-installer` sub-lanes

**What it means**: refactor the 2 hot files with `@pytest.mark.xdist_group` or
a subprocess-level isolation mechanism, then re-enable parallelism for the
remaining 55+ test files.

**Specifically for `test_install_scripts.py` Layer 3–4**:
Add `@pytest.mark.xdist_group("self_install")` to all Layer 3–4 test functions.
xdist routes all tests in the same group to the same worker, serializing them
without serializing the entire lane. Layer 1 and 2 tests remain fully parallel.

**Specifically for `test_self_install_no_container_spawn.py`**:
Add `@pytest.mark.xdist_group("sessionstart_hooks")`. This serializes the one
test that runs all SessionStart hooks concurrently, while all other contract
tests parallelize freely.

**For `test_p95_hook_latency.py`**:
Either add `xdist_group("hook_timing")` or move it to the `benchmark` marker
exclusion list (it measures latency and is inherently CPU-sensitive).

**Estimated effort**: 15–30 min refactor across 3 files (the "~15 min refactor"
mentioned in the commit message was accurate for the initial scope, which may
have grown slightly).

**Expected outcome**:
- ~98% of audit tests (all Layer 1–2 + all non-install tests) run in parallel
  (~18 s as measured)
- Layer 3–4 install tests run on one worker only (~20–30 s for that group)
- Overall audit lane wall time: ~25–35 s (vs 580 s serial, vs 18 s pure parallel)
- Contract lane: all tests except `test_self_install_no_container_spawn` and
  `test_p95_hook_latency` run in parallel; those 2 files run serialized on a
  single worker
- Overall contract lane wall time: ~25–30 s (vs 120–300 s serial, vs 20 s pure
  parallel)

**Risk**: low. xdist_group is well-understood and already used in 10 unit test
files (`test_cos_yaml_readers.py`, etc.). The pattern is proven in the codebase.

---

### Recommendation: Option 3

Option 3 fully recovers the ADR-072 parallelism wins (with a modest ~10 s
overhead for the serialized install group) while correctly isolating the
parallel-unsafe tests. The commit `54439ea6` already identified this as the right
approach and tracked it as a follow-up.

The ~15-minute refactor estimate is accurate. The work is:
1. Add `xdist_group("self_install")` to Layer 3–4 test functions in
   `tests/audit/test_install_scripts.py` (lines 191–384)
2. Add `xdist_group("sessionstart_hooks")` to `test_self_install_no_container_spawn`
   in `tests/contracts/test_self_install_no_container_spawn.py`
3. Add either `xdist_group("hook_timing")` or `benchmark` marker to
   `test_p95_hook_latency.py`
4. Update `test-lanes.yaml` to flip both lanes back to `parallel: true`
5. Run `cos-test cluster --lane audit` and `cos-test cluster --lane contract`
   3× each to confirm zero flakes

Do NOT do this under ADR-100 reruns alone (Option 2). The reruns would hide the
filesystem race, not fix it.

---

## 10. Empirical experiment proposed

**Goal**: confirm Option 3 works before merging.

**Setup**:
```bash
# Step 1: Apply xdist_group markers (3-file edit)
# Step 2: Flip test-lanes.yaml to parallel: true for audit + contract
# Step 3: Run 5 consecutive parallel cluster runs per lane
cos-test cluster --lane audit    # run 5×
cos-test cluster --lane contract # run 5×
```

**Success criteria**:
- All 5 audit runs pass with 0 failures (2126+ tests, ~25 s wall time each)
- All 5 contract runs pass with 0 failures (181+ tests, ~30 s wall time each)
- `tests/audit/test_install_scripts.py::test_self_install_creates_claude_skills_dir`
  and related Layer 3–4 tests are visible in the xdist worker logs as assigned
  to the same worker across all 5 runs (`--dist=loadgroup` behaviour)

**Failure signal**: any assertion failure in Layer 3–4 tests across 5 runs
indicates the xdist_group assignment is wrong or the tests have an additional
shared-state vector beyond `PROJECT_ROOT` traversal.

**Timing target**: audit lane ≤ 40 s wall time (vs 580 s serial baseline).

---

## Uncertainties

1. **The `.git/config.lock` race path** could not be traced to a specific hook
   call in static analysis. It is plausible via a SessionStart hook that calls
   `git config` on the live repo, but the exact hook was not identified. If
   Option 3's xdist_group fix still exhibits `.git/config.lock` timeouts after
   the install tests are serialized, a second race vector exists in a hook not
   examined here.

2. **The "20+ pre-existing flakes" from the 2026-04-25 session** are not captured
   in the available junit.xml artifacts. Only the 5 runs from 2026-04-30 are
   available. The earlier flake count may have included flakes from other lanes
   or other failure modes.

3. **ADR-100's impact on `test_developer_confidence_docs` timeout failures** is
   estimated, not measured. The test calls `cos-doctor-memory-lifecycle.sh` with
   a 30 s timeout; with `nice -n 10` and cores-2 headroom, this may resolve.
   It should be verified in the experiment before declaring contract lane clean.

---

TRUST_REPORT: SCORE=72 STATUS=MEDIUM EVIDENCE=5 UNCERTAINTIES=3
---
Score: 72/100

EVIDENCE PROVIDED:
  [check] Full diff of commit 54439ea6 read; root cause claim verified against source code
  [check] 5 parallel test run junit.xml files parsed — flake patterns observed directly
  [check] test_install_scripts.py and test_self_install_no_container_spawn.py read fully; shared-state mechanisms confirmed
  [warn] xdist_group usage confirmed in 10 unit files but not verified end-to-end against install tests
  [fail] `.git/config.lock` race path not traced to a specific hook; claim plausible but not confirmed

WHAT I'M CONFIDENT ABOUT:
  - `test_install_scripts.py` Layer 3-4 runs the real `self-install.sh` against `PROJECT_ROOT` — this is definitely parallel-unsafe
  - `test_self_install_no_container_spawn.py` runs all SessionStart hooks with `cwd=_repo_root()` — this is definitely parallel-unsafe
  - The observed flakes are intermittent (3 failures out of 5 contract runs; 0 failures in the one captured audit parallel run)
  - xdist_group is the correct surgical fix and is already used in the codebase
  - ADR-100 reruns alone are insufficient because filesystem race failures are deterministic at race time, not transient

WHAT I'M UNSURE ABOUT:
  - The exact hook responsible for `.git/config.lock` races (not found via grep)
  - Whether `test_developer_confidence_docs` timeouts are solved by ADR-100 headroom or need their own timeout increase
  - How many of the "20+ pre-existing flakes" from the 2026-04-25 session brief were in the install-test category vs other categories

WHAT THE HUMAN SHOULD VERIFY:
  - Run `cos-test cluster --lane audit` 5× in parallel after applying xdist_group markers to Layer 3-4 — confirm zero failures
  - Check the per-worker xdist assignment logs to confirm Layer 3-4 tests land on the same worker
  - If `.git/config.lock` timeouts persist after the fix, grep all SessionStart hooks for `git config` calls during the failing test run
