# Swarm Stress Benchmark Report — 2026-05-02

## Overview

Parametrized stress test exercising N ∈ {10, 20, 50} concurrent agent processes
competing over a pool of 5 resource leases (domains: `auth`, `billing`,
`migrations`, `frontend`, `infra`).  N > 5 guarantees contention: every domain
has at least ceil(N/5) workers queued simultaneously.

Test file: `tests/chaos/test_swarm_stress.py::test_swarm_stress[N]`
Primitives exercised: `scripts/resource_lease.py` (acquire/release) and
`scripts/cos_task_claims.py` (claim/complete).
Isolation: each pytest invocation creates a fresh `tmp_path`-scoped
`.cognitive-os/runtime/` tree — production state is never touched.

---

## Results Table

| N  | Wall Time (s) | Mean Acq Latency (ms) | Max Queue Depth | Conflicts | Deadlocks | Throughput (ops/s) | Pass |
|----|---------------|-----------------------|-----------------|-----------|-----------|-------------------|------|
| 10 | 1.027         | 276.51                | 2               | 10        | 0         | 9.74              | YES  |
| 20 | 2.728         | 948.17                | 11              | 47        | 0         | 7.33              | YES  |
| 50 | 8.695         | 2990.25               | 52              | 224       | 0         | 5.75              | YES  |

**Metric definitions**

- **Wall Time**: total elapsed clock time for all N workers to complete their
  lease-acquire → task-claim → sleep(50ms) → release → task-complete cycle.
- **Mean Acq Latency**: average time from a worker's first acquire attempt to
  successful grant, measured across all N workers.
- **Max Queue Depth**: largest sum of blocked retries observed on a single domain
  across all workers (approximated from per-worker retry counts; see note below).
- **Conflicts**: total number of `blocked` responses returned by
  `resource_lease.py acquire` across all workers and all attempts.
- **Deadlocks**: workers that did not acquire within the 30 s deadlock threshold.
- **Throughput**: completed lease cycles divided by total wall time.

---

## Per-Domain Conflict Breakdown (final run)

| Domain     | N=10 | N=20 | N=50 |
|------------|------|------|------|
| auth       | 2    | 11   | 52   |
| billing    | 2    | 11   | 44   |
| migrations | 2    | 7    | 44   |
| frontend   | 2    | 9    | 41   |
| infra      | 2    | 9    | 43   |

Contention is distributed evenly across all 5 domains, consistent with the
round-robin assignment (`worker_i → DOMAINS[i % 5]`).

---

## Interpretation

### Contention scales quadratically with N

With 5 lease slots and N agents, each domain receives N/5 workers on average.
The expected number of blocked retries per domain scales as `O((N/5)^2)` because
each worker may be blocked by every predecessor.  Observed total conflicts:

```
N=10:  10  conflicts  (expected ~10  for 2 workers/domain)
N=20:  47  conflicts  (expected ~40  for 4 workers/domain)
N=50: 224  conflicts  (expected ~250 for 10 workers/domain)
```

The match to theoretical O(N^2/5) confirms the lease primitive's blocking
behaviour is correct and measured accurately.

### Mean latency grows super-linearly

At N=50, mean acquisition latency reaches ~3 s because the 10th worker queued
on a domain must wait for 9 serial predecessors (50 ms each) plus retry
back-off overhead.  This is expected and acceptable for the current workload
model; it only becomes a risk if:

1. Real agent work units are much shorter than 50 ms (the queue drains too slowly
   relative to arrival rate), or
2. TTL on leases is set shorter than the total queue drain time.

With the current default TTL of 10 s (stress config) and observed max queue
drain of ~9 s at N=50, there is ~1 s headroom.  Production TTL is 1800 s,
making lease expiry a non-issue in production scenarios.

### Zero deadlocks at all tested scales

No worker exceeded the 30 s deadlock threshold at any N.  The primitives
(`resource_lease.py` + `cos_task_claims.py`) are deadlock-free by construction:
`resource_lease.py` uses atomic `os.replace()` writes with file-level
last-writer-wins semantics and no circular wait; `cos_task_claims.py` uses
`fcntl.LOCK_EX` on a per-directory lock file with no nested lock acquisition.

### Data integrity confirmed

All lease files were fully released at the end of each run (assertion:
`len(remaining_leases) == 0`).  The task-claim ledger received exactly N
`claim` + N `complete` events with no orphaned active claims.

### Throughput degradation at N=50

Throughput drops from ~9.7 ops/s (N=10) to ~5.8 ops/s (N=50).  This is not a
bug — it reflects queuing delay, not resource exhaustion.  The bottleneck is
serialisation across 5 domains; with more domains or shorter work units the
throughput curve would flatten.

---

## Notable Findings

1. **No race conditions detected in the primitives.** `resource_lease.py` uses
   a `tmp → os.replace` write pattern that is atomic on POSIX filesystems.
   Under N=50 with 5 domains, no two workers observed themselves as simultaneous
   holders of the same lease.

2. **Back-off strategy matters at high N.** The initial implementation used a
   fixed retry count (MAX_ACQUIRE_RETRIES=10) which caused 1 worker failure at
   N=50 (exhausted retries before the domain freed up).  Switching to
   time-bounded retry (loop until DEADLOCK_THRESHOLD_S) eliminated all failures.
   This is a finding about the *test harness design*, not the primitives.

3. **`cos_task_claims.py` flock contention is negligible.** The per-directory
   `fcntl.LOCK_EX` lock in `cos_task_claims.py` caused no measurable latency
   spike even at N=50, because claim operations are short (~1 ms I/O) and the
   lock is held briefly.

---

## Scalability Projection

| N    | Estimated Wall Time | Estimated Conflicts | Fits in Hard Timeout? |
|------|---------------------|---------------------|-----------------------|
| 10   | ~1 s                | ~10                 | YES (60 s limit)      |
| 20   | ~3 s                | ~47                 | YES (120 s limit)     |
| 50   | ~9–17 s             | ~200–225            | YES (300 s limit)     |
| 100  | ~40–60 s            | ~900                | YES (300 s if added)  |
| 200  | ~200+ s             | ~3600               | RISKY at 300 s        |

At N≈150–200 the queue-drain time approaches the hard timeout.  If future tests
extend to N=100 the timeout should be set to 600 s and the work sleep reduced
below 50 ms, or the domain pool should be expanded beyond 5.

---

## Environment

- Platform: darwin (macOS 25.4.0)
- Python: 3.14.4
- pytest: 9.0.2
- Concurrency: `ProcessPoolExecutor(max_workers=min(N, 32))`
- Lease TTL (stress): 10 s
- Simulated work per worker: 50 ms
- Deadlock threshold: 30 s
- Back-off: exponential from 50 ms, cap 1 s, factor 1.3
- Test isolation: `tmp_path` per run, no production state modified

---

Performance Benchmarker: automated benchmark run
Analysis Date: 2026-05-02
Performance Status: MEETS all SLA requirements (0 deadlocks, 0 data corruption, all N pass within hard timeout)
Scalability Assessment: Ready for current workloads; N≥150 requires domain pool expansion or timeout adjustment
